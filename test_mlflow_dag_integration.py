#!/usr/bin/env python3
"""
Test script to verify MLflow integration in the DAG.
This script simulates the MLflow integration code from the DAG.
"""

import os
import sys
import logging
from uuid import UUID

# Add the backend src to the path
sys.path.append('backend/src')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_mlflow_integration():
    """Test the MLflow integration code from the DAG."""
    
    try:
        # Import MLflow client
        from primedata.core.mlflow_client import mlflow_client
        logger.info("✅ MLflow client imported successfully")
        
        # Test product ID and version
        product_id = "8119e959-cdd3-4843-bd4c-0b6318c48dda"
        version = 1
        
        # Test chunking task MLflow integration
        logger.info("🧪 Testing chunking task MLflow integration...")
        
        with mlflow_client.with_mlflow_run(
            product_id=UUID(product_id),
            version=version,
            run_name=f"Test Chunking Task v{version}",
            params={
                'task': 'chunking',
                'product_id': product_id,
                'version': version,
                'chunk_size': 1000,
                'chunk_overlap': 200,
                'min_chunk_size': 100,
                'max_chunk_size': 2000,
                'chunking_strategy': 'fixed_size',
                'chunking_mode': 'manual'
            },
            tags={
                'task_type': 'chunking',
                'pipeline_type': 'primedata_simple'
            }
        ):
            import mlflow
            
            # Log chunking metrics
            mlflow.log_metrics({
                'chunk_count': 10,
                'avg_chunk_size': 950,
                'min_chunk_size_actual': 800,
                'max_chunk_size_actual': 1200,
                'total_chunk_size': 9500,
                'files_processed': 2
            })
            
            logger.info("✅ Chunking task MLflow integration test passed")
        
        # Test embedding task MLflow integration
        logger.info("🧪 Testing embedding task MLflow integration...")
        
        with mlflow_client.with_mlflow_run(
            product_id=UUID(product_id),
            version=version,
            run_name=f"Test Embedding Task v{version}",
            params={
                'task': 'embedding',
                'product_id': product_id,
                'version': version,
                'embedder_name': 'minilm',
                'embedding_dimension': 384
            },
            tags={
                'task_type': 'embedding',
                'pipeline_type': 'primedata_simple'
            }
        ):
            import mlflow
            
            # Log embedding metrics
            mlflow.log_metrics({
                'embedding_count': 10,
                'embedding_dimension': 384,
                'processing_time_seconds': 5.2,
                'embeddings_per_second': 1.92
            })
            
            logger.info("✅ Embedding task MLflow integration test passed")
        
        # Test indexing task MLflow integration
        logger.info("🧪 Testing indexing task MLflow integration...")
        
        with mlflow_client.with_mlflow_run(
            product_id=UUID(product_id),
            version=version,
            run_name=f"Test Indexing Task v{version}",
            params={
                'task': 'indexing',
                'product_id': product_id,
                'version': version,
                'qdrant_collection': 'test_collection'
            },
            tags={
                'task_type': 'indexing',
                'pipeline_type': 'primedata_simple',
                'qdrant_collection': 'test_collection'
            }
        ):
            import mlflow
            
            # Log Qdrant metrics
            mlflow.log_metrics({
                'vector_count': 10,
                'index_time_seconds': 2.1,
                'vectors_per_second': 4.76
            })
            
            logger.info("✅ Indexing task MLflow integration test passed")
        
        logger.info("🎉 All MLflow integration tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ MLflow integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_mlflow_integration()
    sys.exit(0 if success else 1)
