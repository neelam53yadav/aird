# Pipeline Setup & Troubleshooting Guide

## Overview

This guide provides comprehensive instructions for setting up, configuring, and troubleshooting PrimeData pipelines. It covers everything from initial setup to advanced troubleshooting scenarios.

## Pipeline Architecture

### **Pipeline Components**

#### **Data Ingestion**
- **Connectors**: Web, folder, database, API sources
- **Raw Storage**: MinIO object storage
- **Format Support**: PDF, DOCX, TXT, HTML, JSON, XML
- **Volume Mounting**: Docker container path mapping

#### **Data Processing**
- **Cleaning**: Encoding fixes, duplicate removal
- **Chunking**: Hybrid auto/manual chunking strategies
- **Embedding**: Vector generation with multiple models
- **Indexing**: Qdrant vector storage

#### **Orchestration**
- **Airflow DAGs**: Pipeline workflow management
- **MLflow Tracking**: Experiment and metrics tracking
- **Error Handling**: Retry logic and failure recovery
- **Monitoring**: Real-time pipeline status

## Initial Setup

### **Prerequisites**

#### **System Requirements**
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- 8GB+ RAM recommended
- 50GB+ disk space

#### **Environment Setup**
```bash
# Clone repository
git clone <repository-url>
cd PrimeData

# Activate virtual environment
activate_venv.bat

# Install dependencies
pip install -r backend/requirements.txt
```

### **Service Configuration**

#### **Database Setup**
```bash
# Run migrations
cd backend
activate_venv.bat
alembic upgrade head
```

#### **Docker Services**
```bash
# Start all services
docker-compose -f infra/docker-compose.yml up -d

# Verify services
docker-compose ps
```

#### **Service URLs**
- **PrimeData API**: http://localhost:8000
- **PrimeData UI**: http://localhost:3000
- **Airflow UI**: http://localhost:8080 (admin/admin)
- **MLflow UI**: http://localhost:5000
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin123)

## Pipeline Configuration

### **Data Source Setup**

#### **Folder Data Sources**
```json
{
  "type": "folder",
  "config": {
    "root_path": "/opt/airflow/data",
    "include": ["*.pdf", "*.docx", "*.txt"],
    "exclude": ["*.tmp", "*.log"],
    "recursive": true,
    "max_file_size": 104857600
  }
}
```

**Important**: Use Docker container paths (`/opt/airflow/data`) not Windows paths (`D:\projects\data`)

#### **Web Data Sources**
```json
{
  "type": "web",
  "config": {
    "urls": ["https://example.com"],
    "include_patterns": ["*.html", "*.pdf"],
    "exclude_patterns": ["*.css", "*.js"],
    "max_depth": 3,
    "respect_robots_txt": true
  }
}
```

### **Chunking Configuration**

#### **Auto Mode**
```json
{
  "mode": "auto",
  "auto_settings": {
    "content_type": "general",
    "model_optimized": true,
    "confidence_threshold": 0.7
  }
}
```

#### **Manual Mode**
```json
{
  "mode": "manual",
  "manual_settings": {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "min_chunk_size": 100,
    "max_chunk_size": 2000,
    "chunking_strategy": "fixed_size"
  }
}
```

### **Embedding Configuration**
```json
{
  "embedder_name": "minilm",
  "embedding_dimension": 384,
  "batch_size": 100,
  "normalize_embeddings": true
}
```

## Pipeline Execution

### **Manual Pipeline Trigger**

#### **Via UI**
1. Navigate to product page
2. Click "Run Pipeline"
3. Select version and configuration
4. Monitor progress in Airflow UI

#### **Via API**
```bash
curl -X POST "http://localhost:8000/api/v1/pipeline/run" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "your-product-id",
    "version": 1,
    "chunking_config": {...},
    "embedding_config": {...}
  }'
```

### **Pipeline Monitoring**

#### **Airflow UI**
- **URL**: http://localhost:8080
- **Credentials**: admin/admin
- **Features**: DAG status, task logs, retry management

#### **MLflow UI**
- **URL**: http://localhost:5000
- **Features**: Experiment tracking, metrics, artifacts

#### **PrimeData UI**
- **URL**: http://localhost:3000
- **Features**: Pipeline status, quality metrics, results

## Common Issues & Solutions

### **Pipeline Failures**

#### **"No raw data found for preprocessing"**
**Cause**: Ingest task failed or skipped
**Solutions**:
1. Check data source configuration
2. Verify file paths (use Docker container paths)
3. Check file permissions
4. Review ingest task logs in Airflow UI

#### **Database Connection Errors**
**Cause**: Database connectivity issues
**Solutions**:
1. Verify PostgreSQL is running: `docker-compose ps`
2. Check database credentials
3. Verify network connectivity
4. Review database logs

#### **Import Errors in Airflow**
**Cause**: Python path or module issues
**Solutions**:
1. Check PYTHONPATH environment variable
2. Verify module imports in DAG
3. Check file permissions
4. Review Airflow logs

### **Data Source Issues**

#### **Folder Connector Not Finding Files**
**Cause**: Incorrect path configuration
**Solutions**:
1. Use Docker container paths: `/opt/airflow/data`
2. Check volume mounting in docker-compose.yml
3. Verify file permissions
4. Test path accessibility

#### **Web Connector Timeouts**
**Cause**: Network or server issues
**Solutions**:
1. Check network connectivity
2. Verify URL accessibility
3. Adjust timeout settings
4. Check robots.txt compliance

### **Performance Issues**

#### **Slow Pipeline Execution**
**Solutions**:
1. Optimize chunking parameters
2. Adjust embedding batch size
3. Increase system resources
4. Use faster embedding models

#### **Memory Issues**
**Solutions**:
1. Reduce batch sizes
2. Process smaller datasets
3. Increase Docker memory limits
4. Optimize chunking strategy

## Advanced Configuration

### **Custom Connectors**

#### **Creating Custom Connectors**
```python
from primedata.connectors.base import BaseConnector

class CustomConnector(BaseConnector):
    def __init__(self, config):
        super().__init__(config)
        # Custom initialization
    
    def sync_full(self, output_bucket, output_prefix):
        # Custom sync logic
        pass
```

#### **Connector Registration**
```python
# In DAG file
from primedata.connectors.custom import CustomConnector

# Use in pipeline
connector = CustomConnector(config)
result = connector.sync_full("primedata-raw", prefix)
```

### **Custom Chunking Strategies**

#### **Semantic Chunking**
```python
def semantic_chunk(text, chunk_size=1000, overlap=200):
    # Custom semantic chunking logic
    sentences = text.split('. ')
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk + sentence) > chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += sentence + ". "
    
    return chunks
```

### **Performance Optimization**

#### **Parallel Processing**
```python
# Configure parallel processing
from multiprocessing import Pool

def process_chunks_parallel(chunks, num_processes=4):
    with Pool(num_processes) as pool:
        results = pool.map(process_chunk, chunks)
    return results
```

#### **Caching Strategies**
```python
# Implement caching for embeddings
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_cached_embedding(text):
    cache_key = f"embedding:{hash(text)}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    return None
```

## Monitoring & Alerting

### **Pipeline Health Monitoring**

#### **Key Metrics**
- Pipeline execution time
- Success/failure rates
- Data processing volume
- Resource utilization
- Error rates and types

#### **Alerting Configuration**
```python
# Custom alerting logic
def send_alert(message, severity="info"):
    if severity == "error":
        # Send to error notification system
        pass
    elif severity == "warning":
        # Send to warning notification system
        pass
```

### **Logging Configuration**

#### **Structured Logging**
```python
import logging
import json

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Log structured data
logger.info("Pipeline started", extra={
    "product_id": product_id,
    "version": version,
    "timestamp": datetime.utcnow().isoformat()
})
```

## Troubleshooting Checklist

### **Before Starting**
- [ ] All services are running (`docker-compose ps`)
- [ ] Database migrations are up to date
- [ ] Data sources are properly configured
- [ ] File paths are correct (Docker container paths)
- [ ] Network connectivity is working

### **During Execution**
- [ ] Monitor Airflow UI for task status
- [ ] Check MLflow UI for experiment tracking
- [ ] Review logs for errors or warnings
- [ ] Verify data is being processed
- [ ] Monitor system resources

### **After Completion**
- [ ] Verify data quality metrics
- [ ] Check embedding generation
- [ ] Validate vector storage
- [ ] Review performance metrics
- [ ] Test data retrieval

## Support Resources

### **Documentation**
- **Architecture**: `docs/architecture.md`
- **Data Quality**: `docs/data-quality.md`
- **API Reference**: `docs/api-reference.md`

### **Community Support**
- GitHub Issues
- User Forums
- Documentation Wiki
- Expert Consultations

### **Professional Support**
- Enterprise Support
- Custom Development
- Training Services
- Consulting Services

This comprehensive guide ensures successful pipeline setup, configuration, and troubleshooting for PrimeData deployments.
