"""
Chunk coherence calculation for AI-Ready metrics.

Measures semantic cohesion within chunks to ensure they stay on one topic.
"""
import logging
from typing import Dict, List, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Global model instance (lazy-loaded)
_coherence_model: Optional[Any] = None


def get_coherence_model():
    """Get or initialize the coherence model (lazy loading)."""
    global _coherence_model
    if _coherence_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Use a lightweight model for coherence checking
            _coherence_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Initialized coherence model: all-MiniLM-L6-v2")
        except ImportError:
            logger.warning("sentence-transformers not available, coherence will use simple method")
            _coherence_model = None
    return _coherence_model


def calculate_chunk_coherence(
    chunk_text: str,
    method: str = "embedding_similarity",
    sentence_window: int = 3,
    min_coherence_threshold: float = 0.6
) -> Dict[str, Any]:
    """
    Calculate coherence score for a chunk.
    
    Args:
        chunk_text: The chunk text to analyze
        method: Method to use ('embedding_similarity', 'topic_clustering', 'sentence_connectivity')
        sentence_window: Number of previous sentences to compare with (for embedding_similarity)
        min_coherence_threshold: Minimum similarity for "coherent" chunk
        
    Returns:
        Dict with coherence score and metadata
    """
    if not chunk_text or len(chunk_text.strip()) < 50:
        return {
            "coherence_score": 0.0,
            "method": method,
            "sentence_count": 0,
            "avg_similarity": 0.0,
            "is_coherent": False
        }
    
    # Split into sentences (simple approach)
    sentences = [s.strip() for s in chunk_text.split('.') if s.strip()]
    if len(sentences) < 2:
        # Single sentence chunks are considered coherent
        return {
            "coherence_score": 1.0,
            "method": method,
            "sentence_count": len(sentences),
            "avg_similarity": 1.0,
            "is_coherent": True
        }
    
    if method == "embedding_similarity":
        return _coherence_embedding_similarity(sentences, sentence_window, min_coherence_threshold)
    elif method == "sentence_connectivity":
        return _coherence_sentence_connectivity(sentences, min_coherence_threshold)
    else:
        logger.warning(f"Unknown coherence method: {method}, using sentence_connectivity")
        return _coherence_sentence_connectivity(sentences, min_coherence_threshold)


def _coherence_embedding_similarity(
    sentences: List[str],
    window: int,
    threshold: float
) -> Dict[str, Any]:
    """Calculate coherence using sentence embedding similarity."""
    model = get_coherence_model()
    if model is None:
        # Fallback to sentence connectivity if model not available
        return _coherence_sentence_connectivity(sentences, threshold)
    
    try:
        embeddings = model.encode(sentences, convert_to_numpy=True)
        
        similarities = []
        for i in range(1, len(sentences)):
            # Compare current sentence with previous N sentences
            start_idx = max(0, i - window)
            prev_embeddings = embeddings[start_idx:i]
            current_embedding = embeddings[i]
            
            # Calculate average similarity with previous sentences
            if len(prev_embeddings) > 0:
                similarities_matrix = np.dot(prev_embeddings, current_embedding)
                avg_similarity = float(np.mean(similarities_matrix))
                similarities.append(avg_similarity)
        
        if not similarities:
            coherence_score = 1.0
            avg_similarity = 1.0
        else:
            avg_similarity = float(np.mean(similarities))
            # Normalize to 0-100 scale
            coherence_score = min(100.0, max(0.0, avg_similarity * 100))
        
        return {
            "coherence_score": round(coherence_score, 2),
            "method": "embedding_similarity",
            "sentence_count": len(sentences),
            "avg_similarity": round(avg_similarity, 4),
            "is_coherent": avg_similarity >= threshold,
            "similarities": [round(s, 4) for s in similarities[:10]]  # First 10 for debugging
        }
    except Exception as e:
        logger.error(f"Error calculating embedding similarity coherence: {e}")
        # Fallback to sentence connectivity
        return _coherence_sentence_connectivity(sentences, threshold)


def _coherence_sentence_connectivity(
    sentences: List[str],
    threshold: float
) -> Dict[str, Any]:
    """Calculate coherence using sentence connectivity (simple keyword overlap)."""
    # Simple approach: check for common keywords/entities between sentences
    sentence_words = [set(s.lower().split()) for s in sentences]
    
    overlaps = []
    for i in range(1, len(sentence_words)):
        prev_words = sentence_words[i-1]
        curr_words = sentence_words[i]
        
        if len(prev_words) == 0 or len(curr_words) == 0:
            overlap = 0.0
        else:
            # Jaccard similarity
            intersection = len(prev_words & curr_words)
            union = len(prev_words | curr_words)
            overlap = intersection / union if union > 0 else 0.0
        
        overlaps.append(overlap)
    
    if not overlaps:
        avg_overlap = 1.0
    else:
        avg_overlap = float(np.mean(overlaps))
    
    coherence_score = min(100.0, max(0.0, avg_overlap * 100))
    
    return {
        "coherence_score": round(coherence_score, 2),
        "method": "sentence_connectivity",
        "sentence_count": len(sentences),
        "avg_similarity": round(avg_overlap, 4),
        "is_coherent": avg_overlap >= threshold,
        "overlaps": [round(o, 4) for o in overlaps[:10]]
    }

