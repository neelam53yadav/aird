"""
Analytics API endpoints for dashboard metrics and insights.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..db.database import get_db
from ..db.models import DataSource, DqViolation, PipelineRun, PipelineRunStatus, Product, Workspace

logger = logging.getLogger(__name__)

router = APIRouter()


class ProductInsightsResponse(BaseModel):
    """Product insights response (M2)."""

    fingerprint: Optional[Dict[str, Any]] = None  # Readiness fingerprint (can contain nested structures)
    policy: Optional[Dict[str, Any]] = None  # Policy evaluation result
    optimizer: Optional[Dict[str, Any]] = None  # Optimizer suggestions (M3)
    status: str = "available"  # "available", "draft", "no_data"
    message: Optional[str] = None  # Optional message explaining the status


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
    current_user: dict = Depends(get_current_user),
):
    """
    Get analytics metrics for the workspace.
    """
    try:
        from uuid import UUID
        from ..core.scope import ensure_workspace_access

        # Ensure user has access to the workspace
        workspace_uuid = UUID(workspace_id)
        workspace = ensure_workspace_access(db, request, workspace_uuid)

        # Basic counts - filter by workspace_id (already verified access above)
        total_products = db.query(Product).filter(Product.workspace_id == workspace_uuid).count()
        total_data_sources = db.query(DataSource).filter(DataSource.workspace_id == workspace_uuid).count()

        # Pipeline runs metrics - filter by workspace_id (already verified access above)
        pipeline_runs = db.query(PipelineRun).filter(PipelineRun.workspace_id == workspace_uuid)
        total_pipeline_runs = pipeline_runs.count()

        # Success rate calculation
        successful_runs = pipeline_runs.filter(PipelineRun.status == PipelineRunStatus.SUCCEEDED).count()
        success_rate = (successful_runs / max(total_pipeline_runs, 1)) * 100

        # Average processing time (in minutes)
        completed_runs = pipeline_runs.filter(
            and_(
                PipelineRun.status == PipelineRunStatus.SUCCEEDED,
                PipelineRun.started_at.isnot(None),
                PipelineRun.finished_at.isnot(None),
            )
        ).all()

        avg_processing_time = 0
        if completed_runs:
            total_time = sum(
                [
                    (run.finished_at - run.started_at).total_seconds()
                    for run in completed_runs
                    if run.finished_at and run.started_at
                ]
            )
            avg_processing_time = (total_time / len(completed_runs)) / 60  # Convert to minutes

        # Data quality score (based on violations)
        # Get violations through product relationship - filter by workspace_id (already verified access above)
        workspace_products = db.query(Product.id).filter(Product.workspace_id == workspace_uuid).subquery()
        total_violations = db.query(DqViolation).filter(DqViolation.product_id.in_(workspace_products)).count()
        # Simple quality score: higher is better, based on violation rate
        data_quality_score = max(0, 100 - (total_violations * 2))  # Each violation reduces score by 2%

        # Recent activity (last 10 pipeline runs)
        recent_runs = pipeline_runs.order_by(desc(PipelineRun.started_at)).limit(10).all()
        recent_activity = []

        for run in recent_runs:
            status_icon = (
                "success"
                if run.status == PipelineRunStatus.SUCCEEDED
                else "error" if run.status == PipelineRunStatus.FAILED else "warning"
            )
            activity_type = "pipeline"

            if run.status == PipelineRunStatus.SUCCEEDED:
                message = f"Product pipeline completed successfully"
            elif run.status == PipelineRunStatus.FAILED:
                message = f"Product pipeline failed"
            else:
                message = f"Product pipeline {run.status.value}"

            recent_activity.append(
                {
                    "id": str(run.id),
                    "type": activity_type,
                    "message": message,
                    "timestamp": run.started_at.isoformat() if run.started_at else datetime.utcnow().isoformat(),
                    "status": status_icon,
                }
            )

        # Monthly stats (last 4 months)
        monthly_stats = []
        for i in range(4):
            month_start = datetime.utcnow().replace(day=1) - timedelta(days=30 * i)
            month_end = month_start + timedelta(days=30)

            month_runs = pipeline_runs.filter(
                and_(PipelineRun.started_at >= month_start, PipelineRun.started_at < month_end)
            ).count()

            # Estimate data processed (mock calculation)
            data_processed = month_runs * 0.5  # Mock: 0.5TB per run

            # Quality score for the month (mock)
            quality_score = max(80, data_quality_score - (i * 2))

            monthly_stats.append(
                {
                    "month": month_start.strftime("%b"),
                    "pipeline_runs": month_runs,
                    "data_processed": round(data_processed, 1),
                    "quality_score": round(quality_score, 1),
                }
            )

        return AnalyticsMetrics(
            total_products=total_products,
            total_data_sources=total_data_sources,
            total_pipeline_runs=total_pipeline_runs,
            success_rate=round(success_rate, 1),
            avg_processing_time=round(avg_processing_time, 1),
            data_quality_score=round(data_quality_score, 1),
            recent_activity=recent_activity,
            monthly_stats=monthly_stats,
        )

    except Exception as e:
        logger.error(f"Failed to get analytics metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get analytics metrics: {str(e)}"
        )


@router.get("/products/{product_id}/insights", response_model=ProductInsightsResponse)
async def get_product_insights(
    product_id: UUID, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """
    Get product insights including fingerprint, policy, and optimizer (M2).
    This endpoint is available under /api/v1/analytics/products/{product_id}/insights
    """
    from ..core.scope import ensure_product_access
    from ..ingestion_pipeline.aird_stages.config import get_aird_config
    from ..ingestion_pipeline.aird_stages.storage import AirdStorageAdapter
    from ..services.policy_engine import evaluate_policy

    product = ensure_product_access(db, request, product_id)

    # Get fingerprint (lazy load from S3 if needed)
    from primedata.services.lazy_json_loader import load_product_json_field

    fingerprint_data = load_product_json_field(product, "readiness_fingerprint")
    fingerprint = None

    if fingerprint_data:
        # Handle both old format (nested in metrics) and new format (direct fingerprint)
        if isinstance(fingerprint_data, dict):
            # Check if it's the old format with nested fingerprint
            if "fingerprint" in fingerprint_data and isinstance(fingerprint_data["fingerprint"], dict):
                fingerprint = fingerprint_data["fingerprint"]
            else:
                # New format: fingerprint is directly the metrics dict
                fingerprint = fingerprint_data

    if not fingerprint:
        # Try to load from storage
        try:
            storage = AirdStorageAdapter(
                workspace_id=product.workspace_id,
                product_id=product.id,
                version=product.current_version,
            )

            metrics = storage.get_metrics_json()
            if metrics:
                from ..services.fingerprint import generate_fingerprint

                fingerprint = generate_fingerprint(metrics)
        except Exception as e:
            logger.warning(f"Failed to load fingerprint from storage: {e}")

    # If no fingerprint, return a response indicating the product needs a pipeline run
    if not fingerprint:
        # Check if product is in draft state or has no pipeline runs
        from ..db.models import ProductStatus

        if product.status == ProductStatus.DRAFT or product.current_version <= 0:
            return ProductInsightsResponse(
                fingerprint=None,
                policy=None,
                optimizer=None,
                status="draft",
                message="Product is in draft state. Run a pipeline to generate insights.",
            )
        else:
            return ProductInsightsResponse(
                fingerprint=None,
                policy=None,
                optimizer=None,
                status="no_data",
                message="No fingerprint data available. Run a pipeline to generate insights.",
            )

    # Evaluate policy
    config = get_aird_config()
    thresholds = {
        "min_trust_score": config.policy_min_trust_score,
        "min_secure": config.policy_min_secure,
        "min_metadata_presence": config.policy_min_metadata_presence,
        "min_kb_ready": config.policy_min_kb_ready,
    }

    policy_result = evaluate_policy(fingerprint, thresholds)

    # Optimizer suggestions (M5)
    from ..services.optimizer import suggest_next_config

    optimizer = suggest_next_config(
        fingerprint=fingerprint,
        policy=policy_result,
        current_playbook=product.playbook_id,
    )

    return ProductInsightsResponse(
        fingerprint=fingerprint,
        policy=policy_result,
        optimizer=optimizer,
        status="available",
        message=None,
    )
