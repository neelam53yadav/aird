"""
DataSources API router.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from primedata.api.billing import check_billing_limits
from primedata.connectors.folder import FolderConnector
from primedata.connectors.web import WebConnector
from primedata.connectors.s3 import S3Connector
from primedata.connectors.azure_blob import AzureBlobConnector
from primedata.connectors.google_drive import GoogleDriveConnector
from primedata.core.scope import ensure_product_access, ensure_workspace_access
from primedata.core.security import get_current_user
from primedata.db.database import get_db
from primedata.db.models import DataSource, DataSourceType, Product, RawFile, RawFileStatus
from primedata.storage.minio_client import minio_client
from primedata.storage.paths import raw_prefix
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/datasources", tags=["DataSources"])


class DataSourceCreateRequest(BaseModel):
    workspace_id: UUID
    product_id: UUID
    name: Optional[str] = "Unnamed Data Source"
    type: DataSourceType
    config: Dict[str, Any] = {}


class DataSourceUpdateRequest(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class DataSourceResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    product_id: UUID
    name: str
    type: DataSourceType
    config: Dict[str, Any]
    last_cursor: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True  # Pydantic v1 uses orm_mode instead of from_attributes


class TestConnectionResponse(BaseModel):
    ok: bool
    message: str


class TestConfigRequest(BaseModel):
    type: DataSourceType
    config: Dict[str, Any]


class SyncFullRequest(BaseModel):
    version: Optional[int] = None


class SyncFullResponse(BaseModel):
    version: int
    files: int
    bytes: int
    errors: int
    duration: float
    prefix: str
    details: Dict[str, Any]


@router.post("/", response_model=DataSourceResponse)
async def create_datasource(
    request_body: DataSourceCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new data source for a product.
    """
    # Ensure user has access to the product and its workspace
    product = ensure_product_access(db, request, request_body.product_id)

    # Verify that the provided workspace_id matches the product's workspace
    if product.workspace_id != request_body.workspace_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace ID does not match product's workspace")

    # Check billing limits for data source creation
    current_datasource_count = db.query(DataSource).filter(DataSource.product_id == request_body.product_id).count()

    if not check_billing_limits(str(product.workspace_id), "max_data_sources_per_product", current_datasource_count, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Data source limit exceeded. Please upgrade your plan to add more data sources.",
        )

    # Create new data source
    datasource = DataSource(
        workspace_id=request_body.workspace_id,
        product_id=request_body.product_id,
        name=request_body.name or "Unnamed Data Source",
        type=request_body.type,
        config=request_body.config,
    )

    db.add(datasource)
    db.commit()
    db.refresh(datasource)

    return DataSourceResponse.from_orm(datasource)


@router.get("/", response_model=List[DataSourceResponse])
async def list_datasources(
    product_id: Optional[UUID] = Query(None, description="Filter by product ID"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List data sources. If product_id is provided, filter by that product.
    Otherwise, return data sources from all accessible workspaces.
    """
    from primedata.core.scope import allowed_workspaces

    if product_id:
        # Ensure user has access to the product and get the product's workspace
        product = ensure_product_access(db, request, product_id)
        # Filter by product_id directly - ensure_product_access already verified access
        query = db.query(DataSource).filter(DataSource.product_id == product_id)
    else:
        # No product_id provided - filter by allowed workspaces
        allowed_workspace_ids = allowed_workspaces(request, db)
        query = db.query(DataSource).filter(DataSource.workspace_id.in_(allowed_workspace_ids))

    datasources = query.all()
    return [DataSourceResponse.from_orm(datasource) for datasource in datasources]


@router.get("/{datasource_id}", response_model=DataSourceResponse)
async def get_datasource(
    datasource_id: UUID, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """
    Get a specific data source by ID.
    """
    # Get the data source
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")

    # Ensure user has access to the product
    ensure_product_access(db, request, datasource.product_id)

    return DataSourceResponse.from_orm(datasource)


@router.patch("/{datasource_id}", response_model=DataSourceResponse)
async def update_datasource(
    datasource_id: UUID,
    request_body: DataSourceUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Update a data source's configuration.
    """
    # Get the data source
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")

    # Ensure user has access to the product
    ensure_product_access(db, request, datasource.product_id)

    # Update name if provided
    if request_body.name is not None:
        datasource.name = request_body.name

    # Update configuration
    if request_body.config is not None:
        datasource.config = request_body.config

    db.commit()
    db.refresh(datasource)

    return DataSourceResponse.from_orm(datasource)


def _test_connector_config(datasource_type: DataSourceType, config: Dict[str, Any]) -> Tuple[bool, str]:
    """Helper function to test connector configuration."""
    try:
        if datasource_type.value == "web":
            # Convert single URL to list format expected by WebConnector
            test_config = config.copy()
            if "url" in test_config and "urls" not in test_config:
                test_config["urls"] = [test_config["url"]]

            connector = WebConnector(test_config)
            success, message = connector.test_connection()
            return success, message

        elif datasource_type.value == "folder":
            # Check if this is upload mode (no path provided) or path mode
            has_path = config.get("path") or config.get("root_path")
            
            if not has_path:
                # Upload mode - no path needed, files will be uploaded via API
                return True, "Folder datasource configured for file uploads. Use the upload endpoint to add files."
            
            # Path mode - test the server-side path
            # Convert 'path' to 'root_path' format expected by FolderConnector
            test_config = config.copy()
            if "path" in test_config and "root_path" not in test_config:
                test_config["root_path"] = test_config["path"]

            # Convert 'file_types' to 'include' patterns
            if "file_types" in test_config and "include" not in test_config:
                file_types = test_config["file_types"]
                if isinstance(file_types, str):
                    # Split comma-separated file types
                    test_config["include"] = [ft.strip() for ft in file_types.split(",") if ft.strip()]
                elif isinstance(file_types, list):
                    test_config["include"] = file_types
                else:
                    test_config["include"] = ["*"]  # Default to all files

            connector = FolderConnector(test_config)
            success, message = connector.test_connection()
            return success, message

        elif datasource_type.value == "aws_s3":
            connector = S3Connector(config)
            success, message = connector.test_connection()
            return success, message

        elif datasource_type.value == "azure_blob":
            connector = AzureBlobConnector(config)
            success, message = connector.test_connection()
            return success, message

        elif datasource_type.value == "google_drive":
            connector = GoogleDriveConnector(config)
            success, message = connector.test_connection()
            return success, message

        else:
            return False, f"Test connection not supported for data source type: {datasource_type.value}"
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Test connection failed: {str(e)}")
        return False, f"Test connection failed: {str(e)}"


@router.post("/test-config", response_model=TestConnectionResponse)
async def test_config(request_body: TestConfigRequest, current_user: dict = Depends(get_current_user)):
    """
    Test connection configuration without creating a data source.
    """
    try:
        success, message = _test_connector_config(request_body.type, request_body.config)
        return TestConnectionResponse(ok=success, message=message)
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Test config endpoint error: {str(e)}", exc_info=True)
        return TestConnectionResponse(ok=False, message=f"Error testing configuration: {str(e)}")


@router.post("/{datasource_id}/test-connection", response_model=TestConnectionResponse)
async def test_connection(
    datasource_id: UUID, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """
    Test connection to a data source using connector dispatch.
    """
    # Get the data source
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")

    # Ensure user has access to the product
    ensure_product_access(db, request, datasource.product_id)

    # Test connection using helper function
    success, message = _test_connector_config(datasource.type, datasource.config)
    return TestConnectionResponse(ok=success, message=message)


@router.post("/{datasource_id}/sync-full", response_model=SyncFullResponse)
async def sync_full(
    datasource_id: UUID,
    request_body: SyncFullRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Perform full synchronization of a data source.

    This endpoint:
    1. Syncs files from the data source to MinIO
    2. Creates RawFile records in the database
    3. Updates product version if needed
    4. Updates data source last_cursor with sync details
    """
    # Get the data source
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")

    # Ensure user has access to the product
    ensure_product_access(db, request, datasource.product_id)

    # Get the product to determine version
    product = db.query(Product).filter(Product.id == datasource.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Determine version
    version = request_body.version or (product.current_version or 0) + 1

    # Generate output prefix
    output_prefix = raw_prefix(datasource.workspace_id, datasource.product_id, version)

    # Dispatch to appropriate connector
    try:
        if datasource.type.value == "web":
            # Convert single URL to list format expected by WebConnector
            config = datasource.config.copy()
            if "url" in config and "urls" not in config:
                config["urls"] = [config["url"]]

            connector = WebConnector(config)
            result = connector.sync_full("primedata-raw", output_prefix)

        elif datasource.type.value == "folder":
            # Convert 'path' to 'root_path' format expected by FolderConnector
            config = datasource.config.copy()
            if "path" in config and "root_path" not in config:
                config["root_path"] = config["path"]

            # Convert 'file_types' to 'include' patterns
            if "file_types" in config and "include" not in config:
                file_types = config["file_types"]
                if isinstance(file_types, str):
                    # Split comma-separated file types
                    config["include"] = [ft.strip() for ft in file_types.split(",") if ft.strip()]
                elif isinstance(file_types, list):
                    config["include"] = file_types
                else:
                    config["include"] = ["*"]  # Default to all files

            connector = FolderConnector(config)
            result = connector.sync_full("primedata-raw", output_prefix)

        elif datasource.type.value == "aws_s3":
            connector = S3Connector(datasource.config)
            result = connector.sync_full("primedata-raw", output_prefix)

        elif datasource.type.value == "azure_blob":
            connector = AzureBlobConnector(datasource.config)
            result = connector.sync_full("primedata-raw", output_prefix)

        elif datasource.type.value == "google_drive":
            connector = GoogleDriveConnector(datasource.config)
            result = connector.sync_full("primedata-raw", output_prefix)

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sync not supported for data source type: {datasource.type.value}",
            )

        # Store raw file records in database
        details = result.get("details", {})

        # Handle both folder connector (files_processed) and web connector (urls_processed)
        files_processed = details.get("files_processed", [])
        urls_processed = details.get("urls_processed", [])

        files_created = 0

        # Process folder connector files
        for file_info in files_processed:
            try:
                # Extract file stem from the original path or MinIO key
                file_path = file_info.get("path", "")
                minio_key = file_info.get("key", "")

                # Get file stem (filename without extension)
                if file_path:
                    file_stem = Path(file_path).stem
                    filename = Path(file_path).name
                elif minio_key:
                    # Extract from MinIO key if path not available
                    filename = Path(minio_key).name
                    file_stem = Path(minio_key).stem
                else:
                    continue

                # Check if file already exists (avoid duplicates)
                existing = (
                    db.query(RawFile)
                    .filter(
                        RawFile.product_id == datasource.product_id, RawFile.version == version, RawFile.file_stem == file_stem
                    )
                    .first()
                )

                if not existing:
                    raw_file = RawFile(
                        workspace_id=datasource.workspace_id,
                        product_id=datasource.product_id,
                        data_source_id=datasource.id,
                        version=version,
                        filename=filename,
                        file_stem=file_stem,
                        minio_key=minio_key,
                        minio_bucket="primedata-raw",
                        file_size=file_info.get("size", 0),
                        content_type=file_info.get("content_type", "application/octet-stream"),
                        status=RawFileStatus.INGESTED,
                    )
                    db.add(raw_file)
                    files_created += 1

            except Exception as e:
                # Log error but don't fail the entire sync
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to store raw file record: {e}")

        # Process web connector files (URLs)
        for url_info in urls_processed:
            try:
                filename = url_info.get("filename", "")
                if not filename:
                    continue

                # Generate MinIO key from prefix and filename
                minio_key = f"{output_prefix}{filename}"
                file_stem = Path(filename).stem

                # Check if file already exists (avoid duplicates)
                existing = (
                    db.query(RawFile)
                    .filter(
                        RawFile.product_id == datasource.product_id, RawFile.version == version, RawFile.file_stem == file_stem
                    )
                    .first()
                )

                if not existing:
                    raw_file = RawFile(
                        workspace_id=datasource.workspace_id,
                        product_id=datasource.product_id,
                        data_source_id=datasource.id,
                        version=version,
                        filename=filename,
                        file_stem=file_stem,
                        minio_key=minio_key,
                        minio_bucket="primedata-raw",
                        file_size=url_info.get("size", 0),
                        content_type="text/html",  # Web connector stores HTML
                        status=RawFileStatus.INGESTED,
                    )
                    db.add(raw_file)
                    files_created += 1

            except Exception as e:
                # Log error but don't fail the entire sync
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to store raw file record from URL: {e}")

        # Update product version if this was a new version
        if version > (product.current_version or 0):
            product.current_version = version

        # Update data source last_cursor with sync details
        datasource.last_cursor = {
            "last_sync_at": datetime.utcnow().isoformat(),
            "version": version,
            "files_synced": result["files"],
            "bytes_synced": result["bytes"],
            "errors": result["errors"],
            "files_created": files_created,
        }

        db.commit()

        return SyncFullResponse(
            version=version,
            files=result["files"],
            bytes=result["bytes"],
            errors=result["errors"],
            duration=result["duration"],
            prefix=output_prefix,
            details=result["details"],
        )

    except Exception as e:
        db.rollback()
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Sync failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Sync failed: {str(e)}")


@router.post("/{datasource_id}/upload-files")
async def upload_files(
    datasource_id: UUID,
    files: List[UploadFile] = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload files to a folder-type datasource.
    Files are stored directly in MinIO/GCS and RawFile records are created.
    This bypasses the need for a server-side path.
    """
    # Get the data source
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")

    # Only allow for folder type
    if datasource.type != DataSourceType.FOLDER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File upload only supported for folder datasources"
        )

    # Ensure user has access
    ensure_product_access(db, request, datasource.product_id)

    # Get product version
    product = db.query(Product).filter(Product.id == datasource.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    version = product.current_version or 1
    output_prefix = raw_prefix(datasource.workspace_id, datasource.product_id, version)

    uploaded_files = []
    errors = []

    for file in files:
        try:
            content = await file.read()
            file_size = len(content)
            
            # Generate safe key
            safe_key = safe_filename(file.filename)
            key = f"{output_prefix}{safe_key}"

            # Determine content type
            content_type = file.content_type or "application/octet-stream"

            # Upload directly to MinIO/GCS
            success = minio_client.put_bytes("primedata-raw", key, content, content_type)

            if success:
                # Create RawFile record (same as sync-full does)
                file_stem = Path(file.filename).stem
                filename = Path(file.filename).name

                # Check if file already exists
                existing = (
                    db.query(RawFile)
                    .filter(
                        RawFile.product_id == datasource.product_id,
                        RawFile.version == version,
                        RawFile.file_stem == file_stem
                    )
                    .first()
                )

                if not existing:
                    raw_file = RawFile(
                        workspace_id=datasource.workspace_id,
                        product_id=datasource.product_id,
                        data_source_id=datasource.id,
                        version=version,
                        filename=filename,
                        file_stem=file_stem,
                        minio_key=key,
                        minio_bucket="primedata-raw",
                        file_size=file_size,
                        content_type=content_type,
                        status=RawFileStatus.INGESTED,
                    )
                    db.add(raw_file)
                    uploaded_files.append({
                        "filename": filename,
                        "size": file_size,
                        "key": key
                    })
                else:
                    errors.append(f"File {filename} already exists")
            else:
                errors.append(f"Failed to upload {file.filename}")

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error uploading file {file.filename}: {e}")
            errors.append(f"Error uploading {file.filename}: {str(e)}")

    db.commit()

    return {
        "success": len(errors) == 0,
        "uploaded_count": len(uploaded_files),
        "error_count": len(errors),
        "uploaded_files": uploaded_files,
        "errors": errors
    }


@router.delete("/{datasource_id}")
async def delete_datasource(
    datasource_id: UUID, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """
    Delete a data source.
    """
    # Get the data source
    datasource = db.query(DataSource).filter(DataSource.id == datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")

    # Ensure user has access to the product
    ensure_product_access(db, request, datasource.product_id)

    # Delete the data source
    db.delete(datasource)
    db.commit()

    return {"message": "Data source deleted successfully"}
