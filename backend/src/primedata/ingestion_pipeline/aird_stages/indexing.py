"""
AIRD indexing stage for PrimeData.

Ports AIRD FAISS indexing logic to Qdrant, with metadata tracking.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from primedata.indexing.embeddings import EmbeddingGenerator

# Metadata is now stored in Qdrant payload - no PostgreSQL metadata tables needed
from primedata.indexing.qdrant_client import qdrant_client
from primedata.ingestion_pipeline.aird_stages.base import AirdStage, StageResult, StageStatus
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

            # Initialize embedding generator with workspace context for API keys
            embedder = EmbeddingGenerator(model_name=model_name, dimension=dimension, workspace_id=self.workspace_id, db=db)
            actual_dimension = embedder.get_dimension()

            # Check if we're using hash-based fallback (which won't give good semantic search results)
            model_info = embedder.get_model_info()
            if model_info.get("fallback_mode"):
                self.logger.error(
                    f"CRITICAL: Embedding model {model_name} is using hash-based fallback. "
                    f"Semantic search will NOT work correctly - results will be random. "
                    f"Check that the API key is configured for OpenAI models or sentence_transformers is installed."
                )
                # Still proceed but log the issue prominently
            else:
                self.logger.info(
                    f"Embedding model {model_name} loaded successfully. "
                    f"Model type: {model_info.get('model_type', 'unknown')}, "
                    f"Dimension: {actual_dimension}"
                )

            # Create Qdrant collection name using product name for better readability
            self.logger.info(f"Product name from database: '{product.name}'")
            sanitized_product_name = qdrant_client._sanitize_collection_name(product.name)
            self.logger.info(f"Sanitized product name for collection: '{sanitized_product_name}'")
            collection_name = f"ws_{self.workspace_id}__{sanitized_product_name}__v_{self.version}"
            self.logger.info(f"Creating Qdrant collection: '{collection_name}'")

            if not qdrant_client.is_connected():
                return self._create_result(
                    status=StageStatus.FAILED,
                    metrics={},
                    error="Qdrant client not connected",
                    started_at=started_at,
                )

            collection_created = qdrant_client.ensure_collection(collection_name, actual_dimension)
            if not collection_created:
                if close_db:
                    db.close()
                return self._create_result(
                    status=StageStatus.FAILED,
                    metrics={},
                    error=(
                        f"Failed to create Qdrant collection '{collection_name}'. "
                        f"This usually indicates a Qdrant server resource limit issue (check 'too many open files' in Qdrant logs). "
                        f"Ensure Qdrant container has ulimits.nofile set to at least 65536."
                    ),
                    started_at=started_at,
                )

            # Process all files - collect all records first, then batch-embed
            all_records_data = []  # Store record data for batch processing
            total_chunks = 0
            import hashlib

            # First pass: Collect all records and their metadata
            for file_stem in processed_files:
                try:
                    # Load processed JSONL
                    records = storage.get_processed_jsonl(file_stem)
                    if not records:
                        self.logger.warning(f"Processed JSONL not found for {file_stem}, skipping")
                        continue

                    processed_file = f"{file_stem}.jsonl"
                    alt_files = [processed_file, f"{file_stem}.json", f"{file_stem}.txt"]

                    # Process each record to collect data
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

                        # Store record data for batch embedding
                        all_records_data.append(
                            {
                                "text": text,
                                "chunk_id": chunk_id,
                                "filename": processed_file,
                                "document_id": document_id,
                                "page": page,
                                "section": section,
                                "field_name": field_name,
                                "tags": tags,
                                "score": score,
                                "rec": rec,  # Store full record for metadata creation
                            }
                        )

                        total_chunks += 1

                except Exception as e:
                    self.logger.error(f"Failed to process {file_stem}: {e}", exc_info=True)
                    continue

            if not all_records_data:
                return self._create_result(
                    status=StageStatus.FAILED,
                    metrics={},
                    error="No records to index",
                    started_at=started_at,
                )

            # Log total chunks to process
            total_chunks = len(all_records_data)
            avg_chunk_length = sum(len(r["text"]) for r in all_records_data) / total_chunks if total_chunks > 0 else 0
            self.logger.info(
                f"📊 Total chunks to process: {total_chunks}, " f"average chunk length: {avg_chunk_length:.0f} characters"
            )

            # Batch embed all texts for performance (especially important for OpenAI API)
            # Adaptive batch size based on model dimension to prevent memory issues
            # Large models (>=1024 dim) need very small batches, smaller models can handle larger batches
            model_dimension = actual_dimension
            if model_dimension >= 1024:
                # For very large models like BGE Large, use very small batches to avoid timeout
                # With thousands of chunks, even small batches can take hours
                embedding_batch_size = 3  # Very large models need tiny batches to complete in reasonable time
            elif model_dimension >= 768:
                embedding_batch_size = 15  # Large models need medium batches
            else:
                embedding_batch_size = 100  # Smaller models can handle larger batches

            # Estimate processing time (rough estimate: 10-20 seconds per batch for large models)
            total_batches = (total_chunks + embedding_batch_size - 1) // embedding_batch_size
            if model_dimension >= 1024:
                estimated_minutes = total_batches * 0.5  # ~30 seconds per batch of 3 chunks
            elif model_dimension >= 768:
                estimated_minutes = total_batches * 0.3  # ~18 seconds per batch of 15 chunks
            else:
                estimated_minutes = total_batches * 0.1  # ~6 seconds per batch of 100 chunks

            self.logger.info(
                f"Generating embeddings for {total_chunks} chunks in batches of {embedding_batch_size} "
                f"(model dimension: {model_dimension}, {total_batches} batches, "
                f"estimated time: ~{estimated_minutes:.1f} minutes / ~{estimated_minutes/60:.1f} hours)..."
            )

            # Warn if processing will take a very long time
            if estimated_minutes > 60:
                self.logger.warning(
                    f"⚠️  WARNING: Embedding generation is estimated to take {estimated_minutes/60:.1f} hours. "
                    f"Consider using a faster model (e.g., minilm or e5-base) for large documents, "
                    f"or ensure the task has sufficient timeout (currently 2 hours)."
                )
            all_embeddings = []

            import time

            start_time = time.time()

            for i in range(0, len(all_records_data), embedding_batch_size):
                batch_start_time = time.time()
                batch_records = all_records_data[i : i + embedding_batch_size]
                batch_texts = [r["text"] for r in batch_records]
                batch_num = (i // embedding_batch_size) + 1
                total_batches = (len(all_records_data) + embedding_batch_size - 1) // embedding_batch_size

                # Log batch start with timing info
                elapsed = time.time() - start_time
                avg_time_per_batch = elapsed / max(batch_num - 1, 1)
                remaining_batches = total_batches - batch_num
                estimated_remaining = remaining_batches * avg_time_per_batch

                self.logger.info(
                    f"🔄 Embedding batch {batch_num}/{total_batches} ({len(batch_texts)} chunks, "
                    f"progress: {i}/{len(all_records_data)} chunks, "
                    f"elapsed: {elapsed:.1f}s, est. remaining: {estimated_remaining:.1f}s)..."
                )
                try:
                    # Use smaller internal batch size for sentence transformers to manage memory better
                    batch_embeddings = embedder.embed_batch(batch_texts, batch_size=embedding_batch_size)
                    all_embeddings.extend(batch_embeddings)
                    batch_time = time.time() - batch_start_time
                    self.logger.info(
                        f"✅ Generated {len(batch_embeddings)} embeddings for batch {batch_num}/{total_batches} "
                        f"in {batch_time:.1f}s ({batch_time/len(batch_texts):.2f}s per chunk)"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to generate embeddings for batch {batch_num}/{total_batches}: {e}", exc_info=True
                    )
                    # Fallback to individual embeddings for this batch
                    self.logger.warning(f"Falling back to individual embedding generation for batch {batch_num}")
                    for record_data in batch_records:
                        try:
                            embedding = embedder.embed(record_data["text"])
                            all_embeddings.append(embedding)
                        except Exception as emb_error:
                            self.logger.error(f"Failed to embed chunk {record_data['chunk_id']}: {emb_error}")
                            # Add None as placeholder - will skip this record
                            all_embeddings.append(None)

            # Second pass: Build points with embeddings
            all_points = []
            for idx, (record_data, embedding) in enumerate(zip(all_records_data, all_embeddings)):
                if embedding is None:
                    self.logger.warning(f"Skipping chunk {record_data['chunk_id']} due to embedding failure")
                    continue

                embedding_list = embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)

                # Create Qdrant point ID (use chunk_id hash for uniqueness)
                point_id_str = f"{self.product_id}_{record_data['chunk_id']}_{self.version}"
                point_id = int(hashlib.md5(point_id_str.encode()).hexdigest()[:15], 16)

                # Create Qdrant point
                # Store full text (Qdrant supports large payloads, typically up to 64KB per payload)
                max_text_length = 50000  # 50KB should be safe for Qdrant payloads
                stored_text = (
                    record_data["text"][:max_text_length]
                    if len(record_data["text"]) > max_text_length
                    else record_data["text"]
                )

                # Create Qdrant point with all metadata in payload (single source of truth)
                # All metadata is stored in Qdrant payload - no PostgreSQL metadata tables needed
                point = {
                    "id": point_id,
                    "vector": embedding_list,
                    "payload": {
                        "chunk_id": record_data["chunk_id"],
                        "filename": record_data["filename"],
                        "source_file": record_data["filename"],  # Alias for compatibility
                        "document_id": record_data["document_id"],
                        "page": record_data["page"],
                        "page_number": record_data["page"],  # Alias for compatibility
                        "section": record_data["section"],
                        "field_name": record_data["field_name"],
                        "score": record_data["score"],
                        "text": stored_text,
                        "text_length": len(record_data["text"]),
                        "source": record_data["rec"].get("source", "internal"),
                        "audience": record_data["rec"].get("audience", "unknown"),
                        "timestamp": record_data["rec"].get("timestamp", datetime.utcnow().isoformat()),
                        "product_id": str(self.product_id),
                        "version": self.version,  # Add version to payload
                        "collection_id": collection_name,  # Add collection_id to payload
                        "created_at": datetime.utcnow().isoformat(),  # Add created_at timestamp
                        "index_scope": str(self.product_id),
                        "doc_scope": record_data["document_id"],
                        "field_scope": record_data["field_name"],
                        "tags": record_data["tags"],
                        "extra_tags": {"tags": record_data["tags"]} if record_data["tags"] else None,  # For compatibility
                        "token_est": record_data["rec"].get("token_est", 0),
                    },
                }
                all_points.append(point)

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

            finished_at = datetime.utcnow()

            # Calculate aggregate trust score
            scores = [p["payload"]["score"] for p in all_points]
            avg_trust_score = round(sum(scores) / len(scores), 4) if scores else 0.0

            metrics_result = {
                "collection_name": collection_name,
                "points_indexed": len(all_points),
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
