# Pipeline Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting solutions for PrimeData pipeline issues, from common problems to advanced debugging scenarios.

## Common Pipeline Issues

### **1. "No raw data found for preprocessing" Error**

#### **Symptoms**
- Pipeline fails at preprocessing step
- Error message: "No raw data found for preprocessing"
- Ingest task shows 0 files processed

#### **Root Causes**
1. **Data source path issues** (most common)
2. **Ingest task failure**
3. **File permission problems**
4. **Volume mounting issues**

#### **Solutions**

##### **Check Data Source Configuration**
```bash
# Verify data source is using Docker container path
# ❌ Wrong: D:\projects\data
# ✅ Correct: /opt/airflow/data
```

**Fix Steps:**
1. Go to PrimeData UI → Product → Data Sources
2. Edit the folder data source
3. Change path from `D:\projects\data` to `/opt/airflow/data`
4. Save and test connection

##### **Verify Volume Mounting**
```yaml
# Check docker-compose.yml
volumes:
  - D:/projects/data:/opt/airflow/data  # ✅ Correct mounting
```

##### **Test File Access**
```bash
# Test from Airflow container
docker exec -it primedata-airflow-scheduler ls -la /opt/airflow/data
```

#### **Prevention**
- Always use Docker container paths for data sources
- Test data source connections before running pipelines
- Verify volume mounting in docker-compose.yml

### **2. Database Connection Errors**

#### **Symptoms**
- "Database connection failed" errors
- Import errors in Airflow DAGs
- Database query failures

#### **Root Causes**
1. **PostgreSQL not running**
2. **Connection string issues**
3. **Network connectivity problems**
4. **Environment variable issues**

#### **Solutions**

##### **Check PostgreSQL Status**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres
```

##### **Verify Database Connection**
```bash
# Test database connection
docker exec -it primedata-airflow-scheduler python -c "
from primedata.db.database import get_db
db = next(get_db())
print('Database connection successful')
db.close()
"
```

##### **Check Environment Variables**
```bash
# Verify database URL in Airflow container
docker exec -it primedata-airflow-scheduler env | grep DATABASE_URL
```

#### **Prevention**
- Always check service status before running pipelines
- Verify environment variables are correctly set
- Test database connectivity during setup

### **3. Airflow DAG Import Errors**

#### **Symptoms**
- "NameError: name 'logger' is not defined"
- "ModuleNotFoundError: No module named 'primedata'"
- DAG import failures

#### **Root Causes**
1. **Python path issues**
2. **Missing logger definition**
3. **Module import problems**
4. **File permission issues**

#### **Solutions**

##### **Fix Logger Definition**
```python
# In DAG file - move logger to top
import logging
logger = logging.getLogger(__name__)

# Rest of imports...
```

##### **Fix Python Path**
```python
# In DAG file - ensure proper path setup
import sys
import os
primedata_src_path = "/opt/airflow/primedata/src"
if primedata_src_path not in sys.path:
    sys.path.insert(0, primedata_src_path)
```

##### **Verify Module Imports**
```python
# Test imports in DAG
try:
    from primedata.db.database import get_db
    from primedata.db.models import Product, DataSource
    DB_AVAILABLE = True
    logger.info("Database modules imported successfully")
except Exception as e:
    logger.warning(f"Database modules not available: {e}")
    DB_AVAILABLE = False
```

#### **Prevention**
- Always define logger at the top of DAG files
- Use proper Python path management
- Test imports before using modules

### **4. MLflow Integration Issues**

#### **Symptoms**
- MLflow tracking failures
- Experiment not created
- Metrics not recorded

#### **Root Causes**
1. **MLflow server not running**
2. **Connection string issues**
3. **Authentication problems**
4. **Network connectivity issues**

#### **Solutions**

##### **Check MLflow Status**
```bash
# Check MLflow server
curl http://localhost:5000/health

# Check MLflow logs
docker-compose logs mlflow
```

##### **Verify MLflow Configuration**
```python
# Test MLflow connection
import mlflow
mlflow.set_tracking_uri("http://mlflow:5000")
print(f"MLflow tracking URI: {mlflow.get_tracking_uri()}")
```

##### **Check Environment Variables**
```bash
# Verify MLflow environment
docker exec -it primedata-airflow-scheduler env | grep MLFLOW
```

#### **Prevention**
- Always start MLflow server before running pipelines
- Verify MLflow configuration in docker-compose.yml
- Test MLflow connectivity during setup

## Advanced Troubleshooting

### **Pipeline Performance Issues**

#### **Slow Pipeline Execution**
**Symptoms:**
- Pipeline takes hours to complete
- High memory usage
- Timeout errors

**Solutions:**
1. **Optimize Chunking Parameters**
   ```json
   {
     "chunk_size": 1000,  // Reduce from 2000
     "chunk_overlap": 200, // Reduce from 400
     "batch_size": 50      // Reduce from 100
   }
   ```

2. **Increase System Resources**
   ```yaml
   # In docker-compose.yml
   deploy:
     resources:
       limits:
         memory: 4G
         cpus: '2.0'
   ```

3. **Use Faster Embedding Models**
   ```json
   {
     "embedder_name": "minilm",  // Faster than larger models
     "embedding_dimension": 384  // Smaller dimension
   }
   ```

#### **Memory Issues**
**Symptoms:**
- Out of memory errors
- Container crashes
- Slow performance

**Solutions:**
1. **Reduce Batch Sizes**
   ```python
   # In embedding configuration
   batch_size = 25  # Reduce from 100
   ```

2. **Process Smaller Datasets**
   ```python
   # Process data in chunks
   chunk_size = 1000
   for i in range(0, len(data), chunk_size):
       process_chunk(data[i:i+chunk_size])
   ```

3. **Optimize Data Structures**
   ```python
   # Use generators instead of lists
   def process_files_generator(files):
       for file in files:
           yield process_file(file)
   ```

### **Data Quality Issues**

#### **Poor Data Quality Scores**
**Symptoms:**
- Low AI readiness scores
- High violation rates
- Poor chunk quality

**Solutions:**
1. **Adjust Chunking Strategy**
   ```json
   {
     "mode": "manual",
     "manual_settings": {
       "chunk_size": 1000,
       "chunk_overlap": 200,
       "chunking_strategy": "semantic"
     }
   }
   ```

2. **Improve Data Sources**
   - Clean source data
   - Remove duplicates
   - Fix encoding issues
   - Use better file formats

3. **Optimize Data Quality Rules**
   ```json
   {
     "required_fields_rules": [
       {
         "name": "Content Quality",
         "configuration": {
           "min_length": 100,
           "max_length": 2000
         }
       }
     ]
   }
   ```

### **Network and Connectivity Issues**

#### **Service Communication Problems**
**Symptoms:**
- Service discovery failures
- Network timeouts
- Connection refused errors

**Solutions:**
1. **Check Docker Network**
   ```bash
   # Verify network connectivity
   docker network ls
   docker network inspect primedata_primedata-network
   ```

2. **Test Service Connectivity**
   ```bash
   # Test from Airflow container
   docker exec -it primedata-airflow-scheduler curl http://postgres:5432
   docker exec -it primedata-airflow-scheduler curl http://minio:9000
   docker exec -it primedata-airflow-scheduler curl http://mlflow:5000
   ```

3. **Check DNS Resolution**
   ```bash
   # Test DNS resolution
   docker exec -it primedata-airflow-scheduler nslookup postgres
   docker exec -it primedata-airflow-scheduler nslookup minio
   ```

## Debugging Tools and Techniques

### **Log Analysis**

#### **Airflow Logs**
```bash
# View Airflow logs
docker-compose logs airflow-scheduler
docker-compose logs airflow-webserver

# View specific task logs
docker exec -it primedata-airflow-scheduler cat /opt/airflow/logs/dag_id=primedata_simple/task_id=ingest_from_datasources/attempt=1.log
```

#### **Application Logs**
```bash
# View backend logs
docker-compose logs backend

# View MLflow logs
docker-compose logs mlflow
```

#### **Database Logs**
```bash
# View PostgreSQL logs
docker-compose logs postgres

# Connect to database
docker exec -it primedata-postgres psql -U primedata -d primedata
```

### **Performance Monitoring**

#### **System Resource Monitoring**
```bash
# Monitor container resources
docker stats

# Monitor specific container
docker stats primedata-airflow-scheduler
```

#### **Database Performance**
```sql
-- Check database performance
SELECT * FROM pg_stat_activity;
SELECT * FROM pg_stat_database;
```

#### **Pipeline Metrics**
```python
# Monitor pipeline metrics
import mlflow
mlflow.set_tracking_uri("http://localhost:5000")
experiments = mlflow.search_experiments()
for exp in experiments:
    runs = mlflow.search_runs(experiment_ids=[exp.experiment_id])
    print(f"Experiment: {exp.name}, Runs: {len(runs)}")
```

### **Testing and Validation**

#### **Unit Testing**
```python
# Test individual components
def test_folder_connector():
    from primedata.connectors.folder import FolderConnector
    
    config = {
        "root_path": "/opt/airflow/data",
        "include": ["*.pdf"],
        "recursive": True
    }
    
    connector = FolderConnector(config)
    success, message = connector.test_connection()
    assert success, f"Connection test failed: {message}"
```

#### **Integration Testing**
```python
# Test pipeline integration
def test_pipeline_integration():
    # Test data source connection
    # Test database connectivity
    # Test MLflow connection
    # Test MinIO access
    pass
```

#### **End-to-End Testing**
```python
# Test complete pipeline
def test_complete_pipeline():
    # Create test product
    # Add test data source
    # Run pipeline
    # Verify results
    # Check quality metrics
    pass
```

## Prevention Strategies

### **Proactive Monitoring**

#### **Health Checks**
```python
# Implement health checks
def health_check():
    checks = {
        "database": check_database_connection(),
        "minio": check_minio_connection(),
        "mlflow": check_mlflow_connection(),
        "qdrant": check_qdrant_connection()
    }
    return all(checks.values()), checks
```

#### **Automated Testing**
```python
# Automated pipeline testing
def test_pipeline_health():
    # Run health checks
    # Test data source connections
    # Validate configuration
    # Check resource availability
    pass
```

#### **Monitoring Alerts**
```python
# Set up monitoring alerts
def setup_monitoring():
    # Monitor pipeline execution time
    # Monitor error rates
    # Monitor resource usage
    # Monitor data quality scores
    pass
```

### **Best Practices**

#### **Configuration Management**
1. **Use Environment Variables**
   ```bash
   export DATABASE_URL="postgresql://user:pass@host:port/db"
   export MLFLOW_TRACKING_URI="http://localhost:5000"
   ```

2. **Validate Configuration**
   ```python
   def validate_config(config):
       required_fields = ["database_url", "mlflow_uri"]
       for field in required_fields:
           if field not in config:
               raise ValueError(f"Missing required field: {field}")
   ```

3. **Use Configuration Files**
   ```yaml
   # config.yaml
   database:
     url: "postgresql://user:pass@host:port/db"
   mlflow:
     tracking_uri: "http://localhost:5000"
   ```

#### **Error Handling**
1. **Implement Retry Logic**
   ```python
   import time
   from functools import wraps
   
   def retry(max_attempts=3, delay=1):
       def decorator(func):
           @wraps(func)
           def wrapper(*args, **kwargs):
               for attempt in range(max_attempts):
                   try:
                       return func(*args, **kwargs)
                   except Exception as e:
                       if attempt == max_attempts - 1:
                           raise e
                       time.sleep(delay)
               return wrapper
           return decorator
   ```

2. **Graceful Degradation**
   ```python
   def process_with_fallback(data):
       try:
           return process_with_mlflow(data)
       except MLflowError:
           logger.warning("MLflow unavailable, processing without tracking")
           return process_without_mlflow(data)
   ```

3. **Comprehensive Logging**
   ```python
   import logging
   
   logger = logging.getLogger(__name__)
   
   def process_data(data):
       logger.info(f"Processing {len(data)} items")
       try:
           result = process_items(data)
           logger.info(f"Successfully processed {len(result)} items")
           return result
       except Exception as e:
           logger.error(f"Processing failed: {e}")
           raise
   ```

## Support Resources

### **Documentation**
- **Architecture**: `docs/architecture.md`
- **Data Quality**: `docs/data-quality.md`
- **API Reference**: `docs/api-reference.md`
- **Pipeline Guide**: `docs/pipeline-guide.md`

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

This comprehensive troubleshooting guide ensures successful pipeline operation and quick resolution of common issues.
