"""
Products API router.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Response, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from primedata.core.scope import ensure_workspace_access, allowed_workspaces, ensure_product_access
from primedata.core.security import get_current_user
from primedata.core.user_utils import get_user_id
from primedata.db.database import get_db
from primedata.db.models import Product, ProductStatus, PipelineRun, PipelineRunStatus
from primedata.api.billing import check_billing_limits
from primedata.analysis.content_analyzer import content_analyzer, ChunkingConfig
from primedata.core.settings import get_settings

router = APIRouter(prefix="/api/v1/products", tags=["Products"])
logger = logging.getLogger(__name__)


def get_current_user_optional(request: Request, db: Session = Depends(get_db)):
    """Get current user with optional authentication bypass for testing."""
    settings = get_settings()
    if settings.DISABLE_AUTH or settings.TESTING_MODE:
        # Return a mock user for testing
        return {
            "id": "test-user-id",
            "email": "test@example.com",
            "workspace_ids": ["550e8400-e29b-41d4-a716-446655440001"]
        }
    else:
        return get_current_user(request, db)


class ProductCreateRequest(BaseModel):
    workspace_id: UUID
    name: str
    playbook_id: Optional[str] = None  # Optional playbook ID (M1)
    chunking_config: Optional[Dict[str, Any]] = None  # Optional chunking configuration
    embedding_config: Optional[Dict[str, Any]] = None  # Optional embedding configuration


class ChunkingConfigRequest(BaseModel):
    mode: Optional[str] = None  # "auto" or "manual"
    auto_settings: Optional[Dict[str, Any]] = None
    manual_settings: Optional[Dict[str, Any]] = None

class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[ProductStatus] = None
    chunking_config: Optional[ChunkingConfigRequest] = None
    embedding_config: Optional[Dict[str, Any]] = None


class ProductResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    owner_user_id: UUID
    name: str
    status: ProductStatus
    current_version: int
    promoted_version: Optional[int] = None
    playbook_id: Optional[str] = None  # M1
    playbook_selection: Optional[Dict[str, Any]] = None  # Auto-detection metadata: method, reason, detected_at
    preprocessing_stats: Optional[Dict[str, Any]] = None  # M1
    trust_score: Optional[float] = None  # M2
    policy_status: Optional[str] = None  # M2: "passed" or "failed"
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TrustMetricsResponse(BaseModel):
    """Trust metrics response (M2)."""
    ai_trust_score: float
    metrics: Dict[str, Any]  # All 13 metrics (can contain nested structures)
    chunk_count: int
    aggregated_at: Optional[datetime] = None


class ProductInsightsResponse(BaseModel):
    """Product insights response (M2)."""
    fingerprint: Dict[str, Any]  # Readiness fingerprint (can contain nested structures)
    policy: Dict[str, Any]  # Policy evaluation result
    optimizer: Optional[Dict[str, Any]] = None  # Optimizer suggestions (M3)


@router.post("/", response_model=ProductResponse)
async def create_product(
    request_body: ProductCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new product in the specified workspace.
    """
    # Ensure user has access to the workspace
    ensure_workspace_access(db, request, request_body.workspace_id)
    
    # Check billing limits for product creation
    current_product_count = db.query(Product).filter(
        Product.workspace_id == request_body.workspace_id
    ).count()
    
    if not check_billing_limits(str(request_body.workspace_id), 'max_products', current_product_count, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Product limit exceeded. Please upgrade your plan to create more products."
        )
    
    # Check if product name already exists in workspace
    existing_product = db.query(Product).filter(
        Product.workspace_id == request_body.workspace_id,
        Product.name == request_body.name
    ).first()
    
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product name already exists in this workspace"
        )
    
    # Create new product
    # Initialize playbook_selection metadata if playbook is provided
    playbook_selection = None
    if request_body.playbook_id:
        playbook_selection = {
            "playbook_id": request_body.playbook_id,
            "method": "manual",  # User manually selected during creation
            "reason": None,
            "detected_at": None,
        }
    
    product = Product(
        workspace_id=request_body.workspace_id,
        owner_user_id=get_user_id(current_user),
        name=request_body.name,
        status=ProductStatus.DRAFT,
        playbook_id=request_body.playbook_id,  # M1
        playbook_selection=playbook_selection,  # Store selection metadata
        chunking_config=request_body.chunking_config,  # Chunking configuration
        embedding_config=request_body.embedding_config or {  # Embedding configuration
            "embedder_name": "minilm",
            "embedding_dimension": 384
        },
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return ProductResponse.model_validate(product)


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    workspace_id: Optional[UUID] = Query(None, description="Filter by workspace ID"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List products. If workspace_id is provided, filter by that workspace.
    Otherwise, return products from all accessible workspaces.
    """
    allowed_workspace_ids = allowed_workspaces(request)
    
    query = db.query(Product).filter(Product.workspace_id.in_(allowed_workspace_ids))
    
    if workspace_id:
        # Ensure user has access to the specified workspace
        if workspace_id not in allowed_workspace_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to workspace"
            )
        query = query.filter(Product.workspace_id == workspace_id)
    
    products = query.all()
    return [ProductResponse.model_validate(product) for product in products]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific product by ID.
    """
    from primedata.core.scope import ensure_product_access
    
    product = ensure_product_access(db, request, product_id)
    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    request_body: ProductUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a product's name or status.
    """
    from primedata.core.scope import ensure_product_access
    
    product = ensure_product_access(db, request, product_id)
    
    # Check if new name conflicts with existing product in same workspace
    if request_body.name and request_body.name != product.name:
        existing_product = db.query(Product).filter(
            Product.workspace_id == product.workspace_id,
            Product.name == request_body.name,
            Product.id != product_id
        ).first()
        
        if existing_product:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product name already exists in this workspace"
            )
    
    # Update fields
    if request_body.name is not None:
        product.name = request_body.name
    if request_body.status is not None:
        product.status = request_body.status
    
    # Update chunking configuration
    if request_body.chunking_config is not None:
        current_config = product.chunking_config or {}
        
        if request_body.chunking_config.mode is not None:
            current_config['mode'] = request_body.chunking_config.mode
        
        if request_body.chunking_config.auto_settings is not None:
            current_config['auto_settings'] = request_body.chunking_config.auto_settings
        
        if request_body.chunking_config.manual_settings is not None:
            current_config['manual_settings'] = request_body.chunking_config.manual_settings
        
        product.chunking_config = current_config
    
    # Update embedding configuration
    if request_body.embedding_config is not None:
        product.embedding_config = request_body.embedding_config
    
    db.commit()
    db.refresh(product)
    
    return ProductResponse.model_validate(product)


@router.delete("/{product_id}")
async def delete_product(
    product_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a product.
    """
    # Ensure user has access to the product
    product = ensure_product_access(db, request, product_id)
    
    # Delete the product
    db.delete(product)
    db.commit()
    
    return {"message": "Product deleted successfully"}


@router.get("/{product_id}/trust-metrics", response_model=TrustMetricsResponse)
async def get_trust_metrics(
    product_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get aggregated trust metrics for a product (M2).
    """
    from primedata.core.scope import ensure_product_access
    from primedata.ingestion_pipeline.aird_stages.storage import AirdStorageAdapter
    
    product = ensure_product_access(db, request, product_id)
    
    # Try to get from product model first
    if product.readiness_fingerprint:
        fingerprint_data = product.readiness_fingerprint
        
        # Handle both old format (nested in metrics) and new format (direct fingerprint)
        if isinstance(fingerprint_data, dict):
            # Check if it's the old format with nested fingerprint
            if "fingerprint" in fingerprint_data and isinstance(fingerprint_data["fingerprint"], dict):
                fingerprint = fingerprint_data["fingerprint"]
                trust_score = fingerprint.get("AI_Trust_Score", fingerprint_data.get("trust_score", product.trust_score or 0.0))
            else:
                # New format: fingerprint is directly the metrics dict
                fingerprint = fingerprint_data
                trust_score = fingerprint.get("AI_Trust_Score", product.trust_score or 0.0)
        else:
            fingerprint = {}
            trust_score = product.trust_score or 0.0
        
        return TrustMetricsResponse(
            ai_trust_score=float(trust_score) if trust_score is not None else 0.0,
            metrics=fingerprint,
            chunk_count=0,  # Could be calculated from chunk_metrics if available
        )
    
    # Fallback: try to load from storage
    try:
        storage = AirdStorageAdapter(
            workspace_id=product.workspace_id,
            product_id=product.id,
            version=product.current_version,
        )
        
        metrics = storage.get_metrics_json()
        if metrics:
            from primedata.services.fingerprint import generate_fingerprint
            fingerprint = generate_fingerprint(metrics)
            trust_score = fingerprint.get("AI_Trust_Score", 0.0)
            
            return TrustMetricsResponse(
                ai_trust_score=trust_score,
                metrics=fingerprint,
                chunk_count=len(metrics),
            )
    except Exception as e:
        logger.warning(f"Failed to load metrics from storage: {e}")
    
    # Return empty if no metrics found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Trust metrics not available for this product"
    )


@router.get("/{product_id}/insights", response_model=ProductInsightsResponse)
async def get_product_insights(
    product_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get product insights including fingerprint, policy, and optimizer (M2).
    """
    from primedata.core.scope import ensure_product_access
    from primedata.ingestion_pipeline.aird_stages.storage import AirdStorageAdapter
    from primedata.services.policy_engine import evaluate_policy
    from primedata.ingestion_pipeline.aird_stages.config import get_aird_config
    
    product = ensure_product_access(db, request, product_id)
    
    # Get fingerprint
    fingerprint_data = product.readiness_fingerprint
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
                from primedata.services.fingerprint import generate_fingerprint
                fingerprint = generate_fingerprint(metrics)
        except Exception as e:
            logger.warning(f"Failed to load fingerprint from storage: {e}")
    
    if not fingerprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fingerprint not available for this product"
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
    from primedata.services.optimizer import suggest_next_config
    optimizer = suggest_next_config(
        fingerprint=fingerprint,
        policy=policy_result,
        current_playbook=product.playbook_id,
    )
    
    return ProductInsightsResponse(
        fingerprint=fingerprint,
        policy=policy_result,
        optimizer=optimizer,
    )


@router.get("/{product_id}/validation-summary")
async def download_validation_summary(
    product_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Download validation summary CSV for a product (M3).
    """
    from primedata.core.scope import ensure_product_access
    from primedata.ingestion_pipeline.aird_stages.storage import AirdStorageAdapter
    
    product = ensure_product_access(db, request, product_id)
    
    # Try to get from product model first
    if product.validation_summary_path:
        try:
            from primedata.storage.minio_client import minio_client
            # Extract bucket and key from path
            # Path format: "ws/{ws}/prod/{prod}/v/{version}/artifacts/ai_validation_summary.csv"
            # Or full MinIO path
            if product.validation_summary_path.startswith("primedata-exports/"):
                key = product.validation_summary_path.replace("primedata-exports/", "")
                bucket = "primedata-exports"
            else:
                # Assume it's a key in primedata-exports bucket
                bucket = "primedata-exports"
                key = product.validation_summary_path
            
            csv_data = minio_client.get_bytes(bucket, key)
            if csv_data:
                return Response(
                    content=csv_data,
                    media_type="text/csv",
                    headers={
                        "Content-Disposition": f'attachment; filename="validation_summary_{product_id}.csv"'
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to load validation summary from path: {e}")
    
    # Fallback: try to generate on-the-fly from storage
    try:
        storage = AirdStorageAdapter(
            workspace_id=product.workspace_id,
            product_id=product.id,
            version=product.current_version,
        )
        
        metrics = storage.get_metrics_json()
        if metrics:
            from primedata.services.reporting import generate_validation_summary
            from primedata.ingestion_pipeline.aird_stages.config import get_aird_config
            
            config = get_aird_config()
            csv_content = generate_validation_summary(metrics, config.default_scoring_threshold)
            
            return Response(
                content=csv_content.encode("utf-8"),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f'attachment; filename="validation_summary_{product_id}.csv"'
                }
            )
    except Exception as e:
        logger.warning(f"Failed to generate validation summary: {e}")
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Validation summary not available for this product"
    )


@router.get("/{product_id}/trust-report")
async def download_trust_report(
    product_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Download trust report PDF for a product (M3).
    """
    from primedata.core.scope import ensure_product_access
    from primedata.ingestion_pipeline.aird_stages.storage import AirdStorageAdapter
    
    product = ensure_product_access(db, request, product_id)
    
    # Try to get from product model first
    if product.trust_report_path:
        try:
            from primedata.storage.minio_client import minio_client
            # Extract bucket and key from path
            if product.trust_report_path.startswith("primedata-exports/"):
                key = product.trust_report_path.replace("primedata-exports/", "")
                bucket = "primedata-exports"
            else:
                bucket = "primedata-exports"
                key = product.trust_report_path
            
            pdf_data = minio_client.get_bytes(bucket, key)
            if pdf_data:
                return Response(
                    content=pdf_data,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename="trust_report_{product_id}.pdf"'
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to load trust report from path: {e}")
    
    # Fallback: try to generate on-the-fly from storage
    try:
        storage = AirdStorageAdapter(
            workspace_id=product.workspace_id,
            product_id=product.id,
            version=product.current_version,
        )
        
        metrics = storage.get_metrics_json()
        if metrics:
            from primedata.services.reporting import generate_trust_report
            from primedata.ingestion_pipeline.aird_stages.config import get_aird_config
            
            config = get_aird_config()
            pdf_bytes = generate_trust_report(metrics, config.default_scoring_threshold)
            
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="trust_report_{product_id}.pdf"'
                }
            )
    except Exception as e:
        logger.warning(f"Failed to generate trust report: {e}")
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Trust report not available for this product"
    )


class ChunkMetadataResponse(BaseModel):
    """Chunk metadata response (M4)."""
    id: UUID
    chunk_id: str
    score: Optional[float]
    source_file: Optional[str]
    page_number: Optional[int]
    section: Optional[str]
    field_name: Optional[str]
    extra_tags: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/{product_id}/chunk-metadata", response_model=List[ChunkMetadataResponse])
async def list_chunk_metadata(
    product_id: UUID,
    version: Optional[int] = Query(None, description="Filter by version"),
    section: Optional[str] = Query(None, description="Filter by section"),
    field_name: Optional[str] = Query(None, description="Filter by field name"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List chunk metadata for a product (M4).
    """
    from primedata.core.scope import ensure_product_access
    from primedata.services.vector_metadata import get_chunk_metadata
    
    product = ensure_product_access(db, request, product_id)
    
    # Use version from product if not specified
    if version is None:
        version = product.current_version
    
    metadata = get_chunk_metadata(
        db=db,
        product_id=product_id,
        version=version,
        section=section,
        field_name=field_name,
        limit=limit,
        offset=offset,
    )
    
    return [ChunkMetadataResponse.model_validate(m) for m in metadata]


class CostEstimateRequest(BaseModel):
    """Request model for cost estimation (M5)."""
    playbook_id: Optional[str] = None  # REGULATORY/SCANNED/TECH/None


class CostEstimateResponse(BaseModel):
    """Response model for cost estimation (M5)."""
    filename: str
    playbook: str
    estimated_tokens: int
    estimated_chunks: int
    price_model: Dict[str, float]
    estimated_cost_usd: float


@router.post("/estimate", response_model=CostEstimateResponse, status_code=status.HTTP_200_OK)
async def estimate_cost(
    file: UploadFile = File(...),
    playbook_id: Optional[str] = Form(None),  # REGULATORY/SCANNED/TECH/None
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Estimate cost for creating AI-ready data from a file (M5).
    
    Lightweight estimate endpoint:
      • Extracts text from file
      • Selects playbook (forced or via router)
      • Reads chunking.max_tokens from that playbook YAML
      • Computes estimated chunks and cost
    Does NOT create a Product or run the full pipeline.
    """
    import tempfile
    import shutil
    import math
    from pathlib import Path
    from primedata.ingestion_pipeline.aird_stages.playbooks.router import route_playbook, resolve_playbook_file
    from primedata.ingestion_pipeline.aird_stages.playbooks.loader import load_playbook_yaml
    from primedata.ingestion_pipeline.aird_stages.utils.text_processing import tokens_estimate
    
    # Create temp file
    tmp_dir = Path(tempfile.gettempdir()) / "primedata_estimates"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / file.filename
    
    try:
        # 1) Save temp file
        with tmp_path.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)
        
        # 2) Extract text - use simple text extraction for estimate
        try:
            # For cost estimation, we'll use a simple text extraction
            # In production, this should match the actual preprocessing extraction logic
            if tmp_path.suffix.lower() == '.txt':
                text = tmp_path.read_text(encoding='utf-8', errors='ignore')
            elif tmp_path.suffix.lower() == '.pdf':
                # Try PDF extraction if available
                try:
                    import PyPDF2
                    with tmp_path.open('rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        text = '\n'.join([page.extract_text() for page in pdf_reader.pages])
                except ImportError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="PDF extraction requires PyPDF2. Please install it or use a .txt file."
                    )
            else:
                # Try to read as text
                text = tmp_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Failed to extract text: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to extract text for estimate: {e}",
            )
        
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text extracted from file."
            )
        
        # 3) Choose playbook (forced or via router)
        if playbook_id and playbook_id.upper() in {"REGULATORY", "SCANNED", "TECH"}:
            pb_id = playbook_id.upper()
        else:
            # Use router to select playbook
            pb_id, _ = route_playbook(sample_text=text[:1000], filename=file.filename)
        
        # 4) Load chunking config to get max_tokens
        playbook_file = resolve_playbook_file(pb_id)
        if not playbook_file:
            # Fallback to default
            chunk_cfg = {"max_tokens": 900}
        else:
            try:
                playbook_data = load_playbook_yaml(playbook_file)
                chunk_cfg = playbook_data.get("chunking", {}) or {}
            except Exception as e:
                logger.warning(f"Failed to load playbook {pb_id}: {e}, using defaults")
                chunk_cfg = {}
        
        max_tokens = int(chunk_cfg.get("max_tokens", 900) or 900)
        
        # 5) Estimate tokens using same heuristic as preprocess
        token_est = tokens_estimate(text)
        
        # 6) Estimate chunk count
        est_chunks = max(1, math.ceil(token_est / max_tokens)) if max_tokens > 0 else 1
        
        # 7) Simple cost model (adjust to your real infra/API costs)
        PRICE_PREPROC_PER_1K = 0.0001  # $ per 1k tokens for preprocessing
        PRICE_EMBED_PER_1K = 0.0002    # $ per 1k tokens for embedding
        total_per_1k = PRICE_PREPROC_PER_1K + PRICE_EMBED_PER_1K
        
        est_cost = (token_est / 1000.0) * total_per_1k
        
        logger.info(f"Cost estimate: file={file.filename}, playbook={pb_id}, tokens={token_est}, chunks={est_chunks}, cost=${est_cost:.6f}")
        
        return CostEstimateResponse(
            filename=file.filename,
            playbook=pb_id,
            estimated_tokens=token_est,
            estimated_chunks=est_chunks,
            price_model={
                "preprocess_per_1k_tokens": PRICE_PREPROC_PER_1K,
                "embed_per_1k_tokens": PRICE_EMBED_PER_1K,
                "total_per_1k_tokens": total_per_1k,
            },
            estimated_cost_usd=round(est_cost, 6),
        )
    
    finally:
        # Cleanup
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {tmp_path}: {e}")


class ContentAnalysisRequest(BaseModel):
    content: str
    filename: Optional[str] = None

class ContentAnalysisResponse(BaseModel):
    content_type: str
    confidence: float
    recommended_config: Dict[str, Any]
    reasoning: str

class ChunkingPreviewRequest(BaseModel):
    content: str
    config: Dict[str, Any]

class ChunkingPreviewResponse(BaseModel):
    total_chunks: int
    avg_chunk_size: float
    min_chunk_size: int
    max_chunk_size: int
    estimated_retrieval_quality: str
    preview_chunks: List[Dict[str, Any]]


@router.post("/{product_id}/analyze-content", response_model=ContentAnalysisResponse)
async def analyze_content(
    product_id: UUID,
    request_body: ContentAnalysisRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze content and recommend optimal chunking configuration.
    """
    # Ensure user has access to the product
    product = ensure_product_access(db, request, product_id)
    
    try:
        # Analyze content
        chunking_config = content_analyzer.analyze_content(
            request_body.content, 
            request_body.filename
        )
        
        return ContentAnalysisResponse(
            content_type=chunking_config.content_type.value,
            confidence=chunking_config.confidence,
            recommended_config={
                "chunk_size": chunking_config.chunk_size,
                "chunk_overlap": chunking_config.chunk_overlap,
                "min_chunk_size": chunking_config.min_chunk_size,
                "max_chunk_size": chunking_config.max_chunk_size,
                "strategy": chunking_config.strategy.value
            },
            reasoning=chunking_config.reasoning
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Content analysis failed: {str(e)}"
        )


@router.post("/{product_id}/preview-chunking", response_model=ChunkingPreviewResponse)
async def preview_chunking(
    product_id: UUID,
    request_body: ChunkingPreviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Preview how content would be chunked with given configuration.
    """
    # Ensure user has access to the product
    product = ensure_product_access(db, request, product_id)
    
    try:
        # Create ChunkingConfig object from request
        from primedata.analysis.content_analyzer import ChunkingConfig, ChunkingStrategy, ContentType
        
        config = ChunkingConfig(
            chunk_size=request_body.config.get('chunk_size', 1000),
            chunk_overlap=request_body.config.get('chunk_overlap', 200),
            min_chunk_size=request_body.config.get('min_chunk_size', 100),
            max_chunk_size=request_body.config.get('max_chunk_size', 2000),
            strategy=ChunkingStrategy(request_body.config.get('strategy', 'fixed_size')),
            content_type=ContentType(request_body.config.get('content_type', 'general')),
            confidence=1.0,
            reasoning="User preview"
        )
        
        # Generate preview
        preview = content_analyzer.preview_chunking(request_body.content, config)
        
        return ChunkingPreviewResponse(
            total_chunks=preview['total_chunks'],
            avg_chunk_size=preview['avg_chunk_size'],
            min_chunk_size=preview['min_chunk_size'],
            max_chunk_size=preview['max_chunk_size'],
            estimated_retrieval_quality=preview['estimated_retrieval_quality'],
            preview_chunks=preview['chunks']
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chunking preview failed: {str(e)}"
        )


@router.post("/{product_id}/auto-configure-chunking")
async def auto_configure_chunking(
    product_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Automatically configure chunking settings based on product's data sources.
    """
    # Ensure user has access to the product
    product = ensure_product_access(db, request, product_id)
    
    try:
        # Get sample content from data sources
        from primedata.storage.minio_client import minio_client
        from primedata.storage.paths import raw_prefix
        
        # Try to get sample content from the latest version
        version = product.current_version or 1
        raw_prefix_path = raw_prefix(product.workspace_id, product_id, version)
        
        # Get a few sample files
        raw_objects = minio_client.list_objects("primedata-raw", raw_prefix_path)
        sample_content = ""
        
        for obj in raw_objects[:3]:  # Sample first 3 files
            content = minio_client.get_object("primedata-raw", obj['name'])
            if content:
                sample_content += content.decode('utf-8', errors='ignore')[:5000]  # First 5000 chars
                if len(sample_content) > 10000:  # Limit total sample size
                    break
        
        if not sample_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No content found to analyze. Please run data ingestion first."
            )
        
        # Analyze content and get recommended configuration
        chunking_config = content_analyzer.analyze_content(sample_content)
        
        # Update product configuration
        current_config = product.chunking_config or {}
        current_config.update({
            'mode': 'auto',
            'auto_settings': {
                'content_type': chunking_config.content_type.value,
                'model_optimized': True,
                'confidence_threshold': 0.7
            },
            'manual_settings': {
                'chunk_size': chunking_config.chunk_size,
                'chunk_overlap': chunking_config.chunk_overlap,
                'min_chunk_size': chunking_config.min_chunk_size,
                'max_chunk_size': chunking_config.max_chunk_size,
                'chunking_strategy': chunking_config.strategy.value
            },
            'last_analyzed': datetime.utcnow().isoformat(),
            'analysis_confidence': chunking_config.confidence
        })
        
        product.chunking_config = current_config
        db.commit()
        
        return {
            "message": "Chunking configuration updated automatically",
            "content_type": chunking_config.content_type.value,
            "confidence": chunking_config.confidence,
            "reasoning": chunking_config.reasoning,
            "recommended_config": {
                "chunk_size": chunking_config.chunk_size,
                "chunk_overlap": chunking_config.chunk_overlap,
                "min_chunk_size": chunking_config.min_chunk_size,
                "max_chunk_size": chunking_config.max_chunk_size,
                "strategy": chunking_config.strategy.value
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-configuration failed: {str(e)}"
        )


@router.get("/{product_id}/mlflow-metrics")
async def get_mlflow_metrics(
    product_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get MLflow metrics for the product's latest pipeline run.
    DISABLED: MLflow integration removed.
    """
    # Ensure user has access to the product
    product = ensure_product_access(db, request, product_id)
    
    # Return empty response - MLflow disabled (no MLflow queries will be made)
    return {
        "has_mlflow_data": False,
        "message": "MLflow tracking is disabled"
    }


@router.get("/{product_id}/mlflow-run-url")
async def get_mlflow_run_url(
    product_id: UUID,
    request: Request,
    run_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get MLflow UI URL for viewing runs.
    DISABLED: MLflow integration removed.
    """
    # Ensure user has access to the product
    product = ensure_product_access(db, request, product_id)
    
    # Return empty response - MLflow disabled
    return {
        "mlflow_ui_url": None,
        "tracking_uri": None,
        "message": "MLflow tracking is disabled"
    }


class PromoteVersionRequest(BaseModel):
    """Request model for promoting a version to production."""
    version: int


@router.post("/{product_id}/promote")
async def promote_version(
    product_id: UUID,
    request_body: PromoteVersionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Promote a specific version to production by setting up a Qdrant alias.
    """
    # Ensure user has access to the product
    product = ensure_product_access(db, request, product_id)
    
    version = request_body.version
    
    # Check if the version exists and has succeeded
    pipeline_run = db.query(PipelineRun).filter(
        PipelineRun.product_id == product_id,
        PipelineRun.version == version,
        PipelineRun.status == PipelineRunStatus.SUCCEEDED
    ).first()
    
    if not pipeline_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found or has not succeeded"
        )
    
    try:
        from primedata.indexing.qdrant_client import qdrant_client
        
        # Set the production alias in Qdrant
        success = qdrant_client.set_prod_alias(
            workspace_id=str(product.workspace_id),
            product_id=str(product_id),
            version=version
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set production alias in Qdrant"
            )
        
        # Update the product's promoted_version
        product.promoted_version = version
        db.commit()
        db.refresh(product)
        
        return {
            "message": f"Version {version} promoted to production successfully",
            "promoted_version": version,
            "alias_name": f"prod_ws_{product.workspace_id}__prod_{product_id}",
            "collection_name": f"ws_{product.workspace_id}__prod_{product_id}__v_{version}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to promote version: {str(e)}"
        )


@router.get("/{product_id}/mlflow-metrics/{version}")
async def get_mlflow_metrics_for_version(
    product_id: UUID,
    version: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_optional)
):
    """
    Get MLflow metrics for a specific version of the product's pipeline run.
    DISABLED: MLflow integration removed.
    """
    # Ensure user has access to the product
    product = ensure_product_access(db, request, product_id)
    
    # Return empty response - MLflow disabled (no MLflow queries will be made)
    return {
        "has_mlflow_data": False,
        "message": "MLflow tracking is disabled",
        "version": version
    }
