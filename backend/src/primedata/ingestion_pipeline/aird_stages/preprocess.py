"""
AIRD preprocessing stage for PrimeData.

Ports AIRD preprocessing logic with playbook support, adapted for MinIO storage.
"""

import json
import regex as re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import logging as std_logging  # For Airflow compatibility

from loguru import logger

# Use Python logging for Airflow compatibility (Airflow captures standard logging)
std_logger = std_logging.getLogger(__name__)

from primedata.ingestion_pipeline.aird_stages.base import AirdStage, StageResult, StageStatus
from primedata.ingestion_pipeline.aird_stages.playbooks import route_playbook, load_playbook_yaml
from primedata.ingestion_pipeline.aird_stages.utils.text_processing import (
    normalize_wrapped_lines,
    redact_pii,
    apply_normalizers,
    split_pages_by_config,
    detect_sections_configured,
)
from primedata.ingestion_pipeline.aird_stages.utils.chunking import (
    char_chunk,
    sentence_chunk,
    tokens_estimate,
)


# Audience patterns (aligned with AIRD)
AUDIENCE_PATTERNS = {
    "hcp": r"\b(hcp|physician|prescriber|clinical)\b",
    "executive": r"\b(executive|vp|steerco|cxo)\b",
    "patient": r"\b(patient|caregiver)\b",
    "regulatory": r"\b(regulatory|compliance|sop|policy)\b",
    "finance": r"\b(p&l|variance|forecast|budget|kpi|quarter)\b",
    "ops": r"\b(monitoring|deployment|incident|runbook|oncall|slo|sla|kubernetes|cluster)\b",
    "dev": r"\b(api|cli|sdk|endpoint|json|yaml|code|pipeline|ci/cd)\b",
}


def _audience_for(text: str, default: str = "unknown") -> str:
    """Detect audience from text using patterns."""
    for name, pat in AUDIENCE_PATTERNS.items():
        if re.search(pat, text, flags=re.IGNORECASE):
            return name
    return default


def _build_record(
    stem: str,
    filename: str,
    document_id: str,
    page: int,
    canon_section: str,
    title_raw: str,
    text: str,
    chunk_idx: int,
    chunk_of: int,
    product_id: UUID,
) -> Dict[str, Any]:
    """Build a chunk record with PrimeData metadata structure."""
    return {
        "chunk_id": f"{stem}_p{page}_s{canon_section}_c{chunk_idx}",
        "document_id": document_id,
        "filename": filename,
        "page": page,
        "section_raw": title_raw,
        "section": canon_section,
        "field_name": canon_section,
        "text": text,
        "token_est": tokens_estimate(text),
        "chunk_index": chunk_idx,
        "chunk_of": chunk_of,
        "source": "internal",
        "audience": _audience_for(text, "unknown"),
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "product_id": str(product_id),
        "index_scope": None,
        "doc_scope": document_id,
        "field_scope": canon_section,
        "tags": "",
        "doc_date": None,
    }


class PreprocessStage(AirdStage):
    """Preprocessing stage that normalizes, chunks, and sections documents."""
    
    @property
    def stage_name(self) -> str:
        return "preprocess"
    
    def get_required_artifacts(self) -> list[str]:
        """Preprocessing requires raw text files from ingestion."""
        return []  # Raw files come from ingestion stage
    
    def execute(self, context: Dict[str, Any]) -> StageResult:
        """Execute preprocessing stage.
        
        Args:
            context: Stage execution context with:
                - storage: AirdStorageAdapter
                - raw_files: List of raw file stems to process
                - playbook_id: Optional playbook ID override
                - chunking_config: Optional product chunking configuration
                
        Returns:
            StageResult with preprocessing metrics
        """
        started_at = datetime.utcnow()
        storage = context.get("storage")
        raw_files = context.get("raw_files", [])
        initial_playbook_id = context.get("playbook_id") or self.config.get("playbook_id")
        chunking_config = context.get("chunking_config", {})  # Get product chunking config
        
        # Track playbook selection metadata for verification
        playbook_selection_metadata = {
            "method": "manual" if initial_playbook_id else None,  # Will be updated if auto-detected
            "reason": None,
            "detected_at": None,
        }
        
        if not storage:
            return self._create_result(
                status=StageStatus.FAILED,
                metrics={},
                error="Storage adapter not found in context",
                started_at=started_at,
            )
        
        if not raw_files:
            self.logger.warning("No raw files to process")
            return self._create_result(
                status=StageStatus.SKIPPED,
                metrics={"reason": "no_raw_files"},
                started_at=started_at,
            )
        
        self.logger.info(f"Starting preprocessing for {len(raw_files)} files, playbook={playbook_id}")
        
        # Get file_stem to minio_key mapping if provided (for accurate file retrieval)
        file_stem_to_minio_key = context.get("file_stem_to_minio_key", {})
        
        all_records: List[Dict[str, Any]] = []
        total_sections = 0
        total_mid_sentence_ends = 0
        processed_files = []
        failed_files = []
        chunking_config_used: Optional[Dict[str, Any]] = None
        
        for file_stem in raw_files:
            file_start_time = datetime.utcnow()
            # Use both loguru and std logging for Airflow visibility
            self.logger.info(f"[PreprocessStage] ====== Processing file: {file_stem} ======")
            std_logger.info(f"[PreprocessStage] ====== Processing file: {file_stem} ======")
            try:
                # Load raw text - use exact minio_key if available
                file_info = file_stem_to_minio_key.get(file_stem, {})
                minio_key = file_info.get("minio_key")
                minio_bucket = file_info.get("minio_bucket")
                filename = file_info.get("filename", f"{file_stem}.txt")
                
                file_info_msg = f"[PreprocessStage] File info for {file_stem}: minio_key={minio_key}, minio_bucket={minio_bucket}, filename={filename}"
                self.logger.info(file_info_msg)
                std_logger.info(file_info_msg)
                
                keys_msg = f"[PreprocessStage] Available file_stem_to_minio_key keys: {list(file_stem_to_minio_key.keys())}"
                self.logger.info(keys_msg)
                std_logger.info(keys_msg)
                
                if minio_key:
                    load_msg = f"[PreprocessStage] Loading raw file {file_stem} from exact MinIO key: {minio_key} (bucket: {minio_bucket or 'primedata-raw'})"
                    self.logger.info(load_msg)
                    std_logger.info(load_msg)
                    try:
                        self.logger.info(f"[PreprocessStage] About to call storage.get_raw_text(file_stem={file_stem}, minio_key={minio_key}, minio_bucket={minio_bucket})")
                        std_logger.info(f"[PreprocessStage] About to call storage.get_raw_text(file_stem={file_stem}, minio_key={minio_key}, minio_bucket={minio_bucket})")
                        raw_text = storage.get_raw_text(file_stem, minio_key=minio_key, minio_bucket=minio_bucket)
                        self.logger.info(f"[PreprocessStage] storage.get_raw_text() returned: {'None' if raw_text is None else f'{len(raw_text)} characters'}")
                        std_logger.info(f"[PreprocessStage] storage.get_raw_text() returned: {'None' if raw_text is None else f'{len(raw_text)} characters'}")
                    except Exception as e:
                        self.logger.error(f"[PreprocessStage] Exception while calling storage.get_raw_text() for {file_stem}: {type(e).__name__}: {str(e)}", exc_info=True)
                        import traceback
                        self.logger.error(f"[PreprocessStage] get_raw_text() traceback:\n{traceback.format_exc()}")
                        raw_text = None
                else:
                    self.logger.warning(f"[PreprocessStage] No minio_key found for {file_stem} in file_stem_to_minio_key map. Using constructed path (.txt extension)")
                    try:
                        raw_text = storage.get_raw_text(file_stem)
                    except Exception as e:
                        self.logger.error(f"[PreprocessStage] Exception while calling storage.get_raw_text() (constructed path) for {file_stem}: {type(e).__name__}: {str(e)}", exc_info=True)
                        import traceback
                        self.logger.error(f"[PreprocessStage] get_raw_text() (constructed) traceback:\n{traceback.format_exc()}")
                        raw_text = None
                
                if not raw_text:
                    error_msg = (
                        f"[PreprocessStage] ❌ Raw text extraction FAILED for {file_stem}. "
                        f"MinIO key: {minio_key if minio_key else 'constructed path'}, "
                        f"Bucket: {minio_bucket or 'primedata-raw'}, "
                        f"Filename: {filename}. "
                        f"File may be missing from MinIO, corrupted, or in unsupported format."
                    )
                    # Use both loguru and std logging for Airflow visibility
                    self.logger.error(error_msg)
                    std_logger.error(error_msg)
                    failed_files.append(file_stem)
                    continue
                
                self.logger.info(f"[PreprocessStage] ✓ Successfully loaded raw text for {file_stem}: {len(raw_text)} characters")
                
                # Route playbook if not provided
                file_playbook_id = initial_playbook_id  # Use initial playbook_id for this file
                if not file_playbook_id:
                    chosen_id, reason = route_playbook(sample_text=raw_text[:1000], filename=file_stem)
                    file_playbook_id = chosen_id
                    # Update selection metadata for auto-detection (only on first file)
                    if not playbook_selection_metadata.get("method") or playbook_selection_metadata["method"] is None:
                        playbook_selection_metadata["method"] = "auto_detected"
                        playbook_selection_metadata["reason"] = reason
                        playbook_selection_metadata["detected_at"] = datetime.utcnow().isoformat() + "Z"
                    self.logger.info(f"Auto-routed to playbook {file_playbook_id} ({reason})")
                elif not playbook_selection_metadata.get("method") or playbook_selection_metadata["method"] is None:
                    # Playbook was provided, mark as manual
                    playbook_selection_metadata["method"] = "manual"
                
                # Use file_playbook_id for this file's processing
                playbook_id = file_playbook_id
                
                # Load playbook
                try:
                    playbook = load_playbook_yaml(playbook_id)
                except Exception as e:
                    self.logger.error(f"Failed to load playbook {playbook_id}: {e}, using empty config")
                    playbook = {}
                
                # Process document
                records, stats = self._process_document(
                    raw_text=raw_text,
                    file_stem=file_stem,
                    filename=f"{file_stem}.txt",
                    playbook=playbook,
                    playbook_id=playbook_id,
                    chunking_config=chunking_config,  # Pass product chunking config
                )
                
                all_records.extend(records)
                total_sections += stats.get("sections", 0)
                total_mid_sentence_ends += stats.get("mid_sentence_ends", 0)
                if not chunking_config_used and stats.get("chunking_config_used"):
                    chunking_config_used = stats.get("chunking_config_used")
                processed_files.append(file_stem)
                
                # Store processed JSONL for this file
                storage.put_processed_jsonl(file_stem, records)
                
                # Store manifest
                manifest = {
                    "filename": f"{file_stem}.txt",
                    "stem": file_stem,
                    "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    "playbook_id": playbook_id,
                    "stats": stats,
                }
                storage.put_manifest(file_stem, manifest)
                
            except Exception as e:
                error_msg = f"[PreprocessStage] ❌ EXCEPTION while processing {file_stem}: {type(e).__name__}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                import traceback
                self.logger.error(f"[PreprocessStage] Full traceback for {file_stem}:\n{traceback.format_exc()}")
                self.logger.error(f"[PreprocessStage] Exception details for {file_stem}: {repr(e)}")
                failed_files.append(file_stem)
            finally:
                file_duration = (datetime.utcnow() - file_start_time).total_seconds()
                self.logger.info(f"[PreprocessStage] ====== Finished processing {file_stem} in {file_duration:.2f}s ======")
        
        if not all_records:
            return self._create_result(
                status=StageStatus.FAILED,
                metrics={
                    "processed_files": len(processed_files),
                    "failed_files": len(failed_files),
                    "failed_file_list": failed_files,
                },
                error="No records produced from preprocessing",
                started_at=started_at,
            )
        
        # Calculate aggregate metrics
        total_chunks = len(all_records)
        mid_sentence_rate = round(total_mid_sentence_ends / max(total_chunks, 1), 4)
        
        # Store aggregate metrics
        metrics_list = [
            {
                "file_stem": stem,
                "playbook_id": playbook_id,
                "sections": total_sections,
                "chunks": total_chunks,
                "mid_sentence_boundary_rate": mid_sentence_rate,
            }
            for stem in processed_files
        ]
        storage.put_metrics_json(metrics_list)
        
        finished_at = datetime.utcnow()
        
        # Build artifacts map
        artifacts = {
            "processed_jsonl": f"processed/{self.product_id}/v{self.version}/",
            "metrics_json": f"processed/{self.product_id}/v{self.version}/metrics.json",
        }
        
        metrics = {
            "playbook_id": playbook_id,
            "playbook_selection": playbook_selection_metadata,  # Include selection metadata
            "processed_files": len(processed_files),
            "failed_files": len(failed_files),
            "total_sections": total_sections,
            "total_chunks": total_chunks,
            "mid_sentence_boundary_rate": mid_sentence_rate,
            "processed_file_list": processed_files,
            "chunking_config_used": chunking_config_used,
        }
        
        return self._create_result(
            status=StageStatus.SUCCEEDED,
            metrics=metrics,
            artifacts=artifacts,
            started_at=started_at,
            finished_at=finished_at,
        )
    
    def _process_document(
        self,
        raw_text: str,
        file_stem: str,
        filename: str,
        playbook: Dict[str, Any],
        playbook_id: str,
        chunking_config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Process a single document through the preprocessing pipeline.
        
        Args:
            chunking_config: Optional product-level chunking configuration that overrides playbook settings
        
        Returns:
            Tuple of (records_list, stats_dict)
        """
        # 1) Normalize (unwrap + PII redaction + rule-based normalizers)
        unwrapped = normalize_wrapped_lines(raw_text)
        redacted = redact_pii(unwrapped)
        cleaned = apply_normalizers(redacted, playbook.get("pre_normalizers", []))
        
        # 2) Split into pages
        pages = split_pages_by_config(cleaned, playbook.get("page_fences", []))
        
        # 3) Get chunking config (product config overrides playbook defaults)
        playbook_chunking = playbook.get("chunking", {})
        
        # Track the resolved chunking configuration actually used
        resolved_chunking_config: Dict[str, Any] = {
            "mode": (chunking_config or {}).get("mode", "auto"),
            "source": None,  # manual | product_auto | playbook_default
        }
        
        # Priority: Product manual settings > Product auto settings > Playbook defaults
        if chunking_config and chunking_config.get("mode") == "manual":
            manual_settings = chunking_config.get("manual_settings", {})
            # Convert chunk_size (tokens) to max_tokens
            max_tokens = int(manual_settings.get("chunk_size", playbook_chunking.get("max_tokens", 900)))
            # Convert chunk_overlap (tokens) to overlap_sentences and hard_overlap_chars
            chunk_overlap = int(manual_settings.get("chunk_overlap", 200))
            # Estimate: 1 sentence ≈ 20 tokens, so overlap_sentences = chunk_overlap / 20
            overlap_sents = max(1, int(chunk_overlap / 20))
            hard_overlap = chunk_overlap * 4  # Convert tokens to chars (approx 4 chars per token)
            strategy = manual_settings.get("chunking_strategy", playbook_chunking.get("strategy", "sentence")).lower()
            # Map fixed_size to char_chunk, semantic/sentence to sentence
            if strategy == "fixed_size":
                strategy = "char"
            elif strategy in ["semantic", "sentence"]:
                strategy = "sentence"
            resolved_chunking_config.update({
                "source": "manual",
                "chunk_size": max_tokens,
                "chunk_overlap": chunk_overlap,
                "min_chunk_size": int(manual_settings.get("min_chunk_size", playbook_chunking.get("min_chunk_size", 100))),
                "max_chunk_size": int(manual_settings.get("max_chunk_size", playbook_chunking.get("max_chunk_size", 2000))),
                "chunking_strategy": manual_settings.get("chunking_strategy", "sentence"),
            })
        elif chunking_config and chunking_config.get("mode") == "auto":
            # Use playbook settings but respect product content_type recommendations if available
            max_tokens = int(playbook_chunking.get("max_tokens", 900))
            overlap_sents = int(playbook_chunking.get("overlap_sentences", 2))
            hard_overlap = int(playbook_chunking.get("hard_overlap_chars", 300))
            strategy = (playbook_chunking.get("strategy", "sentence") or "sentence").lower()
            resolved_chunking_config.update({
                "source": "product_auto",
                "chunk_size": max_tokens,
                "chunk_overlap": overlap_sents * 20,  # approximate tokens
                "min_chunk_size": int(playbook_chunking.get("min_chunk_size", 100)),
                "max_chunk_size": int(playbook_chunking.get("max_chunk_size", 2000)),
                "chunking_strategy": "fixed_size" if strategy == "char" else "semantic",
            })
        else:
            # Fallback to playbook defaults
            max_tokens = int(playbook_chunking.get("max_tokens", 900))
            overlap_sents = int(playbook_chunking.get("overlap_sentences", 2))
            hard_overlap = int(playbook_chunking.get("hard_overlap_chars", 300))
            strategy = (playbook_chunking.get("strategy", "sentence") or "sentence").lower()
            resolved_chunking_config.update({
                "source": "playbook_default",
                "chunk_size": max_tokens,
                "chunk_overlap": overlap_sents * 20,  # approximate tokens
                "min_chunk_size": int(playbook_chunking.get("min_chunk_size", 100)),
                "max_chunk_size": int(playbook_chunking.get("max_chunk_size", 2000)),
                "chunking_strategy": "fixed_size" if strategy == "char" else "semantic",
            })
        
        # 4) Process pages and sections
        records: List[Dict[str, Any]] = []
        sections_detected = 0
        mid_sentence_ends = 0
        
        for page_data in pages:
            page_text = page_data["text"]
            page_num = page_data["page"]
            
            # Detect sections
            sections = detect_sections_configured(
                page_text,
                playbook.get("headers", []),
                playbook.get("section_aliases", {}),
            )
            sections_detected += len(sections)
            
            # Process each section
            for title_raw, canon_section, body_text in sections:
                # Chunk the section
                if strategy == "sentence":
                    chunks = sentence_chunk(body_text, max_tokens, overlap_sents, hard_overlap)
                elif strategy == "char":
                    # Use character-based chunking for fixed_size strategy
                    chunks = char_chunk(body_text, max_tokens, hard_overlap)
                else:
                    chunks = char_chunk(body_text, max_tokens, hard_overlap)
                
                # Build records for each chunk
                for idx, chunk_text in enumerate(chunks):
                    # Check for mid-sentence boundary
                    if not re.search(r"[.!?]['\")\]]*\s*$", chunk_text):
                        mid_sentence_ends += 1
                    
                    # Build record
                    rec = _build_record(
                        stem=file_stem,
                        filename=filename,
                        document_id=file_stem,
                        page=page_num,
                        canon_section=canon_section,
                        title_raw=title_raw,
                        text=chunk_text,
                        chunk_idx=idx,
                        chunk_of=len(chunks),
                        product_id=self.product_id,
                    )
                    
                    # Apply audience rules from playbook
                    aud = rec["audience"]
                    for rule in playbook.get("audience_rules", []) or []:
                        try:
                            pat = rule.get("pattern")
                            if pat and (
                                re.search(pat, title_raw, flags=re.IGNORECASE) or
                                re.search(pat, chunk_text, flags=re.IGNORECASE)
                            ):
                                aud = rule.get("audience", aud)
                                break
                        except re.error:
                            pass
                    rec["audience"] = aud
                    
                    records.append(rec)
        
        # Calculate stats
        total_chunks = len(records)
        mid_sentence_rate = round(mid_sentence_ends / max(total_chunks, 1), 4)
        
        stats = {
            "playbook_id": playbook_id,
            "sections": sections_detected,
            "chunks": total_chunks,
            "mid_sentence_boundary_rate": mid_sentence_rate,
            "mid_sentence_ends": mid_sentence_ends,
            "chunking_config_used": resolved_chunking_config,
        }
        
        return records, stats



