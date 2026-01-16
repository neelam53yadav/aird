"""
Embedding generation module for PrimeData.

This module provides functionality to generate embeddings for text chunks
using various embedding models, with MiniLM as the default.

Key runtime goals (Airflow-friendly):
- Avoid importing heavy torch/sentence-transformers at DAG import time.
- Prefer fastembed (onnxruntime-based) to avoid torch/transformers ABI issues.
- Provide deterministic hash fallback when model deps are unavailable.
"""

import hashlib
import logging
from typing import List, Optional
from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session

from ..core.embedding_config import get_embedding_model_config
from ..core.settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for text using various models."""

    def __init__(
        self,
        model_name: str = "minilm",
        dimension: int = None,
        workspace_id: UUID = None,
        db: Session = None,
    ):
        """
        Initialize embedding generator.

        Args:
            model_name: Name of the embedding model to use
            dimension: Expected embedding dimension (auto-detected if None)
            workspace_id: Optional workspace ID to check for API keys in workspace settings
            db: Optional database session to query workspace settings
        """
        self.model_name = model_name

        model_config = get_embedding_model_config(model_name)
        self.model_config = model_config

        if model_config:
            self.dimension = int(dimension or model_config.dimension or 384)
            logger.info(f"Initializing {model_config.name} with expected dimension {self.dimension}")
        else:
            self.dimension = int(dimension or 384)
            logger.warning(f"Unknown model {model_name}, using fallback dimension {self.dimension}")

        # Runtime handles
        self.model = None  # may be fastembed embedder or other backend
        self.openai_client = None
        self.workspace_id = workspace_id
        self.db = db

        # Initialize the model
        self._load_model()

    # -------------------------
    # Model loading
    # -------------------------
    def _load_model(self):
        """Load the embedding model using centralized configuration."""
        model_config = self.model_config

        try:
            if not model_config:
                logger.warning(f"Unknown model {self.model_name}, falling back to hash-based embeddings")
                self.model = None
                return

            if not getattr(model_config, "is_available", True):
                logger.warning(f"Model {self.model_name} is not available, falling back to hash-based embeddings")
                self.model = None
                return

            model_type = getattr(model_config.model_type, "value", str(model_config.model_type))

            # --- Prefer fastembed for local sentence-transformer class models ---
            if model_type == "sentence_transformers":
                # IMPORTANT:
                # We intentionally prefer fastembed to avoid torch/transformers issues in containers.
                # fastembed supports several popular ST models via ONNX runtime.
                self.model = self._try_load_fastembed(model_config.model_path)
                if self.model is not None:
                    logger.info(f"Loaded fastembed model for {model_config.name}: {model_config.model_path}")
                    return

                # If fastembed is not installed or model unsupported, do NOT auto-import sentence_transformers
                # (it brings torch/transformers and can crash, as you saw).
                logger.warning(
                    "fastembed not available or model not supported. "
                    "Falling back to hash-based embeddings to keep Airflow stable."
                )
                self.model = None
                return

            # --- OpenAI embeddings ---
            if model_type == "openai":
                api_key = self._get_openai_api_key()
                if not api_key:
                    logger.warning(
                        f"OpenAI API key not configured for {model_config.name}. "
                        "Set workspace setting openai_api_key or OPENAI_API_KEY env var. "
                        "Falling back to hash-based embeddings."
                    )
                    self.model = None
                    self.openai_client = None
                    return

                try:
                    import openai  # type: ignore

                    self.openai_client = openai.OpenAI(api_key=api_key)
                    self.model = "openai"
                    logger.info(f"OpenAI model {model_config.name} configured")
                    return
                except ImportError:
                    logger.error("openai package not installed. Install with: pip install openai")
                    self.model = None
                    self.openai_client = None
                    return

            logger.warning(f"Unsupported model type {model_config.model_type} for {self.model_name}")
            self.model = None

        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            logger.warning("Falling back to hash-based embeddings")
            self.model = None
            self.openai_client = None

    def _try_load_fastembed(self, model_path: str):
        """
        Try to load a fastembed TextEmbedding model.
        Returns the embedder instance or None.
        """
        try:
            from fastembed import TextEmbedding  # type: ignore
        except Exception as e:
            logger.warning(f"fastembed not importable: {e}")
            return None

        try:
            # fastembed expects model names it supports, e.g.
            # "sentence-transformers/all-MiniLM-L6-v2"
            # Your config should set model_path accordingly.
            embedder = TextEmbedding(model_name=model_path)
            return embedder
        except Exception as e:
            logger.warning(f"fastembed failed to initialize for model '{model_path}': {e}")
            return None

    def _get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key: workspace settings first, then environment."""
        api_key = None

        if self.workspace_id and self.db:
            try:
                from primedata.db.models import Workspace  # local import to avoid heavy imports

                ws = self.db.query(Workspace).filter(Workspace.id == self.workspace_id).first()
                if ws and getattr(ws, "settings", None):
                    api_key = ws.settings.get("openai_api_key")
            except Exception as e:
                logger.warning(f"Failed to load workspace settings for OpenAI key: {e}")

        if not api_key:
            settings = get_settings()
            api_key = getattr(settings, "OPENAI_API_KEY", None)

        return api_key

    # -------------------------
    # Embedding generation
    # -------------------------
    def embed(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        if not text:
            return self._coerce_dim(np.zeros(self.dimension, dtype=np.float32))

        # OpenAI
        if self.model == "openai" and self.openai_client and self.model_config:
            try:
                resp = self.openai_client.embeddings.create(model=self.model_config.model_path, input=text)
                vec = np.array(resp.data[0].embedding, dtype=np.float32)
                return self._coerce_dim(vec)
            except Exception as e:
                logger.error(f"Error generating OpenAI embedding: {e}")
                return self._hash_embedding(text)

        # fastembed (TextEmbedding)
        if self.model is not None and self.model != "openai":
            try:
                # fastembed returns an iterator of numpy arrays
                vec = next(iter(self.model.embed([text])))
                vec = np.asarray(vec, dtype=np.float32)
                return self._coerce_dim(vec)
            except Exception as e:
                logger.error(f"Error generating embedding with fastembed: {e}")
                return self._hash_embedding(text)

        # hash fallback
        return self._hash_embedding(text)

    def embed_batch(self, texts: List[str], batch_size: Optional[int] = None) -> List[np.ndarray]:
        """Generate embeddings for a batch of texts."""
        if not texts:
            return []

        # OpenAI
        if self.model == "openai" and self.openai_client and self.model_config:
            try:
                resp = self.openai_client.embeddings.create(model=self.model_config.model_path, input=texts)
                out = [self._coerce_dim(np.array(item.embedding, dtype=np.float32)) for item in resp.data]
                return out
            except Exception as e:
                logger.error(f"Error generating OpenAI batch embeddings: {e}")
                return [self._hash_embedding(t) for t in texts]

        # fastembed
        if self.model is not None and self.model != "openai":
            try:
                # fastembed does its own batching internally
                vectors = list(self.model.embed(texts))
                out = [self._coerce_dim(np.asarray(v, dtype=np.float32)) for v in vectors]
                return out
            except Exception as e:
                logger.error(f"Error generating batch embeddings with fastembed: {e}")
                return [self._hash_embedding(t) for t in texts]

        # hash fallback
        return [self._hash_embedding(t) for t in texts]

    # -------------------------
    # Helpers
    # -------------------------
    def _coerce_dim(self, vec: np.ndarray) -> np.ndarray:
        """
        Ensure vector has exactly self.dimension.
        Pads or truncates deterministically if needed.
        """
        vec = np.asarray(vec, dtype=np.float32).reshape(-1)
        if vec.shape[0] == self.dimension:
            return vec

        if vec.shape[0] > self.dimension:
            return vec[: self.dimension]

        # pad with zeros
        out = np.zeros(self.dimension, dtype=np.float32)
        out[: vec.shape[0]] = vec
        return out

    def _hash_embedding(self, text: str) -> np.ndarray:
        """Generate a deterministic hash-based embedding as fallback."""
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        out = np.zeros(self.dimension, dtype=np.float32)
        hb = bytes.fromhex(text_hash)

        for i in range(self.dimension):
            b = hb[i % len(hb)]
            out[i] = (float(b) - 128.0) / 128.0

        # embed length signal
        out[0] = min(len(text) / 1000.0, 1.0)
        return out

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        if self.model == "openai" and self.model_config:
            return int(self.model_config.dimension)
        return int(self.dimension)

    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        is_openai = self.model == "openai" and self.openai_client is not None
        is_fastembed = self.model is not None and self.model != "openai"
        model_loaded = is_openai or is_fastembed

        model_type = None
        if is_openai:
            model_type = "openai"
        elif is_fastembed:
            model_type = "fastembed"

        return {
            "model_name": self.model_name,
            "dimension": self.get_dimension(),
            "model_loaded": model_loaded,
            "model_type": model_type,
            "fallback_mode": not model_loaded,
        }


def create_embedding_generator(
    model_name: str = "minilm",
    dimension: int = 384,
    workspace_id: UUID = None,
    db: Session = None,
) -> EmbeddingGenerator:
    """Factory function to create an embedding generator."""
    return EmbeddingGenerator(model_name, dimension, workspace_id, db)


_default_embedder = None


def get_default_embedder() -> EmbeddingGenerator:
    """
    Lazy-loaded default embedder.

    Do NOT load models at import time (Airflow DAG import timeout risk).
    """
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = EmbeddingGenerator("minilm", 384)
    return _default_embedder
