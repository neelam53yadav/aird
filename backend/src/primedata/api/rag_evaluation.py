"""
RAG Evaluation API endpoints.

Handles synthetic query generation and retrieval metrics calculation.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session

from primedata.core.scope import ensure_product_access
from primedata.core.security import get_current_user
from primedata.db.database import get_db
from primedata.db.models import EvalQuery, EvalRun, Product
from primedata.services.query_generation import generate_queries_for_chunk

router = APIRouter(prefix="/api/v1/rag-evaluation", tags=["RAG Evaluation"])


class EvalQueryResponse(BaseModel):
    """Response model for evaluation query."""
    
    id: str
    chunk_id: str
    query: str
    expected_chunk_id: str
    query_style: Optional[str]
    created_at: str


class EvalRunResponse(BaseModel):
    """Response model for evaluation run."""
    
    id: str
    product_id: str
    version: int
    status: str
    metrics: Optional[dict]
    started_at: Optional[str]
    finished_at: Optional[str]
    created_at: str


@router.post("/products/{product_id}/generate-queries")
async def generate_eval_queries(
    product_id: UUID,
    version: Optional[int] = Query(None, description="Version number (defaults to current)"),
    request_obj: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Generate synthetic evaluation queries for a product version.
    
    This creates queries from chunks to enable RAG evaluation metrics.
    """
    product = ensure_product_access(db, request_obj, product_id)
    
    if version is None:
        version = product.current_version
    
    # TODO: Load chunks from storage and generate queries
    # For Phase 1, this is a placeholder that will be implemented
    # when we have chunk loading infrastructure
    
    return {
        "message": "Query generation endpoint created. Implementation in progress.",
        "product_id": str(product_id),
        "version": version,
        "note": "This will generate queries from chunks in the next iteration"
    }


@router.get("/products/{product_id}/queries", response_model=List[EvalQueryResponse])
async def get_eval_queries(
    product_id: UUID,
    version: Optional[int] = Query(None, description="Version number (defaults to current)"),
    request_obj: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get evaluation queries for a product version."""
    product = ensure_product_access(db, request_obj, product_id)
    
    if version is None:
        version = product.current_version
    
    queries = db.query(EvalQuery).filter(
        EvalQuery.product_id == product_id,
        EvalQuery.version == version
    ).all()
    
    return [
        EvalQueryResponse(
            id=str(q.id),
            chunk_id=q.chunk_id,
            query=q.query,
            expected_chunk_id=q.expected_chunk_id,
            query_style=q.query_style,
            created_at=q.created_at.isoformat()
        )
        for q in queries
    ]


@router.get("/products/{product_id}/runs", response_model=List[EvalRunResponse])
async def get_eval_runs(
    product_id: UUID,
    version: Optional[int] = Query(None, description="Version number (defaults to current)"),
    request_obj: Request = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get evaluation runs for a product version."""
    product = ensure_product_access(db, request_obj, product_id)
    
    if version is None:
        version = product.current_version
    
    runs = db.query(EvalRun).filter(
        EvalRun.product_id == product_id,
        EvalRun.version == version
    ).order_by(EvalRun.created_at.desc()).all()
    
    return [
        EvalRunResponse(
            id=str(r.id),
            product_id=str(r.product_id),
            version=r.version,
            status=r.status,
            metrics=r.metrics,
            started_at=r.started_at.isoformat() if r.started_at else None,
            finished_at=r.finished_at.isoformat() if r.finished_at else None,
            created_at=r.created_at.isoformat()
        )
        for r in runs
    ]

