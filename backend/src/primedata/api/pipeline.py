"""
Pipeline API endpoints for PrimeData.

This module provides REST API endpoints for managing data processing pipelines,
including triggering pipeline runs and monitoring their status.
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from primedata.core.scope import ensure_product_access
from primedata.core.security import get_current_user
from primedata.db.database import get_db
from primedata.db.models import Product, PipelineRun, PipelineRunStatus, RawFile, RawFileStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipeline", tags=["Pipeline"])

class PipelineRunRequest(BaseModel):
    """Request model for triggering a pipeline run."""
    product_id: UUID
    version: Optional[int] = None
    force_run: Optional[bool] = False

class PipelineRunResponse(BaseModel):
    """Response model for pipeline run information."""
    id: UUID
    product_id: UUID
    version: int
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    dag_run_id: Optional[str]
    metrics: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True

class TriggerPipelineResponse(BaseModel):
    """Response model for pipeline trigger."""
    product_id: UUID
    version: int
    run_id: UUID
    status: str
    message: str

@router.post("/run", response_model=TriggerPipelineResponse)
async def trigger_pipeline(
    request: PipelineRunRequest,
    request_obj: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger a pipeline run for a product.
    
    **Smart Version Resolution (Enterprise Best Practice)**:
    - If `version` is explicitly provided: Validates that raw files exist for that version
    - If `version` is `None`: Automatically uses the latest ingested version that has raw files
    
    This ensures seamless workflow: users can simply click "Run Pipeline" without 
    manual version coordination. The system automatically processes the latest available data.
    
    **Examples**:
    - Auto-detect: `{"product_id": "...", "version": null}` → Uses latest ingested version
    - Explicit: `{"product_id": "...", "version": 3}` → Processes version 3 (validates files exist)
    """
    # Ensure user has access to the product
    ensure_product_access(db, request_obj, request.product_id)
    
    # Get the product
    product = db.query(Product).filter(Product.id == request.product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Option C: Smart Version Resolution (Enterprise Best Practice)
    # If version is explicitly provided, validate it exists
    # If version is None, auto-detect latest ingested version
    if request.version is not None:
        # Explicit version provided - validate raw files exist
        # Look for files that can be processed: INGESTED, FAILED (can retry), or PROCESSING (stuck, can retry)
        version = request.version
        raw_file_count = db.query(RawFile).filter(
            RawFile.product_id == product.id,
            RawFile.version == version,
            RawFile.status.in_([RawFileStatus.INGESTED, RawFileStatus.FAILED, RawFileStatus.PROCESSING])
        ).count()
        
        if raw_file_count == 0:
            # Provide helpful error message with available versions
            latest_version = db.query(
                func.max(RawFile.version)
            ).filter(
                RawFile.product_id == product.id,
                RawFile.status != RawFileStatus.DELETED
            ).scalar()
            
            # Get all available versions
            available_versions = db.query(
                RawFile.version
            ).filter(
                RawFile.product_id == product.id,
                RawFile.status != RawFileStatus.DELETED
            ).distinct().order_by(RawFile.version.desc()).all()
            
            available_versions_list = [v[0] for v in available_versions] if available_versions else []
            
            error_detail = {
                "message": f"No raw files found for version {version}",
                "requested_version": version,
                "latest_ingested_version": latest_version,
                "available_versions": available_versions_list,
                "suggestion": (
                    f"Please run initial ingestion for version {version}, "
                    f"or use version={latest_version} to process latest ingested data"
                    if latest_version else
                    "Please run initial ingestion first"
                )
            }
            
            logger.warning(
                f"Pipeline trigger failed: No raw files for product {product.id}, version {version}. "
                f"Available versions: {available_versions_list}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_detail
            )
        
        logger.info(f"Using explicit version {version} (validated: {raw_file_count} raw files found)")
    else:
        # Auto-detect: Use latest version with raw files
        latest_raw_file = db.query(RawFile).filter(
            RawFile.product_id == product.id,
            RawFile.status.in_([RawFileStatus.INGESTED, RawFileStatus.FAILED])
        ).order_by(RawFile.version.desc()).first()
        
        if not latest_raw_file:
            # Check if any raw files exist at all (even processed ones)
            any_raw_file = db.query(RawFile).filter(
                RawFile.product_id == product.id,
                RawFile.status != RawFileStatus.DELETED
            ).first()
            
            if any_raw_file:
                error_detail = {
                    "message": "No unprocessed raw files found. All ingested files have been processed or deleted.",
                    "suggestion": "Please run initial ingestion to create a new version with raw files"
                }
            else:
                error_detail = {
                    "message": "No raw files found for this product",
                    "suggestion": "Please run initial ingestion first to upload data"
                }
            
            logger.warning(f"Pipeline trigger failed: No raw files for product {product.id}")
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail
            )
        
        version = latest_raw_file.version
        logger.info(
            f"Auto-detected latest ingested version: {version} "
            f"(found file: {latest_raw_file.filename}, status: {latest_raw_file.status.value})"
        )
    
    # Check if there's already a running pipeline for this version
    existing_run = db.query(PipelineRun).filter(
        PipelineRun.product_id == request.product_id,
        PipelineRun.version == version,
        PipelineRun.status.in_([PipelineRunStatus.QUEUED, PipelineRunStatus.RUNNING])
    ).first()
    
    if existing_run:
        # Check if user wants to force run (override existing)
        force_run = request.force_run
        
        if not force_run:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": f"Pipeline run already exists for product {request.product_id} version {version}",
                    "existing_run_id": str(existing_run.id),
                    "existing_status": existing_run.status.value,
                    "existing_started_at": existing_run.started_at.isoformat() if existing_run.started_at else None,
                    "suggestion": "Use force_run=true to override existing run or wait for current run to complete"
                }
            )
        else:
            # Cancel existing run and start new one
            logger.info(f"Cancelling existing pipeline run {existing_run.id} to start new run")
            existing_run.status = PipelineRunStatus.FAILED
            existing_run.finished_at = datetime.utcnow()
            existing_run.metrics = existing_run.metrics or {}
            existing_run.metrics["cancelled_reason"] = "Replaced by new pipeline run"
            db.commit()
    
    try:
        # Create pipeline run record
        pipeline_run = PipelineRun(
            workspace_id=product.workspace_id,
            product_id=request.product_id,
            version=version,
            status=PipelineRunStatus.QUEUED,
            metrics={}
        )
        db.add(pipeline_run)
        db.commit()
        db.refresh(pipeline_run)
        
        # Get chunking and embedding configuration from product
        chunking_config = product.chunking_config or {}
        embedding_config = product.embedding_config or {}
        
        # Trigger Airflow DAG with configuration
        dag_run_id = await _trigger_airflow_dag(
            workspace_id=product.workspace_id,
            product_id=request.product_id,
            version=version,
            pipeline_run_id=pipeline_run.id,
            chunking_config=chunking_config,
            embedding_config=embedding_config
        )
        
        # Update pipeline run with DAG run ID
        pipeline_run.dag_run_id = dag_run_id
        pipeline_run.status = PipelineRunStatus.RUNNING
        pipeline_run.started_at = datetime.utcnow()
        db.commit()
        
        # Create informative message
        version_source = "explicitly provided" if request.version is not None else "auto-detected (latest ingested)"
        message = (
            f"Pipeline run triggered successfully for version {version} ({version_source}). "
            f"DAG Run ID: {dag_run_id}"
        )
        
        logger.info(f"Triggered pipeline run {pipeline_run.id} for product {request.product_id} version {version} ({version_source})")
        
        return TriggerPipelineResponse(
            product_id=request.product_id,
            version=version,
            run_id=pipeline_run.id,
            status=pipeline_run.status.value,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger pipeline for product {request.product_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger pipeline: {str(e)}"
        )

@router.get("/runs", response_model=List[PipelineRunResponse])
async def list_pipeline_runs(
    product_id: UUID,
    limit: int = 10,
    sync: bool = Query(True, description="Sync with Airflow before returning"),
    request_obj: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List pipeline runs for a product.
    """
    # Ensure user has access to the product
    ensure_product_access(db, request_obj, product_id)
    
    # Sync with Airflow if requested
    if sync:
        _sync_pipeline_runs_with_airflow(db)
    
    # Get pipeline runs
    runs = db.query(PipelineRun).filter(
        PipelineRun.product_id == product_id
    ).order_by(
        PipelineRun.created_at.desc()
    ).limit(limit).all()
    
    return [
        PipelineRunResponse(
            id=run.id,
            product_id=run.product_id,
            version=run.version,
            status=run.status.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
            dag_run_id=run.dag_run_id,
            metrics=run.metrics,
            created_at=run.created_at
        )
        for run in runs
    ]

@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(
    run_id: UUID,
    request_obj: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get details of a specific pipeline run.
    """
    # Get pipeline run
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline run not found"
        )
    
    # Ensure user has access to the product
    ensure_product_access(db, request_obj, run.product_id)
    
    return PipelineRunResponse(
        id=run.id,
        product_id=run.product_id,
        version=run.version,
        status=run.status.value,
        started_at=run.started_at,
        finished_at=run.finished_at,
        dag_run_id=run.dag_run_id,
        metrics=run.metrics,
        created_at=run.created_at
    )

class PipelineRunUpdateRequest(BaseModel):
    """Request model for updating a pipeline run."""
    status: Optional[str] = None
    finished_at: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None

@router.patch("/runs/{run_id}")
async def update_pipeline_run(
    run_id: UUID,
    request_body: PipelineRunUpdateRequest,
    request_obj: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a pipeline run status (used by Airflow DAG).
    """
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline run not found"
        )
    
    # Update fields if provided
    if request_body.status is not None:
        try:
            run.status = PipelineRunStatus(request_body.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {request_body.status}"
            )
    
    if request_body.finished_at is not None:
        try:
            run.finished_at = datetime.fromisoformat(request_body.finished_at.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid finished_at format: {request_body.finished_at}"
            )
    
    if request_body.metrics is not None:
        run.metrics = request_body.metrics
    
    db.commit()
    db.refresh(run)
    
    logger.info(f"Updated pipeline run {run_id} to status {run.status}")
    
    return PipelineRunResponse(
        id=run.id,
        product_id=run.product_id,
        version=run.version,
        status=run.status.value,
        started_at=run.started_at,
        finished_at=run.finished_at,
        dag_run_id=run.dag_run_id,
        metrics=run.metrics,
        created_at=run.created_at
    )

@router.post("/sync")
async def sync_pipeline_runs_with_airflow(
    request_obj: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Manually sync all running pipeline runs with Airflow status.
    """
    try:
        updated_count = _sync_pipeline_runs_with_airflow(db)
        return {
            "message": f"Successfully synced {updated_count} pipeline runs with Airflow",
            "updated_count": updated_count
        }
    except Exception as e:
        logger.error(f"Error in manual sync: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync with Airflow: {str(e)}"
        )

@router.get("/status/{run_id}")
async def get_pipeline_status(
    run_id: UUID,
    request_obj: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get the current status of a pipeline run.
    """
    # Get pipeline run
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline run not found"
        )
    
    # Ensure user has access to the product
    ensure_product_access(db, request_obj, run.product_id)
    
    return {
        "run_id": str(run.id),
        "status": run.status.value,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "dag_run_id": run.dag_run_id,
        "metrics": run.metrics
    }

def _check_airflow_dag_run_status(airflow_url: str, airflow_username: str, airflow_password: str, dag_run_id: str) -> Dict[str, Any]:
    """
    Check the status of a specific DAG run in Airflow.
    Returns the DAG run status and details.
    """
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        
        # Get DAG run status from Airflow REST API
        dag_run_url = f"{airflow_url}/api/v1/dags/primedata_simple/dagRuns/{dag_run_id}"
        
        response = requests.get(
            dag_run_url,
            auth=HTTPBasicAuth(airflow_username, airflow_password),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            dag_run_data = response.json()
            return {
                'status': dag_run_data.get('state', 'unknown'),
                'start_date': dag_run_data.get('start_date'),
                'end_date': dag_run_data.get('end_date'),
                'execution_date': dag_run_data.get('execution_date'),
                'dag_run_id': dag_run_data.get('dag_run_id')
            }
        else:
            logger.error(f"Failed to get DAG run status: {response.status_code} - {response.text}")
            return {'status': 'unknown', 'error': f"HTTP {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Error checking DAG run status: {e}")
        return {'status': 'unknown', 'error': str(e)}

def _sync_pipeline_runs_with_airflow(db: Session) -> int:
    """
    Sync running pipeline runs with Airflow status.
    Returns the number of runs updated.
    """
    try:
        # Get Airflow configuration
        airflow_url = os.getenv('AIRFLOW_URL', 'http://localhost:8080')
        airflow_username = os.getenv('AIRFLOW_USERNAME', 'admin')
        airflow_password = os.getenv('AIRFLOW_PASSWORD', 'admin')
        
        # Get all running pipeline runs
        running_runs = db.query(PipelineRun).filter(
            PipelineRun.status.in_([PipelineRunStatus.RUNNING, PipelineRunStatus.QUEUED])
        ).all()
        
        updated_count = 0
        
        for run in running_runs:
            if not run.dag_run_id:
                continue
                
            # Check Airflow status
            airflow_status = _check_airflow_dag_run_status(
                airflow_url, airflow_username, airflow_password, run.dag_run_id
            )
            
            if airflow_status.get('status') in ['success', 'failed']:
                # Update the pipeline run status
                if airflow_status['status'] == 'success':
                    run.status = PipelineRunStatus.SUCCEEDED
                else:
                    run.status = PipelineRunStatus.FAILED
                
                # Update finished_at if available
                if airflow_status.get('end_date'):
                    try:
                        from datetime import datetime
                        run.finished_at = datetime.fromisoformat(
                            airflow_status['end_date'].replace('Z', '+00:00')
                        )
                    except ValueError:
                        run.finished_at = datetime.utcnow()
                else:
                    run.finished_at = datetime.utcnow()
                
                # Add some basic metrics
                if not run.metrics:
                    run.metrics = {}
                run.metrics['airflow_sync'] = True
                run.metrics['airflow_status'] = airflow_status['status']
                
                updated_count += 1
                logger.info(f"Updated pipeline run {run.id} to status {run.status.value}")
        
        if updated_count > 0:
            db.commit()
            logger.info(f"Synced {updated_count} pipeline runs with Airflow")
        
        return updated_count
        
    except Exception as e:
        logger.error(f"Error syncing pipeline runs with Airflow: {e}")
        return 0

def _ensure_dag_unpaused(airflow_url: str, airflow_username: str, airflow_password: str, dag_id: str) -> bool:
    """
    Ensure a DAG is unpaused. Returns True if successful, False otherwise.
    """
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        
        # Get DAG info
        dag_info_url = f"{airflow_url}/api/v1/dags/{dag_id}"
        dag_info_response = requests.get(
            dag_info_url,
            auth=HTTPBasicAuth(airflow_username, airflow_password),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if dag_info_response.status_code == 200:
            dag_info = dag_info_response.json()
            is_paused = dag_info.get('is_paused', True)
            
            if is_paused:
                logger.info(f"DAG {dag_id} is paused, attempting to unpause")
                unpause_data = {"is_paused": False}
                
                unpause_response = requests.patch(
                    dag_info_url,
                    json=unpause_data,
                    auth=HTTPBasicAuth(airflow_username, airflow_password),
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                
                if unpause_response.status_code == 200:
                    logger.info(f"Successfully unpaused DAG {dag_id}")
                    return True
                else:
                    logger.error(f"Failed to unpause DAG {dag_id}: {unpause_response.status_code} - {unpause_response.text}")
                    return False
            else:
                logger.info(f"DAG {dag_id} is already unpaused")
                return True
        elif dag_info_response.status_code == 404:
            logger.error(f"DAG {dag_id} not found in Airflow")
            return False
        else:
            logger.error(f"Failed to get DAG info for {dag_id}: {dag_info_response.status_code} - {dag_info_response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking/unpausing DAG {dag_id}: {e}")
        return False

async def _trigger_airflow_dag(
    workspace_id: UUID,
    product_id: UUID,
    version: int,
    pipeline_run_id: UUID,
    chunking_config: Dict[str, Any] = None,
    embedding_config: Dict[str, Any] = None
) -> str:
    """
    Trigger Airflow DAG for pipeline execution.
    
    This function creates a trigger file that the Airflow scheduler can read
    to trigger the DAG with the appropriate parameters.
    
    Args:
        workspace_id: Workspace ID
        product_id: Product ID
        version: Version number
        pipeline_run_id: Pipeline run ID
        
    Returns:
        DAG run ID
    """
    try:
        # Generate DAG run ID
        dag_run_id = f"primedata_simple_{pipeline_run_id}_{int(datetime.utcnow().timestamp())}"
        
        # Trigger DAG using Airflow REST API
        airflow_url = os.getenv('AIRFLOW_URL', 'http://localhost:8080')
        airflow_username = os.getenv('AIRFLOW_USERNAME', 'admin')
        airflow_password = os.getenv('AIRFLOW_PASSWORD', 'admin')
        
        trigger_url = f"{airflow_url}/api/v1/dags/primedata_simple/dagRuns"
        
        trigger_data = {
            "dag_run_id": dag_run_id,
            "conf": {
                "workspace_id": str(workspace_id),
                "product_id": str(product_id),
                "version": version,
                "pipeline_run_id": str(pipeline_run_id),
                "chunking_config": chunking_config or {},
                "embedding_config": embedding_config or {}
            }
        }
        
        try:
            import requests
            from requests.auth import HTTPBasicAuth
            
            # Ensure DAG is unpaused before triggering
            if not _ensure_dag_unpaused(airflow_url, airflow_username, airflow_password, "primedata_simple"):
                raise Exception("Failed to ensure DAG is unpaused")
            
            # Now trigger the DAG run
            response = requests.post(
                trigger_url,
                json=trigger_data,
                auth=HTTPBasicAuth(airflow_username, airflow_password),
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully triggered DAG run {dag_run_id} via REST API")
            else:
                logger.error(f"Failed to trigger DAG run: {response.status_code} - {response.text}")
                raise Exception(f"Failed to trigger DAG run: {response.text}")
                
        except Exception as e:
            logger.error(f"Error triggering DAG via REST API: {e}")
            # Fallback to file-based trigger
            trigger_dir = os.getenv('AIRFLOW_TRIGGER_DIR', '/opt/airflow/triggers')
            os.makedirs(trigger_dir, exist_ok=True)
            
            trigger_file = os.path.join(trigger_dir, f"{dag_run_id}.json")
            
            with open(trigger_file, 'w') as f:
                json.dump(trigger_data, f, indent=2)
            
            logger.info(f"Created trigger file {trigger_file} for DAG run {dag_run_id}")
        
        return dag_run_id
        
    except Exception as e:
        logger.error(f"Failed to create Airflow trigger file: {e}")
        raise

def update_pipeline_run_status(
    db: Session,
    dag_run_id: str,
    status: PipelineRunStatus,
    metrics: Optional[Dict[str, Any]] = None
):
    """
    Update pipeline run status from Airflow.
    
    This function is called by the Airflow DAG to update the pipeline run status.
    
    Args:
        db: Database session
        dag_run_id: DAG run ID
        status: New status
        metrics: Optional metrics to update
    """
    try:
        # Find pipeline run by DAG run ID
        pipeline_run = db.query(PipelineRun).filter(
            PipelineRun.dag_run_id == dag_run_id
        ).first()
        
        if not pipeline_run:
            logger.warning(f"Pipeline run not found for DAG run ID: {dag_run_id}")
            return
        
        # Update status
        pipeline_run.status = status
        
        if status == PipelineRunStatus.RUNNING and not pipeline_run.started_at:
            pipeline_run.started_at = datetime.utcnow()
        elif status in [PipelineRunStatus.SUCCEEDED, PipelineRunStatus.FAILED]:
            pipeline_run.finished_at = datetime.utcnow()
        
        # Update metrics if provided
        if metrics:
            pipeline_run.metrics.update(metrics)
        
        db.commit()
        
        logger.info(f"Updated pipeline run {pipeline_run.id} status to {status.value}")
        
    except Exception as e:
        logger.error(f"Failed to update pipeline run status: {e}")
        db.rollback()
        raise
