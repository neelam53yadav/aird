"""
Pipeline API endpoints for PrimeData.

This module provides REST API endpoints for managing data processing pipelines,
including triggering pipeline runs and monitoring their status.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from primedata.core.scope import allowed_workspaces, ensure_product_access
from primedata.core.security import get_current_user
from primedata.db.database import get_db
from primedata.db.models import PipelineRun, PipelineRunStatus, Product, RawFile, RawFileStatus
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

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
        orm_mode = True  # Pydantic v1 uses orm_mode instead of from_attributes


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
    current_user: dict = Depends(get_current_user),
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Option C: Smart Version Resolution (Enterprise Best Practice)
    # If version is explicitly provided, validate it exists
    # If version is None, auto-detect latest ingested version
    if request.version is not None:
        # Explicit version provided - validate raw files exist
        # Include PROCESSED files to allow reprocessing with new configurations
        version = request.version
        raw_file_count = (
            db.query(RawFile)
            .filter(
                RawFile.product_id == product.id,
                RawFile.version == version,
                RawFile.status.in_(
                    [RawFileStatus.INGESTED, RawFileStatus.FAILED, RawFileStatus.PROCESSING, RawFileStatus.PROCESSED]
                ),
            )
            .count()
        )

        if raw_file_count == 0:
            # Provide helpful error message with available versions
            latest_version = (
                db.query(func.max(RawFile.version))
                .filter(RawFile.product_id == product.id, RawFile.status != RawFileStatus.DELETED)
                .scalar()
            )

            # Get all available versions
            available_versions = (
                db.query(RawFile.version)
                .filter(RawFile.product_id == product.id, RawFile.status != RawFileStatus.DELETED)
                .distinct()
                .order_by(RawFile.version.desc())
                .all()
            )

            available_versions_list = [v[0] for v in available_versions] if available_versions else []

            error_detail = {
                "message": f"No raw files found for version {version}",
                "requested_version": version,
                "latest_ingested_version": latest_version,
                "available_versions": available_versions_list,
                "suggestion": (
                    f"Please run initial ingestion for version {version}, "
                    f"or use version={latest_version} to process latest ingested data"
                    if latest_version
                    else "Please run initial ingestion first"
                ),
            }

            logger.warning(
                f"Pipeline trigger failed: No raw files for product {product.id}, version {version}. "
                f"Available versions: {available_versions_list}"
            )

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_detail)

        logger.info(f"Using explicit version {version} (validated: {raw_file_count} raw files found)")
    else:
        # Auto-detect: Prefer PROCESSED versions over FAILED versions for reprocessing
        # This ensures we use valid, successfully processed data as the source
        latest_processed = (
            db.query(RawFile)
            .filter(RawFile.product_id == product.id, RawFile.status == RawFileStatus.PROCESSED)
            .order_by(RawFile.version.desc())
            .first()
        )

        if latest_processed:
            version = latest_processed.version
            logger.info(f"Auto-detected latest processed version: {version} " f"(found file: {latest_processed.filename})")
        else:
            # Fallback to INGESTED files if no PROCESSED files exist
            latest_ingested = (
                db.query(RawFile)
                .filter(RawFile.product_id == product.id, RawFile.status == RawFileStatus.INGESTED)
                .order_by(RawFile.version.desc())
                .first()
            )

            if not latest_ingested:
                # Check if any raw files exist at all
                any_raw_file = (
                    db.query(RawFile).filter(RawFile.product_id == product.id, RawFile.status != RawFileStatus.DELETED).first()
                )

                if any_raw_file:
                    error_detail = {
                        "message": "No raw files found for processing.",
                        "suggestion": "Please run initial ingestion to create a new version with raw files",
                    }
                else:
                    error_detail = {
                        "message": "No raw files found for this product",
                        "suggestion": "Please run initial ingestion first to upload data",
                    }

                logger.warning(f"Pipeline trigger failed: No raw files for product {product.id}")

                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail)

            version = latest_ingested.version
            logger.info(f"Auto-detected latest ingested version: {version} " f"(found file: {latest_ingested.filename})")

    # Check if there's already a running pipeline for this version
    existing_run = (
        db.query(PipelineRun)
        .filter(
            PipelineRun.product_id == request.product_id,
            PipelineRun.version == version,
            PipelineRun.status.in_([PipelineRunStatus.QUEUED, PipelineRunStatus.RUNNING]),
        )
        .first()
    )

    if existing_run:
        # Check if user wants to force run (override existing)
        force_run = request.force_run

        if not force_run:
            # Provide helpful error message with details about existing run
            status_msg = existing_run.status.value.lower()
            started_msg = ""
            if existing_run.started_at:
                now = datetime.now(timezone.utc)
                elapsed = now - existing_run.started_at.replace(tzinfo=timezone.utc)
                started_msg = f" (running for {int(elapsed.total_seconds() / 60)} minutes)"

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": f"A pipeline run is already {status_msg} for this product (version {version}){started_msg}",
                    "existing_run_id": str(existing_run.id),
                    "existing_status": existing_run.status.value,
                    "existing_started_at": existing_run.started_at.isoformat() if existing_run.started_at else None,
                    "suggestion": "You can force run to cancel the existing run and start a new one, or wait for the current run to complete.",
                },
            )
        else:
            # Cancel existing run and start new one
            logger.info(f"Cancelling existing pipeline run {existing_run.id} to start new run")
            existing_run.status = PipelineRunStatus.FAILED
            existing_run.finished_at = datetime.utcnow()
            existing_run.metrics = existing_run.metrics or {}
            existing_run.metrics["cancelled_reason"] = "Replaced by new pipeline run"
            db.commit()

    # Check if we're reprocessing already-processed files - if so, create a new version
    # Only do this if version was auto-detected (not explicitly provided)
    if request.version is None:
        # First, check if there are any existing raw files for this version that might be missing files in MinIO
        existing_files_for_version = (
            db.query(RawFile)
            .filter(
                RawFile.product_id == request.product_id,
                RawFile.version == version,
                RawFile.status.in_([RawFileStatus.FAILED, RawFileStatus.INGESTED, RawFileStatus.PROCESSING]),
            )
            .all()
        )

        # Check if any of these files are missing in MinIO and need to be copied from previous version
        if existing_files_for_version:
            from primedata.storage.minio_client import minio_client as minio_client_instance

            files_need_copy = []

            for existing_file in existing_files_for_version:
                if not minio_client_instance.object_exists(existing_file.storage_bucket, existing_file.storage_key):
                    # File doesn't exist, need to find the original source file from previous version
                    # Find the original PROCESSED file from previous versions
                    original_file = (
                        db.query(RawFile)
                        .filter(
                            RawFile.product_id == request.product_id,
                            RawFile.filename == existing_file.filename,
                            RawFile.status == RawFileStatus.PROCESSED,
                        )
                        .order_by(RawFile.version.desc())
                        .first()
                    )

                    if original_file and minio_client_instance.object_exists(
                        original_file.storage_bucket, original_file.storage_key
                    ):
                        # Copy from original location
                        logger.info(
                            f"Copying missing file from original version: {original_file.storage_key} to {existing_file.storage_key}"
                        )
                        copy_success = minio_client_instance.copy_object(
                            source_bucket=original_file.storage_bucket,
                            source_key=original_file.storage_key,
                            dest_bucket=existing_file.storage_bucket,
                            dest_key=existing_file.storage_key,
                        )

                        if copy_success:
                            # Verify copy succeeded
                            if minio_client_instance.object_exists(existing_file.storage_bucket, existing_file.storage_key):
                                existing_file.status = RawFileStatus.INGESTED
                                existing_file.error_message = None
                                logger.info(f"Successfully copied file and updated status for {existing_file.filename}")
                            else:
                                logger.error(f"Copy verification failed for {existing_file.filename}")
                        else:
                            logger.error(f"Failed to copy file for {existing_file.filename}")
                    else:
                        logger.warning(f"Cannot find source file to copy for {existing_file.filename}")

            if existing_files_for_version:
                db.commit()

        # Now check for PROCESSED files to create a new version from
        processed_files_to_reprocess = (
            db.query(RawFile)
            .filter(
                RawFile.product_id == request.product_id, RawFile.version == version, RawFile.status == RawFileStatus.PROCESSED
            )
            .all()
        )

        if processed_files_to_reprocess:
            # We're reprocessing - create a new version by incrementing
            # Get the maximum version number for this product
            max_version = db.query(func.max(RawFile.version)).filter(RawFile.product_id == request.product_id).scalar() or 0

            new_version = max_version + 1
            logger.info(
                f"Reprocessing {len(processed_files_to_reprocess)} PROCESSED files from version {version} "
                f"to new version {new_version} with new configuration"
            )

            # Create new raw file records with the new version (copy the old ones)
            import uuid as uuid_lib

            from primedata.storage.minio_client import minio_client as minio_client_instance
            from primedata.storage.paths import raw_prefix

            for old_raw_file in processed_files_to_reprocess:
                # Update storage_key to use the new version number
                # Extract just the filename from the old storage_key
                # Old format: ws/{ws}/prod/{prod}/v/{old_version}/raw/{filename}
                # New format: ws/{ws}/prod/{prod}/v/{new_version}/raw/{filename}
                old_key_parts = old_raw_file.storage_key.split("/")
                filename = old_key_parts[-1]  # Get the filename
                new_storage_key = f"{raw_prefix(old_raw_file.workspace_id, old_raw_file.product_id, new_version)}{filename}"

                # Verify source file exists before copying
                source_exists = minio_client_instance.object_exists(old_raw_file.storage_bucket, old_raw_file.storage_key)

                if not source_exists:
                    logger.error(f"Source file does not exist in storage: {old_raw_file.storage_key}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Source file {old_raw_file.filename} not found in storage at {old_raw_file.storage_key}. Cannot reprocess.",
                    )

                # Check if destination already exists (shouldn't happen, but be safe)
                dest_exists = minio_client_instance.object_exists(old_raw_file.storage_bucket, new_storage_key)
                if dest_exists:
                    logger.info(f"Destination file already exists in storage: {new_storage_key}, skipping copy")
                else:
                    # Copy the file in storage from old version path to new version path
                    logger.info(f"Copying file from {old_raw_file.storage_key} to {new_storage_key}")
                    copy_success = minio_client_instance.copy_object(
                        source_bucket=old_raw_file.storage_bucket,
                        source_key=old_raw_file.storage_key,
                        dest_bucket=old_raw_file.storage_bucket,
                        dest_key=new_storage_key,
                    )

                    if not copy_success:
                        logger.error(f"Failed to copy file from {old_raw_file.storage_key} to {new_storage_key}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to copy file {old_raw_file.filename} to new version path",
                        )

                    # Verify the copy succeeded
                    verify_exists = minio_client_instance.object_exists(old_raw_file.storage_bucket, new_storage_key)
                    if not verify_exists:
                        logger.error(f"Copy verification failed: file does not exist at {new_storage_key} after copy")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"File copy verification failed for {old_raw_file.filename}",
                        )

                new_raw_file = RawFile(
                    id=uuid_lib.uuid4(),
                    workspace_id=old_raw_file.workspace_id,
                    product_id=old_raw_file.product_id,
                    data_source_id=old_raw_file.data_source_id,
                    version=new_version,
                    filename=old_raw_file.filename,
                    file_stem=old_raw_file.file_stem,
                    storage_key=new_storage_key,  # Use new version in the key
                    storage_bucket=old_raw_file.storage_bucket,
                    file_size=old_raw_file.file_size,
                    content_type=old_raw_file.content_type,
                    status=RawFileStatus.INGESTED,  # Start as INGESTED for reprocessing
                    file_checksum=old_raw_file.file_checksum,
                    storage_etag=old_raw_file.storage_etag,
                    ingested_at=datetime.utcnow(),
                    processed_at=None,
                    error_message=None,
                )
                db.add(new_raw_file)
                logger.info(f"Copied file {old_raw_file.filename} from v{version} to v{new_version} in MinIO")

            version = new_version  # Use the new version for the pipeline run
            db.commit()
            logger.info(f"Created new version {version} for reprocessing")

    try:
        # Create pipeline run record
        pipeline_run = PipelineRun(
            workspace_id=product.workspace_id,
            product_id=request.product_id,
            version=version,
            status=PipelineRunStatus.QUEUED,
            started_at=datetime.now(timezone.utc),  # Explicitly set started_at with timezone
            metrics={},
        )
        db.add(pipeline_run)
        db.commit()
        db.refresh(pipeline_run)

        # Refresh product from database to ensure we have latest configuration
        db.refresh(product)

        # Get chunking and embedding configuration from product (after refresh)
        chunking_config = product.chunking_config or {}
        embedding_config = product.embedding_config or {}

        # Log the configuration being passed to Airflow for verification
        logger.info(
            f"Triggering pipeline for product {request.product_id} with configuration:\n"
            f"  chunking_config: {chunking_config}\n"
            f"  embedding_config: {embedding_config}\n"
            f"  playbook_id: {product.playbook_id}"
        )

        # Trigger Airflow DAG with configuration
        dag_run_id = await _trigger_airflow_dag(
            workspace_id=product.workspace_id,
            product_id=request.product_id,
            version=version,
            pipeline_run_id=pipeline_run.id,
            chunking_config=chunking_config,
            embedding_config=embedding_config,
            playbook_id=product.playbook_id,
        )

        # Update pipeline run with DAG run ID
        pipeline_run.dag_run_id = dag_run_id
        pipeline_run.status = PipelineRunStatus.RUNNING
        pipeline_run.started_at = datetime.utcnow()
        db.commit()

        # Create informative message
        version_source = "explicitly provided" if request.version is not None else "auto-detected (latest ingested)"
        message = f"Pipeline run triggered successfully for version {version} ({version_source}). " f"DAG Run ID: {dag_run_id}"

        logger.info(
            f"Triggered pipeline run {pipeline_run.id} for product {request.product_id} version {version} ({version_source})"
        )

        return TriggerPipelineResponse(
            product_id=request.product_id,
            version=version,
            run_id=pipeline_run.id,
            status=pipeline_run.status.value,
            message=message,
        )

    except Exception as e:
        logger.error(f"Failed to trigger pipeline for product {request.product_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to trigger pipeline: {str(e)}")


@router.get("/runs", response_model=List[PipelineRunResponse])
async def list_pipeline_runs(
    product_id: UUID,
    request_obj: Request,
    limit: int = 10,
    sync: bool = Query(True, description="Sync with Airflow before returning"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List pipeline runs for a product.
    """
    # Ensure user has access to the product
    product = ensure_product_access(db, request_obj, product_id)

    # Sync with Airflow if requested
    if sync:
        _sync_pipeline_runs_with_airflow(db)

    # Get pipeline runs - filter by product_id AND workspace_id for security
    # This ensures users can only see pipeline runs for products in their workspaces
    allowed_workspace_ids = allowed_workspaces(request_obj, db)
    runs = (
        db.query(PipelineRun)
        .join(Product, PipelineRun.product_id == Product.id)
        .filter(PipelineRun.product_id == product_id, Product.workspace_id.in_(allowed_workspace_ids))
        .order_by(PipelineRun.created_at.desc())
        .limit(limit)
        .all()
    )

    # Lazy-load metrics from S3 if archived
    from primedata.services.lazy_json_loader import load_pipeline_run_metrics

    return [
        PipelineRunResponse(
            id=run.id,
            product_id=run.product_id,
            version=run.version,
            status=run.status.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
            dag_run_id=run.dag_run_id,
            metrics=load_pipeline_run_metrics(run),
            created_at=run.created_at,
        )
        for run in runs
    ]


@router.get("/runs/{run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(
    run_id: UUID, request_obj: Request, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """
    Get details of a specific pipeline run.
    """
    # Get pipeline run
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found")

    # Ensure user has access to the product
    ensure_product_access(db, request_obj, run.product_id)

    # Lazy-load metrics from S3 if archived
    from primedata.services.lazy_json_loader import load_pipeline_run_metrics

    metrics = load_pipeline_run_metrics(run)

    return PipelineRunResponse(
        id=run.id,
        product_id=run.product_id,
        version=run.version,
        status=run.status.value,
        started_at=run.started_at,
        finished_at=run.finished_at,
        dag_run_id=run.dag_run_id,
        metrics=metrics,
        created_at=run.created_at,
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
    request_obj: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Update a pipeline run status (used by Airflow DAG or for manual cancellation).
    """
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found")

    # Ensure user has access to the product
    ensure_product_access(db, request_obj, run.product_id)

    # Update fields if provided
    if request_body.status is not None:
        try:
            new_status = PipelineRunStatus(request_body.status)
            # If cancelling a running/queued pipeline, mark it as failed
            if new_status == PipelineRunStatus.FAILED and run.status in [PipelineRunStatus.RUNNING, PipelineRunStatus.QUEUED]:
                logger.info(f"Cancelling pipeline run {run_id} (was {run.status.value})")
                run.status = PipelineRunStatus.FAILED
                run.finished_at = datetime.utcnow()
                if not run.metrics:
                    run.metrics = {}
                run.metrics["cancelled_reason"] = "Manually cancelled by user"
            else:
                run.status = new_status
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {request_body.status}")

    if request_body.finished_at is not None:
        try:
            run.finished_at = datetime.fromisoformat(request_body.finished_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid finished_at format: {request_body.finished_at}"
            )

    if request_body.metrics is not None:
        if run.metrics:
            run.metrics.update(request_body.metrics)
        else:
            run.metrics = request_body.metrics

    db.commit()
    db.refresh(run)

    logger.info(f"Updated pipeline run {run_id} to status {run.status.value}")

    # Lazy-load metrics from S3 if archived
    from primedata.services.lazy_json_loader import load_pipeline_run_metrics

    metrics = load_pipeline_run_metrics(run)

    return PipelineRunResponse(
        id=run.id,
        product_id=run.product_id,
        version=run.version,
        status=run.status.value,
        started_at=run.started_at,
        finished_at=run.finished_at,
        dag_run_id=run.dag_run_id,
        metrics=metrics,
        created_at=run.created_at,
    )


@router.post("/sync")
async def sync_pipeline_runs_with_airflow(
    request_obj: Request, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """
    Manually sync all running pipeline runs with Airflow status.
    """
    try:
        updated_count = _sync_pipeline_runs_with_airflow(db)
        return {"message": f"Successfully synced {updated_count} pipeline runs with Airflow", "updated_count": updated_count}
    except Exception as e:
        logger.error(f"Error in manual sync: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to sync with Airflow: {str(e)}")


@router.get("/status/{run_id}")
async def get_pipeline_status(
    run_id: UUID, request_obj: Request, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """
    Get the current status of a pipeline run.
    """
    # Get pipeline run
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pipeline run not found")

    # Ensure user has access to the product
    ensure_product_access(db, request_obj, run.product_id)

    return {
        "run_id": str(run.id),
        "status": run.status.value,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "dag_run_id": run.dag_run_id,
        "metrics": run.metrics,
    }


def _check_airflow_dag_run_status(
    airflow_url: str, airflow_username: str, airflow_password: str, dag_run_id: str
) -> Dict[str, Any]:
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
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        if response.status_code == 200:
            dag_run_data = response.json()
            return {
                "status": dag_run_data.get("state", "unknown"),
                "start_date": dag_run_data.get("start_date"),
                "end_date": dag_run_data.get("end_date"),
                "execution_date": dag_run_data.get("execution_date"),
                "dag_run_id": dag_run_data.get("dag_run_id"),
            }
        else:
            logger.error(f"Failed to get DAG run status: {response.status_code} - {response.text}")
            return {"status": "unknown", "error": f"HTTP {response.status_code}"}

    except Exception as e:
        logger.error(f"Error checking DAG run status: {e}")
        return {"status": "unknown", "error": str(e)}


def _sync_pipeline_runs_with_airflow(db: Session) -> int:
    """
    Sync running pipeline runs with Airflow status.
    Returns the number of runs updated.
    """
    try:
        # Get Airflow configuration
        airflow_url = os.getenv("AIRFLOW_URL", "http://localhost:8080")
        airflow_username = os.getenv("AIRFLOW_USERNAME", "admin")
        airflow_password = os.getenv("AIRFLOW_PASSWORD", "admin")

        # Get all running pipeline runs
        running_runs = (
            db.query(PipelineRun).filter(PipelineRun.status.in_([PipelineRunStatus.RUNNING, PipelineRunStatus.QUEUED])).all()
        )

        updated_count = 0

        for run in running_runs:
            if not run.dag_run_id:
                continue

            # Check Airflow status
            airflow_status = _check_airflow_dag_run_status(airflow_url, airflow_username, airflow_password, run.dag_run_id)

            if airflow_status.get("status") in ["success", "failed"]:
                # Update the pipeline run status
                if airflow_status["status"] == "success":
                    run.status = PipelineRunStatus.SUCCEEDED
                else:
                    run.status = PipelineRunStatus.FAILED

                # Update finished_at if available
                if airflow_status.get("end_date"):
                    try:
                        from datetime import datetime, timezone

                        run.finished_at = datetime.fromisoformat(airflow_status["end_date"].replace("Z", "+00:00"))
                    except ValueError:
                        run.finished_at = datetime.utcnow()
                else:
                    run.finished_at = datetime.utcnow()

                # Add some basic metrics
                if not run.metrics:
                    run.metrics = {}
                run.metrics["airflow_sync"] = True
                run.metrics["airflow_status"] = airflow_status["status"]

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
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        if dag_info_response.status_code == 200:
            dag_info = dag_info_response.json()
            is_paused = dag_info.get("is_paused", True)

            if is_paused:
                logger.info(f"DAG {dag_id} is paused, attempting to unpause")
                unpause_data = {"is_paused": False}

                unpause_response = requests.patch(
                    dag_info_url,
                    json=unpause_data,
                    auth=HTTPBasicAuth(airflow_username, airflow_password),
                    headers={"Content-Type": "application/json"},
                    timeout=30,
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
    embedding_config: Dict[str, Any] = None,
    playbook_id: str = None,
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
        airflow_url = os.getenv("AIRFLOW_URL", "http://localhost:8080")
        airflow_username = os.getenv("AIRFLOW_USERNAME", "admin")
        airflow_password = os.getenv("AIRFLOW_PASSWORD", "admin")

        trigger_url = f"{airflow_url}/api/v1/dags/primedata_simple/dagRuns"

        trigger_data = {
            "dag_run_id": dag_run_id,
            "conf": {
                "workspace_id": str(workspace_id),
                "product_id": str(product_id),
                "version": version,
                "pipeline_run_id": str(pipeline_run_id),
                "chunking_config": chunking_config or {},
                "embedding_config": embedding_config or {},
                "playbook_id": playbook_id,
            },
        }

        # Log the exact configuration being sent to Airflow
        logger.info(
            f"Sending to Airflow DAG:\n"
            f"  chunking_config: {json.dumps(chunking_config or {}, indent=2)}\n"
            f"  embedding_config: {json.dumps(embedding_config or {}, indent=2)}\n"
            f"  playbook_id: {playbook_id}"
        )

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
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            if response.status_code in [200, 201]:
                logger.info(f"Successfully triggered DAG run {dag_run_id} via REST API (status {response.status_code})")
            else:
                error_msg = f"Failed to trigger DAG run via REST API: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Error triggering DAG via REST API: {e}", exc_info=True)
            # Fallback to file-based trigger (use tmp directory that's writable)
            import tempfile

            trigger_dir = os.getenv("AIRFLOW_TRIGGER_DIR", os.path.join(tempfile.gettempdir(), "airflow_triggers"))

            try:
                os.makedirs(trigger_dir, exist_ok=True)
            except OSError as dir_error:
                logger.error(f"Failed to create trigger directory {trigger_dir}: {dir_error}")
                # Last resort: use tempfile.gettempdir() directly
                trigger_dir = tempfile.gettempdir()
                logger.warning(f"Using temp directory as fallback: {trigger_dir}")

            trigger_file = os.path.join(trigger_dir, f"{dag_run_id}.json")

            try:
                with open(trigger_file, "w") as f:
                    json.dump(trigger_data, f, indent=2)
                logger.info(f"Created trigger file {trigger_file} for DAG run {dag_run_id}")
                logger.warning(
                    f"Using file-based trigger fallback. Ensure Airflow can read from {trigger_dir}. "
                    f"REST API error was: {e}"
                )
            except OSError as file_error:
                error_msg = (
                    f"Failed to create trigger file {trigger_file}: {file_error}. "
                    f"REST API error was: {e}. "
                    f"Please check AIRFLOW_URL, AIRFLOW_USERNAME, and AIRFLOW_PASSWORD environment variables."
                )
                logger.error(error_msg)
                raise Exception(error_msg) from e

        return dag_run_id

    except Exception as e:
        error_msg = f"Failed to trigger Airflow DAG: {e}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e


def update_pipeline_run_status(
    db: Session, dag_run_id: str, status: PipelineRunStatus, metrics: Optional[Dict[str, Any]] = None
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
        pipeline_run = db.query(PipelineRun).filter(PipelineRun.dag_run_id == dag_run_id).first()

        if not pipeline_run:
            logger.warning(f"Pipeline run not found for DAG run ID: {dag_run_id}")
            return

        # Update status
        pipeline_run.status = status

        if status == PipelineRunStatus.RUNNING and not pipeline_run.started_at:
            pipeline_run.started_at = datetime.utcnow()
        elif status in [PipelineRunStatus.SUCCEEDED, PipelineRunStatus.FAILED]:
            pipeline_run.finished_at = datetime.utcnow()

        # Update metrics if provided (save to S3 if large)
        if metrics:
            from primedata.services.s3_json_storage import save_json_to_s3, should_save_to_s3

            # Merge with existing metrics
            if pipeline_run.metrics is None:
                pipeline_run.metrics = {}
            pipeline_run.metrics.update(metrics)

            # Check if metrics should be saved to S3 (if >1MB)
            if should_save_to_s3(pipeline_run.metrics):
                s3_path = save_json_to_s3(
                    pipeline_run.workspace_id,
                    pipeline_run.product_id,
                    "metrics",
                    pipeline_run.metrics,
                    version=pipeline_run.version,
                    subfolder="pipeline_runs",
                )
                if s3_path:
                    pipeline_run.metrics_path = s3_path
                    pipeline_run.archived_at = datetime.utcnow()
                    pipeline_run.metrics = {}  # Clear DB field after archiving
                    logger.info(f"Archived metrics to S3 for pipeline run {pipeline_run.id}")

        db.commit()

        logger.info(f"Updated pipeline run {pipeline_run.id} status to {status.value}")

    except Exception as e:
        logger.error(f"Failed to update pipeline run status: {e}")
        db.rollback()
        raise
