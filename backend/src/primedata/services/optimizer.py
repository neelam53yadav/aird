"""
Optimizer service for PrimeData.

Provides suggestions for improving AI readiness based on fingerprint and policy evaluation.
"""

from typing import Dict, Any, Optional, List
from loguru import logger


def suggest_next_config(
    fingerprint: Dict[str, float],
    policy: Dict[str, Any],
    current_playbook: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Rule-based Readiness Optimizer that provides actionable recommendations.
    
    Given:
      - fingerprint: aggregate metrics (Readiness Fingerprint)
      - policy: result from policy_engine.evaluate_policy(...)
      - current_playbook: e.g. "REGULATORY" / "SCANNED" / "TECH"
    
    Returns a dict:
      {
        "next_playbook": str | None,
        "config_tweaks": { ... },
        "suggestions": [str, ...],  # General recommendations
        "playbook_recommendations": [str, ...]  # Playbook-specific recommendations
      }
    """
    if not fingerprint:
        return {
            "next_playbook": current_playbook,
            "config_tweaks": {},
            "suggestions": ["No fingerprint available. Run the pipeline to generate metrics."],
            "playbook_recommendations": [],
        }
    
    suggestions: List[str] = []
    playbook_recommendations: List[str] = []
    config_tweaks: Dict[str, Any] = {}
    next_playbook = current_playbook
    
    # Extract metrics
    trust_score = float(fingerprint.get("AI_Trust_Score", 0.0))
    completeness = float(fingerprint.get("Completeness", 0.0))
    kb_ready = float(fingerprint.get("KnowledgeBase_Ready", 0.0))
    secure = float(fingerprint.get("Secure", 0.0))
    metadata = float(fingerprint.get("Metadata_Presence", 0.0))
    quality = float(fingerprint.get("Quality", 0.0))
    
    violations = policy.get("violations", []) if isinstance(policy, dict) else []
    policy_passed = policy.get("policy_passed", False) if isinstance(policy, dict) else False
    
    # Get thresholds for context
    thresholds = policy.get("thresholds", {}) if isinstance(policy, dict) else {}
    min_trust = thresholds.get("min_trust_score", 50.0)
    min_secure = thresholds.get("min_secure", 90.0)
    min_metadata = thresholds.get("min_metadata_presence", 80.0)
    min_kb_ready = thresholds.get("min_kb_ready", 50.0)
    
    # Trust Score recommendations (expanded logic)
    if trust_score < min_trust:
        suggestions.append(f"AI Trust Score ({trust_score:.1f}%) is below the policy threshold ({min_trust}%). Focus on improving overall data quality.")
    elif trust_score < 70.0:
        suggestions.append(f"AI Trust Score ({trust_score:.1f}%) is acceptable but could be improved. Consider enhancing data completeness and quality.")
    elif trust_score < 85.0:
        suggestions.append(f"AI Trust Score ({trust_score:.1f}%) is good. Minor improvements could push it to excellent (>85%).")
    
    # Security recommendations (expanded logic)
    if "security_not_full" in violations:
        suggestions.append(f"Security score ({secure:.1f}%) is below threshold ({min_secure}%). Enable stricter PII redaction and data masking.")
        config_tweaks["redaction_strict"] = True
    elif secure < 100.0:
        if secure < 95.0:
            suggestions.append(f"Security score ({secure:.1f}%) is good but not perfect. Review PII detection and redaction rules.")
        else:
            suggestions.append(f"Security score ({secure:.1f}%) is excellent. Minor improvements could achieve 100%.")
    
    # Metadata recommendations (expanded logic)
    if metadata < min_metadata:
        suggestions.append(f"Metadata Presence ({metadata:.1f}%) is below threshold ({min_metadata}%). Enhance metadata extraction and enrichment.")
        config_tweaks["force_metadata_extraction"] = True
    elif metadata < 90.0:
        if metadata < 85.0:
            suggestions.append(f"Metadata Presence ({metadata:.1f}%) is acceptable. Consider adding more metadata fields for better context.")
        else:
            suggestions.append(f"Metadata Presence ({metadata:.1f}%) is good. Minor enhancements could improve searchability.")
    
    # KB Readiness recommendations (expanded logic)
    if kb_ready < min_kb_ready:
        suggestions.append(f"Knowledge Base Readiness ({kb_ready:.1f}%) is below threshold ({min_kb_ready}%). Improve chunking strategy and sectioning.")
        if current_playbook is None or current_playbook.upper() != "TECH":
            playbook_recommendations.append("Consider using TECH playbook for better chunking and sectioning.")
    elif kb_ready < 70.0:
        suggestions.append(f"Knowledge Base Readiness ({kb_ready:.1f}%) could be improved. Review chunking parameters and semantic boundaries.")
        if current_playbook is None or current_playbook.upper() != "TECH":
            playbook_recommendations.append("TECH playbook may provide better chunking for RAG applications.")
    elif kb_ready < 85.0:
        suggestions.append(f"Knowledge Base Readiness ({kb_ready:.1f}%) is good. Fine-tuning chunking could improve retrieval quality.")
    
    # Completeness recommendations (expanded logic)
    if completeness < 60.0:
        suggestions.append(f"Completeness ({completeness:.1f}%) is low. Review data extraction and ensure all content is captured.")
        if current_playbook is None or current_playbook.upper() == "REGULATORY":
            next_playbook = "SCANNED"
            playbook_recommendations.append("Consider SCANNED playbook for OCR-heavy cleanup and better completeness.")
        config_tweaks["increase_chunk_overlap"] = True
    elif completeness < 75.0:
        suggestions.append(f"Completeness ({completeness:.1f}%) is acceptable. Increase chunk overlap to reduce context loss at boundaries.")
        config_tweaks["increase_chunk_overlap"] = True
    elif completeness < 90.0:
        suggestions.append(f"Completeness ({completeness:.1f}%) is good. Minor improvements in chunking could enhance completeness.")
    
    # Quality recommendations
    if quality < 70.0:
        suggestions.append(f"Quality score ({quality:.1f}%) is below optimal. Review data cleaning and normalization processes.")
    elif quality < 85.0:
        suggestions.append(f"Quality score ({quality:.1f}%) is good. Enhance text normalization and error correction.")
    
    # Policy-specific recommendations
    if not policy_passed:
        if violations:
            violation_count = len(violations)
            suggestions.append(f"Policy evaluation failed with {violation_count} violation(s). Address the issues above to meet compliance requirements.")
    else:
        # Even if passed, provide improvement suggestions
        if trust_score < 80.0:
            suggestions.append("Policy passed, but improving trust score above 80% would enhance data readiness.")
    
    # Playbook-specific recommendations
    if next_playbook and next_playbook != current_playbook:
        playbook_recommendations.append(f"Consider switching to {next_playbook} playbook for better results.")
    
    # If no specific recommendations, provide general guidance
    if not suggestions and not playbook_recommendations:
        suggestions.append("Metrics are within acceptable ranges. Continue monitoring and consider fine-tuning for optimal performance.")
    
    logger.info(
        f"Optimizer suggestions: playbook={next_playbook}, tweaks={len(config_tweaks)}, "
        f"suggestions={len(suggestions)}, playbook_recs={len(playbook_recommendations)}"
    )
    
    return {
        "next_playbook": next_playbook,
        "config_tweaks": config_tweaks,
        "suggestions": suggestions,
        "playbook_recommendations": playbook_recommendations,
    }




