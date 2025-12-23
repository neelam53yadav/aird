"""
Primary scoring utilities (optional).

This module provides advanced scoring using external libraries.
If these libraries are not available, the fallback scorer in trust_scoring.py will be used.
"""

import json
import re
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

try:
    import textstat
    HAS_TEXTSTAT = True
except ImportError:
    HAS_TEXTSTAT = False

try:
    import tiktoken
    TOK = tiktoken.get_encoding("cl100k_base")
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

try:
    from spellchecker import SpellChecker
    spell = SpellChecker()
    HAS_SPELLCHECKER = True
except ImportError:
    HAS_SPELLCHECKER = False

# PII Detection patterns
PII_PATTERNS = [
    r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b",
    r"\b(?:\+?\d{1,3})?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
]


def detect_pii(text: str) -> bool:
    """Detect PII in text."""
    return any(re.search(p, text) for p in PII_PATTERNS)


def score_completeness(tokens) -> float:
    """Score completeness based on token count."""
    return 100.0 if len(tokens) > 1000 else 75.0


def score_accuracy(words) -> float:
    """Score accuracy using spell checker."""
    if not HAS_SPELLCHECKER:
        return 85.0  # Default if spellchecker unavailable
    errors = len(spell.unknown(words[:500]))
    ratio = 1.0 - (errors / max(len(words), 1))
    return max(0.0, min(ratio * 100, 100))


def score_secure(text: str) -> float:
    """Score security (PII detection)."""
    return 0.0 if detect_pii(text) else 100.0


def score_quality(text: str) -> float:
    """Score quality using readability metrics."""
    if not HAS_TEXTSTAT:
        return 75.0  # Default if textstat unavailable
    return max(0.0, min(textstat.flesch_reading_ease(text), 100.0))


def score_timeliness(timestamp: str, ref: str = "2023-01-01") -> float:
    """Score timeliness based on date."""
    try:
        t1 = datetime.strptime(timestamp, "%Y-%m-%d")
        t2 = datetime.strptime(ref, "%Y-%m-%d")
        days = (t2 - t1).days
        return max(0.0, min((1 - days / 365.0) * 100, 100.0))
    except:
        return 50.0


def score_gpt_confidence(text: str) -> float:
    """Placeholder for GPT confidence."""
    return 85.0


def score_context_quality(text: str) -> float:
    """Score context quality based on keyword presence."""
    keywords = ["dose", "indicated", "contraindicated", "elderly",
                "adolescents", "pregnant"]
    hits = sum(1 for kw in keywords if kw in text.lower())
    return min((hits / len(keywords)) * 100, 100.0)


def score_metadata_presence(meta: Dict[str, Any]) -> float:
    """Score metadata presence."""
    required = ["source", "section", "audience", "timestamp"]
    present = sum(1 for k in required if k in meta)
    return (present / len(required)) * 100


def score_audience_intentionality(text: str) -> float:
    """Score audience intentionality."""
    terms = ["hcp", "patient", "regulatory", "doctor"]
    return 100.0 if any(t in text.lower() for t in terms) else 0.0


def score_diversity(text: str) -> float:
    """Score diversity."""
    terms = ["male", "female", "child", "elderly", "comorbid", "pregnant"]
    hits = sum(1 for t in terms if t in text.lower())
    return min((hits / len(terms)) * 100, 100.0)


def score_audience_accessibility(meta: Dict[str, Any]) -> float:
    """Score audience accessibility."""
    return 100.0 if meta.get("audience", "") in ["HCP", "R&D", "Regulatory"] else 0.0


def score_kb_ready(text: str) -> float:
    """Score knowledge base readiness."""
    return 100.0 if len(text.split()) > 50 and "\n" in text else 50.0


def load_weights(path: str) -> Dict[str, float]:
    """Load scoring weights from JSON file."""
    with open(path) as f:
        return json.load(f)


def score_file_data(data: Dict[str, Any], weights: Dict[str, float]) -> Dict[str, Any]:
    """
    Score a file data record using primary scoring methods.
    
    Args:
        data: Record with text and metadata
        weights: Scoring weights dictionary
        
    Returns:
        Dictionary with all 13 metrics + AI_Trust_Score
    """
    text = data.get("text", "")
    meta = data.copy()
    
    if HAS_TIKTOKEN:
        tokens = TOK.encode(text)
    else:
        tokens = text.split()  # Fallback
    
    words = text.split()
    token_score = min(len(tokens) / 1000.0, 1.0) * 100.0
    
    scores = {
        "Completeness": score_completeness(tokens),
        "Accuracy": score_accuracy(words),
        "Secure": score_secure(text),
        "Quality": score_quality(text),
        "Timeliness": score_timeliness(meta.get("timestamp", "")),
        "Token_Count": round(token_score, 2),
        "GPT_Confidence": score_gpt_confidence(text),
        "Context_Quality": score_context_quality(text),
        "Metadata_Presence": score_metadata_presence(meta),
        "Audience_Intentionality": score_audience_intentionality(text),
        "Diversity": score_diversity(text),
        "Audience_Accessibility": score_audience_accessibility(meta),
        "KnowledgeBase_Ready": score_kb_ready(text),
    }
    
    # Penalty adjustments
    alpha = sum(c.isalpha() for c in text) / max(len(text), 1)
    if alpha < 0.5:
        scores["Quality"] *= 0.4
        scores["Accuracy"] *= 0.7
    
    # Weighted aggregate
    total_w = sum(weights.values())
    weighted = sum(min(scores[k], 100.0) * weights.get(k, 0) for k in weights)
    scores["AI_Trust_Score"] = round(weighted / total_w, 2)
    
    return scores




