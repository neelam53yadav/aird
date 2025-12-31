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

import json
import logging
import os

# Import PrimeData modules
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

sys.path.append("/opt/airflow/dags/primedata")

from primedata.connectors.azure_blob import AzureBlobConnector
from primedata.connectors.folder import FolderConnector
from primedata.connectors.google_drive import GoogleDriveConnector
from primedata.connectors.s3 import S3Connector
from primedata.connectors.web import WebConnector
from primedata.db.database import SessionLocal, get_db
from primedata.db.models import DataSource, DqViolation, PipelineRun, Product, ProductStatus
from primedata.dq.validator import DataQualityValidator
from primedata.indexing.embeddings import EmbeddingGenerator
from primedata.indexing.qdrant_client import QdrantClient
from primedata.ingestion_pipeline.aird_stages.config import get_aird_config
from primedata.ingestion_pipeline.aird_stages.storage import AirdStorageAdapter

# AIRD stages integration (M0)
from primedata.ingestion_pipeline.aird_stages.tracking import StageTracker, track_stage_execution
from primedata.storage.minio_client import minio_client
from primedata.storage.paths import chunk_prefix, clean_prefix, embed_prefix, raw_prefix

logger = logging.getLogger(__name__)

# Default arguments for the DAG
default_args = {
    "owner": "primedata",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    "primedata_v1",
    default_args=default_args,
    description="PrimeData complete pipeline v1",
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=["primedata", "pipeline"],
    params={
        "workspace_id": None,  # Must be provided when triggering the DAG
        "product_id": None,  # Required parameter
        "version": None,  # Will be computed if not provided
        "embedder_name": "minilm",  # Default embedder
        "dim": 384,  # Default embedding dimension
    },
)


def get_dag_params(**context) -> Dict[str, Any]:
    """Extract and validate DAG parameters."""
    params = context["params"]

    # Get required parameters
    workspace_id = params.get("workspace_id")
    product_id = params.get("product_id")
    version = params.get("version")
    embedder_name = params.get("embedder_name", "minilm")
    dim = int(params.get("dim", 384))

    # Get chunking configuration
    chunking_config = params.get(
        "chunking_config",
        {
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "min_chunk_size": 100,
            "max_chunk_size": 2000,
            "chunking_strategy": "fixed_size",
        },
    )

    # Get AIRD-specific parameters (M0)
    playbook_id = params.get("playbook_id")  # Optional playbook override

    if not product_id:
        raise ValueError("product_id parameter is required")

    logger.info(
        f"Pipeline parameters: workspace_id={workspace_id}, product_id={product_id}, version={version}, embedder={embedder_name}, dim={dim}"
    )
    logger.info(f"Chunking config: {chunking_config}")
    if playbook_id:
        logger.info(f"AIRD playbook: {playbook_id}")

    return {
        "workspace_id": workspace_id,
        "product_id": product_id,
        "version": version,
        "embedder_name": embedder_name,
        "dim": dim,
        "chunking_config": chunking_config,
        "playbook_id": playbook_id,  # AIRD playbook parameter
    }


def get_aird_context(**context) -> Dict[str, Any]:
    """Get AIRD stage execution context.

    This helper function provides context for AIRD stages including:
    - Pipeline parameters
    - Storage adapter
    - Database session
    - Pipeline run tracking

    Args:
        context: Airflow task context

    Returns:
        Dictionary with AIRD context (storage, tracker, config, etc.)
    """
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]

    # Get database session
    db = next(get_db())

    # Get pipeline run
    pipeline_run = db.query(PipelineRun).filter(PipelineRun.product_id == product_id, PipelineRun.version == version).first()

    if not pipeline_run:
        logger.warning(f"Pipeline run not found for product {product_id}, version {version}")
        # Create a placeholder - in practice, pipeline run should exist
        pipeline_run = None

    # Create storage adapter
    storage = AirdStorageAdapter(
        workspace_id=workspace_id,
        product_id=product_id,
        version=version,
    )

    # Create stage tracker (if pipeline run exists)
    tracker = None
    if pipeline_run:
        tracker = StageTracker(db, pipeline_run)

    # Get AIRD config
    aird_config = get_aird_config()

    return {
        "workspace_id": workspace_id,
        "product_id": product_id,
        "version": version,
        "storage": storage,
        "tracker": tracker,
        "db": db,
        "pipeline_run": pipeline_run,
        "config": aird_config,
        "playbook_id": params.get("playbook_id"),
    }


def ingest_from_datasources(**context) -> Dict[str, Any]:
    """Ingest data from all data sources to raw storage."""
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]

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
            return {"status": "skipped", "message": "Raw data already exists", "files_count": len(existing_objects)}

        # Ingest from each data source
        total_files = 0
        total_bytes = 0
        total_errors = 0

        for ds in data_sources:
            logger.info(f"Processing data source: {ds.name} (type: {ds.type})")

            try:
                if ds.type.value == "web":
                    config = ds.config.copy()
                    if "url" in config and "urls" not in config:
                        config["urls"] = [config["url"]]
                    connector = WebConnector(config)
                    result = connector.sync_full("primedata-raw", raw_prefix_path)

                elif ds.type.value == "folder":
                    config = ds.config.copy()
                    if "path" in config and "root_path" not in config:
                        config["root_path"] = config["path"]

                    # Convert file_types to include patterns
                    if "file_types" in config and "include" not in config:
                        file_types = config["file_types"]
                        if isinstance(file_types, str):
                            config["include"] = [ft.strip() for ft in file_types.split(",") if ft.strip()]
                        elif isinstance(file_types, list):
                            config["include"] = file_types
                        else:
                            config["include"] = ["*"]

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

                total_files += result["files"]
                total_bytes += result["bytes"]
                total_errors += result["errors"]

                logger.info(
                    f"Data source {ds.name}: {result['files']} files, {result['bytes']} bytes, {result['errors']} errors"
                )

            except Exception as e:
                logger.error(f"Error processing data source {ds.name}: {e}")
                total_errors += 1

        logger.info(f"Ingestion completed: {total_files} files, {total_bytes} bytes, {total_errors} errors")

        return {"status": "completed", "files_count": total_files, "bytes_count": total_bytes, "errors_count": total_errors}

    finally:
        db.close()


def preprocess(**context) -> Dict[str, Any]:
    """Preprocess and clean raw data using AIRD preprocessing stage (M1)."""
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]
    playbook_id = params.get("playbook_id")

    logger.info(f"Starting AIRD preprocessing for product {product_id}, version {version}, playbook={playbook_id}")

    # Get AIRD context
    aird_context = get_aird_context(**context)
    storage = aird_context["storage"]
    tracker = aird_context.get("tracker")
    db = aird_context["db"]

    try:
        # Get product to check playbook_id
        product = db.query(Product).filter(Product.id == product_id).first()
        if product and product.playbook_id and not playbook_id:
            playbook_id = product.playbook_id
            logger.info(f"Using playbook from product: {playbook_id}")

        # List raw files from MinIO
        raw_prefix_path = raw_prefix(workspace_id, product_id, version)
        raw_objects = minio_client.list_objects("primedata-raw", raw_prefix_path)

        if not raw_objects:
            logger.warning(f"No raw files found at {raw_prefix_path}")
            return {"status": "skipped", "message": "No raw files to process", "files_count": 0}

        # Extract file stems (remove .txt extension)
        raw_files = []
        for obj in raw_objects:
            if obj["name"].endswith(".txt"):
                # Extract stem from path like "ws/.../prod/.../v/1/raw/filename.txt"
                stem = Path(obj["name"]).stem
                raw_files.append(stem)

        if not raw_files:
            logger.warning("No .txt files found in raw storage")
            return {"status": "skipped", "message": "No .txt files to process", "files_count": 0}

        logger.info(f"Found {len(raw_files)} raw files to process: {raw_files}")

        # Create preprocessing stage
        from primedata.ingestion_pipeline.aird_stages.preprocess import PreprocessStage

        preprocess_stage = PreprocessStage(
            product_id=product_id,
            version=version,
            workspace_id=workspace_id,
            config={"playbook_id": playbook_id} if playbook_id else {},
        )

        # Execute preprocessing
        stage_context = {
            "storage": storage,
            "raw_files": raw_files,
            "playbook_id": playbook_id,
        }

        result = preprocess_stage.execute(stage_context)

        # Track stage result
        if tracker:
            tracker.record_stage_result(result)

        # Update product preprocessing stats
        if product and result.status.value == "succeeded":
            product.preprocessing_stats = result.metrics
            if playbook_id:
                product.playbook_id = playbook_id
            db.commit()

        logger.info(f"Preprocessing completed: {result.status.value}, chunks={result.metrics.get('total_chunks', 0)}")

        return {
            "status": result.status.value,
            "files_count": result.metrics.get("processed_files", 0),
            "total_chunks": result.metrics.get("total_chunks", 0),
            "playbook_id": result.metrics.get("playbook_id"),
            "mid_sentence_boundary_rate": result.metrics.get("mid_sentence_boundary_rate"),
        }

    except Exception as e:
        logger.error(f"Preprocessing failed: {e}", exc_info=True)
        if tracker:
            from primedata.ingestion_pipeline.aird_stages.base import StageResult, StageStatus

            error_result = StageResult(
                status=StageStatus.FAILED,
                stage_name="preprocess",
                product_id=product_id,
                version=version,
                metrics={},
                error=str(e),
            )
            tracker.record_stage_result(error_result)
        raise
    finally:
        db.close()
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]

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
            raw_content = minio_client.get_object("primedata-raw", obj["name"])
            if not raw_content:
                logger.warning(f"Failed to download {obj['name']}")
                continue

            # Basic text extraction based on content type
            content_type = obj.get("content_type", "")
            clean_text = ""

            if content_type == "text/html":
                # Simple HTML text extraction
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(raw_content.decode("utf-8", errors="ignore"), "html.parser")
                clean_text = soup.get_text(separator=" ", strip=True)

            elif content_type == "text/plain":
                # Plain text
                clean_text = raw_content.decode("utf-8", errors="ignore")

            elif content_type == "application/pdf":
                # Basic PDF text extraction (requires PyPDF2 or similar)
                try:
                    from io import BytesIO

                    import PyPDF2

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
                    clean_text = raw_content.decode("utf-8", errors="ignore")
                except:
                    clean_text = f"[Binary file: {obj['name']}]"

            # Clean and normalize text
            clean_text = clean_text.strip()

            # Debug: Log content info
            logger.info(f"Processing {obj['name']}: content_type={content_type}, clean_text_length={len(clean_text)}")

            if not clean_text:
                logger.warning(f"Skipping {obj['name']} - no text content after cleaning")
                continue

            # Generate clean file key
            clean_key = obj["name"].replace("/raw/", "/clean/")

            # Upload cleaned content
            if minio_client.put_bytes("primedata-clean", clean_key, clean_text.encode("utf-8"), "text/plain"):
                processed_files += 1
                total_bytes += len(clean_text.encode("utf-8"))
                logger.info(f"Processed: {obj['name']} -> {clean_key}")

        except Exception as e:
            logger.error(f"Error processing {obj['name']}: {e}")

    logger.info(f"Preprocessing completed: {processed_files} files processed")

    return {"status": "completed", "files_processed": processed_files, "bytes_processed": total_bytes}


def chunk(**context) -> Dict[str, Any]:
    """Chunk cleaned documents into smaller pieces."""
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]
    chunking_config = params["chunking_config"]

    logger.info(f"Starting chunking for product {product_id}, version {version}")
    logger.info(f"Using chunking config: {chunking_config}")

    clean_prefix_path = clean_prefix(workspace_id, product_id, version)
    chunk_prefix_path = chunk_prefix(workspace_id, product_id, version)

    # Get cleaned objects
    clean_objects = minio_client.list_objects("primedata-clean", clean_prefix_path)

    if not clean_objects:
        raise ValueError("No cleaned data found for chunking")

    # Use chunking configuration from product settings
    chunk_size = chunking_config.get("chunk_size", 1000)
    chunk_overlap = chunking_config.get("chunk_overlap", 200)
    min_chunk_size = chunking_config.get("min_chunk_size", 100)
    max_chunk_size = chunking_config.get("max_chunk_size", 2000)
    chunking_strategy = chunking_config.get("chunking_strategy", "fixed_size")

    chunks_created = 0

    for obj in clean_objects:
        try:
            # Download cleaned content
            clean_content = minio_client.get_object("primedata-clean", obj["name"])
            if not clean_content:
                continue

            text = clean_content.decode("utf-8", errors="ignore")

            # Simple chunking by character count
            chunks = []
            start = 0

            # Debug: Log text length and content preview
            logger.info(f"Text length: {len(text)}, preview: {text[:100]}...")

            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk_text = text[start:end]

                # Skip empty chunks but continue processing
                if not chunk_text.strip():
                    start += 1  # Move forward by 1 character
                    continue

                # Apply min/max chunk size filtering
                chunk_length = len(chunk_text.strip())
                if chunk_length < min_chunk_size:
                    # Chunk too small, try to extend it
                    if end < len(text):
                        # Try to extend to next sentence or word boundary
                        extended_end = min(end + (min_chunk_size - chunk_length), len(text))
                        extended_chunk = text[start:extended_end]
                        if len(extended_chunk.strip()) >= min_chunk_size:
                            chunk_text = extended_chunk
                            end = extended_end
                        else:
                            # Skip this chunk if we can't make it big enough
                            start += 1
                            continue
                    else:
                        # At end of text, skip small chunks
                        start += 1
                        continue

                if chunk_length > max_chunk_size:
                    # Chunk too large, try to split at sentence boundary
                    # For now, just truncate (could be improved with smarter splitting)
                    chunk_text = chunk_text[:max_chunk_size]
                    end = start + max_chunk_size

                chunk_index = len(chunks)
                chunks.append(
                    {
                        "text": chunk_text.strip(),
                        "source_file": obj["name"],
                        "chunk_index": chunk_index,
                        "start_char": start,
                        "end_char": end,
                    }
                )

                # Move start position forward with overlap
                step_size = max(1, chunk_size - chunk_overlap)
                start = start + step_size

                # Safety check to prevent infinite loops
                if start >= len(text):
                    break

            # Save chunks as JSONL
            for i, chunk in enumerate(chunks):
                chunk_key = f"{chunk_prefix_path}{Path(obj['name']).stem}_chunk_{i:04d}.json"
                chunk_json = json.dumps(chunk, indent=2)

                if minio_client.put_bytes("primedata-chunk", chunk_key, chunk_json.encode("utf-8"), "application/json"):
                    chunks_created += 1

            logger.info(f"Created {len(chunks)} chunks from {obj['name']}")

        except Exception as e:
            logger.error(f"Error chunking {obj['name']}: {e}")

    logger.info(f"Chunking completed: {chunks_created} chunks created")

    return {"status": "completed", "chunks_created": chunks_created}


def embed(**context) -> Dict[str, Any]:
    """Generate embeddings for chunks."""
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]
    embedder_name = params["embedder_name"]
    dim = params["dim"]

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
            chunk_content = minio_client.get_object("primedata-chunk", obj["name"])
            if not chunk_content:
                continue

            chunk_data = json.loads(chunk_content.decode("utf-8"))
            text = chunk_data["text"]

            # Generate embedding
            embedding = embedder.embed(text)

            # Store embedding data
            embedding_data = {
                "chunk_id": f"{Path(obj['name']).stem}",
                "text": text,
                "embedding": embedding.tolist(),
                "source_file": chunk_data["source_file"],
                "chunk_index": chunk_data["chunk_index"],
                "metadata": {"start_char": chunk_data["start_char"], "end_char": chunk_data["end_char"]},
            }

            # Save embedding as JSON
            embed_key = f"{embed_prefix_path}{Path(obj['name']).stem}.json"
            embed_json = json.dumps(embedding_data, indent=2)

            if minio_client.put_bytes("primedata-embed", embed_key, embed_json.encode("utf-8"), "application/json"):
                embeddings_created += 1
                vectors_data.append(
                    {
                        "id": embedding_data["chunk_id"],
                        "vector": embedding,
                        "payload": {
                            "text": text,
                            "source_file": chunk_data["source_file"],
                            "chunk_index": chunk_data["chunk_index"],
                            "metadata": embedding_data["metadata"],
                        },
                    }
                )

        except Exception as e:
            logger.error(f"Error embedding {obj['name']}: {e}")

    logger.info(f"Embedding completed: {embeddings_created} embeddings created")

    # Store vectors data for indexing task
    context["task_instance"].xcom_push(key="vectors_data", value=vectors_data)

    return {"status": "completed", "embeddings_created": embeddings_created, "dimension": dim}


def index(**context) -> Dict[str, Any]:
    """Index embeddings to Qdrant using AIRD indexing stage (M4)."""
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]

    logger.info(f"Starting AIRD indexing for product {product_id}, version {version}")

    aird_context = get_aird_context(**context)
    storage = aird_context["storage"]
    tracker = aird_context.get("tracker")
    db = aird_context["db"]

    try:
        from primedata.ingestion_pipeline.aird_stages.indexing import IndexingStage

        indexing_stage = IndexingStage(
            product_id=product_id,
            version=version,
            workspace_id=workspace_id,
        )

        # Get processed files from preprocessing
        preprocess_result = context.get("task_instance").xcom_pull(task_ids="preprocess")
        processed_files = preprocess_result.get("processed_file_list", []) if preprocess_result else []

        stage_context = {
            "storage": storage,
            "processed_files": processed_files,
            "preprocess_result": preprocess_result,
            "db": db,  # Pass db from context
        }

        result = indexing_stage.execute(stage_context)

        if tracker:
            tracker.record_stage_result(result)

        logger.info(f"Indexing completed: {result.status.value}, points={result.metrics.get('points_indexed', 0)}")

        return {
            "status": result.status.value,
            "points_indexed": result.metrics.get("points_indexed", 0),
            "collection_name": result.metrics.get("collection_name"),
            "avg_trust_score": result.metrics.get("avg_trust_score", 0.0),
        }

    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        if tracker:
            from primedata.ingestion_pipeline.aird_stages.base import StageResult, StageStatus

            error_result = StageResult(
                status=StageStatus.FAILED,
                stage_name="indexing",
                product_id=product_id,
                version=version,
                metrics={},
                error=str(e),
            )
            tracker.record_stage_result(error_result)
        raise
    finally:
        db.close()


# Legacy index function (kept for backward compatibility, but AIRD indexing is preferred)
def index_legacy(**context) -> Dict[str, Any]:
    """Legacy indexing function (kept for backward compatibility)."""
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]
    dim = params.get("dim", 384)

    logger.info(f"Starting legacy indexing for product {product_id}, version {version}")

    # Get vectors data from previous task
    vectors_data = context["task_instance"].xcom_pull(key="vectors_data")

    if not vectors_data:
        raise ValueError("No vectors data found for indexing")

    # Initialize Qdrant client
    from primedata.indexing.qdrant_client import QdrantClient

    qdrant_client = QdrantClient()

    # Create collection name
    collection_name = f"ws_{workspace_id}__prod_{product_id}__v_{version}"

    # Ensure collection exists
    qdrant_client.ensure_collection(collection_name, dim)

    # Prepare points for upsert
    points = []
    for i, vector_data in enumerate(vectors_data):
        # Use a hash-based approach to create unique integer IDs
        import hashlib

        unique_string = f"{vector_data['payload']['source_file']}_{vector_data['payload']['chunk_index']}"
        unique_id = int(hashlib.md5(unique_string.encode()).hexdigest()[:8], 16)
        points.append(
            {
                "id": unique_id,  # Use unique integer IDs based on hash
                "vector": vector_data["vector"].tolist(),
                "payload": vector_data["payload"],
            }
        )

    # Upsert points
    qdrant_client.upsert_points(collection_name, points)

    logger.info(f"Indexing completed: {len(points)} points indexed to collection {collection_name}")

    return {"status": "completed", "points_indexed": len(points), "collection_name": collection_name}


def validate(**context) -> Dict[str, Any]:
    """Validate pipeline results and compute metrics."""
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]

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
            content = minio_client.get_object("primedata-clean", obj["name"])
            if content:
                total_chars += len(content.decode("utf-8", errors="ignore"))

        avg_tokens = total_chars / max(doc_count, 1) / 4  # Rough estimate

        # Calculate duplicate rate (simplified: check for identical chunk texts)
        chunk_texts = set()
        duplicates = 0
        for obj in chunk_objects:
            content = minio_client.get_object("primedata-chunk", obj["name"])
            if content:
                chunk_data = json.loads(content.decode("utf-8"))
                text = chunk_data["text"]
                if text in chunk_texts:
                    duplicates += 1
                else:
                    chunk_texts.add(text)

        dup_rate = duplicates / max(chunk_count, 1)

        metrics = {
            "doc_count": doc_count,
            "chunk_count": chunk_count,
            "avg_tokens": round(avg_tokens, 2),
            "dup_rate": round(dup_rate, 4),
            "embed_count": len(embed_objects),
        }

        logger.info(f"Validation metrics: {metrics}")

        # Store metrics in PipelineRun
        dag_run_id = context["dag_run"].run_id
        pipeline_run = (
            db.query(PipelineRun)
            .filter(PipelineRun.product_id == product_id, PipelineRun.version == version, PipelineRun.dag_run_id == dag_run_id)
            .first()
        )

        if pipeline_run:
            pipeline_run.metrics = metrics
            pipeline_run.status = "succeeded"
            pipeline_run.finished_at = datetime.utcnow()
            db.commit()

        return {"status": "completed", "metrics": metrics}

    finally:
        db.close()


def validate_data_quality(**context) -> Dict[str, Any]:
    """Validate data quality against configured rules."""
    import asyncio

    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]
    pipeline_run_id = context.get("dag_run", {}).get("run_id", "")

    logger.info(f"Starting data quality validation for product {product_id}, version {version}")

    # Get database session
    db = SessionLocal()

    try:
        # Initialize data quality validator
        validator = DataQualityValidator(minio_client)

        # Run validation using asyncio.run for async function
        report = asyncio.run(
            validator.validate_product_data(
                product_id=product_id, version=version, pipeline_run_id=pipeline_run_id, workspace_id=workspace_id
            )
        )

        # Save violations to database
        violations_saved = 0
        for violation in report.violations:
            db_violation = DqViolation(
                product_id=product_id,
                version=version,
                pipeline_run_id=pipeline_run_id,
                rule_name=violation.rule_name,
                rule_type=violation.rule_type,
                severity=violation.severity,
                message=violation.message,
                details=violation.details,
                affected_count=violation.affected_count,
                total_count=violation.total_count,
                violation_rate=violation.violation_rate,
            )
            db.add(db_violation)
            violations_saved += 1

        db.commit()

        logger.info(f"Data quality validation completed: {violations_saved} violations saved")

        return {
            "status": "completed",
            "violations_found": len(report.violations),
            "violations_saved": violations_saved,
            "has_errors": report.has_errors,
            "has_warnings": report.has_warnings,
            "quality_score": report.overall_quality_score,
        }

    except Exception as e:
        logger.error(f"Data quality validation failed: {e}")
        db.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


def finalize(**context) -> Dict[str, Any]:
    """Finalize pipeline by updating product status."""
    params = get_dag_params(**context)
    product_id = params["product_id"]
    version = params["version"]

    logger.info(f"Finalizing pipeline for product {product_id}, version {version}")

    # Get database session
    db = next(get_db())

    try:
        # Update product status and version
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            product.status = "ready"
            if version and version > product.current_version:
                product.current_version = version
            db.commit()
            logger.info(f"Product {product_id} status updated to 'ready', version {version}")

        return {"status": "completed", "product_status": "ready", "version": version}

    finally:
        db.close()


# Define tasks
ingest_task = PythonOperator(
    task_id="ingest_from_datasources",
    python_callable=ingest_from_datasources,
    dag=dag,
)

preprocess_task = PythonOperator(
    task_id="preprocess",
    python_callable=preprocess,
    dag=dag,
)

chunk_task = PythonOperator(
    task_id="chunk",
    python_callable=chunk,
    dag=dag,
)

embed_task = PythonOperator(
    task_id="embed",
    python_callable=embed,
    dag=dag,
)

index_task = PythonOperator(
    task_id="index",
    python_callable=index,
    dag=dag,
)

validate_task = PythonOperator(
    task_id="validate",
    python_callable=validate,
    dag=dag,
)

validate_dq_task = PythonOperator(
    task_id="validate_data_quality",
    python_callable=validate_data_quality,
    dag=dag,
)

finalize_task = PythonOperator(
    task_id="finalize",
    python_callable=finalize,
    dag=dag,
)


# AIRD scoring, fingerprint, and policy tasks (M2)
def score(**context) -> Dict[str, Any]:
    """Score processed chunks using AIRD scoring stage."""
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]

    logger.info(f"Starting AIRD scoring for product {product_id}, version {version}")

    aird_context = get_aird_context(**context)
    storage = aird_context["storage"]
    tracker = aird_context.get("tracker")
    db = aird_context["db"]

    try:
        from primedata.ingestion_pipeline.aird_stages.scoring import ScoringStage

        scoring_stage = ScoringStage(
            product_id=product_id,
            version=version,
            workspace_id=workspace_id,
        )

        # Get processed files from preprocessing
        preprocess_result = context.get("task_instance").xcom_pull(task_ids="preprocess")
        processed_files = preprocess_result.get("processed_file_list", []) if preprocess_result else []
        
        # Load playbook for AI-Ready metrics (noise patterns, coherence settings)
        playbook_id = params.get("playbook_id")
        if not playbook_id:
            # Try to get from product
            from primedata.db.models import Product
            product = db.query(Product).filter(Product.id == product_id).first()
            if product and product.playbook_id:
                playbook_id = product.playbook_id
        
        playbook = {}
        if playbook_id:
            try:
                from primedata.ingestion_pipeline.aird_stages.playbooks import load_playbook_yaml
                playbook = load_playbook_yaml(playbook_id, workspace_id=str(workspace_id), db_session=db)
                logger.info(f"Loaded playbook {playbook_id} for scoring stage")
            except Exception as e:
                logger.warning(f"Failed to load playbook {playbook_id}: {e}, using empty playbook")

        stage_context = {
            "storage": storage,
            "processed_files": processed_files,
            "preprocess_result": preprocess_result,
            "playbook": playbook,
            "playbook_id": playbook_id,
        }

        result = scoring_stage.execute(stage_context)

        if tracker:
            tracker.record_stage_result(result)

        logger.info(f"Scoring completed: {result.status.value}, chunks={result.metrics.get('total_chunks', 0)}")

        return {
            "status": result.status.value,
            "total_chunks": result.metrics.get("total_chunks", 0),
            "avg_trust_score": result.metrics.get("avg_trust_score", 0.0),
        }
    except Exception as e:
        logger.error(f"Scoring failed: {e}", exc_info=True)
        if tracker:
            from primedata.ingestion_pipeline.aird_stages.base import StageResult, StageStatus

            error_result = StageResult(
                status=StageStatus.FAILED,
                stage_name="scoring",
                product_id=product_id,
                version=version,
                metrics={},
                error=str(e),
            )
            tracker.record_stage_result(error_result)
        raise
    finally:
        db.close()


def fingerprint(**context) -> Dict[str, Any]:
    """Generate readiness fingerprint from metrics."""
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]

    logger.info(f"Starting fingerprint generation for product {product_id}, version {version}")

    aird_context = get_aird_context(**context)
    storage = aird_context["storage"]
    tracker = aird_context.get("tracker")
    db = aird_context["db"]

    try:
        from primedata.ingestion_pipeline.aird_stages.fingerprint import FingerprintStage

        fingerprint_stage = FingerprintStage(
            product_id=product_id,
            version=version,
            workspace_id=workspace_id,
        )

        # Get scoring result
        scoring_result = context.get("task_instance").xcom_pull(task_ids="score")

        stage_context = {
            "storage": storage,
            "scoring_result": scoring_result,
        }

        result = fingerprint_stage.execute(stage_context)

        if tracker:
            tracker.record_stage_result(result)

        # Update product with fingerprint
        product = db.query(Product).filter(Product.id == product_id).first()
        if product and result.status.value == "succeeded":
            fingerprint = result.metrics.get("fingerprint", {})
            product.readiness_fingerprint = fingerprint
            product.trust_score = fingerprint.get("AI_Trust_Score")
            db.commit()

        logger.info(
            f"Fingerprint generation completed: {result.status.value}, trust_score={result.metrics.get('trust_score', 0.0)}"
        )

        return {
            "status": result.status.value,
            "trust_score": result.metrics.get("trust_score", 0.0),
        }
    except Exception as e:
        logger.error(f"Fingerprint generation failed: {e}", exc_info=True)
        if tracker:
            from primedata.ingestion_pipeline.aird_stages.base import StageResult, StageStatus

            error_result = StageResult(
                status=StageStatus.FAILED,
                stage_name="fingerprint",
                product_id=product_id,
                version=version,
                metrics={},
                error=str(e),
            )
            tracker.record_stage_result(error_result)
        raise
    finally:
        db.close()


def policy(**context) -> Dict[str, Any]:
    """Evaluate policy against fingerprint."""
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]

    logger.info(f"Starting policy evaluation for product {product_id}, version {version}")

    aird_context = get_aird_context(**context)
    storage = aird_context["storage"]
    tracker = aird_context.get("tracker")
    db = aird_context["db"]

    try:
        from primedata.ingestion_pipeline.aird_stages.policy import PolicyStage

        policy_stage = PolicyStage(
            product_id=product_id,
            version=version,
            workspace_id=workspace_id,
        )

        # Get fingerprint result
        fingerprint_result = context.get("task_instance").xcom_pull(task_ids="fingerprint")

        stage_context = {
            "storage": storage,
            "fingerprint_result": fingerprint_result,
        }

        result = policy_stage.execute(stage_context)

        if tracker:
            tracker.record_stage_result(result)

        # Update product with policy status
        product = db.query(Product).filter(Product.id == product_id).first()
        if product and result.status.value in ("succeeded", "failed"):
            product.policy_status = "passed" if result.metrics.get("policy_passed") else "failed"
            product.policy_violations = result.metrics.get("violations", [])

            # Update product status based on policy
            if not result.metrics.get("policy_passed"):
                product.status = ProductStatus.FAILED_POLICY
            elif product.status == ProductStatus.DRAFT:
                product.status = ProductStatus.READY

            db.commit()

        logger.info(f"Policy evaluation completed: passed={result.metrics.get('policy_passed', False)}")

        return {
            "status": result.status.value,
            "policy_passed": result.metrics.get("policy_passed", False),
            "violations": result.metrics.get("violations", []),
        }
    except Exception as e:
        logger.error(f"Policy evaluation failed: {e}", exc_info=True)
        if tracker:
            from primedata.ingestion_pipeline.aird_stages.base import StageResult, StageStatus

            error_result = StageResult(
                status=StageStatus.FAILED,
                stage_name="policy",
                product_id=product_id,
                version=version,
                metrics={},
                error=str(e),
            )
            tracker.record_stage_result(error_result)
        raise
    finally:
        db.close()


score_task = PythonOperator(
    task_id="score",
    python_callable=score,
    dag=dag,
)

fingerprint_task = PythonOperator(
    task_id="fingerprint",
    python_callable=fingerprint,
    dag=dag,
)

policy_task = PythonOperator(
    task_id="policy",
    python_callable=policy,
    dag=dag,
)


# AIRD validation and reporting tasks (M3) - optional, can run after policy
def validation(**context) -> Dict[str, Any]:
    """Generate validation summary CSV."""
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]

    logger.info(f"Starting validation summary generation for product {product_id}, version {version}")

    aird_context = get_aird_context(**context)
    storage = aird_context["storage"]
    tracker = aird_context.get("tracker")
    db = aird_context["db"]

    try:
        from primedata.ingestion_pipeline.aird_stages.validation import ValidationStage

        validation_stage = ValidationStage(
            product_id=product_id,
            version=version,
            workspace_id=workspace_id,
        )

        stage_context = {
            "storage": storage,
        }

        result = validation_stage.execute(stage_context)

        if tracker:
            tracker.record_stage_result(result)

        # Update product with validation summary path
        product = db.query(Product).filter(Product.id == product_id).first()
        if product and result.status.value == "succeeded" and result.artifacts:
            product.validation_summary_path = result.artifacts.get("validation_summary_csv")
            db.commit()

        logger.info(f"Validation summary generation completed: {result.status.value}")

        return {
            "status": result.status.value,
            "entries_processed": result.metrics.get("entries_processed", 0),
        }
    except Exception as e:
        logger.error(f"Validation summary generation failed: {e}", exc_info=True)
        if tracker:
            from primedata.ingestion_pipeline.aird_stages.base import StageResult, StageStatus

            error_result = StageResult(
                status=StageStatus.FAILED,
                stage_name="validation",
                product_id=product_id,
                version=version,
                metrics={},
                error=str(e),
            )
            tracker.record_stage_result(error_result)
        raise
    finally:
        db.close()


def reporting(**context) -> Dict[str, Any]:
    """Generate PDF trust report."""
    params = get_dag_params(**context)
    workspace_id = params["workspace_id"]
    product_id = params["product_id"]
    version = params["version"]

    logger.info(f"Starting PDF report generation for product {product_id}, version {version}")

    aird_context = get_aird_context(**context)
    storage = aird_context["storage"]
    tracker = aird_context.get("tracker")
    db = aird_context["db"]

    try:
        from primedata.ingestion_pipeline.aird_stages.reporting import ReportingStage

        reporting_stage = ReportingStage(
            product_id=product_id,
            version=version,
            workspace_id=workspace_id,
        )

        stage_context = {
            "storage": storage,
        }

        result = reporting_stage.execute(stage_context)

        if tracker:
            tracker.record_stage_result(result)

        # Update product with trust report path
        product = db.query(Product).filter(Product.id == product_id).first()
        if product and result.status.value == "succeeded" and result.artifacts:
            product.trust_report_path = result.artifacts.get("trust_report_pdf")
            db.commit()

        logger.info(f"PDF report generation completed: {result.status.value}")

        return {
            "status": result.status.value,
            "pdf_size_bytes": result.metrics.get("pdf_size_bytes", 0),
        }
    except Exception as e:
        logger.error(f"PDF report generation failed: {e}", exc_info=True)
        if tracker:
            from primedata.ingestion_pipeline.aird_stages.base import StageResult, StageStatus

            error_result = StageResult(
                status=StageStatus.FAILED,
                stage_name="reporting",
                product_id=product_id,
                version=version,
                metrics={},
                error=str(e),
            )
            tracker.record_stage_result(error_result)
        raise
    finally:
        db.close()


validation_task = PythonOperator(
    task_id="validation",
    python_callable=validation,
    dag=dag,
)

reporting_task = PythonOperator(
    task_id="reporting",
    python_callable=reporting,
    dag=dag,
)

# Define task dependencies
# Validation and reporting are optional and can run in parallel after policy
(
    ingest_task
    >> preprocess_task
    >> score_task
    >> fingerprint_task
    >> policy_task
    >> [validation_task, reporting_task]
    >> chunk_task
    >> embed_task
    >> index_task
    >> validate_task
    >> validate_dq_task
    >> finalize_task
)
