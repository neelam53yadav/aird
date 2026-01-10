"""
AIRD preprocessing stage for PrimeData.

Ports AIRD preprocessing logic with playbook support, adapted for MinIO storage.
"""

import json
import logging as std_logging  # For Airflow compatibility
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import regex as re
from loguru import logger

# Use Python logging for Airflow compatibility (Airflow captures standard logging)
std_logger = std_logging.getLogger(__name__)

from primedata.ingestion_pipeline.aird_stages.base import AirdStage, StageResult, StageStatus
from primedata.ingestion_pipeline.aird_stages.playbooks import load_playbook_yaml, route_playbook
from primedata.ingestion_pipeline.aird_stages.utils.chunking import (
    char_chunk,
    paragraph_chunk,
    sentence_chunk,
    tokens_estimate,
)
from primedata.ingestion_pipeline.aird_stages.utils.text_processing import (
    apply_normalizers,
    detect_sections_configured,
    normalize_wrapped_lines,
    redact_pii,
    split_pages_by_config,
)
from primedata.analysis.content_analyzer import content_analyzer

# Audience patterns (aligned with AIRD) - ordered by specificity
AUDIENCE_PATTERNS = {
    "hcp": r"\b(hcp|physician|prescriber|clinical|doctor|nurse|clinician|healthcare provider)\b",
    "executive": r"\b(executive|vp|vice president|steerco|cxo|ceo|cto|cfo|board|director|leadership|management)\b",
    "patient": r"\b(patient|caregiver|consumer|user)\b",
    "regulatory": r"\b(regulatory|compliance|sop|policy|regulation|fda|ema|regulatory authority)\b",
    "finance": r"\b(p&l|profit.*loss|variance|forecast|budget|kpi|quarter|quarterly|financial|revenue|earnings|income statement)\b",
    "ops": r"\b(monitoring|deployment|incident|runbook|oncall|slo|sla|kubernetes|cluster|operations|infrastructure)\b",
    "dev": r"\b(api|cli|sdk|endpoint|json|yaml|code|pipeline|ci/cd|developer|engineer|programmer)\b",
    "general": r"\b(overview|introduction|getting started|guide|tutorial|documentation|help|support)\b",
}


def _audience_for(text: str, section: str = "", default: str = "general") -> str:
    """Detect audience from text and section using patterns."""
    # Combine text and section for better detection
    search_text = f"{section} {text}".lower()

    # Score each audience pattern
    scores = {}
    for name, pat in AUDIENCE_PATTERNS.items():
        matches = len(re.findall(pat, search_text, flags=re.IGNORECASE))
        if matches > 0:
            scores[name] = matches

    if scores:
        # Return the audience with the highest score (most matches)
        return max(scores.items(), key=lambda x: x[1])[0]

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
    domain_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a chunk record with PrimeData metadata structure."""
    record = {
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
        "audience": _audience_for(text, section=title_raw or canon_section, default="general"),
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "product_id": str(product_id),
        "index_scope": None,
        "doc_scope": document_id,
        "field_scope": canon_section,
        "tags": "",
        "doc_date": None,
    }
    
    # Add domain_type if provided (for domain-adaptive scoring)
    if domain_type:
        record["domain_type"] = domain_type
    
    return record


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

        # Cache context for use in _process_document (for workspace settings lookup)
        self._context_cache = {
            "workspace_id": context.get("workspace_id"),
            "db": context.get("db"),
        }

        storage = context.get("storage")
        raw_files = context.get("raw_files", [])
        # Get playbook_id from context or config, but allow None/empty for auto-detection
        initial_playbook_id = context.get("playbook_id") or self.config.get("playbook_id")
        # Normalize empty string to None to allow auto-detection
        if initial_playbook_id == "":
            initial_playbook_id = None
        chunking_config = context.get("chunking_config", {})  # Get product chunking config

        # Track playbook selection metadata for verification
        # Will be updated based on whether playbook is provided or auto-detected
        playbook_selection_metadata = {
            "method": None,  # Will be set to "manual", "auto_detected", or "default"
            "reason": None,
            "detected_at": None,
            "playbook_id": None,  # Will be set when playbook is determined
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

        # Initialize playbook_id for logging (will be reassigned per file in loop)
        playbook_id = initial_playbook_id
        self.logger.info(f"Starting preprocessing for {len(raw_files)} files, playbook={playbook_id}")

        # Get file_stem to storage_key mapping if provided (for accurate file retrieval)
        file_stem_to_storage_key = context.get("file_stem_to_storage_key", {})

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
                # Load raw text - use exact storage_key if available
                file_info = file_stem_to_storage_key.get(file_stem, {})
                storage_key = file_info.get("storage_key")
                storage_bucket = file_info.get("storage_bucket")
                filename = file_info.get("filename", f"{file_stem}.txt")

                file_info_msg = f"[PreprocessStage] File info for {file_stem}: storage_key={storage_key}, storage_bucket={storage_bucket}, filename={filename}"
                self.logger.info(file_info_msg)
                std_logger.info(file_info_msg)

                keys_msg = (
                    f"[PreprocessStage] Available file_stem_to_storage_key keys: {list(file_stem_to_storage_key.keys())}"
                )
                self.logger.info(keys_msg)
                std_logger.info(keys_msg)

                # OPTIMIZATION: Route playbook BEFORE loading full file (for performance)
                # Route playbook if not provided
                file_playbook_id = initial_playbook_id  # Use initial_playbook_id for this file
                if not file_playbook_id:
                    # OPTIMIZATION: For playbook routing, only read sample text
                    # This avoids extracting full PDF when we only need first 1000-2000 chars
                    sample_for_playbook = None
                    try:
                        if filename.lower().endswith('.pdf'):
                            # For PDFs, extract only first 2 pages for playbook routing
                            sample_for_playbook = self._get_pdf_sample_for_routing(
                                storage, file_stem, storage_key, storage_bucket, max_chars=2000
                            )
                        else:
                            # For text files, read only first 2000 chars
                            sample_for_playbook = self._get_text_sample_for_routing(
                                storage, file_stem, storage_key, storage_bucket, max_chars=2000
                            )
                    except Exception as e:
                        self.logger.warning(f"Failed to get sample for playbook routing: {e}, will use filename only")
                        sample_for_playbook = None
                    
                    # Use sample if available, otherwise use filename only
                    if sample_for_playbook:
                        chosen_id, reason = route_playbook(
                            sample_text=sample_for_playbook[:1000], 
                            filename=file_stem
                        )
                        file_playbook_id = chosen_id
                        # Update selection metadata for auto-detection (only on first file)
                        if playbook_selection_metadata.get("method") is None:
                            playbook_selection_metadata["method"] = "auto_detected"
                            playbook_selection_metadata["playbook_id"] = chosen_id
                            playbook_selection_metadata["reason"] = reason
                            playbook_selection_metadata["detected_at"] = datetime.utcnow().isoformat() + "Z"
                        self.logger.info(f"Auto-routed to playbook {file_playbook_id} ({reason}) using sample text")
                    else:
                        # Fallback: use filename only for routing
                        chosen_id, reason = route_playbook(sample_text=None, filename=file_stem)
                        file_playbook_id = chosen_id
                        if playbook_selection_metadata.get("method") is None:
                            playbook_selection_metadata["method"] = "auto_detected"
                            playbook_selection_metadata["playbook_id"] = chosen_id
                            playbook_selection_metadata["reason"] = reason
                            playbook_selection_metadata["detected_at"] = datetime.utcnow().isoformat() + "Z"
                        self.logger.info(f"Auto-routed to playbook {file_playbook_id} ({reason}) using filename only")
                else:
                    # Playbook was provided, mark as manual (only on first file)
                    if playbook_selection_metadata.get("method") is None:
                        playbook_selection_metadata["method"] = "manual"
                        playbook_selection_metadata["playbook_id"] = file_playbook_id

                # NOW load full file for actual processing
                if storage_key:
                    load_msg = f"[PreprocessStage] Loading raw file {file_stem} from exact MinIO key: {storage_key} (bucket: {storage_bucket or 'primedata-raw'})"
                    self.logger.info(load_msg)
                    std_logger.info(load_msg)
                    try:
                        self.logger.info(
                            f"[PreprocessStage] About to call storage.get_raw_text(file_stem={file_stem}, minio_key={storage_key}, minio_bucket={storage_bucket})"
                        )
                        std_logger.info(
                            f"[PreprocessStage] About to call storage.get_raw_text(file_stem={file_stem}, minio_key={storage_key}, minio_bucket={storage_bucket})"
                        )
                        raw_text = storage.get_raw_text(file_stem, minio_key=storage_key, minio_bucket=storage_bucket)
                        self.logger.info(
                            f"[PreprocessStage] storage.get_raw_text() returned: {'None' if raw_text is None else f'{len(raw_text)} characters'}"
                        )
                        std_logger.info(
                            f"[PreprocessStage] storage.get_raw_text() returned: {'None' if raw_text is None else f'{len(raw_text)} characters'}"
                        )
                    except Exception as e:
                        self.logger.error(
                            f"[PreprocessStage] Exception while calling storage.get_raw_text() for {file_stem}: {type(e).__name__}: {str(e)}",
                            exc_info=True,
                        )
                        import traceback

                        self.logger.error(f"[PreprocessStage] get_raw_text() traceback:\n{traceback.format_exc()}")
                        raw_text = None
                else:
                    self.logger.warning(
                        f"[PreprocessStage] No storage_key found for {file_stem} in file_stem_to_storage_key map. Using constructed path (.txt extension)"
                    )
                    try:
                        raw_text = storage.get_raw_text(file_stem)
                    except Exception as e:
                        self.logger.error(
                            f"[PreprocessStage] Exception while calling storage.get_raw_text() (constructed path) for {file_stem}: {type(e).__name__}: {str(e)}",
                            exc_info=True,
                        )
                        import traceback

                        self.logger.error(
                            f"[PreprocessStage] get_raw_text() (constructed) traceback:\n{traceback.format_exc()}"
                        )
                        raw_text = None

                if not raw_text:
                    # Check if it's an image file (expected to fail)
                    is_image_file = filename.lower().endswith(
                        (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg")
                    )
                    if is_image_file:
                        warn_msg = (
                            f"[PreprocessStage] ⚠️ Skipping image file {file_stem} (filename: {filename}). "
                            f"Image files cannot be extracted as text. "
                            f"Only PDF, text, and HTML files are supported for text extraction."
                        )
                        self.logger.warning(warn_msg)
                        std_logger.warning(warn_msg)
                        failed_files.append(file_stem)
                        continue
                    else:
                        error_msg = (
                            f"[PreprocessStage] ❌ Raw text extraction FAILED for {file_stem}. "
                            f"MinIO key: {storage_key if storage_key else 'constructed path'}, "
                            f"Bucket: {storage_bucket or 'primedata-raw'}, "
                            f"Filename: {filename}. "
                            f"File may be missing from MinIO, corrupted, or in unsupported format. "
                            f"Supported formats: PDF, TXT, HTML, JSON, CSV"
                        )
                        # Use both loguru and std logging for Airflow visibility
                        self.logger.error(error_msg)
                        std_logger.error(error_msg)
                        failed_files.append(file_stem)
                        continue

                self.logger.info(
                    f"[PreprocessStage] ✓ Successfully loaded raw text for {file_stem}: {len(raw_text)} characters"
                )

                # Route playbook if not provided
                file_playbook_id = initial_playbook_id  # Use initial playbook_id for this file
                if not file_playbook_id:
                    # Auto-detect playbook
                    chosen_id, reason = route_playbook(sample_text=raw_text[:1000], filename=file_stem)
                    file_playbook_id = chosen_id
                    # Update selection metadata for auto-detection (only on first file)
                    if playbook_selection_metadata.get("method") is None:
                        playbook_selection_metadata["method"] = "auto_detected"
                        playbook_selection_metadata["playbook_id"] = chosen_id
                        playbook_selection_metadata["reason"] = reason
                        playbook_selection_metadata["detected_at"] = datetime.utcnow().isoformat() + "Z"
                    self.logger.info(f"Auto-routed to playbook {file_playbook_id} ({reason})")
                else:
                    # Playbook was provided, mark as manual (only on first file)
                    if playbook_selection_metadata.get("method") is None:
                        playbook_selection_metadata["method"] = "manual"
                        playbook_selection_metadata["playbook_id"] = file_playbook_id

                # Use file_playbook_id for this file's processing
                playbook_id = file_playbook_id

                # Load playbook (support custom playbooks from database)
                try:
                    workspace_id = context.get("workspace_id")
                    db_session = context.get("db")
                    playbook = load_playbook_yaml(
                        playbook_id, workspace_id=str(workspace_id) if workspace_id else None, db_session=db_session
                    )
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

        # Ensure playbook_id is set from selection metadata if available
        final_playbook_id = playbook_selection_metadata.get("playbook_id") or playbook_id

        # Store aggregate metrics
        metrics_list = [
            {
                "file_stem": stem,
                "playbook_id": final_playbook_id,
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
            "playbook_id": final_playbook_id,
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
        # 1) Basic normalization (unwrap + PII redaction) - but NOT line-joining normalizers yet
        # We need to preserve page markers for page splitting
        unwrapped = normalize_wrapped_lines(raw_text)
        redacted = redact_pii(unwrapped)

        # 2) Split into pages FIRST (before applying normalizers that join lines)
        # This preserves page markers which are needed for correct page detection
        pages = split_pages_by_config(redacted, playbook.get("page_fences", []))

        # Log page splitting results
        if len(pages) > 1:
            self.logger.info(f"✅ Split text into {len(pages)} pages (page numbers: {[p['page'] for p in pages]})")
            std_logger.info(f"✅ Split text into {len(pages)} pages (page numbers: {[p['page'] for p in pages]})")
        else:
            self.logger.warning(
                f"⚠️ Page splitting found only {len(pages)} page(s). Page markers may be missing or not matching patterns."
            )
            std_logger.warning(
                f"⚠️ Page splitting found only {len(pages)} page(s). Page markers may be missing or not matching patterns."
            )

        # 3) Now apply normalizers to each page separately (after page markers have been used)
        # Filter out normalizers that join lines across page boundaries (we'll apply those per-page)
        line_joining_patterns = [
            r"(?m)(?<![.!?])\r?\n(?!\r?\n)",  # Join continuation lines
            r"(?m)\r?\n(?=[a-z])",  # Join lowercase-leading lines
        ]
        pre_normalizers = playbook.get("pre_normalizers", [])
        safe_normalizers = []
        line_joining_normalizers = []

        for norm in pre_normalizers:
            pattern = norm.get("pattern", "")
            # Check if this normalizer joins lines (could affect page markers)
            is_line_joiner = any(re.search(pat, pattern) for pat in line_joining_patterns)
            if is_line_joiner:
                line_joining_normalizers.append(norm)
            else:
                safe_normalizers.append(norm)

        # Apply safe normalizers to the full text (before page splitting, but they're safe)
        # Actually, we already split pages, so apply safe normalizers per-page
        # But first, let's apply them to the original redacted text for consistency
        # Actually, let's apply normalizers per-page after splitting

        # 4) Apply normalizers to each page
        normalized_pages = []
        for page_data in pages:
            page_text = page_data["text"]
            page_num = page_data["page"]

            # Apply all normalizers to this page
            normalized_text = apply_normalizers(page_text, pre_normalizers)
            normalized_pages.append({"page": page_num, "text": normalized_text})

        # 5) Fix PDF extraction corruption: spaces between characters (e.g., "B e z o s" -> "Bezos")
        # This is a common issue with certain PDF extraction libraries
        cleaned_pages = []
        for page_data in normalized_pages:
            page_text = page_data["text"]
            page_num = page_data["page"]

            if len(page_text) > 100:
                sample = page_text[:1000]
                space_ratio = sample.count(" ") / len(sample) if len(sample) > 0 else 0
                if space_ratio > 0.3:  # More than 30% spaces suggests corruption
                    self.logger.warning(
                        f"Detected PDF extraction corruption on page {page_num} (space ratio: {space_ratio:.2%}), attempting to fix..."
                    )
                    std_logger.warning(
                        f"Detected PDF extraction corruption on page {page_num} (space ratio: {space_ratio:.2%}), attempting to fix..."
                    )
                    # Remove spaces between alphanumeric characters that are part of words
                    # Pattern: space between single alphanumeric characters -> remove space
                    # This fixes "B e z o s" -> "Bezos" by removing spaces between single chars
                    # Multiple passes needed: "B e z" -> "Be z" -> "Bez" (each pass fixes one space)
                    for _ in range(10):  # Multiple passes to catch all cases (10 should be enough for long corrupted words)
                        old_page_text = page_text
                        # Match: single alphanumeric, space, single alphanumeric
                        page_text = re.sub(r"([A-Za-z0-9]) ([A-Za-z0-9])", r"\1\2", page_text)
                        if page_text == old_page_text:
                            break
                    self.logger.info(f"Applied fix for PDF extraction corruption on page {page_num}")
                    std_logger.info(f"Applied fix for PDF extraction corruption on page {page_num}")

            cleaned_pages.append({"page": page_num, "text": page_text})

        # Combine pages back into single text for optimization (which works at document level)
        # Add page markers back so they can be detected during re-splitting after optimization
        # This preserves page information through the optimization step
        cleaned = "\n".join([f"\n=== PAGE {p['page']} ===\n{p['text']}" for p in cleaned_pages])

        # Store page mapping for later use in chunk creation
        # We'll need to map chunk positions back to page numbers
        self._page_boundaries = []
        offset = 0
        for p in cleaned_pages:
            self._page_boundaries.append({"page": p["page"], "start": offset, "end": offset + len(p["text"])})
            offset += len(p["text"]) + 2  # +2 for "\n\n" separator

        # Apply pattern-based optimization at document level (fast, free)
        # LLM/hybrid optimization will be applied per-chunk after chunking
        preprocessing_flags = {}
        optimization_mode = "pattern"  # Default to pattern-based
        llm_config = None
        quality_threshold = 75

        if chunking_config:
            preprocessing_flags = chunking_config.get("preprocessing_flags", {})
            optimization_mode = chunking_config.get("optimization_mode", "pattern")
            quality_threshold = preprocessing_flags.get("llm_quality_threshold", 75)

            # Prepare LLM config if LLM or hybrid mode is enabled (for per-chunk optimization)
            if optimization_mode in ["llm", "hybrid"]:
                # Try to get LLM API key from workspace settings first, then environment
                llm_api_key = None

                # Get workspace_id and db from cached context (set in execute method)
                workspace_id = None
                db_session = None

                if hasattr(self, "_context_cache"):
                    workspace_id = self._context_cache.get("workspace_id")
                    db_session = self._context_cache.get("db")

                # Try to get from workspace settings
                if workspace_id and db_session:
                    try:
                        from uuid import UUID as UUIDType

                        from primedata.db.models import Workspace

                        # Convert string UUID to UUID object if needed
                        if isinstance(workspace_id, str):
                            workspace_id = UUIDType(workspace_id)

                        workspace = db_session.query(Workspace).filter(Workspace.id == workspace_id).first()

                        if workspace and workspace.settings:
                            llm_api_key = workspace.settings.get("openai_api_key")
                            if llm_api_key:
                                self.logger.info(
                                    f"✅ Using OpenAI API key from workspace settings for {optimization_mode} optimization (per-chunk)"
                                )
                                std_logger.info(
                                    f"✅ Using OpenAI API key from workspace settings for {optimization_mode} optimization (per-chunk)"
                                )
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch API key from workspace settings: {e}")
                        std_logger.warning(f"Failed to fetch API key from workspace settings: {e}")

                # Fallback to environment variable if not found in workspace settings
                if not llm_api_key:
                    import os

                    llm_api_key = os.getenv("OPENAI_API_KEY")
                    if llm_api_key:
                        self.logger.info(
                            f"✅ Using OPENAI_API_KEY from environment variable for {optimization_mode} optimization (per-chunk)"
                        )
                        std_logger.info(
                            f"✅ Using OPENAI_API_KEY from environment variable for {optimization_mode} optimization (per-chunk)"
                        )

                if llm_api_key:
                    llm_config = {
                        "api_key": llm_api_key,
                        "model": preprocessing_flags.get("llm_model", "gpt-4-turbo-preview"),
                        "base_url": preprocessing_flags.get("llm_base_url"),  # Optional
                    }
                else:
                    self.logger.warning(
                        f"⚠️ Optimization mode is '{optimization_mode}' but OPENAI_API_KEY not found in workspace settings or environment. "
                        "Falling back to pattern-based optimization."
                    )
                    std_logger.warning(
                        f"⚠️ Optimization mode is '{optimization_mode}' but OPENAI_API_KEY not found in workspace settings or environment. "
                        "Falling back to pattern-based optimization."
                    )
                    optimization_mode = "pattern"  # Fallback to pattern-based

        # Apply pattern-based optimization at document level (fast, free, handles most issues)
        # This improves the base text quality before chunking
        if optimization_mode in ["pattern", "llm", "hybrid"]:
            try:
                from primedata.ingestion_pipeline.aird_stages.optimization.pattern_based import PatternBasedOptimizer

                pattern_optimizer = PatternBasedOptimizer()
                cleaned = pattern_optimizer.optimize(cleaned, preprocessing_flags)

                self.logger.info(f"✅ Pattern-based optimization applied at document level")
                std_logger.info(f"✅ Pattern-based optimization applied at document level")

            except ImportError as e:
                self.logger.warning(f"Pattern optimizer not available ({e}). Using legacy pattern-based optimization.")
                std_logger.warning(f"Pattern optimizer not available ({e}). Using legacy pattern-based optimization.")
                # Fallback to legacy pattern-based optimization
                if preprocessing_flags.get("enhanced_normalization"):
                    from primedata.ingestion_pipeline.aird_stages.utils.text_processing import apply_enhanced_normalization

                    self.logger.info("Applying enhanced normalization (legacy method)")
                    std_logger.info("Applying enhanced normalization (legacy method)")
                    cleaned = apply_enhanced_normalization(cleaned)

                if preprocessing_flags.get("error_correction"):
                    from primedata.ingestion_pipeline.aird_stages.utils.text_processing import apply_error_correction

                    self.logger.info("Applying error correction (legacy method)")
                    std_logger.info("Applying error correction (legacy method)")
                    cleaned = apply_error_correction(cleaned)
            except Exception as e:
                self.logger.error(f"Pattern-based optimization failed: {e}. Using original text.", exc_info=True)
                std_logger.error(f"Pattern-based optimization failed: {e}. Using original text.", exc_info=True)
                # Continue with original cleaned text

        # Store optimization config for per-chunk LLM optimization (if needed)
        self._optimization_config = {
            "mode": optimization_mode,
            "llm_config": llm_config,
            "quality_threshold": quality_threshold,
            "preprocessing_flags": preprocessing_flags,
        }

        # Re-split into pages after optimization (text structure should be preserved)
        # Use the page boundaries we stored earlier, or re-detect if markers are still present
        # Since we combined pages earlier, we need to re-split the optimized text
        # If page markers were preserved in optimization, they'll be detected; otherwise we'll use stored boundaries
        if hasattr(self, "_page_boundaries") and self._page_boundaries:
            # Use stored page boundaries to map back to page numbers
            # For now, re-split and hope markers are still there, or use stored page info
            pages = split_pages_by_config(cleaned, playbook.get("page_fences", []))
            # If re-split only found 1 page, use stored page boundaries
            if len(pages) == 1 and len(self._page_boundaries) > 1:
                # Fall back to stored page info - split by stored boundaries
                pages = []
                text_offset = 0
                for boundary in self._page_boundaries:
                    page_text = cleaned[boundary["start"] : min(boundary["end"], len(cleaned))]
                    if page_text.strip():
                        pages.append({"page": boundary["page"], "text": page_text})
                    text_offset = boundary["end"]
        else:
            # No stored boundaries, just re-split normally
            pages = split_pages_by_config(cleaned, playbook.get("page_fences", []))

        # Validate that we have pages with content
        if not pages:
            error_msg = f"No pages found after optimization and re-splitting for {file_stem}. Original text length: {len(raw_text)}, Cleaned text length: {len(cleaned)}"
            self.logger.error(error_msg)
            std_logger.error(error_msg)
            return [], {
                "error": "No pages after processing",
                "sections": 0,
                "chunks": 0,
                "sections_detected": 0,
                "mid_sentence_ends": 0,
                "chunking_config_used": None,
            }
        
        # Check if all pages are empty
        pages_with_content = [p for p in pages if p.get("text", "").strip()]
        if not pages_with_content:
            error_msg = (
                f"All pages are empty after processing for {file_stem}. "
                f"Original text length: {len(raw_text)}, Cleaned text length: {len(cleaned)}. "
                f"Total pages: {len(pages)}"
            )
            self.logger.error(error_msg)
            std_logger.error(error_msg)
            return [], {
                "error": "All pages empty after processing",
                "sections": 0,
                "chunks": 0,
                "sections_detected": 0,
                "mid_sentence_ends": 0,
                "chunking_config_used": None,
            }
        
        # Use pages with content
        if len(pages_with_content) < len(pages):
            self.logger.warning(
                f"After processing: {len(pages_with_content)} pages with content (out of {len(pages)} total). "
                f"Some pages were empty and will be skipped."
            )
            std_logger.warning(
                f"After processing: {len(pages_with_content)} pages with content (out of {len(pages)} total)"
            )
        pages = pages_with_content
        self.logger.info(f"Processing {len(pages)} pages with content for {file_stem}")
        std_logger.info(f"Processing {len(pages)} pages with content for {file_stem}")
        
        # Log page content summary for debugging
        if pages:
            total_chars = sum(len(p.get("text", "")) for p in pages)
            avg_chars_per_page = total_chars // len(pages) if pages else 0
            self.logger.info(
                f"📄 Page summary for {file_stem}: {len(pages)} pages, "
                f"total_chars={total_chars:,}, avg_chars_per_page={avg_chars_per_page:,}"
            )
            std_logger.info(
                f"📄 Page summary: {len(pages)} pages, total_chars={total_chars:,}"
            )
            # Log preview of first page
            if pages[0].get("text"):
                first_page_preview = pages[0]["text"][:200].replace("\n", " ")
                self.logger.info(f"First page preview (page {pages[0].get('page', '?')}): {first_page_preview}...")
        else:
            self.logger.error(f"⚠️ No pages with content found for {file_stem} after processing!")
            std_logger.error(f"⚠️ No pages with content found for {file_stem}")

        # Check for enhanced metadata extraction flag from chunking_config
        preprocessing_flags = {}
        if chunking_config:
            preprocessing_flags = chunking_config.get("preprocessing_flags", {})

        # 3) Get chunking config (product config overrides playbook defaults)
        playbook_chunking = playbook.get("chunking", {})

        # Ensure chunking_config is a valid dict (fix for None or invalid values)
        if not chunking_config or not isinstance(chunking_config, dict):
            self.logger.warning(
                f"chunking_config is {type(chunking_config).__name__}, initializing with defaults"
            )
            chunking_config = {
                "mode": "auto",
                "auto_settings": {"content_type": "general", "model_optimized": True, "confidence_threshold": 0.7},
                "manual_settings": {
                    "chunk_size": 1000,
                    "chunk_overlap": 200,
                    "min_chunk_size": 100,
                    "max_chunk_size": 2000,
                    "chunking_strategy": "fixed_size",
                },
            }

        # Track the resolved chunking configuration actually used
        resolved_chunking_config: Dict[str, Any] = {
            "mode": chunking_config.get("mode", "auto"),
            "source": None,  # manual | product_auto | playbook_default
        }

        # Priority: Product manual settings > Product auto settings > Playbook defaults
        if chunking_config and chunking_config.get("mode") == "manual":
            manual_settings = chunking_config.get("manual_settings", {})
            # Get original strategy from manual_settings (preserve UI value)
            original_strategy = manual_settings.get("chunking_strategy", playbook_chunking.get("strategy", "sentence"))

            # chunk_size is already in tokens, use it directly as max_tokens
            max_tokens = int(manual_settings.get("chunk_size", playbook_chunking.get("max_tokens", 900)))
            # chunk_overlap is already in tokens
            chunk_overlap = int(manual_settings.get("chunk_overlap", 200))
            # Estimate: 1 sentence ≈ 20 tokens, so overlap_sentences = chunk_overlap / 20
            overlap_sents = max(1, int(chunk_overlap / 20))
            # Convert tokens to chars for hard_overlap: 1 token ≈ 4 chars
            hard_overlap = chunk_overlap * 4

            # Convert strategy for playbook processing (internal use only)
            strategy = original_strategy.lower()
            # Map fixed_size to char_chunk, semantic/sentence to sentence for playbook
            if strategy == "fixed_size":
                playbook_strategy = "char"
            elif strategy == "semantic":
                # Use paragraph chunking for semantic to better preserve context
                playbook_strategy = "paragraph"
            elif strategy == "paragraph_boundary":
                playbook_strategy = "paragraph"
            elif strategy in ["sentence", "sentence_boundary"]:
                playbook_strategy = "sentence"
            elif strategy == "recursive":
                playbook_strategy = "sentence"  # Recursive not directly supported, use sentence
            else:
                playbook_strategy = playbook_chunking.get("strategy", "sentence")

            # Store resolved config with ORIGINAL strategy from UI (not converted playbook strategy)
            resolved_chunking_config.update(
                {
                    "source": "manual",
                    "chunk_size": max_tokens,
                    "chunk_overlap": chunk_overlap,
                    "min_chunk_size": int(manual_settings.get("min_chunk_size", playbook_chunking.get("min_chunk_size", 100))),
                    "max_chunk_size": int(
                        manual_settings.get("max_chunk_size", playbook_chunking.get("max_chunk_size", 2000))
                    ),
                    "chunking_strategy": original_strategy,  # Preserve original UI value (semantic, fixed_size, etc.)
                }
            )
            
            # For manual mode, try to infer domain_type from resolved config if available
            detected_domain_type = None
            if chunking_config:
                resolved = chunking_config.get("resolved_settings", {})
                detected_domain_type = resolved.get("content_type")

            # Use playbook_strategy for actual chunking processing
            strategy = playbook_strategy
        elif chunking_config and chunking_config.get("mode") == "auto":
            # Auto mode: Check if resolved_settings already exist from auto-detection in task_preprocess
            # This avoids redundant content analysis and uses the pre-detected values
            resolved_settings = chunking_config.get("resolved_settings", {})
            
            # Ensure manual_settings exists with defaults (fix for missing structure after vector_creation_enabled changes)
            manual_settings = chunking_config.get("manual_settings", {})
            if not manual_settings or not isinstance(manual_settings, dict):
                # Fallback to defaults if manual_settings is missing or invalid
                manual_settings = {
                    "chunk_size": 1000,
                    "chunk_overlap": 200,
                    "min_chunk_size": 100,
                    "max_chunk_size": 2000,
                    "chunking_strategy": "fixed_size",
                }
                chunking_config["manual_settings"] = manual_settings
                self.logger.info(f"✅ Initialized missing manual_settings with defaults: {manual_settings}")
                std_logger.info(f"✅ Initialized missing manual_settings with defaults")
            
            if resolved_settings and isinstance(resolved_settings, dict):
                # Use existing resolved_settings from task_preprocess auto-detection
                self.logger.info(
                    f"✅ Using existing resolved_settings from auto-detection: "
                    f"content_type={resolved_settings.get('content_type')}, "
                    f"chunk_size={resolved_settings.get('chunk_size')}, "
                    f"chunking_strategy={resolved_settings.get('chunking_strategy')}"
                )
                std_logger.info(
                    f"✅ Using existing resolved_settings from auto-detection"
                )
                
                # Extract values from resolved_settings
                chunk_size = resolved_settings.get("chunk_size", 1000)
                chunk_overlap = resolved_settings.get("chunk_overlap", 200)
                min_chunk_size = resolved_settings.get("min_chunk_size", 100)
                max_chunk_size = resolved_settings.get("max_chunk_size", 2000)
                strategy = resolved_settings.get("chunking_strategy", "fixed_size")
                content_type = resolved_settings.get("content_type", "general")
                confidence = resolved_settings.get("confidence", 0.5)
                reasoning = resolved_settings.get("reasoning", "Auto-detected from sample files")
                evidence = resolved_settings.get("evidence")
                
                # Allow manual_settings to override if explicitly provided
                if manual_settings.get("chunk_size"):
                    chunk_size = manual_settings["chunk_size"]
                    self.logger.info(f"Overriding chunk_size with manual_settings: {chunk_size}")
                if manual_settings.get("chunk_overlap"):
                    chunk_overlap = manual_settings["chunk_overlap"]
                if manual_settings.get("min_chunk_size"):
                    min_chunk_size = manual_settings["min_chunk_size"]
                if manual_settings.get("max_chunk_size"):
                    max_chunk_size = manual_settings["max_chunk_size"]
                if manual_settings.get("chunking_strategy"):
                    strategy = manual_settings["chunking_strategy"]
                    self.logger.info(f"Overriding chunking_strategy with manual_settings: {strategy}")
            else:
                # No resolved_settings, analyze content now (should only happen if auto-detection was skipped)
                self.logger.info("No resolved_settings found, running content analysis in preprocessing stage")
                std_logger.info("No resolved_settings found, running content analysis")
                
                # Sample cleaned text for analysis (use up to 20k chars for good detection)
                sample_text = cleaned[:20000] if len(cleaned) > 20000 else cleaned
                
                # Extract playbook hint (map playbook_id to domain hint)
                playbook_hint = None
                playbook_id_lower = playbook_id.lower() if playbook_id else ""
                if "regulatory" in playbook_id_lower or playbook_id_lower in ["regulatory", "reg"]:
                    playbook_hint = "regulatory"
                elif "finance" in playbook_id_lower or "banking" in playbook_id_lower or playbook_id_lower in ["finance", "banking"]:
                    playbook_hint = "finance_banking"
                elif "legal" in playbook_id_lower:
                    playbook_hint = "legal"
                elif "academic" in playbook_id_lower:
                    playbook_hint = "academic"
                elif "technical" in playbook_id_lower or playbook_id_lower == "tech":
                    playbook_hint = "technical"
                
                # Analyze content using ContentAnalyzer
                try:
                    detected_config = content_analyzer.analyze_content(
                        content=sample_text,
                        filename=filename,
                        hint=playbook_hint
                    )
                    
                    # Use detected configuration
                    chunk_size = detected_config.chunk_size
                    chunk_overlap = detected_config.chunk_overlap
                    min_chunk_size = detected_config.min_chunk_size
                    max_chunk_size = detected_config.max_chunk_size
                    strategy = detected_config.strategy.value  # Convert enum to string
                    content_type = detected_config.content_type.value  # Convert enum to string
                    confidence = detected_config.confidence
                    reasoning = detected_config.reasoning
                    evidence = detected_config.evidence
                    
                    self.logger.info(
                        f"✅ Content analysis detected: {content_type} (confidence: {confidence:.2f}, strategy: {strategy}, "
                        f"chunk_size: {chunk_size}, overlap: {chunk_overlap})"
                    )
                    std_logger.info(
                        f"✅ Content analysis detected: {content_type} (confidence: {confidence:.2f}, strategy: {strategy}, "
                        f"chunk_size: {chunk_size}, overlap: {chunk_overlap})"
                    )
                    
                    # Allow manual_settings to override if provided
                    if manual_settings.get("chunk_size"):
                        chunk_size = manual_settings["chunk_size"]
                    if manual_settings.get("chunk_overlap"):
                        chunk_overlap = manual_settings["chunk_overlap"]
                    if manual_settings.get("min_chunk_size"):
                        min_chunk_size = manual_settings["min_chunk_size"]
                    if manual_settings.get("max_chunk_size"):
                        max_chunk_size = manual_settings["max_chunk_size"]
                    if manual_settings.get("chunking_strategy"):
                        strategy = manual_settings["chunking_strategy"]
                        
                except Exception as e:
                    # Fallback to default if analysis fails
                    self.logger.warning(f"Content analysis failed: {e}. Falling back to default configuration.", exc_info=True)
                    std_logger.warning(f"Content analysis failed: {e}. Falling back to default configuration.")
                    
                    # Fallback to general config
                    chunk_size = 1000
                    chunk_overlap = 200
                    min_chunk_size = 100
                    max_chunk_size = 2000
                    strategy = "fixed_size"
                    content_type = "general"
                    confidence = 0.3
                    reasoning = "Fallback to default due to analysis error"
                    evidence = None

            # Store domain_type for use when building records
            detected_domain_type = content_type  # Store for later use
            strategy_lower = strategy.lower()
            if strategy_lower == "fixed_size":
                playbook_strategy = "char"
            elif strategy_lower == "semantic":
                # Use paragraph chunking for semantic to better preserve context
                playbook_strategy = "paragraph"
            elif strategy_lower == "paragraph_boundary":
                playbook_strategy = "paragraph"
            elif strategy_lower in ["sentence", "sentence_boundary"]:
                playbook_strategy = "sentence"
            elif strategy_lower == "recursive":
                playbook_strategy = "sentence"  # Recursive not directly supported, use sentence
            else:
                playbook_strategy = playbook_chunking.get("strategy", "sentence")

            # chunk_size is already in tokens, use it directly as max_tokens
            max_tokens = int(chunk_size) if chunk_size else int(playbook_chunking.get("max_tokens", 900))
            # Estimate: 1 sentence ≈ 20 tokens, so overlap_sentences = chunk_overlap / 20
            overlap_sents = max(1, int(chunk_overlap / 20))  # 1 sentence ≈ 20 tokens
            # Convert tokens to chars for hard_overlap: 1 token ≈ 4 chars
            hard_overlap = chunk_overlap * 4

            # Store resolved config with detection evidence
            resolved_chunking_config.update(
                {
                    "source": "product_auto",
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "min_chunk_size": min_chunk_size,
                    "max_chunk_size": max_chunk_size,
                    "chunking_strategy": strategy,  # Preserve original UI value
                    "content_type": content_type,  # Store detected content type
                    "detection_confidence": confidence,  # Store confidence score
                    "detection_reasoning": reasoning,  # Store reasoning
                    "detection_evidence": evidence,  # Store evidence for UI
                }
            )

            # Use playbook_strategy for actual chunking processing
            strategy = playbook_strategy
        else:
            # Fallback to playbook defaults
            max_tokens = int(playbook_chunking.get("max_tokens", 900))
            overlap_sents = int(playbook_chunking.get("overlap_sentences", 2))
            hard_overlap = int(playbook_chunking.get("hard_overlap_chars", 300))
            strategy = (playbook_chunking.get("strategy", "sentence") or "sentence").lower()
            resolved_chunking_config.update(
                {
                    "source": "playbook_default",
                    "chunk_size": max_tokens,
                    "chunk_overlap": overlap_sents * 20,  # approximate tokens
                    "min_chunk_size": int(playbook_chunking.get("min_chunk_size", 100)),
                    "max_chunk_size": int(playbook_chunking.get("max_chunk_size", 2000)),
                    "chunking_strategy": "fixed_size" if strategy == "char" else "semantic",
                }
            )
            # For manual/playbook_default mode, try to infer domain_type from resolved config if available
            detected_domain_type = None
            if chunking_config:
                resolved = chunking_config.get("resolved_settings", {})
                detected_domain_type = resolved.get("content_type")

        # 4) Process pages and sections
        records: List[Dict[str, Any]] = []
        sections_detected = 0
        mid_sentence_ends = 0

        # Log chunking configuration being used
        self.logger.info(
            f"📊 Chunking configuration for {file_stem}: "
            f"strategy={strategy}, max_tokens={max_tokens}, "
            f"overlap_sents={overlap_sents}, hard_overlap={hard_overlap}"
        )
        std_logger.info(
            f"📊 Chunking config: strategy={strategy}, max_tokens={max_tokens}"
        )

        # First, estimate total chunks for progress tracking
        estimated_chunks = 0
        total_text_length = 0
        for page_data in pages:
            page_text = page_data["text"]
            total_text_length += len(page_text)
            try:
                sections = detect_sections_configured(
                    page_text,
                    playbook.get("headers", []),
                    playbook.get("section_aliases", {}),
                )
                for title_raw, canon_section, body_text in sections:
                    if strategy == "paragraph":
                        para_overlap = max(1, int(overlap_sents / 2))
                        chunks = paragraph_chunk(body_text, max_tokens, para_overlap, hard_overlap)
                    elif strategy == "sentence":
                        chunks = sentence_chunk(body_text, max_tokens, overlap_sents, hard_overlap)
                    elif strategy == "char":
                        chunks = char_chunk(body_text, max_tokens, hard_overlap)
                    else:
                        chunks = sentence_chunk(body_text, max_tokens, overlap_sents, hard_overlap)
                    estimated_chunks += len(chunks)
            except Exception as e:
                self.logger.warning(f"Error estimating chunks for page {page_data.get('page', '?')}: {e}", exc_info=True)
                # Continue with estimation

        # Log initial progress info
        opt_config = getattr(self, "_optimization_config", None)
        opt_mode = opt_config.get("mode", "pattern") if opt_config else "pattern"
        if opt_mode in ["llm", "hybrid"]:
            self.logger.info(
                f"📊 Starting chunk processing: ~{estimated_chunks} chunks, ~{total_text_length:,} characters, mode={opt_mode}"
            )
            std_logger.info(
                f"📊 Starting chunk processing: ~{estimated_chunks} chunks, ~{total_text_length:,} characters, mode={opt_mode}"
            )

        # Track progress for periodic logging
        chunks_processed = 0
        chars_processed = 0
        last_progress_log_time = datetime.utcnow()
        PROGRESS_LOG_INTERVAL = 20  # Log progress every N chunks

        for page_data in pages:
            page_text = page_data["text"]
            page_num = page_data["page"]

            # Validate page has content
            if not page_text.strip():
                self.logger.warning(f"Skipping empty page {page_num} for {file_stem}")
                std_logger.warning(f"Skipping empty page {page_num} for {file_stem}")
                continue

            # Detect sections
            try:
                sections = detect_sections_configured(
                    page_text,
                    playbook.get("headers", []),
                    playbook.get("section_aliases", {}),
                )
                sections_detected += len(sections)
                
                # Log if no sections detected
                if not sections:
                    self.logger.warning(
                        f"No sections detected on page {page_num} for {file_stem}. "
                        f"Page text length: {len(page_text)}, Preview: {page_text[:100]}..."
                    )
                    std_logger.warning(
                        f"No sections detected on page {page_num} for {file_stem}. "
                        f"Text length: {len(page_text)}"
                    )
                    # Log first few lines of page text to help diagnose
                    if page_text:
                        first_lines = "\n".join(page_text.split("\n")[:3])
                        self.logger.debug(f"First 3 lines of page {page_num}: {first_lines}")
                    continue
            except Exception as e:
                self.logger.error(
                    f"Error detecting sections on page {page_num} for {file_stem}: {e}",
                    exc_info=True
                )
                std_logger.error(
                    f"Error detecting sections on page {page_num}: {e}"
                )
                continue

            # Process each section
            for title_raw, canon_section, body_text in sections:
                # Validate section has content
                if not body_text.strip():
                    self.logger.warning(
                        f"Skipping empty section '{canon_section}' on page {page_num} for {file_stem}"
                    )
                    std_logger.warning(
                        f"Skipping empty section '{canon_section}' on page {page_num} for {file_stem}"
                    )
                    continue
                # Chunk the section based on strategy
                if strategy == "paragraph":
                    # Use paragraph overlap (approximately 1 paragraph for overlap)
                    para_overlap = max(1, int(overlap_sents / 2))  # Convert sentence overlap to paragraph overlap
                    chunks = paragraph_chunk(body_text, max_tokens, para_overlap, hard_overlap)
                elif strategy == "sentence":
                    chunks = sentence_chunk(body_text, max_tokens, overlap_sents, hard_overlap)
                elif strategy == "char":
                    # Use character-based chunking for fixed_size strategy
                    chunks = char_chunk(body_text, max_tokens, hard_overlap)
                else:
                    # Default to sentence chunking for unknown strategies
                    chunks = sentence_chunk(body_text, max_tokens, overlap_sents, hard_overlap)

                # Log if chunks are empty
                if not chunks:
                    self.logger.warning(
                        f"No chunks created for section '{canon_section}' on page {page_num} for {file_stem}. "
                        f"Body text length: {len(body_text)}, Strategy: {strategy}, Max tokens: {max_tokens}, "
                        f"Overlap sentences: {overlap_sents}, Hard overlap: {hard_overlap}"
                    )
                    std_logger.warning(
                        f"No chunks created for section '{canon_section}' on page {page_num} for {file_stem}"
                    )
                    continue
                
                # Log first few chunks for debugging
                if chunks_processed == 0:
                    self.logger.info(
                        f"First chunk created: section='{canon_section}', page={page_num}, "
                        f"chunk_length={len(chunks[0])}, total_chunks_in_section={len(chunks)}"
                    )
                    std_logger.info(
                        f"First chunk created: section='{canon_section}', page={page_num}"
                    )

                # Build records for each chunk
                for idx, chunk_text in enumerate(chunks):
                    # Check for mid-sentence boundary (improved regex)
                    # Look for sentence-ending punctuation followed by optional quotes/parentheses and whitespace/newline
                    # Also check if chunk ends with a complete word (not mid-word)
                    chunk_stripped = chunk_text.strip()
                    chunk_tokens = tokens_estimate(chunk_text)
                    
                    ends_with_punctuation = bool(re.search(r"[.!?]['\")\]]*\s*$", chunk_stripped))
                    ends_with_word_boundary = bool(re.search(r"\w\s*$", chunk_stripped))  # Ends with word char + optional whitespace
                    
                    # Consider it mid-sentence if:
                    # 1. Doesn't end with sentence punctuation, AND
                    # 2. Doesn't end at a natural word boundary (or is very short)
                    is_mid_sentence = not ends_with_punctuation and (not ends_with_word_boundary or len(chunk_stripped) < 20)
                    
                    if is_mid_sentence:
                        mid_sentence_ends += 1
                        # Diagnostic logging for mid-sentence breaks
                        if chunks_processed < 10 or mid_sentence_ends <= 5:  # Log first few for diagnostics
                            self.logger.warning(
                                f"⚠️ Mid-sentence break detected in chunk {chunks_processed + 1} "
                                f"(section: {canon_section}, page: {page_num}, tokens: {chunk_tokens}): "
                                f"'{chunk_stripped[-50:]}...'"
                            )
                    
                    # Diagnostic logging: log chunk statistics periodically
                    if chunks_processed < 5 or (chunks_processed % 50 == 0):
                        self.logger.info(
                            f"📊 Chunk {chunks_processed + 1}: tokens={chunk_tokens}, "
                            f"chars={len(chunk_text)}, ends_with_punct={ends_with_punctuation}, "
                            f"mid_sentence={is_mid_sentence}"
                        )

                    # Track progress
                    chunks_processed += 1
                    chars_processed += len(chunk_text)

                    # Log progress periodically
                    if opt_mode in ["llm", "hybrid"] and chunks_processed % PROGRESS_LOG_INTERVAL == 0:
                        elapsed_time = (datetime.utcnow() - last_progress_log_time).total_seconds()
                        chunks_per_sec = PROGRESS_LOG_INTERVAL / max(elapsed_time, 0.1)
                        remaining_chunks = estimated_chunks - chunks_processed
                        estimated_remaining_sec = remaining_chunks / max(chunks_per_sec, 0.1)
                        estimated_remaining_min = estimated_remaining_sec / 60

                        progress_msg = (
                            f"📈 Progress: {chunks_processed}/{estimated_chunks} chunks processed "
                            f"({chunks_processed*100//max(estimated_chunks, 1)}%), "
                            f"{chars_processed:,}/{total_text_length:,} chars ({chars_processed*100//max(total_text_length, 1)}%), "
                            f"~{estimated_remaining_min:.1f} min remaining"
                        )
                        self.logger.info(progress_msg)
                        std_logger.info(progress_msg)
                        last_progress_log_time = datetime.utcnow()

                    # Apply per-chunk LLM/hybrid optimization if needed
                    optimized_chunk_text = chunk_text
                    if hasattr(self, "_optimization_config"):
                        opt_config = self._optimization_config
                        opt_mode = opt_config.get("mode", "pattern")

                        # Apply LLM/hybrid optimization per-chunk if mode is llm or hybrid
                        # BUT: Only optimize chunks that need it (quality threshold) and limit total chunks
                        if opt_mode in ["llm", "hybrid"] and opt_config.get("llm_config"):
                            # Initialize stats if not already done
                            if not hasattr(self, "_chunk_optimization_stats"):
                                self._chunk_optimization_stats = {
                                    "total_chunks": 0,
                                    "llm_optimized": 0,
                                    "skipped_high_quality": 0,
                                    "failed": 0,
                                    "pattern_only": 0,
                                    "total_cost": 0.0,
                                }

                            self._chunk_optimization_stats["total_chunks"] += 1

                            # Quick quality check first - skip if already high quality
                            # This avoids unnecessary API calls
                            quality_threshold = opt_config.get("quality_threshold", 75)
                            try:
                                from primedata.ingestion_pipeline.aird_stages.optimization.pattern_based import (
                                    PatternBasedOptimizer,
                                )

                                quick_quality_check = PatternBasedOptimizer()
                                current_quality = quick_quality_check.estimate_quality(chunk_text)

                                # Skip LLM optimization if quality is already above threshold
                                # This significantly speeds up processing for good-quality chunks
                                if current_quality >= quality_threshold:
                                    self._chunk_optimization_stats["skipped_high_quality"] += 1
                                    optimized_chunk_text = chunk_text  # Use as-is
                                else:
                                    # Only optimize chunks that need improvement
                                    try:
                                        from primedata.ingestion_pipeline.aird_stages.optimization.hybrid import (
                                            HybridOptimizer,
                                        )

                                        optimizer = HybridOptimizer()
                                        # Note: pattern_flags is empty because pattern-based optimization
                                        # was already applied at document level. We only need LLM optimization here.
                                        chunk_result = optimizer.optimize(
                                            text=chunk_text,
                                            mode=opt_mode,
                                            pattern_flags={},  # Pattern-based already applied at document level
                                            llm_config=opt_config.get("llm_config"),
                                            quality_threshold=quality_threshold,
                                        )

                                        optimized_chunk_text = chunk_result["optimized_text"]

                                        if chunk_result["method_used"] in ["llm", "hybrid"]:
                                            self._chunk_optimization_stats["llm_optimized"] += 1
                                            self._chunk_optimization_stats["total_cost"] += chunk_result.get("cost", 0.0)
                                        else:
                                            self._chunk_optimization_stats["pattern_only"] += 1

                                    except Exception as e:
                                        self._chunk_optimization_stats["failed"] += 1
                                        self.logger.warning(f"Per-chunk LLM optimization failed for chunk {idx}: {e}")
                                        std_logger.warning(f"Per-chunk LLM optimization failed for chunk {idx}: {e}")
                                        # Use original chunk text on error
                                        optimized_chunk_text = chunk_text
                            except Exception as e:
                                # If quality check fails, try optimization anyway but log warning
                                self.logger.warning(f"Quality check failed for chunk {idx}, attempting optimization: {e}")
                                try:
                                    from primedata.ingestion_pipeline.aird_stages.optimization.hybrid import HybridOptimizer

                                    optimizer = HybridOptimizer()
                                    chunk_result = optimizer.optimize(
                                        text=chunk_text,
                                        mode=opt_mode,
                                        pattern_flags={},
                                        llm_config=opt_config.get("llm_config"),
                                        quality_threshold=quality_threshold,
                                    )
                                    optimized_chunk_text = chunk_result["optimized_text"]
                                    if chunk_result["method_used"] in ["llm", "hybrid"]:
                                        self._chunk_optimization_stats["llm_optimized"] += 1
                                        self._chunk_optimization_stats["total_cost"] += chunk_result.get("cost", 0.0)
                                    else:
                                        self._chunk_optimization_stats["pattern_only"] += 1
                                except Exception as opt_error:
                                    self._chunk_optimization_stats["failed"] += 1
                                    self.logger.warning(f"Per-chunk LLM optimization failed for chunk {idx}: {opt_error}")
                                    optimized_chunk_text = chunk_text

                    # Build record with optimized chunk text
                    rec = _build_record(
                        stem=file_stem,
                        filename=filename,
                        document_id=file_stem,
                        page=page_num,
                        canon_section=canon_section,
                        title_raw=title_raw,
                        text=optimized_chunk_text,
                        chunk_idx=idx,
                        chunk_of=len(chunks),
                        product_id=self.product_id,
                        domain_type=detected_domain_type,  # Pass domain_type for domain-adaptive scoring
                    )
                    
                    # Log domain_type for verification (only log first chunk to avoid spam)
                    if idx == 0:
                        if detected_domain_type:
                            self.logger.info(f"✅ Record {rec['chunk_id']} has domain_type: {detected_domain_type}")
                            std_logger.info(f"✅ Record {rec['chunk_id']} has domain_type: {detected_domain_type}")
                        else:
                            self.logger.warning(f"⚠️ Record {rec['chunk_id']} missing domain_type (detected_domain_type was None)")
                            std_logger.warning(f"⚠️ Record {rec['chunk_id']} missing domain_type")

                    # Enhanced metadata extraction if flag is set
                    if preprocessing_flags.get("force_metadata_extraction") or preprocessing_flags.get(
                        "additional_metadata_fields"
                    ):
                        # Extract additional metadata fields
                        import re as regex_module

                        # Try to extract dates from text
                        date_patterns = [
                            r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",  # MM/DD/YYYY or DD/MM/YYYY
                            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",  # Month DD, YYYY
                            r"\b\d{4}-\d{2}-\d{2}\b",  # ISO format YYYY-MM-DD
                        ]

                        dates_found = []
                        for pattern in date_patterns:
                            matches = regex_module.findall(pattern, chunk_text, regex_module.IGNORECASE)
                            dates_found.extend(matches[:3])  # Limit to 3 dates per chunk

                        if dates_found:
                            rec["doc_date"] = dates_found[0]  # Use first date found
                            # Store all dates in tags if additional fields requested
                            if preprocessing_flags.get("additional_metadata_fields"):
                                existing_tags = rec.get("tags", "")
                                if existing_tags:
                                    rec["tags"] = f"{existing_tags}; dates:{','.join(dates_found[:3])}"
                                else:
                                    rec["tags"] = f"dates:{','.join(dates_found[:3])}"

                        # Extract additional metadata if additional_fields flag is set
                        if preprocessing_flags.get("additional_metadata_fields"):
                            # Extract potential author names (simple pattern: "By Author Name" or "Author: Name")
                            author_pattern = r"(?:By|Author|Written by|Created by):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
                            author_match = regex_module.search(author_pattern, chunk_text, regex_module.IGNORECASE)
                            if author_match:
                                author = author_match.group(1)
                                existing_tags = rec.get("tags", "")
                                if existing_tags:
                                    rec["tags"] = f"{existing_tags}; author:{author}"
                                else:
                                    rec["tags"] = f"author:{author}"

                            # Extract version numbers
                            version_pattern = r"\b(v|version|ver|v\.)\s*(\d+(?:\.\d+)+)\b"
                            version_matches = regex_module.findall(version_pattern, chunk_text, regex_module.IGNORECASE)
                            if version_matches:
                                versions = [m[1] for m in version_matches[:2]]  # Limit to 2 versions
                                existing_tags = rec.get("tags", "")
                                if existing_tags:
                                    rec["tags"] = f"{existing_tags}; versions:{','.join(versions)}"
                                else:
                                    rec["tags"] = f"versions:{','.join(versions)}"

                    # Apply audience rules from playbook
                    aud = rec["audience"]
                    for rule in playbook.get("audience_rules", []) or []:
                        try:
                            pat = rule.get("pattern")
                            if pat and (
                                re.search(pat, title_raw, flags=re.IGNORECASE)
                                or re.search(pat, chunk_text, flags=re.IGNORECASE)
                            ):
                                aud = rule.get("audience", aud)
                                break
                        except re.error:
                            pass
                    rec["audience"] = aud

                    records.append(rec)

        # Log final progress
        if opt_mode in ["llm", "hybrid"]:
            final_progress_msg = (
                f"✅ Chunk processing complete: {chunks_processed} chunks processed, "
                f"{chars_processed:,} characters processed"
            )
            self.logger.info(final_progress_msg)
            std_logger.info(final_progress_msg)

        # Log per-chunk optimization summary if LLM/hybrid mode was used
        if hasattr(self, "_chunk_optimization_stats"):
            stats_data = self._chunk_optimization_stats
            opt_config = self._optimization_config
            opt_mode = opt_config.get("mode", "pattern")

            if opt_mode in ["llm", "hybrid"]:
                summary_msg = (
                    f"✅ Per-chunk optimization summary: "
                    f"{stats_data['llm_optimized']}/{stats_data['total_chunks']} chunks optimized with LLM, "
                    f"{stats_data['skipped_high_quality']} skipped (already high quality ≥75%), "
                    f"{stats_data['pattern_only']} pattern-only, "
                    f"{stats_data['failed']} failed, "
                    f"total cost=${stats_data['total_cost']:.4f}"
                )
                self.logger.info(summary_msg)
                std_logger.info(summary_msg)

            # Reset stats for next document
            delattr(self, "_chunk_optimization_stats")

        # Calculate stats
        total_chunks = len(records)
        mid_sentence_rate = round(mid_sentence_ends / max(total_chunks, 1), 4)

        # Log comprehensive summary
        self.logger.info(
            f"📊 Processing summary for {file_stem}: "
            f"pages={len(pages)}, sections_detected={sections_detected}, "
            f"total_chunks={total_chunks}, mid_sentence_rate={mid_sentence_rate:.4f}"
        )
        std_logger.info(
            f"📊 Summary for {file_stem}: pages={len(pages)}, sections={sections_detected}, chunks={total_chunks}"
        )
        
        # If no records were created, provide detailed diagnostic info
        if total_chunks == 0:
            self.logger.error(
                f"❌ No records created for {file_stem}! "
                f"Pages processed: {len(pages)}, Sections detected: {sections_detected}, "
                f"Strategy: {strategy}, Max tokens: {max_tokens}"
            )
            std_logger.error(
                f"❌ No records created for {file_stem}! "
                f"Pages: {len(pages)}, Sections: {sections_detected}"
            )
            # Log sample page text to help diagnose
            if pages and pages[0].get("text"):
                sample_page = pages[0]["text"]
                self.logger.error(
                    f"Sample page text (first 500 chars): {sample_page[:500]}"
                )

        stats = {
            "playbook_id": playbook_id,
            "sections": sections_detected,
            "chunks": total_chunks,
            "mid_sentence_boundary_rate": mid_sentence_rate,
            "mid_sentence_ends": mid_sentence_ends,
            "chunking_config_used": resolved_chunking_config,
        }

        return records, stats

    def _get_pdf_sample_for_routing(
        self, 
        storage, 
        file_stem: str, 
        storage_key: Optional[str], 
        storage_bucket: Optional[str],
        max_chars: int = 2000
    ) -> Optional[str]:
        """
        Extract sample text from PDF for playbook routing (optimization: only first 2 pages).
        
        Args:
            storage: Storage adapter instance
            file_stem: File stem
            storage_key: Optional storage key
            storage_bucket: Optional storage bucket
            max_chars: Maximum characters to extract
            
        Returns:
            Sample text or None if extraction fails
        """
        try:
            from io import BytesIO
            from primedata.storage.minio_client import get_minio_client
            
            minio_client = get_minio_client()
            bucket = storage_bucket or "primedata-raw"
            key = storage_key or f"{storage._get_raw_prefix()}{file_stem}.pdf"
            
            # Get PDF bytes
            pdf_data = minio_client.get_bytes(bucket, key)
            if not pdf_data:
                return None
            
            # Extract only first 2 pages
            try:
                from pypdf import PdfReader
                pdf_file = BytesIO(pdf_data)
                reader = PdfReader(pdf_file)
                
                text_parts = []
                for i, page in enumerate(reader.pages[:2]):  # Only first 2 pages
                    try:
                        page_text = page.extract_text()
                        text_parts.append(page_text)
                        if len(''.join(text_parts)) > max_chars:
                            break
                    except Exception:
                        continue
                
                sample_text = '\n'.join(text_parts)
                return sample_text[:max_chars] if sample_text else None
            except ImportError:
                # Fallback to PyPDF2
                try:
                    from PyPDF2 import PdfReader
                    pdf_file = BytesIO(pdf_data)
                    reader = PdfReader(pdf_file)
                    text_parts = []
                    for page in reader.pages[:2]:  # Only first 2 pages
                        text_parts.append(page.extract_text())
                    sample_text = '\n'.join(text_parts)
                    return sample_text[:max_chars] if sample_text else None
                except Exception:
                    return None
        except Exception as e:
            self.logger.warning(f"Failed to extract PDF sample for routing: {e}")
            return None

    def _get_text_sample_for_routing(
        self,
        storage,
        file_stem: str,
        storage_key: Optional[str],
        storage_bucket: Optional[str],
        max_chars: int = 2000
    ) -> Optional[str]:
        """
        Get sample text from text file for playbook routing (optimization: only first N chars).
        
        Args:
            storage: Storage adapter instance
            file_stem: File stem
            storage_key: Optional storage key
            storage_bucket: Optional storage bucket
            max_chars: Maximum characters to read
            
        Returns:
            Sample text or None if reading fails
        """
        try:
            from primedata.storage.minio_client import get_minio_client
            
            minio_client = get_minio_client()
            bucket = storage_bucket or "primedata-raw"
            key = storage_key or f"{storage._get_raw_prefix()}{file_stem}.txt"
            
            # Get object bytes
            data = minio_client.get_bytes(bucket, key)
            if not data:
                return None
            
            # Try to decode as UTF-8 and return first max_chars
            try:
                text = data.decode("utf-8", errors="ignore")
                return text[:max_chars]
            except Exception:
                return None
        except Exception as e:
            self.logger.warning(f"Failed to read text sample for routing: {e}")
            return None
