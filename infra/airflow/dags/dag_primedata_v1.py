"""
PrimeData Pipeline DAG v1

This DAG orchestrates the complete data processing pipeline:
1. Ingest from data sources to raw storage
2. Preprocess and clean data
3. Chunk documents
4. Generate embeddings
5. Index to Qdrant
6. Validate and finalize
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from airflow.utils.dates import days_ago

# Import PrimeData modules
import sys
sys.path.append('/opt/airflow/dags/primedata')

from primedata.storage.minio_client import minio_client
from primedata.storage.paths import raw_prefix, clean_prefix, chunk_prefix, embed_prefix
from primedata.connectors.web import WebConnector
from primedata.connectors.folder import FolderConnector
from primedata.connectors.s3 import S3Connector
from primedata.connectors.azure_blob import AzureBlobConnector
from primedata.connectors.google_drive import GoogleDriveConnector
from primedata.db.database import get_db
from primedata.db.models import Product, DataSource, PipelineRun
from primedata.indexing.embeddings import EmbeddingGenerator
from primedata.indexing.qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

# Default arguments for the DAG
default_args = {
    'owner': 'primedata',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    'primedata_v1',
    default_args=default_args,
    description='PrimeData complete pipeline v1',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['primedata', 'pipeline'],
    params={
        'workspace_id': '550e8400-e29b-41d4-a716-446655440001',  # Default workspace
        'product_id': None,  # Required parameter
        'version': None,     # Will be computed if not provided
        'embedder_name': 'minilm',  # Default embedder
        'dim': 384,          # Default embedding dimension
    }
)

def get_dag_params(**context) -> Dict[str, Any]:
    """Extract and validate DAG parameters."""
    params = context['params']
    
    # Get required parameters
    workspace_id = params.get('workspace_id')
    product_id = params.get('product_id')
    version = params.get('version')
    embedder_name = params.get('embedder_name', 'minilm')
    dim = int(params.get('dim', 384))
    
    if not product_id:
        raise ValueError("product_id parameter is required")
    
    logger.info(f"Pipeline parameters: workspace_id={workspace_id}, product_id={product_id}, version={version}, embedder={embedder_name}, dim={dim}")
    
    return {
        'workspace_id': workspace_id,
        'product_id': product_id,
        'version': version,
        'embedder_name': embedder_name,
        'dim': dim
    }

def ingest_from_datasources(**context) -> Dict[str, Any]:
    """Ingest data from all data sources to raw storage."""
    params = get_dag_params(**context)
    workspace_id = params['workspace_id']
    product_id = params['product_id']
    version = params['version']
    
    logger.info(f"Starting ingestion for product {product_id}, version {version}")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get product and data sources
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        data_sources = db.query(DataSource).filter(DataSource.product_id == product_id).all()
        if not data_sources:
            raise ValueError(f"No data sources found for product {product_id}")
        
        # Check if raw data already exists
        raw_prefix_path = raw_prefix(workspace_id, product_id, version)
        existing_objects = minio_client.list_objects("primedata-raw", raw_prefix_path)
        
        if existing_objects:
            logger.info(f"Raw data already exists for version {version}, skipping ingestion")
            return {
                'status': 'skipped',
                'message': 'Raw data already exists',
                'files_count': len(existing_objects)
            }
        
        # Ingest from each data source
        total_files = 0
        total_bytes = 0
        total_errors = 0
        
        for ds in data_sources:
            logger.info(f"Processing data source: {ds.name} (type: {ds.type})")
            
            try:
                if ds.type.value == "web":
                    config = ds.config.copy()
                    if 'url' in config and 'urls' not in config:
                        config['urls'] = [config['url']]
                    connector = WebConnector(config)
                    result = connector.sync_full("primedata-raw", raw_prefix_path)
                    
                elif ds.type.value == "folder":
                    config = ds.config.copy()
                    if 'path' in config and 'root_path' not in config:
                        config['root_path'] = config['path']
                    
                    # Convert file_types to include patterns
                    if 'file_types' in config and 'include' not in config:
                        file_types = config['file_types']
                        if isinstance(file_types, str):
                            config['include'] = [ft.strip() for ft in file_types.split(',') if ft.strip()]
                        elif isinstance(file_types, list):
                            config['include'] = file_types
                        else:
                            config['include'] = ['*']
                    
                    connector = FolderConnector(config)
                    result = connector.sync_full("primedata-raw", raw_prefix_path)
                    
                elif ds.type.value == "aws_s3":
                    connector = S3Connector(ds.config)
                    result = connector.sync_full("primedata-raw", raw_prefix_path)
                    
                elif ds.type.value == "azure_blob":
                    connector = AzureBlobConnector(ds.config)
                    result = connector.sync_full("primedata-raw", raw_prefix_path)
                    
                elif ds.type.value == "google_drive":
                    connector = GoogleDriveConnector(ds.config)
                    result = connector.sync_full("primedata-raw", raw_prefix_path)
                    
                else:
                    logger.warning(f"Unsupported data source type: {ds.type.value}")
                    continue
                
                total_files += result['files']
                total_bytes += result['bytes']
                total_errors += result['errors']
                
                logger.info(f"Data source {ds.name}: {result['files']} files, {result['bytes']} bytes, {result['errors']} errors")
                
            except Exception as e:
                logger.error(f"Error processing data source {ds.name}: {e}")
                total_errors += 1
        
        logger.info(f"Ingestion completed: {total_files} files, {total_bytes} bytes, {total_errors} errors")
        
        return {
            'status': 'completed',
            'files_count': total_files,
            'bytes_count': total_bytes,
            'errors_count': total_errors
        }
        
    finally:
        db.close()

def preprocess(**context) -> Dict[str, Any]:
    """Preprocess and clean raw data."""
    params = get_dag_params(**context)
    workspace_id = params['workspace_id']
    product_id = params['product_id']
    version = params['version']
    
    logger.info(f"Starting preprocessing for product {product_id}, version {version}")
    
    raw_prefix_path = raw_prefix(workspace_id, product_id, version)
    clean_prefix_path = clean_prefix(workspace_id, product_id, version)
    
    # Get raw objects
    raw_objects = minio_client.list_objects("primedata-raw", raw_prefix_path)
    
    if not raw_objects:
        raise ValueError("No raw data found for preprocessing")
    
    processed_files = 0
    total_bytes = 0
    
    for obj in raw_objects:
        try:
            # Download raw content
            raw_content = minio_client.get_object("primedata-raw", obj['name'])
            if not raw_content:
                logger.warning(f"Failed to download {obj['name']}")
                continue
            
            # Basic text extraction based on content type
            content_type = obj.get('content_type', '')
            clean_text = ""
            
            if content_type == 'text/html':
                # Simple HTML text extraction
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(raw_content.decode('utf-8', errors='ignore'), 'html.parser')
                clean_text = soup.get_text(separator=' ', strip=True)
                
            elif content_type == 'text/plain':
                # Plain text
                clean_text = raw_content.decode('utf-8', errors='ignore')
                
            elif content_type == 'application/pdf':
                # Basic PDF text extraction (requires PyPDF2 or similar)
                try:
                    import PyPDF2
                    from io import BytesIO
                    pdf_reader = PyPDF2.PdfReader(BytesIO(raw_content))
                    clean_text = ""
                    for page in pdf_reader.pages:
                        clean_text += page.extract_text() + "\n"
                except ImportError:
                    logger.warning("PyPDF2 not available, skipping PDF text extraction")
                    clean_text = f"[PDF file: {obj['name']}]"
                    
            else:
                # For other types, try to decode as text
                try:
                    clean_text = raw_content.decode('utf-8', errors='ignore')
                except:
                    clean_text = f"[Binary file: {obj['name']}]"
            
            # Clean and normalize text
            clean_text = clean_text.strip()
            if not clean_text:
                continue
            
            # Generate clean file key
            clean_key = obj['name'].replace('/raw/', '/clean/')
            
            # Upload cleaned content
            if minio_client.put_bytes("primedata-clean", clean_key, clean_text.encode('utf-8'), 'text/plain'):
                processed_files += 1
                total_bytes += len(clean_text.encode('utf-8'))
                logger.info(f"Processed: {obj['name']} -> {clean_key}")
            
        except Exception as e:
            logger.error(f"Error processing {obj['name']}: {e}")
    
    logger.info(f"Preprocessing completed: {processed_files} files processed")
    
    return {
        'status': 'completed',
        'files_processed': processed_files,
        'bytes_processed': total_bytes
    }

def chunk(**context) -> Dict[str, Any]:
    """Chunk cleaned documents into smaller pieces."""
    params = get_dag_params(**context)
    workspace_id = params['workspace_id']
    product_id = params['product_id']
    version = params['version']
    
    logger.info(f"Starting chunking for product {product_id}, version {version}")
    
    clean_prefix_path = clean_prefix(workspace_id, product_id, version)
    chunk_prefix_path = chunk_prefix(workspace_id, product_id, version)
    
    # Get cleaned objects
    clean_objects = minio_client.list_objects("primedata-clean", clean_prefix_path)
    
    if not clean_objects:
        raise ValueError("No cleaned data found for chunking")
    
    chunk_size = 1000  # characters
    chunk_overlap = 200  # characters
    chunks_created = 0
    
    for obj in clean_objects:
        try:
            # Download cleaned content
            clean_content = minio_client.get_object("primedata-clean", obj['name'])
            if not clean_content:
                continue
            
            text = clean_content.decode('utf-8', errors='ignore')
            
            # Simple chunking by character count
            chunks = []
            start = 0
            
            while start < len(text):
                end = start + chunk_size
                chunk_text = text[start:end]
                
                # Try to break at word boundary
                if end < len(text):
                    last_space = chunk_text.rfind(' ')
                    if last_space > chunk_size * 0.8:  # If we can break at a reasonable point
                        end = start + last_space
                        chunk_text = text[start:end]
                
                chunks.append({
                    'text': chunk_text.strip(),
                    'source_file': obj['name'],
                    'chunk_index': len(chunks),
                    'start_char': start,
                    'end_char': end
                })
                
                start = end - chunk_overlap
                if start >= len(text):
                    break
            
            # Save chunks as JSONL
            for i, chunk in enumerate(chunks):
                chunk_key = f"{chunk_prefix_path}{Path(obj['name']).stem}_chunk_{i:04d}.json"
                chunk_json = json.dumps(chunk, indent=2)
                
                if minio_client.put_bytes("primedata-chunk", chunk_key, chunk_json.encode('utf-8'), 'application/json'):
                    chunks_created += 1
            
            logger.info(f"Created {len(chunks)} chunks from {obj['name']}")
            
        except Exception as e:
            logger.error(f"Error chunking {obj['name']}: {e}")
    
    logger.info(f"Chunking completed: {chunks_created} chunks created")
    
    return {
        'status': 'completed',
        'chunks_created': chunks_created
    }

def embed(**context) -> Dict[str, Any]:
    """Generate embeddings for chunks."""
    params = get_dag_params(**context)
    workspace_id = params['workspace_id']
    product_id = params['product_id']
    version = params['version']
    embedder_name = params['embedder_name']
    dim = params['dim']
    
    logger.info(f"Starting embedding for product {product_id}, version {version}")
    
    chunk_prefix_path = chunk_prefix(workspace_id, product_id, version)
    embed_prefix_path = embed_prefix(workspace_id, product_id, version)
    
    # Get chunk objects
    chunk_objects = minio_client.list_objects("primedata-chunk", chunk_prefix_path)
    
    if not chunk_objects:
        raise ValueError("No chunks found for embedding")
    
    # Initialize embedding generator
    embedder = EmbeddingGenerator(embedder_name, dim)
    
    embeddings_created = 0
    vectors_data = []
    
    for obj in chunk_objects:
        try:
            # Download chunk
            chunk_content = minio_client.get_object("primedata-chunk", obj['name'])
            if not chunk_content:
                continue
            
            chunk_data = json.loads(chunk_content.decode('utf-8'))
            text = chunk_data['text']
            
            # Generate embedding
            embedding = embedder.embed(text)
            
            # Store embedding data
            embedding_data = {
                'chunk_id': f"{Path(obj['name']).stem}",
                'text': text,
                'embedding': embedding.tolist(),
                'source_file': chunk_data['source_file'],
                'chunk_index': chunk_data['chunk_index'],
                'metadata': {
                    'start_char': chunk_data['start_char'],
                    'end_char': chunk_data['end_char']
                }
            }
            
            # Save embedding as JSON
            embed_key = f"{embed_prefix_path}{Path(obj['name']).stem}.json"
            embed_json = json.dumps(embedding_data, indent=2)
            
            if minio_client.put_bytes("primedata-embed", embed_key, embed_json.encode('utf-8'), 'application/json'):
                embeddings_created += 1
                vectors_data.append({
                    'id': embedding_data['chunk_id'],
                    'vector': embedding,
                    'payload': {
                        'text': text,
                        'source_file': chunk_data['source_file'],
                        'chunk_index': chunk_data['chunk_index'],
                        'metadata': embedding_data['metadata']
                    }
                })
            
        except Exception as e:
            logger.error(f"Error embedding {obj['name']}: {e}")
    
    logger.info(f"Embedding completed: {embeddings_created} embeddings created")
    
    # Store vectors data for indexing task
    context['task_instance'].xcom_push(key='vectors_data', value=vectors_data)
    
    return {
        'status': 'completed',
        'embeddings_created': embeddings_created,
        'dimension': dim
    }

def index(**context) -> Dict[str, Any]:
    """Index embeddings to Qdrant."""
    params = get_dag_params(**context)
    workspace_id = params['workspace_id']
    product_id = params['product_id']
    version = params['version']
    dim = params['dim']
    
    logger.info(f"Starting indexing for product {product_id}, version {version}")
    
    # Get vectors data from previous task
    vectors_data = context['task_instance'].xcom_pull(key='vectors_data')
    
    if not vectors_data:
        raise ValueError("No vectors data found for indexing")
    
    # Initialize Qdrant client
    qdrant_client = QdrantClient()
    
    # Create collection name
    collection_name = f"ws_{workspace_id}__prod_{product_id}__v_{version}"
    
    # Ensure collection exists
    qdrant_client.ensure_collection(collection_name, dim)
    
    # Prepare points for upsert
    points = []
    for i, vector_data in enumerate(vectors_data):
        points.append({
            'id': i,  # Qdrant uses integer IDs
            'vector': vector_data['vector'].tolist(),
            'payload': vector_data['payload']
        })
    
    # Upsert points
    qdrant_client.upsert_points(collection_name, points)
    
    logger.info(f"Indexing completed: {len(points)} points indexed to collection {collection_name}")
    
    return {
        'status': 'completed',
        'points_indexed': len(points),
        'collection_name': collection_name
    }

def validate(**context) -> Dict[str, Any]:
    """Validate pipeline results and compute metrics."""
    params = get_dag_params(**context)
    workspace_id = params['workspace_id']
    product_id = params['product_id']
    version = params['version']
    
    logger.info(f"Starting validation for product {product_id}, version {version}")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Compute metrics
        raw_objects = minio_client.list_objects("primedata-raw", raw_prefix(workspace_id, product_id, version))
        clean_objects = minio_client.list_objects("primedata-clean", clean_prefix(workspace_id, product_id, version))
        chunk_objects = minio_client.list_objects("primedata-chunk", chunk_prefix(workspace_id, product_id, version))
        embed_objects = minio_client.list_objects("primedata-embed", embed_prefix(workspace_id, product_id, version))
        
        # Calculate basic metrics
        doc_count = len(raw_objects)
        chunk_count = len(chunk_objects)
        
        # Calculate average tokens (rough estimate: 1 token ≈ 4 characters)
        total_chars = 0
        for obj in clean_objects:
            content = minio_client.get_object("primedata-clean", obj['name'])
            if content:
                total_chars += len(content.decode('utf-8', errors='ignore'))
        
        avg_tokens = total_chars / max(doc_count, 1) / 4  # Rough estimate
        
        # Calculate duplicate rate (simplified: check for identical chunk texts)
        chunk_texts = set()
        duplicates = 0
        for obj in chunk_objects:
            content = minio_client.get_object("primedata-chunk", obj['name'])
            if content:
                chunk_data = json.loads(content.decode('utf-8'))
                text = chunk_data['text']
                if text in chunk_texts:
                    duplicates += 1
                else:
                    chunk_texts.add(text)
        
        dup_rate = duplicates / max(chunk_count, 1)
        
        metrics = {
            'doc_count': doc_count,
            'chunk_count': chunk_count,
            'avg_tokens': round(avg_tokens, 2),
            'dup_rate': round(dup_rate, 4),
            'embed_count': len(embed_objects)
        }
        
        logger.info(f"Validation metrics: {metrics}")
        
        # Store metrics in PipelineRun
        dag_run_id = context['dag_run'].run_id
        pipeline_run = db.query(PipelineRun).filter(
            PipelineRun.product_id == product_id,
            PipelineRun.version == version,
            PipelineRun.dag_run_id == dag_run_id
        ).first()
        
        if pipeline_run:
            pipeline_run.metrics = metrics
            pipeline_run.status = 'succeeded'
            pipeline_run.finished_at = datetime.utcnow()
            db.commit()
        
        return {
            'status': 'completed',
            'metrics': metrics
        }
        
    finally:
        db.close()

def finalize(**context) -> Dict[str, Any]:
    """Finalize pipeline by updating product status."""
    params = get_dag_params(**context)
    product_id = params['product_id']
    version = params['version']
    
    logger.info(f"Finalizing pipeline for product {product_id}, version {version}")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Update product status and version
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            product.status = 'ready'
            if version and version > product.current_version:
                product.current_version = version
            db.commit()
            logger.info(f"Product {product_id} status updated to 'ready', version {version}")
        
        return {
            'status': 'completed',
            'product_status': 'ready',
            'version': version
        }
        
    finally:
        db.close()

# Define tasks
ingest_task = PythonOperator(
    task_id='ingest_from_datasources',
    python_callable=ingest_from_datasources,
    dag=dag,
)

preprocess_task = PythonOperator(
    task_id='preprocess',
    python_callable=preprocess,
    dag=dag,
)

chunk_task = PythonOperator(
    task_id='chunk',
    python_callable=chunk,
    dag=dag,
)

embed_task = PythonOperator(
    task_id='embed',
    python_callable=embed,
    dag=dag,
)

index_task = PythonOperator(
    task_id='index',
    python_callable=index,
    dag=dag,
)

validate_task = PythonOperator(
    task_id='validate',
    python_callable=validate,
    dag=dag,
)

finalize_task = PythonOperator(
    task_id='finalize',
    python_callable=finalize,
    dag=dag,
)

# Define task dependencies
ingest_task >> preprocess_task >> chunk_task >> embed_task >> index_task >> validate_task >> finalize_task
