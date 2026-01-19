"""
Main evaluation harness that replays datasets through pipeline.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.orm import Session

from primedata.api.chat import ChatRequest, chat_query
from primedata.db.models import EvalDataset, EvalDatasetItem, EvalRun
from primedata.evaluation.harness.evaluator import Evaluator
from primedata.indexing.embeddings import EmbeddingGenerator


class EvaluationRunner:
    """Main evaluation harness runner."""

    def __init__(
        self,
        db: Session,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        llm_client=None,
    ):
        """
        Initialize evaluation runner.
        
        Args:
            db: Database session
            embedding_generator: Embedding generator
            llm_client: LLM client
        """
        self.db = db
        self.evaluator = Evaluator(embedding_generator=embedding_generator, llm_client=llm_client)

    def run_evaluation(
        self,
        dataset_id: UUID,
        product_id: UUID,
        version: int,
        thresholds: Optional[Dict[str, float]] = None,
    ) -> EvalRun:
        """
        Run evaluation on a dataset.
        
        Args:
            dataset_id: Dataset ID
            product_id: Product ID
            version: Product version
            thresholds: Quality thresholds
            
        Returns:
            EvalRun with results
        """
        # Get dataset
        dataset = self.db.query(EvalDataset).filter(EvalDataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Get dataset items
        items = self.db.query(EvalDatasetItem).filter(EvalDatasetItem.dataset_id == dataset_id).all()
        if not items:
            raise ValueError(f"Dataset {dataset_id} has no items")

        # Get or create eval run (should already exist when called from DAG)
        eval_run = self.db.query(EvalRun).filter(
            EvalRun.dataset_id == dataset_id,
            EvalRun.product_id == product_id,
            EvalRun.version == version,
        ).order_by(EvalRun.created_at.desc()).first()
        
        # If eval_run doesn't exist, create it (fallback for direct calls)
        if not eval_run:
            eval_run = EvalRun(
                workspace_id=dataset.workspace_id,
                product_id=product_id,
                version=version,
                dataset_id=dataset_id,
                status="running",
            )
            self.db.add(eval_run)
            self.db.commit()
            self.db.refresh(eval_run)
        else:
            # Update existing eval run to running status
            eval_run.status = "running"
            eval_run.started_at = datetime.utcnow()
            self.db.commit()

        logger.info(f"Starting evaluation run {eval_run.id} with {len(items)} items")

        # Process each item
        per_query_results = []
        for i, item in enumerate(items):
            try:
                logger.info(f"Processing item {i+1}/{len(items)}: {item.query[:50]}...")
                
                # TODO: Call chat endpoint to get answer
                # For now, this is a placeholder - in production, you'd call the chat endpoint
                # or simulate the RAG pipeline
                answer = ""  # Would come from chat endpoint
                retrieved_chunks = []  # Would come from retrieval
                citations = []  # Would be extracted from answer
                
                # Evaluate
                metrics = self.evaluator.evaluate_query(
                    query=item.query,
                    answer=answer,
                    retrieved_chunks=retrieved_chunks,
                    citations=citations,
                    expected_refusal=item.extra_metadata.get("expected_refusal", False) if item.extra_metadata else False,
                    has_evidence=bool(item.expected_chunks),
                    thresholds=thresholds,
                )
                
                per_query_results.append({
                    "item_id": str(item.id),
                    "query": item.query,
                    "metrics": metrics,
                })
            except Exception as e:
                logger.error(f"Error processing item {item.id}: {e}", exc_info=True)
                per_query_results.append({
                    "item_id": str(item.id),
                    "query": item.query,
                    "error": str(e),
                })

        # Calculate aggregate metrics
        aggregate_metrics = self._calculate_aggregates(per_query_results)

        # Update eval run
        eval_run.metrics = {
            "per_query": per_query_results,
            "aggregate": aggregate_metrics,
        }
        eval_run.status = "completed"
        self.db.commit()

        logger.info(f"Completed evaluation run {eval_run.id}")
        return eval_run

    def _calculate_aggregates(self, per_query_results: List[Dict]) -> Dict:
        """Calculate aggregate metrics from per-query results."""
        if not per_query_results:
            return {}

        metric_scores = {
            "groundedness": [],
            "context_relevance": [],
            "answer_relevance": [],
            "citation_coverage": [],
            "refusal_correctness": [],
        }

        for result in per_query_results:
            if "error" in result:
                continue
            metrics = result.get("metrics", {})
            for metric_name in metric_scores.keys():
                if metric_name in metrics:
                    score = metrics[metric_name].get("score", 0.0)
                    metric_scores[metric_name].append(score)

        aggregates = {}
        for metric_name, scores in metric_scores.items():
            if scores:
                aggregates[metric_name] = {
                    "mean": sum(scores) / len(scores),
                    "min": min(scores),
                    "max": max(scores),
                    "count": len(scores),
                }
            else:
                aggregates[metric_name] = {
                    "mean": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "count": 0,
                }

        return aggregates

