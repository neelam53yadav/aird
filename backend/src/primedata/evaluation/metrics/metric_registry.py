"""
Metric registry for RAG quality metrics.
"""

from typing import Dict, List, Optional

from .citation_coverage import CitationCoverageMetric
from .groundedness import GroundednessMetric
from .refusal_correctness import RefusalCorrectnessMetric
from .relevance import RelevanceMetric
from .scoring import MetricScore


class MetricRegistry:
    """Registry for all RAG quality metrics."""

    def __init__(
        self,
        embedding_generator=None,
        llm_client=None,
    ):
        """
        Initialize metric registry.
        
        Args:
            embedding_generator: Embedding generator for similarity calculations
            llm_client: LLM client for LLM-based metrics
        """
        self.embedding_generator = embedding_generator
        self.llm_client = llm_client
        
        # Initialize metric evaluators
        self.groundedness = GroundednessMetric(llm_client=llm_client)
        self.relevance = RelevanceMetric(
            embedding_generator=embedding_generator,
            llm_client=llm_client,
        )
        self.citation_coverage = CitationCoverageMetric()
        self.refusal_correctness = RefusalCorrectnessMetric()

    def evaluate_all(
        self,
        query: str,
        answer: str,
        retrieved_chunks: List[Dict],
        citations: Optional[List[str]] = None,
        acl_denied: bool = False,
        expected_refusal: bool = False,
        has_evidence: bool = True,
        thresholds: Optional[Dict[str, float]] = None,
    ) -> Dict[str, MetricScore]:
        """
        Evaluate all metrics.
        
        Args:
            query: Query text
            answer: Generated answer
            retrieved_chunks: List of retrieved chunks
            citations: Optional citations
            acl_denied: Whether ACL denied
            expected_refusal: Whether refusal was expected
            has_evidence: Whether evidence was available
            thresholds: Optional custom thresholds
            
        Returns:
            Dictionary of metric name to MetricScore
        """
        if thresholds is None:
            thresholds = {
                "groundedness": 0.80,
                "context_relevance": 0.75,
                "answer_relevance": 0.80,
                "citation_coverage": 0.90,
                "refusal_correctness": 0.95,
            }

        results = {}
        
        # Groundedness
        results["groundedness"] = self.groundedness.evaluate(
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            citations=citations,
            threshold=thresholds.get("groundedness", 0.80),
        )
        
        # Context relevance
        results["context_relevance"] = self.relevance.evaluate_context_relevance(
            query=query,
            retrieved_chunks=retrieved_chunks,
            threshold=thresholds.get("context_relevance", 0.75),
        )
        
        # Answer relevance
        results["answer_relevance"] = self.relevance.evaluate_answer_relevance(
            query=query,
            answer=answer,
            threshold=thresholds.get("answer_relevance", 0.80),
        )
        
        # Citation coverage
        results["citation_coverage"] = self.citation_coverage.evaluate(
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            citations=citations,
            threshold=thresholds.get("citation_coverage", 0.90),
        )
        
        # Refusal correctness
        results["refusal_correctness"] = self.refusal_correctness.evaluate(
            answer=answer,
            acl_denied=acl_denied,
            expected_refusal=expected_refusal,
            has_evidence=has_evidence,
            threshold=thresholds.get("refusal_correctness", 0.95),
        )
        
        return results

