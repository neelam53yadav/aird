"""
AIRD fingerprint generation stage for PrimeData.

Generates readiness fingerprints by aggregating chunk-level metrics.
"""

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from loguru import logger

import json
from primedata.ingestion_pipeline.aird_stages.base import AirdStage, StageResult, StageStatus
from primedata.services.fingerprint import generate_fingerprint


class FingerprintStage(AirdStage):
    """Fingerprint stage that aggregates metrics into readiness fingerprints."""

    @property
    def stage_name(self) -> str:
        return "fingerprint"

    def get_required_artifacts(self) -> list[str]:
        """Fingerprint requires metrics from scoring stage."""
        return ["metrics_json"]

    def execute(self, context: Dict[str, Any]) -> StageResult:
        """Execute fingerprint generation stage.

        Args:
            context: Stage execution context with:
                - storage: AirdStorageAdapter
                - scoring_result: Optional result from scoring stage

        Returns:
            StageResult with fingerprint metrics
        """
        started_at = datetime.utcnow()
        storage = context.get("storage")

        if not storage:
            return self._create_result(
                status=StageStatus.FAILED,
                metrics={},
                error="Storage adapter not found in context",
                started_at=started_at,
            )

        try:
            # Load metrics from storage
            metrics = storage.get_metrics_json()
            if not metrics:
                self.logger.warning("No metrics found for fingerprint generation")
                return self._create_result(
                    status=StageStatus.SKIPPED,
                    metrics={"reason": "no_metrics"},
                    started_at=started_at,
                )

            self.logger.info(f"Generating fingerprint from {len(metrics)} metric entries")

            # Generate fingerprint
            fingerprint = generate_fingerprint(metrics)

            if not fingerprint:
                return self._create_result(
                    status=StageStatus.FAILED,
                    metrics={},
                    error="Failed to generate fingerprint",
                    started_at=started_at,
                )

            # Store fingerprint
            fingerprint_path = storage.put_artifact(
                f"fingerprint.json",
                json.dumps({"fingerprint": fingerprint}, indent=2),
                content_type="application/json",
            )

            finished_at = datetime.utcnow()

            # Extract key metrics
            trust_score = fingerprint.get("AI_Trust_Score", 0.0)

            artifacts = {
                "fingerprint_json": fingerprint_path,
            }

            metrics_result = {
                "trust_score": trust_score,
                "metrics_count": len(fingerprint),
                "fingerprint": fingerprint,  # Include full fingerprint in metrics
            }

            return self._create_result(
                status=StageStatus.SUCCEEDED,
                metrics=metrics_result,
                artifacts=artifacts,
                started_at=started_at,
                finished_at=finished_at,
            )

        except Exception as e:
            self.logger.error(f"Fingerprint generation failed: {e}", exc_info=True)
            return self._create_result(
                status=StageStatus.FAILED,
                metrics={},
                error=str(e),
                started_at=started_at,
            )
