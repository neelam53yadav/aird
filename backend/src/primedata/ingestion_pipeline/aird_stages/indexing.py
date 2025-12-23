"""
AIRD indexing stage for PrimeData.

Ports AIRD FAISS indexing logic to Qdrant, with metadata tracking.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger

from primedata.ingestion_pipeline.aird_stages.base import AirdStage, StageResult, StageStatus
from primedata.services.vector_metadata import create_document_metadata, create_vector_metadata
from primedata.indexing.qdrant_client import qdrant_client
from primedata.indexing.embeddings import EmbeddingGenerator
from primedata.services.trust_scoring import get_scoring_weights


def load_metrics_index(metrics: List[Dict[str, Any]]) -> Dict[str, Dict]:
    """
    Build lookups from metrics:
      - by_chunk[(file, chunk_id)] -> score
      - by_chunk_any[chunk_id] -> score (file-agnostic fallback)
      - by_section[(file, section)] -> score
      - by_file[file] -> max score
    """
    idx = {"by_chunk": {}, "by_chunk_any": {}, "by_section": {}, "by_file": {}}
    
    if not metrics:
        logger.warning("No metrics provided — scores will default to 0.0")
        return idx
    
    for m in metrics:
        file = m.get("file")
        score = float(m.get("AI_Trust_Score", 0.0))
        cid = m.get("chunk_id")
        sec = m.get("section")
        
        if file and cid:
            idx["by_chunk"][(file, cid)] = score
        if cid:
            idx["by_chunk_any"][cid] = score
        if file and sec:
            idx["by_section"][(file, sec)] = score
        if file:
            idx["by_file"][file] = max(score, idx["by_file"].get(file, 0.0))
    
    return idx


def lookup_score(
    metrics_idx: Dict[str, Dict],
    file_name: str,
    rec: Dict[str, Any],
    alt_files: List[str],
) -> float:
    """Find the best available score for a record using multiple fallbacks."""
    cid = rec.get("chunk_id")
    sec = rec.get("section")
    
    # 1) exact file+chunk
    if cid and (file_name, cid) in metrics_idx["by_chunk"]:
        return metrics_idx["by_chunk"][(file_name, cid)]
    
    # 2) try alternate file tags (jsonl/json/txt)
    for f in alt_files:
        if cid and (f, cid) in metrics_idx["by_chunk"]:
            return metrics_idx["by_chunk"][(f, cid)]
        if sec and (f, sec) in metrics_idx["by_section"]:
            return metrics_idx["by_section"][(f, sec)]
    
    # 3) chunk-only fallback
    if cid and cid in metrics_idx["by_chunk_any"]:
        return metrics_idx["by_chunk_any"][cid]
    
    # 4) section/file or file-only fallback
    if sec and (file_name, sec) in metrics_idx["by_section"]:
        return metrics_idx["by_section"][(file_name, sec)]
    
    return metrics_idx["by_file"].get(file_name, 0.0)


class IndexingStage(AirdStage):
    """Indexing stage that embeds chunks and stores them in Qdrant with metadata."""
    
    @property
    def stage_name(self) -> str:
        return "indexing"
    
    def get_required_artifacts(self) -> list[str]:
        """Indexing requires processed JSONL files and metrics."""
        return ["processed_jsonl", "metrics_json"]
    
    def execute(self, context: Dict[str, Any]) -> StageResult:
        """Execute indexing stage.
        
        Args:
            context: Stage execution context with:
                - storage: AirdStorageAdapter
                - processed_files: List of processed file stems
                - scoring_result: Optional result from scoring stage
                
        Returns:
            StageResult with indexing metrics
        """
        started_at = datetime.utcnow()
        storage = context.get("storage")
        processed_files = context.get("processed_files", [])
        
        if not storage:
            return self._create_result(
                status=StageStatus.FAILED,
                metrics={},
                error="Storage adapter not found in context",
                started_at=started_at,
            )
        
        if not processed_files:
            # Try to get from previous stage
            preprocess_result = context.get("preprocess_result")
            if preprocess_result and preprocess_result.get("processed_file_list"):
                processed_files = preprocess_result["processed_file_list"]
            else:
                self.logger.warning("No processed files to index")
                return self._create_result(
                    status=StageStatus.SKIPPED,
                    metrics={"reason": "no_processed_files"},
                    started_at=started_at,
                )
        
        self.logger.info(f"Starting indexing for {len(processed_files)} files")
        
        # Get database from context (should be provided by get_aird_context)
        db = context.get("db")
        if not db:
            from primedata.db.database import SessionLocal
            db = SessionLocal()
            close_db = True
        else:
            close_db = False
        
        try:
            # Load metrics for score lookup
            metrics = storage.get_metrics_json()
            metrics_idx = load_metrics_index(metrics) if metrics else {}
            
            # Get embedding generator from product config or use default
            from primedata.db.models import Product
            product = db.query(Product).filter(Product.id == self.product_id).first()
            if not product:
                if close_db:
                    db.close()
                return self._create_result(
                    status=StageStatus.FAILED,
                    metrics={},
                    error=f"Product {self.product_id} not found",
                    started_at=started_at,
                )
                
            # Get embedding config
            embedding_config = product.embedding_config or {}
            model_name = embedding_config.get("embedder_name", "minilm")
            dimension = embedding_config.get("embedding_dimension", 384)
            
            # Initialize embedding generator
            embedder = EmbeddingGenerator(model_name=model_name, dimension=dimension)
            actual_dimension = embedder.get_dimension()
            
            # Create Qdrant collection
            collection_name = f"ws_{self.workspace_id}__prod_{self.product_id}__v_{self.version}"
            
            if not qdrant_client.is_connected():
                return self._create_result(
                    status=StageStatus.FAILED,
                    metrics={},
                    error="Qdrant client not connected",
                    started_at=started_at,
                )
            
            qdrant_client.ensure_collection(collection_name, actual_dimension)
            
            # Process all files
            all_points = []
            doc_meta_objs = []
            vec_meta_objs = []
            total_chunks = 0
            
            for file_stem in processed_files:
                try:
                    # Load processed JSONL
                    records = storage.get_processed_jsonl(file_stem)
                    if not records:
                        self.logger.warning(f"Processed JSONL not found for {file_stem}, skipping")
                        continue
                    
                    processed_file = f"{file_stem}.jsonl"
                    alt_files = [processed_file, f"{file_stem}.json", f"{file_stem}.txt"]
                    
                    # Process each record
                    for rec in records:
                        if not isinstance(rec, dict):
                            continue
                        
                        text = rec.get("text", "")
                        if not text.strip():
                            continue
                        
                        # Extract metadata
                        chunk_id = rec.get("chunk_id") or f"{file_stem}_{rec.get('section', 'general')}"
                        section = rec.get("section", "general")
                        field_name = rec.get("field_name", section)
                        page = rec.get("page")
                        document_id = rec.get("document_id") or rec.get("doc_scope") or file_stem
                        tags = rec.get("tags", "")
                        
                        # Lookup score
                        score = lookup_score(metrics_idx, processed_file, rec, alt_files)
                        
                        # Generate embedding
                        embedding = embedder.embed(text)
                        embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
                        
                        # Create Qdrant point ID (use chunk_id hash for uniqueness)
                        import hashlib
                        point_id_str = f"{self.product_id}_{chunk_id}_{self.version}"
                        point_id = int(hashlib.md5(point_id_str.encode()).hexdigest()[:15], 16)
                        
                        # Create Qdrant point
                        point = {
                            "id": point_id,
                            "vector": embedding_list,
                            "payload": {
                                "chunk_id": chunk_id,
                                "filename": processed_file,
                                "document_id": document_id,
                                "page": page,
                                "section": section,
                                "field_name": field_name,
                                "score": score,
                                "text": text[:500],  # Store first 500 chars for preview
                                "source": rec.get("source", "internal"),
                                "audience": rec.get("audience", "unknown"),
                                "timestamp": rec.get("timestamp", datetime.utcnow().isoformat()),
                                "product_id": str(self.product_id),
                                "index_scope": str(self.product_id),
                                "doc_scope": document_id,
                                "field_scope": field_name,
                                "tags": tags,
                            }
                        }
                        all_points.append(point)
                        
                        # Create document metadata
                        doc_meta = create_document_metadata(
                            db=db,
                            product_id=self.product_id,
                            version=self.version,
                            chunk_id=chunk_id,
                            score=score,
                            source_file=processed_file,
                            page_number=page,
                            section=section,
                            field_name=field_name,
                            extra_tags={"tags": tags} if tags else None,
                        )
                        doc_meta_objs.append(doc_meta)
                        
                        # Create vector metadata
                        vec_meta = create_vector_metadata(
                            db=db,
                            product_id=self.product_id,
                            version=self.version,
                            collection_id=collection_name,
                            chunk_id=chunk_id,
                            page_number=page,
                            section=section,
                            field_name=field_name,
                            tags={"tags": tags} if tags else None,
                        )
                        vec_meta_objs.append(vec_meta)
                        
                        total_chunks += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to process {file_stem}: {e}", exc_info=True)
                    continue
            
            if not all_points:
                return self._create_result(
                    status=StageStatus.FAILED,
                    metrics={},
                    error="No points to index",
                    started_at=started_at,
                )
            
            # Upsert to Qdrant
            success = qdrant_client.upsert_points(collection_name, all_points)
            if not success:
                return self._create_result(
                    status=StageStatus.FAILED,
                    metrics={},
                    error="Failed to upsert points to Qdrant",
                    started_at=started_at,
                )
            
            # Commit metadata to database
            db.commit()
            
            finished_at = datetime.utcnow()
            
            # Calculate aggregate trust score
            scores = [p["payload"]["score"] for p in all_points]
            avg_trust_score = round(sum(scores) / len(scores), 4) if scores else 0.0
            
            metrics_result = {
                "collection_name": collection_name,
                "points_indexed": len(all_points),
                "doc_metadata_count": len(doc_meta_objs),
                "vec_metadata_count": len(vec_meta_objs),
                "avg_trust_score": avg_trust_score,
            }
            
            return self._create_result(
                status=StageStatus.SUCCEEDED,
                metrics=metrics_result,
                started_at=started_at,
                finished_at=finished_at,
            )
                
        except Exception as e:
            self.logger.error(f"Indexing failed: {e}", exc_info=True)
            return self._create_result(
                status=StageStatus.FAILED,
                metrics={},
                error=str(e),
                started_at=started_at,
            )
        finally:
            if close_db:
                db.close()

