"""
Policy engine service for PrimeData.

Evaluates readiness fingerprints against policy thresholds.
"""

from typing import Dict, Any, List, Optional
from loguru import logger

# Default thresholds
DEFAULT_THRESHOLDS: Dict[str, float] = {
    "min_trust_score": 50.0,
    "min_secure": 90.0,
    "min_metadata_presence": 80.0,
    "min_kb_ready": 50.0,
}


def evaluate_policy(
    fingerprint: Dict[str, float],
    thresholds: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Evaluate whether a readiness fingerprint satisfies policy constraints.
    
    Args:
        fingerprint: Readiness fingerprint dictionary with metrics
        thresholds: Optional threshold overrides
        
    Returns:
        Dict with:
            - policy_passed: bool
            - violations: List[str]
            - thresholds: Dict[str, float]
    """
    # Merge defaults + overrides
    th = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        th.update(thresholds)
    
    # No fingerprint at all → automatic fail
    if not fingerprint:
        return {
            "status": "failed",
            "policy_passed": False,
            "violations": ["no_fingerprint"],
            "warnings": [],
            "thresholds": th,
        }
    
    violations: List[str] = []
    
    trust = float(fingerprint.get("AI_Trust_Score", 0.0))
    secure = float(fingerprint.get("Secure", 0.0))
    metadata = float(fingerprint.get("Metadata_Presence", 0.0))
    kb_ready = float(fingerprint.get("KnowledgeBase_Ready", 0.0))
    
    # Overall trust
    if trust < th["min_trust_score"]:
        violations.append(f"low_trust(<{th['min_trust_score']})")
    
    # Security
    if secure < th["min_secure"]:
        violations.append(f"security_not_full(<{th['min_secure']})")
    
    # Metadata completeness
    if metadata < th["min_metadata_presence"]:
        violations.append(f"weak_metadata(<{th['min_metadata_presence']})")
    
    # KB / RAG readiness
    if kb_ready < th["min_kb_ready"]:
        violations.append(f"kb_not_ready(<{th['min_kb_ready']})")
    
    policy_passed = len(violations) == 0
    
    # Determine status: "passed", "failed", or "warnings" (if passed but has minor issues)
    if policy_passed:
        status = "passed"
    else:
        # Check if violations are critical (trust score or security) vs warnings
        critical_violations = [v for v in violations if "low_trust" in v or "security_not_full" in v]
        status = "failed" if critical_violations else "warnings"
    
    logger.info(
        f"Policy evaluation: passed={policy_passed}, status={status}, violations={len(violations)}",
        trust_score=trust,
        secure=secure,
    )
    
    return {
        "status": status,  # "passed", "failed", or "warnings"
        "policy_passed": policy_passed,
        "violations": violations,
        "warnings": [],  # Separate warnings from violations if needed
        "thresholds": th,
    }




