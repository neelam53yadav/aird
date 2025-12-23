"""
MLflow client for tracking pipeline runs and experiments.
"""

import os
import logging
import mlflow
import mlflow.sklearn
from typing import Dict, Any, List, Optional, ContextManager
from contextlib import contextmanager
from uuid import UUID
import json
from datetime import datetime
from primedata.core.settings import get_settings

logger = logging.getLogger(__name__)

class MLflowClient:
    """MLflow client for tracking pipeline experiments and runs."""
    
    def __init__(self):
        """Initialize MLflow client with tracking URI and artifact location."""
        # Get MLflow configuration from settings
        settings = get_settings()
        self.tracking_uri = settings.MLFLOW_TRACKING_URI
        self.backend_store_uri = settings.MLFLOW_BACKEND_STORE_URI
        self.artifact_location = settings.MLFLOW_DEFAULT_ARTIFACT_ROOT
        
        # Set MLflow tracking URI (this will be the MLflow server URL)
        mlflow.set_tracking_uri(self.tracking_uri)
        
        # Set default experiment name
        self.default_experiment_name = "PrimeData Pipeline Runs"
        
        logger.info(f"MLflow client initialized with tracking URI: {self.tracking_uri}")
        logger.info(f"Backend store URI: {self.backend_store_uri}")
        logger.info(f"Artifact location: {self.artifact_location}")
    
    def get_or_create_experiment(self, product_id: UUID, product_name: str) -> str:
        """
        Get or create an experiment for a specific product.
        
        Args:
            product_id: UUID of the product
            product_name: Name of the product
            
        Returns:
            Experiment ID
        """
        experiment_name = f"{self.default_experiment_name} - {product_name} ({str(product_id)[:8]})"
        
        try:
            # Try to get existing experiment
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment:
                logger.info(f"Using existing experiment: {experiment_name}")
                return experiment.experiment_id
        except Exception as e:
            logger.info(f"Experiment not found, will create new one: {e}")
        
        try:
            # Create new experiment
            experiment_id = mlflow.create_experiment(
                name=experiment_name,
                artifact_location=self.artifact_location
            )
            logger.info(f"Created new experiment: {experiment_name} (ID: {experiment_id})")
            return experiment_id
        except Exception as e:
            logger.error(f"Failed to create experiment: {e}")
            # Fallback to default experiment
            return "0"
    
    @contextmanager
    def with_mlflow_run(
        self, 
        product_id: UUID, 
        version: int, 
        run_name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> ContextManager[mlflow.ActiveRun]:
        """
        Context manager for MLflow runs.
        
        Args:
            product_id: UUID of the product
            version: Version number of the pipeline run
            run_name: Optional custom run name
            params: Parameters to log at the start of the run
            tags: Tags to add to the run
            
        Yields:
            mlflow.ActiveRun: The active MLflow run
        """
        # Get product name (we'll need to fetch this from database or pass it)
        product_name = f"Product-{str(product_id)[:8]}"
        
        # Get or create experiment
        experiment_id = self.get_or_create_experiment(product_id, product_name)
        
        # Set experiment
        mlflow.set_experiment(experiment_id=experiment_id)
        
        # Create run name if not provided
        if not run_name:
            run_name = f"Pipeline Run v{version} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Default tags
        default_tags = {
            "product_id": str(product_id),
            "version": str(version),
            "pipeline_type": "primedata_v1",
            "run_timestamp": datetime.now().isoformat()
        }
        
        if tags:
            default_tags.update(tags)
        
        # Start MLflow run
        with mlflow.start_run(run_name=run_name, tags=default_tags) as run:
            logger.info(f"Started MLflow run: {run.info.run_id}")
            
            # Log initial parameters if provided
            if params:
                mlflow.log_params(params)
                logger.info(f"Logged parameters: {list(params.keys())}")
            
            try:
                yield run
            except Exception as e:
                # Log error as a tag
                mlflow.set_tag("status", "failed")
                mlflow.set_tag("error", str(e))
                logger.error(f"MLflow run failed: {e}")
                raise
            else:
                # Mark as successful
                mlflow.set_tag("status", "completed")
                logger.info(f"MLflow run completed successfully: {run.info.run_id}")
    
    def log_pipeline_metrics(
        self, 
        metrics: Dict[str, float],
        step: Optional[int] = None
    ) -> None:
        """
        Log pipeline metrics to the current MLflow run.
        
        Args:
            metrics: Dictionary of metric names and values
            step: Optional step number for the metrics
        """
        try:
            mlflow.log_metrics(metrics, step=step)
            logger.info(f"Logged metrics: {list(metrics.keys())}")
        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")
    
    def log_pipeline_artifacts(
        self, 
        artifacts: List[str],
        artifact_path: Optional[str] = None
    ) -> None:
        """
        Log pipeline artifacts to the current MLflow run.
        
        Args:
            artifacts: List of file paths to log as artifacts
            artifact_path: Optional subdirectory in artifacts folder
        """
        try:
            for artifact in artifacts:
                if os.path.exists(artifact):
                    mlflow.log_artifact(artifact, artifact_path)
                    logger.info(f"Logged artifact: {artifact}")
                else:
                    logger.warning(f"Artifact file not found: {artifact}")
        except Exception as e:
            logger.error(f"Failed to log artifacts: {e}")
    
    def log_chunking_analysis(
        self,
        chunk_count: int,
        avg_chunk_size: float,
        min_chunk_size: int,
        max_chunk_size: int,
        total_tokens: int,
        duplicate_rate: float = 0.0
    ) -> None:
        """
        Log chunking analysis metrics.
        
        Args:
            chunk_count: Total number of chunks created
            avg_chunk_size: Average chunk size in characters
            min_chunk_size: Minimum chunk size
            max_chunk_size: Maximum chunk size
            total_tokens: Total number of tokens processed
            duplicate_rate: Rate of duplicate chunks (0.0 to 1.0)
        """
        metrics = {
            "chunk_count": chunk_count,
            "avg_chunk_size": avg_chunk_size,
            "min_chunk_size": min_chunk_size,
            "max_chunk_size": max_chunk_size,
            "total_tokens": total_tokens,
            "duplicate_rate": duplicate_rate,
            "chunks_per_document": chunk_count / max(1, total_tokens / avg_chunk_size) if avg_chunk_size > 0 else 0
        }
        
        self.log_pipeline_metrics(metrics)
    
    def log_embedding_metrics(
        self,
        embedding_count: int,
        embedding_dimension: int,
        embedder_name: str,
        processing_time_seconds: float
    ) -> None:
        """
        Log embedding generation metrics.
        
        Args:
            embedding_count: Number of embeddings created
            embedding_dimension: Dimension of embeddings
            embedder_name: Name of the embedder used
            processing_time_seconds: Time taken to generate embeddings
        """
        metrics = {
            "embedding_count": embedding_count,
            "embedding_dimension": embedding_dimension,
            "embedder_name": embedder_name,
            "processing_time_seconds": processing_time_seconds,
            "embeddings_per_second": embedding_count / max(processing_time_seconds, 0.001)
        }
        
        self.log_pipeline_metrics(metrics)
    
    def log_qdrant_metrics(
        self,
        collection_name: str,
        vector_count: int,
        index_time_seconds: float,
        collection_size_mb: float
    ) -> None:
        """
        Log Qdrant collection metrics.
        
        Args:
            collection_name: Name of the Qdrant collection
            vector_count: Number of vectors in collection
            index_time_seconds: Time taken to index vectors
            collection_size_mb: Size of collection in MB
        """
        metrics = {
            "qdrant_collection_name": collection_name,
            "vector_count": vector_count,
            "index_time_seconds": index_time_seconds,
            "collection_size_mb": collection_size_mb,
            "vectors_per_second": vector_count / max(index_time_seconds, 0.001)
        }
        
        self.log_pipeline_metrics(metrics)
    
    def get_run_url(self, run_id: str) -> str:
        """
        Get the URL for viewing a specific run in MLflow UI.
        
        Args:
            run_id: MLflow run ID
            
        Returns:
            URL to view the run in MLflow UI
        """
        return f"{self.tracking_uri}/#/experiments/0/runs/{run_id}"
    
    def get_experiment_url(self, experiment_id: str) -> str:
        """
        Get the URL for viewing an experiment in MLflow UI.
        
        Args:
            experiment_id: MLflow experiment ID
            
        Returns:
            URL to view the experiment in MLflow UI
        """
        return f"{self.tracking_uri}/#/experiments/{experiment_id}"


# Global MLflow client instance
mlflow_client = MLflowClient()
