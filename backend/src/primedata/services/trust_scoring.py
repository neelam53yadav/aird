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
