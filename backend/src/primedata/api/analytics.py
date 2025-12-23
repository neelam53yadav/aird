"""
Analytics API endpoints for dashboard metrics and insights.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
import logging

from ..core.security import get_current_user
from ..db.database import get_db
from ..db.models import Product, DataSource, PipelineRun, DqViolation, Workspace, PipelineRunStatus

logger = logging.getLogger(__name__)

router = APIRouter()

class AnalyticsMetrics(BaseModel):
    """Analytics metrics response model."""
    total_products: int
    total_data_sources: int
    total_pipeline_runs: int
    success_rate: float
    avg_processing_time: float
    data_quality_score: float
    recent_activity: List[Dict[str, Any]]
    monthly_stats: List[Dict[str, Any]]

@router.get("/metrics", response_model=AnalyticsMetrics)
async def get_analytics_metrics(
    request: Request,
    workspace_id: str = Query(..., description="Workspace ID"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get analytics metrics for the workspace.
    """
    try:
        # Get workspace
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Basic counts
        total_products = db.query(Product).filter(Product.workspace_id == workspace_id).count()
        total_data_sources = db.query(DataSource).filter(DataSource.workspace_id == workspace_id).count()
        
        # Pipeline runs metrics
        pipeline_runs = db.query(PipelineRun).filter(PipelineRun.workspace_id == workspace_id)
        total_pipeline_runs = pipeline_runs.count()
        
        # Success rate calculation
        successful_runs = pipeline_runs.filter(PipelineRun.status == PipelineRunStatus.SUCCEEDED).count()
        success_rate = (successful_runs / max(total_pipeline_runs, 1)) * 100
        
        # Average processing time (in minutes)
        completed_runs = pipeline_runs.filter(
            and_(
                PipelineRun.status == PipelineRunStatus.SUCCEEDED,
                PipelineRun.started_at.isnot(None),
                PipelineRun.finished_at.isnot(None)
            )
        ).all()
        
        avg_processing_time = 0
        if completed_runs:
            total_time = sum([
                (run.finished_at - run.started_at).total_seconds() 
                for run in completed_runs 
                if run.finished_at and run.started_at
            ])
            avg_processing_time = (total_time / len(completed_runs)) / 60  # Convert to minutes
        
        # Data quality score (based on violations)
        # Get violations through product relationship
        workspace_products = db.query(Product.id).filter(Product.workspace_id == workspace_id).subquery()
        total_violations = db.query(DqViolation).filter(DqViolation.product_id.in_(workspace_products)).count()
        # Simple quality score: higher is better, based on violation rate
        data_quality_score = max(0, 100 - (total_violations * 2))  # Each violation reduces score by 2%
        
        # Recent activity (last 10 pipeline runs)
        recent_runs = pipeline_runs.order_by(desc(PipelineRun.started_at)).limit(10).all()
        recent_activity = []
        
        for run in recent_runs:
            status_icon = "success" if run.status == PipelineRunStatus.SUCCEEDED else "error" if run.status == PipelineRunStatus.FAILED else "warning"
            activity_type = "pipeline"
            
            if run.status == PipelineRunStatus.SUCCEEDED:
                message = f'Product pipeline completed successfully'
            elif run.status == PipelineRunStatus.FAILED:
                message = f'Product pipeline failed'
            else:
                message = f'Product pipeline {run.status.value}'
            
            recent_activity.append({
                "id": str(run.id),
                "type": activity_type,
                "message": message,
                "timestamp": run.started_at.isoformat() if run.started_at else datetime.utcnow().isoformat(),
                "status": status_icon
            })
        
        # Monthly stats (last 4 months)
        monthly_stats = []
        for i in range(4):
            month_start = datetime.utcnow().replace(day=1) - timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            
            month_runs = pipeline_runs.filter(
                and_(
                    PipelineRun.started_at >= month_start,
                    PipelineRun.started_at < month_end
                )
            ).count()
            
            # Estimate data processed (mock calculation)
            data_processed = month_runs * 0.5  # Mock: 0.5TB per run
            
            # Quality score for the month (mock)
            quality_score = max(80, data_quality_score - (i * 2))
            
            monthly_stats.append({
                "month": month_start.strftime("%b"),
                "pipeline_runs": month_runs,
                "data_processed": round(data_processed, 1),
                "quality_score": round(quality_score, 1)
            })
        
        return AnalyticsMetrics(
            total_products=total_products,
            total_data_sources=total_data_sources,
            total_pipeline_runs=total_pipeline_runs,
            success_rate=round(success_rate, 1),
            avg_processing_time=round(avg_processing_time, 1),
            data_quality_score=round(data_quality_score, 1),
            recent_activity=recent_activity,
            monthly_stats=monthly_stats
        )
        
    except Exception as e:
        logger.error(f"Failed to get analytics metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics metrics: {str(e)}"
        )
