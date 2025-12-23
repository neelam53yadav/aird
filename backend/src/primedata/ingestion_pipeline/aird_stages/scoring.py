"""
AIRD scoring stage for PrimeData.

Scores processed chunks and generates per-chunk metrics.
"""

import json
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from loguru import logger

from primedata.ingestion_pipeline.aird_stages.base import AirdStage, StageResult, StageStatus
from primedata.services.trust_scoring import score_record, get_scoring_weights


class ScoringStage(AirdStage):
    """Scoring stage that calculates trust metrics for processed chunks."""
    
    @property
    def stage_name(self) -> str:
        return "scoring"
    
    def get_required_artifacts(self) -> list[str]:
        """Scoring requires processed JSONL files from preprocessing."""
        return ["processed_jsonl"]
    
    def execute(self, context: Dict[str, Any]) -> StageResult:
        """Execute scoring stage.
        
        Args:
            context: Stage execution context with:
                - storage: AirdStorageAdapter
                - processed_files: List of processed file stems
                
        Returns:
            StageResult with scoring metrics
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
                self.logger.warning("No processed files to score")
                return self._create_result(
                    status=StageStatus.SKIPPED,
                    metrics={"reason": "no_processed_files"},
                    started_at=started_at,
                )
        
        self.logger.info(f"Starting scoring for {len(processed_files)} files")
        
        all_metrics: List[Dict[str, Any]] = []
        scored_files = []
        failed_files = []
        total_chunks = 0
        
        # Get scoring weights
        weights = get_scoring_weights()
        
        for file_stem in processed_files:
            try:
                # Load processed JSONL
                records = storage.get_processed_jsonl(file_stem)
                if not records:
                    self.logger.warning(f"Processed JSONL not found for {file_stem}, skipping")
                    failed_files.append(file_stem)
                    continue
                
                # Score each record
                file_metrics = []
                file_tag = f"{file_stem}.jsonl"
                
                for record in records:
                    try:
                        scored = score_record(record, weights)
                        # Add file tag and metadata
                        scored["file"] = file_tag
                        scored["section"] = record.get("section", "unknown")
                        if record.get("chunk_id"):
                            scored["chunk_id"] = record["chunk_id"]
                        if record.get("document_id"):
                            scored["document_id"] = record["document_id"]
                        if record.get("page") is not None:
                            scored["page"] = record["page"]
                        
                        file_metrics.append(scored)
                        total_chunks += 1
                    except Exception as e:
                        self.logger.error(f"Failed to score chunk in {file_stem}: {e}")
                        continue
                
                if file_metrics:
                    all_metrics.extend(file_metrics)
                    scored_files.append(file_stem)
                    
                    # Store per-file metrics
                    storage.put_artifact(
                        f"{file_stem}.score.metrics.json",
                        json.dumps(file_metrics, indent=2),
                        content_type="application/json",
                    )
                else:
                    failed_files.append(file_stem)
                    
            except Exception as e:
                self.logger.error(f"Failed to score {file_stem}: {e}", exc_info=True)
                failed_files.append(file_stem)
        
        if not all_metrics:
            return self._create_result(
                status=StageStatus.FAILED,
                metrics={
                    "scored_files": len(scored_files),
                    "failed_files": len(failed_files),
                    "failed_file_list": failed_files,
                },
                error="No metrics produced from scoring",
                started_at=started_at,
            )
        
        # Store aggregate metrics
        storage.put_metrics_json(all_metrics)
        
        finished_at = datetime.utcnow()
        
        # Calculate aggregate trust score
        trust_scores = [m.get("AI_Trust_Score", 0.0) for m in all_metrics]
        avg_trust_score = round(sum(trust_scores) / len(trust_scores), 4) if trust_scores else 0.0
        
        artifacts = {
            "metrics_json": f"processed/{self.product_id}/v{self.version}/metrics.json",
        }
        
        metrics = {
            "scored_files": len(scored_files),
            "failed_files": len(failed_files),
            "total_chunks": total_chunks,
            "avg_trust_score": avg_trust_score,
            "scored_file_list": scored_files,
        }
        
        return self._create_result(
            status=StageStatus.SUCCEEDED,
            metrics=metrics,
            artifacts=artifacts,
            started_at=started_at,
            finished_at=finished_at,
        )




