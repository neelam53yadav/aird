"""
Fingerprint service for PrimeData.

Generates readiness fingerprints by aggregating chunk-level metrics.
"""

from typing import Any, Dict, List, Optional

from loguru import logger
from primedata.services.trust_scoring import aggregate_metrics, aggregate_metrics_with_ai_ready


def generate_fingerprint(
    metrics: List[Dict[str, Any]], 
    preprocessing_stats: Optional[Dict[str, Any]] = None
) -> Dict[str, float]:
    """
    Generate a readiness fingerprint from chunk-level metrics.

    Args:
        metrics: List of metric dictionaries (one per chunk)
        preprocessing_stats: Optional preprocessing statistics for Chunk Boundary Quality

    Returns:
        Readiness fingerprint dictionary with aggregated metrics
    """
    if not metrics:
        logger.warning("No metrics provided for fingerprint generation")
        return {}

    # Use AI-Ready aggregation if preprocessing stats are available
    if preprocessing_stats:
        fingerprint = aggregate_metrics_with_ai_ready(metrics, preprocessing_stats)
    else:
        fingerprint = aggregate_metrics(metrics)

    logger.info(f"Generated fingerprint with {len(fingerprint)} metrics")
    return fingerprint


def aggregate_metrics_by_file(
    metrics: List[Dict[str, Any]],
    file_tag: str,
) -> Optional[Dict[str, float]]:
    """
    Aggregate metrics for a specific file tag.

    Args:
        metrics: List of all metrics
        file_tag: File identifier (e.g., "MyDoc.jsonl")

    Returns:
        Aggregated metrics for the file, or None if no metrics found
    """
    from primedata.services.trust_scoring import aggregate_metrics
    
    file_metrics = [m for m in metrics if m.get("file") == file_tag]
    if not file_metrics:
        return None

    return aggregate_metrics(file_metrics)
