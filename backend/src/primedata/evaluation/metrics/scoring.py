"""
Unified scoring interface for RAG quality metrics.
"""

from typing import Dict, List, Optional


class MetricScore:
    """Represents a metric score result."""

    def __init__(
        self,
        metric_name: str,
        score: float,
        passed: bool,
        details: Optional[Dict] = None,
        evidence: Optional[List] = None,
    ):
        """
        Initialize metric score.
        
        Args:
            metric_name: Name of the metric
            score: Score value (0-1 scale)
            passed: Whether metric passed threshold
            details: Metric-specific details
            evidence: Supporting evidence
        """
        self.metric_name = metric_name
        self.score = score
        self.passed = passed
        self.details = details or {}
        self.evidence = evidence or []

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "score": self.score,
            "passed": self.passed,
            "details": self.details,
            "evidence": self.evidence,
        }



