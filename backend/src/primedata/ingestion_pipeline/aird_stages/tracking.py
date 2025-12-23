"""
Pipeline stage tracking for AIRD stages.

Tracks stage execution and stores metrics in PipelineRun model.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from loguru import logger

from primedata.db.models import PipelineRun
from .base import StageResult, StageStatus


class StageTracker:
    """Tracks AIRD stage execution and updates PipelineRun metrics."""
    
    def __init__(self, db: Session, pipeline_run: PipelineRun):
        """Initialize tracker.
        
        Args:
            db: Database session
            pipeline_run: PipelineRun model instance
        """
        self.db = db
        self.pipeline_run = pipeline_run
        self.logger = logger.bind(
            pipeline_run_id=str(pipeline_run.id),
            product_id=str(pipeline_run.product_id),
            version=pipeline_run.version,
        )
    
    def record_stage_result(self, result: StageResult) -> None:
        """Record a stage execution result.
        
        Args:
            result: StageResult from stage execution
        """
        # Initialize metrics if not present (JSON field defaults to dict but may be None)
        if self.pipeline_run.metrics is None:
            self.pipeline_run.metrics = {}
        
        # Initialize aird_stages if not present
        if "aird_stages" not in self.pipeline_run.metrics:
            self.pipeline_run.metrics["aird_stages"] = {}
        
        # Store stage result
        stage_data = result.to_dict()
        self.pipeline_run.metrics["aird_stages"][result.stage_name] = stage_data
        
        # Update aird_stages_completed list
        if "aird_stages_completed" not in self.pipeline_run.metrics:
            self.pipeline_run.metrics["aird_stages_completed"] = []
        
        if result.status == StageStatus.SUCCEEDED:
            if result.stage_name not in self.pipeline_run.metrics["aird_stages_completed"]:
                self.pipeline_run.metrics["aird_stages_completed"].append(result.stage_name)
        elif result.status == StageStatus.FAILED:
            # Remove from completed list if it was there
            if result.stage_name in self.pipeline_run.metrics["aird_stages_completed"]:
                self.pipeline_run.metrics["aird_stages_completed"].remove(result.stage_name)
        
        # Update overall pipeline run status based on stage results
        self._update_pipeline_status()
        
        # Commit changes
        self.db.commit()
        
        self.logger.info(
            f"Recorded stage result: {result.stage_name} = {result.status.value}",
            metrics=result.metrics,
        )
    
    def _update_pipeline_status(self) -> None:
        """Update pipeline run status based on stage results."""
        stages = self.pipeline_run.metrics.get("aird_stages", {})
        
        if not stages:
            return
        
        # Check if any stage failed
        has_failed = any(
            stage.get("status") == StageStatus.FAILED.value
            for stage in stages.values()
        )
        
        # Check if all required stages succeeded
        # For now, we'll keep the existing status logic
        # This can be enhanced in future milestones
        if has_failed and self.pipeline_run.status.value == "running":
            # Don't auto-update to failed - let Airflow handle it
            # But we can log it
            self.logger.warning("One or more AIRD stages failed, but keeping pipeline status as running")
    
    def get_stage_result(self, stage_name: str) -> Optional[Dict[str, Any]]:
        """Get result for a specific stage.
        
        Args:
            stage_name: Name of the stage
            
        Returns:
            Stage result dictionary, or None if not found
        """
        stages = self.pipeline_run.metrics.get("aird_stages", {})
        return stages.get(stage_name)
    
    def get_completed_stages(self) -> list[str]:
        """Get list of completed stage names.
        
        Returns:
            List of stage names that have succeeded
        """
        return self.pipeline_run.metrics.get("aird_stages_completed", [])


def track_stage_execution(
    db: Session,
    pipeline_run_id: UUID,
    result: StageResult,
) -> None:
    """Convenience function to track stage execution.
    
    Args:
        db: Database session
        pipeline_run_id: Pipeline run UUID
        result: Stage execution result
    """
    pipeline_run = db.query(PipelineRun).filter(PipelineRun.id == pipeline_run_id).first()
    if not pipeline_run:
        logger.error(f"Pipeline run {pipeline_run_id} not found")
        return
    
    tracker = StageTracker(db, pipeline_run)
    tracker.record_stage_result(result)

