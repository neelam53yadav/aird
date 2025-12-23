"""
Embedding generation module for PrimeData.

This module provides functionality to generate embeddings for text chunks
using various embedding models, with MiniLM as the default.
"""

import logging
import hashlib
import numpy as np
from typing import List, Optional, Union
from pathlib import Path
from ..core.embedding_config import EmbeddingModelRegistry, get_embedding_model_config

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """Generate embeddings for text using various models."""
    
    def __init__(self, model_name: str = "minilm", dimension: int = None):
        """
        Initialize embedding generator.
        
        Args:
            model_name: Name of the embedding model to use
            dimension: Expected embedding dimension (auto-detected if None)
        """
        self.model_name = model_name
        
        # Get model configuration and validate
        model_config = get_embedding_model_config(model_name)
        if model_config:
            # Use configured dimension if not provided
            self.dimension = dimension or model_config.dimension
            logger.info(f"Initializing {model_config.name} with dimension {self.dimension}")
        else:
            # Fallback for unknown models
            self.dimension = dimension or 384
            logger.warning(f"Unknown model {model_name}, using fallback dimension {self.dimension}")
        
        self.model = None
        self.tokenizer = None
        
        # Initialize the model
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model using centralized configuration."""
        try:
            # Get model configuration from registry
            model_config = get_embedding_model_config(self.model_name)
            
            if not model_config:
                logger.warning(f"Unknown model {self.model_name}, falling back to hash-based embeddings")
                self.model = None
                return
            
            if not model_config.is_available:
                logger.warning(f"Model {self.model_name} is not available, falling back to hash-based embeddings")
                self.model = None
                return
            
            # Load model based on type
            if model_config.model_type.value == "sentence_transformers":
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_config.model_path)
                logger.info(f"Loaded {model_config.name} model with dimension {self.model.get_sentence_embedding_dimension()}")
                
            elif model_config.model_type.value == "openai":
                # OpenAI models are handled differently - they require API calls
                # For now, we'll use a placeholder that indicates OpenAI integration needed
                logger.info(f"OpenAI model {model_config.name} configured - API integration required")
                self.model = None  # Will be handled by OpenAI client
                
            else:
                logger.warning(f"Unsupported model type {model_config.model_type} for {self.model_name}")
                self.model = None
                
        except ImportError as e:
            logger.warning(f"Failed to import required dependencies: {e}")
            logger.warning("Falling back to hash-based embeddings")
            self.model = None
            
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            logger.warning("Falling back to hash-based embeddings")
            self.model = None
    
    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        if self.model is not None:
            try:
                # Use the loaded model
                embedding = self.model.encode(text, convert_to_numpy=True)
                return embedding
                
            except Exception as e:
                logger.error(f"Error generating embedding with model: {e}")
                logger.warning("Falling back to hash-based embedding")
                return self._hash_embedding(text)
        else:
            # Fallback to hash-based embedding
            return self._hash_embedding(text)
    
    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors as numpy arrays
        """
        if self.model is not None:
            try:
                # Use the loaded model for batch processing
                embeddings = self.model.encode(texts, convert_to_numpy=True)
                return [emb for emb in embeddings]
                
            except Exception as e:
                logger.error(f"Error generating batch embeddings with model: {e}")
                logger.warning("Falling back to hash-based embeddings")
                return [self._hash_embedding(text) for text in texts]
        else:
            # Fallback to hash-based embeddings
            return [self._hash_embedding(text) for text in texts]
    
    def _hash_embedding(self, text: str) -> np.ndarray:
        """
        Generate a hash-based embedding as fallback.
        
        This creates a deterministic embedding by hashing the text
        and converting it to a vector of the expected dimension.
        
        Args:
            text: Input text
            
        Returns:
            Hash-based embedding vector
        """
        # Create a hash of the text
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        
        # Convert hash to a vector of the expected dimension
        embedding = np.zeros(self.dimension)
        
        # Use hash bytes to fill the embedding
        hash_bytes = bytes.fromhex(text_hash)
        for i in range(self.dimension):
            byte_idx = i % len(hash_bytes)
            embedding[i] = (hash_bytes[byte_idx] - 128) / 128.0  # Normalize to [-1, 1]
        
        # Add some text length information
        text_length = len(text)
        embedding[0] = min(text_length / 1000.0, 1.0)  # Normalize length to [0, 1]
        
        return embedding
    
    def get_dimension(self) -> int:
        """Get the embedding dimension."""
        if self.model is not None:
            try:
                return self.model.get_sentence_embedding_dimension()
            except:
                return self.dimension
        return self.dimension
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            'model_name': self.model_name,
            'dimension': self.get_dimension(),
            'model_loaded': self.model is not None,
            'fallback_mode': self.model is None
        }


def create_embedding_generator(model_name: str = "minilm", dimension: int = 384) -> EmbeddingGenerator:
    """
    Factory function to create an embedding generator.
    
    Args:
        model_name: Name of the embedding model
        dimension: Expected embedding dimension
        
    Returns:
        EmbeddingGenerator instance
    """
    return EmbeddingGenerator(model_name, dimension)


# Default embedding generator instance - REMOVED to avoid loading model at import time
# This was causing Airflow DAG import timeouts (30s limit exceeded)
# 
# DO NOT create EmbeddingGenerator instances at module import time!
# Always create them inside task functions or use lazy loading.
#
# For backward compatibility, use get_default_embedder() function below,
# but prefer creating EmbeddingGenerator() instances inside your task functions
# to avoid import-time model loading.

_default_embedder = None

def get_default_embedder() -> EmbeddingGenerator:
    """
    Get the default embedding generator (lazy-loaded).
    
    This avoids loading the model at module import time, which is critical
    for Airflow DAG imports that have a 30s timeout.
    
    Returns:
        EmbeddingGenerator instance
    """
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = EmbeddingGenerator("minilm", 384)
    return _default_embedder

# Removed: default_embedder = EmbeddingGenerator("minilm", 384)
# This was causing import-time model loading which timed out Airflow DAG imports
# Use get_default_embedder() or create EmbeddingGenerator() inside task functions instead
