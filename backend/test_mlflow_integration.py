#!/usr/bin/env python3
"""
Test script for MLflow integration with PrimeData pipeline.
"""

import os
import sys
import json
import logging
from datetime import datetime
from uuid import uuid4

# Add the src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_mlflow_client():
    """Test the MLflow client functionality."""
    try:
        from primedata.core.mlflow_client import mlflow_client
        logger.info("✅ MLflow client imported successfully")
        
        # Test experiment creation
        test_product_id = uuid4()
        test_product_name = "Test Product"
        
        experiment_id = mlflow_client.get_or_create_experiment(test_product_id, test_product_name)
        logger.info(f"✅ Created experiment: {experiment_id}")
        
        # Test MLflow run context
        with mlflow_client.with_mlflow_run(
            product_id=test_product_id,
            version=1,
            run_name="Test Run",
            params={
                'chunk_size': 1000,
                'chunk_overlap': 200,
                'embedder_name': 'minilm',
                'embedding_dimension': 384
            },
            tags={
                'test': 'true',
                'pipeline_type': 'test'
            }
        ) as run:
            logger.info(f"✅ Started MLflow run: {run.info.run_id}")
            
            # Test logging metrics
            mlflow_client.log_pipeline_metrics({
                'chunk_count': 150,
                'avg_chunk_size': 950.5,
                'embedding_count': 150,
                'vector_count': 150
            })
            logger.info("✅ Logged pipeline metrics")
            
            # Test logging chunking analysis
            mlflow_client.log_chunking_analysis(
                chunk_count=150,
                avg_chunk_size=950.5,
                min_chunk_size=200,
                max_chunk_size=1200,
                total_tokens=142575,
                duplicate_rate=0.05
            )
            logger.info("✅ Logged chunking analysis")
            
            # Test logging embedding metrics
            mlflow_client.log_embedding_metrics(
                embedding_count=150,
                embedding_dimension=384,
                embedder_name='minilm',
                processing_time_seconds=45.2
            )
            logger.info("✅ Logged embedding metrics")
            
            # Test logging Qdrant metrics
            mlflow_client.log_qdrant_metrics(
                collection_name='test_collection',
                vector_count=150,
                index_time_seconds=12.5,
                collection_size_mb=2.3
            )
            logger.info("✅ Logged Qdrant metrics")
            
            # Test artifact logging
            test_artifact = {
                'sample_chunks': [
                    {'chunk_id': 1, 'text_preview': 'This is a sample chunk...', 'length': 950},
                    {'chunk_id': 2, 'text_preview': 'Another sample chunk...', 'length': 875}
                ],
                'metadata': {
                    'total_chunks': 150,
                    'avg_size': 950.5,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Create temporary artifact file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(test_artifact, f, indent=2)
                temp_file = f.name
            
            try:
                mlflow_client.log_pipeline_artifacts([temp_file], "test_artifacts")
                logger.info("✅ Logged pipeline artifacts")
            finally:
                os.unlink(temp_file)
        
        logger.info("✅ MLflow run completed successfully")
        
        # Test URL generation
        run_url = mlflow_client.get_run_url(run.info.run_id)
        experiment_url = mlflow_client.get_experiment_url(experiment_id)
        
        logger.info(f"✅ Run URL: {run_url}")
        logger.info(f"✅ Experiment URL: {experiment_url}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MLflow client test failed: {e}")
        return False

def test_mlflow_environment():
    """Test MLflow environment configuration."""
    logger.info("Testing MLflow environment configuration...")
    
    # Check environment variables
    tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
    backend_store_uri = os.getenv('MLFLOW_BACKEND_STORE_URI', 'postgresql://primedata:primedata123@localhost:5432/primedata')
    artifact_root = os.getenv('MLFLOW_DEFAULT_ARTIFACT_ROOT', 's3://mlflow-artifacts')
    
    logger.info(f"MLflow Tracking URI: {tracking_uri}")
    logger.info(f"MLflow Backend Store URI: {backend_store_uri}")
    logger.info(f"MLflow Artifact Root: {artifact_root}")
    
    # Test MLflow connection
    try:
        import mlflow
        mlflow.set_tracking_uri(tracking_uri)
        
        # Try to list experiments
        experiments = mlflow.search_experiments()
        logger.info(f"✅ Connected to MLflow. Found {len(experiments)} experiments.")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ MLflow connection failed: {e}")
        logger.error("Make sure MLflow server is running and accessible.")
        return False

def main():
    """Run all MLflow integration tests."""
    logger.info("🚀 Starting MLflow integration tests...")
    
    # Test 1: Environment configuration
    env_ok = test_mlflow_environment()
    if not env_ok:
        logger.error("❌ Environment test failed. Please check MLflow configuration.")
        return False
    
    # Test 2: MLflow client functionality
    client_ok = test_mlflow_client()
    if not client_ok:
        logger.error("❌ MLflow client test failed.")
        return False
    
    logger.info("🎉 All MLflow integration tests passed!")
    logger.info("📊 You can now view the test run in MLflow UI at: http://localhost:5000")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
