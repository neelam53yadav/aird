"""
Trust scoring service for PrimeData.

Ports AIRD scoring logic with support for primary scorer (scoring_utils) and fallback scorer.
"""

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import regex as re
from loguru import logger

# Import AI-Ready metric services
from primedata.services.chunk_coherence import calculate_chunk_coherence
from primedata.services.noise_detection import calculate_noise_ratio

# Try to import primary scorer
try:
    from primedata.services.scoring_utils import load_weights, score_file_data

    _PRIMARY_SCORER = True
    logger.info("Primary scorer (scoring_utils) available")
except ImportError:
    _PRIMARY_SCORER = False
    logger.warning("Primary scorer not available, using fallback scorer")
    score_file_data = None
    load_weights = None

# Regex patterns for fallback scorer
ASCII_RE = re.compile(r"^[\x00-\x7F]+$")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\s-]?)?(?:\(\d{3}\)|\d{3})[\s-]?\d{3}[\s-]?\d{4}")
SENT_SPLIT_RE = re.compile(r"(?<!\b[A-Z])[.!?。۔؟]+(?=\s+[A-Z0-9\"'])")


def _ttr(tokens: List[str]) -> float:
    """Type-token ratio."""
    if not tokens:
        return 0.0
    return len(set(tokens)) / max(1, len(tokens))


def _ascii_ratio(s: str, probe: int = 1000) -> float:
    """Calculate ASCII character ratio."""
    ss = s[:probe]
    if not ss:
        return 1.0
    ascii_count = sum(1 for c in ss if ord(c) < 128)
    return ascii_count / len(ss)


def _avg_sentence_len(s: str) -> float:
    """Calculate average sentence length."""
    sents = [x.strip() for x in re.split(SENT_SPLIT_RE, s) if x and x.strip()]
    if not sents:
        return float(len(s.split()))
    return sum(len(x.split()) for x in sents) / max(1, len(sents))


def _clip01(x: float) -> float:
    """Clip value to [0, 1] range."""
    return max(0.0, min(1.0, x))


def _normalize_token_count(n_tokens: float, target: float = 900.0) -> float:
    """Normalize token count to 0-1 range around target."""
    if n_tokens <= 0:
        return 0.0
    ratio = n_tokens / target
    return _clip01(math.exp(-((ratio - 1.0) ** 2) / 0.5))


def _fallback_weights() -> Dict[str, float]:
    """Default weights for fallback scorer."""
    return {
        "Completeness": 0.08,
        "Accuracy": 0.08,
        "Secure": 0.10,
        "Quality": 0.10,
        "Timeliness": 0.04,
        "Token_Count": 0.06,
        "GPT_Confidence": 0.08,
        "Context_Quality": 0.10,
        "Metadata_Presence": 0.10,
        "Audience_Intentionality": 0.06,
        "Diversity": 0.06,
        "Audience_Accessibility": 0.06,
        "KnowledgeBase_Ready": 0.08,
    }


def _fallback_score_record(entry: Dict[str, Any], weights: Dict[str, float]) -> Dict[str, Any]:
    """
    Fallback heuristic scorer that emits the same metric keys as primary scorer.
    All metric values are 0–100; AI_Trust_Score is a weighted sum.
    """
    text = (entry.get("text") or "").strip()
    section = (entry.get("section") or "").strip().lower()
    field_name = (entry.get("field_name") or "").strip().lower()
    document_id = (entry.get("document_id") or "").strip()
    audience = (entry.get("audience") or "unknown").strip().lower()
    token_est = float(entry.get("token_est") or len(text) / 4.0)

    # 1) Basic signals
    completeness = 1.0 if text else 0.0
    accuracy = _ascii_ratio(text)
    pii_hits = bool(EMAIL_RE.search(text) or PHONE_RE.search(text))
    secure = 1.0 if not pii_hits else 0.75

    # 2) Quality/readability proxies
    avg_sl = _avg_sentence_len(text) if text else 0.0
    if avg_sl <= 0:
        quality = 0.0
    elif avg_sl < 10:
        quality = avg_sl / 10.0
    elif avg_sl > 30:
        quality = max(0.0, 1.0 - (avg_sl - 30) / 30.0)
    else:
        quality = 1.0

    # 3) Timeliness (no date here) -> neutral 0.5
    timeliness = 0.5

    # 4) Token count shape
    token_count = _normalize_token_count(token_est)

    # 5) Placeholder confidence
    gpt_conf = 0.85

    # 6) Context quality
    ctx_hit = 1.0 if (section and section in text.lower()) else 0.5
    context_quality = ctx_hit

    # 7) Metadata presence
    meta_presence = 1.0 if (section and field_name and document_id) else 0.5

    # 8) Audience intentionality
    aud_intent = 1.0 if audience not in ("", "unknown") else 0.25

    # 9) Diversity
    toks = re.findall(r"\w+", text.lower())
    diversity = _ttr(toks)

    # 10) Audience accessibility
    if 10 <= avg_sl <= 25:
        aud_access = 1.0
    else:
        d = min(abs(avg_sl - 17.5) / 25.0, 1.0) if avg_sl > 0 else 1.0
        aud_access = max(0.0, 1.0 - d)

    # 11) KnowledgeBase_Ready
    kbr = _clip01(0.4 * meta_presence + 0.4 * quality + 0.2 * context_quality)

    # Convert to 0–100
    metrics_01 = {
        "Completeness": completeness,
        "Accuracy": accuracy,
        "Secure": secure,
        "Quality": quality,
        "Timeliness": timeliness,
        "Token_Count": token_count,
        "GPT_Confidence": gpt_conf,
        "Context_Quality": context_quality,
        "Metadata_Presence": meta_presence,
        "Audience_Intentionality": aud_intent,
        "Diversity": diversity,
        "Audience_Accessibility": aud_access,
        "KnowledgeBase_Ready": kbr,
    }
    metrics_100 = {k: round(v * 100.0, 2) for k, v in metrics_01.items()}

    # Weighted trust
    trust = 0.0
    for k, w in weights.items():
        trust += float(metrics_01.get(k, 0.0)) * float(w)
    trust_100 = round(_clip01(trust) * 100.0, 4)

    out = dict(metrics_100)
    out["AI_Trust_Score"] = trust_100
    return out


def get_scoring_weights(config_path: Optional[str] = None) -> Dict[str, float]:
    """Load scoring weights from config or use defaults."""
    if _PRIMARY_SCORER and load_weights:
        try:
            if config_path:
                return load_weights(config_path)
            # Try default path
            from primedata.ingestion_pipeline.aird_stages.config import get_aird_config

            config = get_aird_config()
            if config.scoring_weights_path:
                return load_weights(config.scoring_weights_path)
        except Exception as e:
            logger.warning(f"Failed to load weights from config: {e}, using fallback")

    return _fallback_weights()


def score_record(record: Dict[str, Any], weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    Score a single record (chunk).

    Args:
        record: Chunk record with text, metadata, etc.
        weights: Optional scoring weights (uses defaults if not provided)

    Returns:
        Dict with all 13 metrics + AI_Trust_Score (0-100 scale)
    """
    if weights is None:
        weights = get_scoring_weights()

    if _PRIMARY_SCORER and score_file_data:
        try:
            return score_file_data(record, weights)
        except Exception as e:
            logger.warning(f"Primary scorer failed: {e}, falling back to heuristic scorer")

    return _fallback_score_record(record, weights)


def aggregate_metrics(metrics: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Aggregate metrics across multiple chunks by averaging.

    Args:
        metrics: List of metric dictionaries (one per chunk)

    Returns:
        Aggregated metrics dictionary (Readiness Fingerprint)
    """
    if not metrics:
        return {}

    sums: Dict[str, float] = {}
    counts: Dict[str, int] = {}

    for m in metrics:
        for k, v in m.items():
            if isinstance(v, (int, float)) and k != "file":  # Exclude non-numeric and file tag
                sums[k] = sums.get(k, 0.0) + float(v)
                counts[k] = counts.get(k, 0) + 1

    agg: Dict[str, float] = {}
    for k, total in sums.items():
        c = counts.get(k, 0)
        if c > 0:
            agg[k] = round(total / c, 4)

    return agg


def score_record_with_ai_ready_metrics(
    record: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
    playbook: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Score a record with AI-Ready metrics included.
    
    This extends the existing score_record function with:
    - Chunk Coherence Score
    - Noise Ratio (converted to Noise_Free_Score)
    - Chunk Boundary Quality (calculated at aggregate level)
    - Duplicate Rate (calculated separately at aggregate level)
    
    Args:
        record: Chunk record with text, metadata, etc.
        weights: Optional scoring weights (uses defaults if not provided)
        playbook: Optional playbook configuration for noise patterns and coherence settings
        
    Returns:
        Dict with all metrics including AI-Ready metrics (0-100 scale)
    """
    # Get base metrics from existing scorer
    base_metrics = score_record(record, weights)
    
    # Extract chunk text and domain_type
    chunk_text = (record.get("text") or "").strip()
    domain_type = record.get("domain_type") or record.get("metadata", {}).get("domain_type")
    
    # 1. Calculate Chunk Coherence with domain-adaptive thresholds
    coherence_config = playbook.get("coherence", {}) if playbook else {}
    
    # Get domain-specific threshold if available, otherwise use default
    domain_thresholds = coherence_config.get("domain_min_thresholds", {})
    default_threshold = coherence_config.get("min_coherence_threshold", 0.6)
    
    if domain_type and domain_type.lower() in domain_thresholds:
        min_coherence_threshold = domain_thresholds[domain_type.lower()]
    elif domain_type and domain_type.lower() in ["regulatory", "finance_banking"]:
        # Regulatory/finance content may have lower coherence due to cross-references
        min_coherence_threshold = coherence_config.get("regulatory_min_threshold", 0.5)
    else:
        min_coherence_threshold = default_threshold
    
    coherence_result = calculate_chunk_coherence(
        chunk_text=chunk_text,
        method=coherence_config.get("method", "embedding_similarity"),
        sentence_window=coherence_config.get("sentence_window", 3),
        min_coherence_threshold=min_coherence_threshold
    )
    base_metrics["Chunk_Coherence"] = coherence_result["coherence_score"]
    
    # 2. Calculate Noise Ratio (inverted to score: lower noise = higher score)
    noise_patterns = playbook.get("noise_patterns") if playbook else None
    noise_result = calculate_noise_ratio(chunk_text, noise_patterns)
    # Convert noise ratio to score (0-100, where 0% noise = 100 score)
    noise_score = max(0.0, 100.0 - noise_result["noise_ratio"])
    base_metrics["Noise_Free_Score"] = round(noise_score, 2)
    
    # 3. Chunk Boundary Quality (from existing preprocessing stats)
    # This is calculated at aggregate level, but we can add a per-chunk indicator
    # For now, we'll calculate it at aggregate level in the scoring stage
    
    return base_metrics


def aggregate_metrics_with_ai_ready(
    metrics: List[Dict[str, Any]],
    preprocessing_stats: Optional[Dict[str, Any]] = None
) -> Dict[str, float]:
    """
    Aggregate metrics including AI-Ready metrics.
    
    Args:
        metrics: List of metric dictionaries (one per chunk)
        preprocessing_stats: Preprocessing statistics including mid_sentence_boundary_rate
        
    Returns:
        Aggregated metrics dictionary with AI-Ready metrics included
    """
    # Get base aggregated metrics
    agg = aggregate_metrics(metrics)
    
    # Add AI-Ready aggregate metrics
    
    # 1. Average Chunk Coherence
    coherence_scores = [m.get("Chunk_Coherence", 0) for m in metrics if "Chunk_Coherence" in m]
    if coherence_scores:
        agg["Avg_Chunk_Coherence"] = round(sum(coherence_scores) / len(coherence_scores), 2)
    
    # 2. Average Noise-Free Score
    noise_scores = [m.get("Noise_Free_Score", 100) for m in metrics if "Noise_Free_Score" in m]
    if noise_scores:
        agg["Avg_Noise_Free_Score"] = round(sum(noise_scores) / len(noise_scores), 2)
    
    # 3. Chunk Boundary Quality (from preprocessing stats)
    if preprocessing_stats:
        mid_sentence_rate = preprocessing_stats.get("mid_sentence_boundary_rate", 0.0)
        # Convert to score: 0% mid-sentence breaks = 100 score
        boundary_quality = max(0.0, 100.0 - (mid_sentence_rate * 100))
        agg["Chunk_Boundary_Quality"] = round(boundary_quality, 2)
    
    # 4. Duplicate Rate (calculated separately, but included here for completeness)
    # This would be calculated during preprocessing/fingerprint stage
    
    return agg
