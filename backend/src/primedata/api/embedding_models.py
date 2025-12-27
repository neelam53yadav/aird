"""
API endpoints for embedding model configuration.

This module provides REST API endpoints to serve embedding model configurations
to the frontend, ensuring consistency and centralized management.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..core.embedding_config import EmbeddingModelRegistry, EmbeddingModelType, EmbeddingModelConfig

router = APIRouter(prefix="/api/v1/embedding-models", tags=["embedding-models"])


class EmbeddingModelResponse(BaseModel):
    """Response model for embedding model information."""

    id: str
    name: str
    description: str
    dimension: int
    requires_api_key: bool
    cost_per_token: float = None
    metadata: Dict[str, Any] = None


class EmbeddingModelsListResponse(BaseModel):
    """Response model for list of embedding models."""

    models: List[EmbeddingModelResponse]
    total: int


@router.get("/", response_model=EmbeddingModelsListResponse)
async def get_embedding_models(
    model_type: EmbeddingModelType = Query(None, description="Filter by model type"),
    free_only: bool = Query(False, description="Show only free models (no API key required)"),
    paid_only: bool = Query(False, description="Show only paid models (require API key)"),
):
    """
    Get all available embedding models.

    Args:
        model_type: Filter by specific model type
        free_only: Show only models that don't require API keys
        paid_only: Show only models that require API keys

    Returns:
        List of available embedding models
    """
    try:
        # Get models based on filters
        if model_type:
            models = EmbeddingModelRegistry.get_models_by_type(model_type)
        elif free_only:
            models = EmbeddingModelRegistry.get_free_models()
        elif paid_only:
            models = EmbeddingModelRegistry.get_paid_models()
        else:
            models = EmbeddingModelRegistry.get_available_models()

        # Convert to response format
        model_responses = [
            EmbeddingModelResponse(
                id=model.id,
                name=model.name,
                description=model.description,
                dimension=model.dimension,
                requires_api_key=model.requires_api_key,
                cost_per_token=model.cost_per_token,
                metadata=model.metadata,
            )
            for model in models
        ]

        return EmbeddingModelsListResponse(models=model_responses, total=len(model_responses))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve embedding models: {str(e)}")


@router.get("/{model_id}", response_model=EmbeddingModelResponse)
async def get_embedding_model(model_id: str):
    """
    Get specific embedding model configuration.

    Args:
        model_id: The ID of the embedding model

    Returns:
        Embedding model configuration
    """
    try:
        model = EmbeddingModelRegistry.get_model(model_id)

        if not model:
            raise HTTPException(status_code=404, detail=f"Embedding model '{model_id}' not found")

        if not model.is_available:
            raise HTTPException(status_code=400, detail=f"Embedding model '{model_id}' is not available")

        return EmbeddingModelResponse(
            id=model.id,
            name=model.name,
            description=model.description,
            dimension=model.dimension,
            requires_api_key=model.requires_api_key,
            cost_per_token=model.cost_per_token,
            metadata=model.metadata,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve embedding model: {str(e)}")


@router.get("/{model_id}/dimension")
async def get_embedding_model_dimension(model_id: str):
    """
    Get the embedding dimension for a specific model.

    Args:
        model_id: The ID of the embedding model

    Returns:
        Embedding dimension
    """
    try:
        dimension = EmbeddingModelRegistry.get_model_dimension(model_id)

        if dimension is None:
            raise HTTPException(status_code=404, detail=f"Embedding model '{model_id}' not found")

        return {"model_id": model_id, "dimension": dimension}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve embedding dimension: {str(e)}")


@router.get("/{model_id}/validate")
async def validate_embedding_model(model_id: str):
    """
    Validate if an embedding model ID is valid and available.

    Args:
        model_id: The ID of the embedding model to validate

    Returns:
        Validation result
    """
    try:
        is_valid = EmbeddingModelRegistry.validate_model_id(model_id)

        return {"model_id": model_id, "is_valid": is_valid, "is_available": is_valid}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate embedding model: {str(e)}")


@router.get("/types/", response_model=List[str])
async def get_embedding_model_types():
    """
    Get all available embedding model types.

    Returns:
        List of available model types
    """
    try:
        return [model_type.value for model_type in EmbeddingModelType]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve model types: {str(e)}")
