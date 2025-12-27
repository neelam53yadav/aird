"""
Optimizer service for PrimeData.

Provides suggestions for improving AI readiness based on fingerprint and policy evaluation.
"""

from typing import Any, Dict, List, Optional

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
        "actionable_recommendations": [
          {
            "type": str,  # "chunk_overlap", "playbook", "quality_normalization", "metadata_extraction"
            "message": str,
            "action": str,  # "increase_chunk_overlap", "switch_playbook", "enhance_normalization", "extract_metadata"
            "config": { ... }  # Specific config changes needed
          }
        ]
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
    actionable_recommendations: List[Dict[str, Any]] = []

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

    # Trust Score recommendations (more actionable - focus on pushing to excellent)
    if trust_score < min_trust:
        suggestions.append(
            f"AI Trust Score ({trust_score:.1f}%) is below the policy threshold ({min_trust}%). Focus on improving overall data quality."
        )
        # Add actionable recommendations targeting trust score components
        if quality < 70.0:
            actionable_recommendations.append(
                {
                    "type": "quality_normalization",
                    "message": f"Low Quality score is dragging down AI Trust Score. Enable enhanced normalization to improve overall trust score.",
                    "action": "enhance_normalization",
                    "config": {"enable_advanced_cleaning": True, "error_correction": True},
                    "expected_impact": "AI Trust Score improvement: +5-10%",
                    "priority": "high",
                }
            )
        if completeness < 75.0:
            actionable_recommendations.append(
                {
                    "type": "chunk_overlap",
                    "message": f"Low Completeness is dragging down AI Trust Score. Increase chunk overlap to improve overall trust score.",
                    "action": "increase_chunk_overlap",
                    "config": {"increase_by_percent": 25, "min_overlap": 200},
                    "expected_impact": "AI Trust Score improvement: +3-7%",
                    "priority": "high",
                }
            )
    elif trust_score < 70.0:
        suggestions.append(
            f"AI Trust Score ({trust_score:.1f}%) is acceptable but could be improved. Consider enhancing data completeness and quality."
        )
        # Add actionable recommendations to push above 70%
        actionable_recommendations.append(
            {
                "type": "composite_improvement",
                "message": f"AI Trust Score ({trust_score:.1f}%) can be improved. Apply all quality enhancements to push above 70%.",
                "action": "apply_all_quality_improvements",
                "config": {"enhance_normalization": True, "error_correction": True, "increase_overlap": True},
                "expected_impact": "AI Trust Score improvement: +5-12% to reach 70%+",
                "priority": "medium",
            }
        )
    elif trust_score < 85.0:
        suggestions.append(
            f"AI Trust Score ({trust_score:.1f}%) is good. Apply recommended improvements to push it to excellent (>85%) and maximize AI efficiency."
        )
        # Add actionable recommendations to push to excellent
        actionable_recommendations.append(
            {
                "type": "excellence_push",
                "message": f"AI Trust Score ({trust_score:.1f}%) is good. Apply all quality improvements to reach excellent (>85%) and maximize AI application efficiency.",
                "action": "apply_all_quality_improvements",
                "config": {"enhance_normalization": True, "error_correction": True, "extract_metadata": True},
                "expected_impact": f"AI Trust Score improvement: +{(85.0 - trust_score):.1f}% to reach excellent threshold",
                "priority": "high",
            }
        )

    # Security recommendations (expanded logic)
    if "security_not_full" in violations:
        suggestions.append(
            f"Security score ({secure:.1f}%) is below threshold ({min_secure}%). Enable stricter PII redaction and data masking."
        )
        config_tweaks["redaction_strict"] = True
    elif secure < 100.0:
        if secure < 95.0:
            suggestions.append(
                f"Security score ({secure:.1f}%) is good but not perfect. Review PII detection and redaction rules."
            )
        else:
            suggestions.append(f"Security score ({secure:.1f}%) is excellent. Minor improvements could achieve 100%.")

    # Metadata recommendations (expanded logic)
    if metadata < min_metadata:
        suggestions.append(
            f"Metadata Presence ({metadata:.1f}%) is below threshold ({min_metadata}%). Enhance metadata extraction and enrichment."
        )
        config_tweaks["force_metadata_extraction"] = True
        actionable_recommendations.append(
            {
                "type": "metadata_extraction",
                "message": f"Metadata Presence ({metadata:.1f}%) is below threshold ({min_metadata}%). Enhance metadata extraction and enrichment.",
                "action": "extract_metadata",
                "config": {"force_extraction": True, "additional_fields": True},
            }
        )
    elif metadata < 90.0:
        if metadata < 85.0:
            suggestions.append(
                f"Metadata Presence ({metadata:.1f}%) is acceptable. Consider adding more metadata fields for better context."
            )
            actionable_recommendations.append(
                {
                    "type": "metadata_extraction",
                    "message": f"Metadata Presence ({metadata:.1f}%) is acceptable. Consider adding more metadata fields for better context.",
                    "action": "extract_metadata",
                    "config": {"additional_fields": True},
                }
            )
        else:
            suggestions.append(f"Metadata Presence ({metadata:.1f}%) is good. Minor enhancements could improve searchability.")

    # KB Readiness recommendations (expanded logic)
    if kb_ready < min_kb_ready:
        suggestions.append(
            f"Knowledge Base Readiness ({kb_ready:.1f}%) is below threshold ({min_kb_ready}%). Improve chunking strategy and sectioning."
        )
        if current_playbook is None or current_playbook.upper() != "TECH":
            playbook_recommendations.append("Consider using TECH playbook for better chunking and sectioning.")
            actionable_recommendations.append(
                {
                    "type": "playbook",
                    "message": f"Knowledge Base Readiness ({kb_ready:.1f}%) is below threshold. Consider switching to TECH playbook for better chunking.",
                    "action": "switch_playbook",
                    "config": {"playbook_id": "TECH", "reason": "Better chunking strategy for RAG applications"},
                }
            )
    elif kb_ready < 70.0:
        suggestions.append(
            f"Knowledge Base Readiness ({kb_ready:.1f}%) could be improved. Review chunking parameters and semantic boundaries."
        )
        if current_playbook is None or current_playbook.upper() != "TECH":
            playbook_recommendations.append("TECH playbook may provide better chunking for RAG applications.")
            actionable_recommendations.append(
                {
                    "type": "playbook",
                    "message": f"Knowledge Base Readiness ({kb_ready:.1f}%) could be improved. TECH playbook may provide better chunking for RAG.",
                    "action": "switch_playbook",
                    "config": {"playbook_id": "TECH", "reason": "Better chunking for RAG applications"},
                }
            )
    elif kb_ready < 85.0:
        suggestions.append(
            f"Knowledge Base Readiness ({kb_ready:.1f}%) is good. Fine-tuning chunking could improve retrieval quality."
        )

    # Completeness recommendations (expanded logic)
    if completeness < 60.0:
        suggestions.append(
            f"Completeness ({completeness:.1f}%) is low. Review data extraction and ensure all content is captured."
        )
        if current_playbook is None or current_playbook.upper() == "REGULATORY":
            next_playbook = "SCANNED"
            playbook_recommendations.append("Consider SCANNED playbook for OCR-heavy cleanup and better completeness.")
            actionable_recommendations.append(
                {
                    "type": "playbook",
                    "message": f"Completeness ({completeness:.1f}%) is low. Consider switching to SCANNED playbook for better OCR cleanup.",
                    "action": "switch_playbook",
                    "config": {"playbook_id": "SCANNED", "reason": "Better OCR cleanup for improved completeness"},
                }
            )
        config_tweaks["increase_chunk_overlap"] = True
        actionable_recommendations.append(
            {
                "type": "chunk_overlap",
                "message": f"Completeness ({completeness:.1f}%) is low. Increase chunk overlap to reduce context loss at boundaries.",
                "action": "increase_chunk_overlap",
                "config": {"increase_by_percent": 25, "min_overlap": 200},
            }
        )
    elif completeness < 75.0:
        suggestions.append(
            f"Completeness ({completeness:.1f}%) is acceptable. Increase chunk overlap to reduce context loss at boundaries."
        )
        config_tweaks["increase_chunk_overlap"] = True
        actionable_recommendations.append(
            {
                "type": "chunk_overlap",
                "message": f"Completeness ({completeness:.1f}%) is acceptable. Increase chunk overlap to reduce context loss at boundaries.",
                "action": "increase_chunk_overlap",
                "config": {"increase_by_percent": 20, "min_overlap": 200},
            }
        )
    elif completeness < 90.0:
        suggestions.append(
            f"Completeness ({completeness:.1f}%) is good. Minor improvements in chunking could enhance completeness."
        )

    # Quality recommendations (more aggressive to push to excellent)
    if quality < 70.0:
        suggestions.append(
            f"Quality score ({quality:.1f}%) is below optimal. Review data cleaning and normalization processes."
        )
        actionable_recommendations.append(
            {
                "type": "quality_normalization",
                "message": f"Quality score ({quality:.1f}%) is below optimal. Enable enhanced normalization and error correction to improve readability and text quality.",
                "action": "enhance_normalization",
                "config": {"enable_advanced_cleaning": True, "error_correction": True},
                "expected_impact": "Quality score improvement: +15-25%",
                "priority": "high",
            }
        )
        # Also suggest error correction specifically
        actionable_recommendations.append(
            {
                "type": "error_correction",
                "message": f"Quality score ({quality:.1f}%) is below optimal. Enable error correction to fix OCR mistakes and typos.",
                "action": "error_correction",
                "config": {"enable_error_correction": True},
                "expected_impact": "Quality score improvement: +5-10%",
                "priority": "high",
            }
        )
    elif quality < 85.0:
        suggestions.append(
            f"Quality score ({quality:.1f}%) is good but can be improved to excellent (>85%). Enable enhanced normalization and error correction to maximize AI efficiency."
        )
        actionable_recommendations.append(
            {
                "type": "quality_normalization",
                "message": f"Quality score ({quality:.1f}%) can be improved to excellent (>85%). Enable enhanced normalization and error correction to maximize data quality for AI applications.",
                "action": "enhance_normalization",
                "config": {"enable_advanced_cleaning": True, "error_correction": True},
                "expected_impact": f"Quality score improvement: +{(85.0 - quality):.1f}% to reach excellent threshold",
                "priority": "medium",
            }
        )
        actionable_recommendations.append(
            {
                "type": "error_correction",
                "message": f"Quality score ({quality:.1f}%) can be improved to excellent (>85%). Enable error correction to fix remaining OCR mistakes and improve text quality.",
                "action": "error_correction",
                "config": {"enable_error_correction": True},
                "expected_impact": f"Quality score improvement: +{(85.0 - quality) * 0.3:.1f}%",
                "priority": "medium",
            }
        )

    # Policy-specific recommendations (focus on excellence, not just passing)
    if not policy_passed:
        if violations:
            violation_count = len(violations)
            suggestions.append(
                f"Policy evaluation failed with {violation_count} violation(s). Address the issues above to meet compliance requirements."
            )
    else:
        # Even if passed, aggressively push to excellence for maximum AI efficiency
        if trust_score < 80.0:
            suggestions.append(
                "Policy passed, but improving trust score above 80% would enhance data readiness and maximize AI application efficiency."
            )
            actionable_recommendations.append(
                {
                    "type": "excellence_push",
                    "message": "Policy passed, but improving trust score above 80% would enhance data readiness. Apply all recommended improvements to maximize AI efficiency (target: 4x improvement).",
                    "action": "apply_all_quality_improvements",
                    "config": {
                        "enhance_normalization": True,
                        "error_correction": True,
                        "extract_metadata": True,
                        "increase_overlap": completeness < 80.0,
                    },
                    "expected_impact": f"AI Trust Score improvement: +{(80.0 - trust_score):.1f}% to reach 80%+ (enhanced AI efficiency)",
                    "priority": "high",
                }
            )
        elif trust_score < 85.0:
            suggestions.append(
                "Policy passed. Push AI Trust Score above 85% (excellent) to maximize AI application efficiency and achieve 4x productivity gains."
            )
            actionable_recommendations.append(
                {
                    "type": "excellence_push",
                    "message": "Policy passed. Push AI Trust Score above 85% (excellent) to maximize AI application efficiency. Apply all quality improvements to achieve excellence.",
                    "action": "apply_all_quality_improvements",
                    "config": {"enhance_normalization": True, "error_correction": True, "extract_metadata": True},
                    "expected_impact": f"AI Trust Score improvement: +{(85.0 - trust_score):.1f}% to reach excellent threshold (maximize AI efficiency)",
                    "priority": "high",
                }
            )

    # Playbook-specific recommendations
    if next_playbook and next_playbook != current_playbook:
        playbook_recommendations.append(f"Consider switching to {next_playbook} playbook for better results.")

    # If no specific recommendations, provide general guidance
    if not suggestions and not playbook_recommendations:
        suggestions.append(
            "Metrics are within acceptable ranges. Continue monitoring and consider fine-tuning for optimal performance."
        )

    logger.info(
        f"Optimizer suggestions: playbook={next_playbook}, tweaks={len(config_tweaks)}, "
        f"suggestions={len(suggestions)}, playbook_recs={len(playbook_recommendations)}"
    )

    return {
        "next_playbook": next_playbook,
        "config_tweaks": config_tweaks,
        "suggestions": suggestions,
        "playbook_recommendations": playbook_recommendations,
        "actionable_recommendations": actionable_recommendations,
    }
