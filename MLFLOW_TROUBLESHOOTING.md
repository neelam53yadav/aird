# MLflow Integration Troubleshooting Guide

## 🚨 Common Issues and Solutions

### 1. Airflow DAG Import Errors

#### **Error**: `ModuleNotFoundError: No module named 'mlflow'`
**Solution**: 
```bash
# Rebuild Airflow container with MLflow
rebuild_airflow_with_mlflow.bat
```

#### **Error**: `NameError: name 'logger' is not defined`
**Solution**: Fixed in the latest DAG code - logger is now defined before MLflow import.

### 2. MLflow Server Connection Issues

#### **Error**: `Connection refused` when accessing MLflow UI
**Solutions**:
1. **Start MLflow Server**:
   ```bash
   start_mlflow_server.bat
   ```

2. **Check Environment Variables**:
   ```bash
   set MLFLOW_TRACKING_URI=http://localhost:5000
   set MLFLOW_BACKEND_STORE_URI=postgresql://primedata:primedata123@localhost:5432/primedata
   set MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://mlflow-artifacts
   ```

3. **Verify PostgreSQL Connection**:
   - Ensure PostgreSQL is running
   - Check database credentials
   - Verify database exists

### 3. Pipeline Metrics Issues

#### **Issue**: Processing time showing as 0 seconds
**Solution**: Fixed in latest backend - processing time is now calculated from pipeline start/end times.

#### **Issue**: Vector count showing as 0 despite successful indexing
**Solution**: Enhanced indexing task MLflow logging - now properly tracks vector counts and indexing performance.

#### **Issue**: Incomplete pipeline timing in metrics
**Solution**: Improved metrics aggregation to include all task timings (chunking, embedding, indexing).

### 4. Metrics Verification

#### **How to Verify Metrics Accuracy**:
1. **Check API Response**:
   ```bash
   curl http://localhost:8000/api/v1/products/{product_id}/mlflow-metrics
   ```

2. **Verify Processing Time**:
   - Should show actual seconds (not 0)
   - Calculated from pipeline start to end time

3. **Check Vector Count**:
   - Should match actual vectors in Qdrant
   - Verify in MLflow UI: http://localhost:5000

4. **Cross-reference with Airflow Logs**:
   ```bash
   docker-compose -f infra/docker-compose.yml logs airflow-scheduler
   ```

### 5. Virtual Environment Issues

#### **Error**: `The term 'alembic' is not recognized`
**Solution**:
```bash
# Activate virtual environment first
activate_venv.bat
# Then run commands
```

#### **Error**: `No module named 'primedata'`
**Solution**:
```bash
# Make sure you're in the project root directory
cd D:\projects\enterprise\PrimeData
# Activate virtual environment
activate_venv.bat
```

### 4. Pipeline Execution Issues

#### **Error**: MLflow metrics not appearing
**Solutions**:
1. **Check MLflow Server**: Ensure it's running on port 5000
2. **Verify Environment Variables**: Set in both backend and Airflow
3. **Check Logs**: Look for MLflow-related warnings in pipeline logs
4. **Test Connection**: Run `test_mlflow.bat`

### 5. UI Integration Issues

#### **Error**: "No Pipeline Metrics" shown in UI
**Solutions**:
1. **Run a Pipeline**: Execute at least one pipeline run
2. **Check Backend Logs**: Look for MLflow API errors
3. **Verify Database**: Ensure pipeline runs are recorded
4. **Check MLflow Data**: Verify experiments exist in MLflow UI

## 🔧 Step-by-Step Recovery

### Complete Reset and Setup

1. **Stop All Services**:
   ```bash
   docker-compose -f infra\docker-compose.yml down
   ```

2. **Rebuild Airflow with MLflow**:
   ```bash
   rebuild_airflow_with_mlflow.bat
   ```

3. **Start All Services**:
   ```bash
   docker-compose -f infra\docker-compose.yml up -d
   ```

4. **Start MLflow Server**:
   ```bash
   start_mlflow_server.bat
   ```

5. **Test Integration**:
   ```bash
   test_mlflow.bat
   ```

6. **Run Test Pipeline**:
   - Go to PrimeData UI
   - Create/select a product
   - Run pipeline
   - Check MLflow UI for results

## 📊 Verification Checklist

### ✅ Airflow DAG
- [ ] DAG imports without errors
- [ ] MLflow client imports successfully
- [ ] No `NameError` or `ModuleNotFoundError`

### ✅ MLflow Server
- [ ] Server starts without errors
- [ ] Accessible at `http://localhost:5000`
- [ ] PostgreSQL backend connected
- [ ] Artifact storage configured

### ✅ Backend API
- [ ] MLflow endpoints respond
- [ ] No import errors in logs
- [ ] Environment variables set

### ✅ Pipeline Execution
- [ ] Pipeline runs successfully
- [ ] MLflow metrics logged
- [ ] Artifacts stored
- [ ] No MLflow-related errors in logs

### ✅ UI Integration
- [ ] Pipeline metrics display
- [ ] MLflow UI link works
- [ ] No API errors in browser console

## 🆘 Emergency Fallback

If MLflow integration continues to fail:

1. **Disable MLflow Temporarily**:
   ```python
   # In DAG file, set:
   MLFLOW_AVAILABLE = False
   ```

2. **Run Pipeline Without Tracking**:
   - Pipeline will work normally
   - No MLflow metrics will be logged
   - All other functionality preserved

3. **Re-enable Later**:
   - Fix MLflow issues
   - Set `MLFLOW_AVAILABLE = True`
   - Restart services

## 📞 Getting Help

If issues persist:

1. **Check Logs**:
   - Airflow logs: `docker-compose logs airflow`
   - Backend logs: Check console output
   - MLflow logs: Check MLflow server console

2. **Verify Environment**:
   - Docker containers running
   - Virtual environment activated
   - All services accessible

3. **Test Components Individually**:
   - Test MLflow server separately
   - Test backend API endpoints
   - Test Airflow DAG import

## 🔄 Quick Commands Reference

```bash
# Activate virtual environment
activate_venv.bat

# Install MLflow
install_mlflow.bat

# Test MLflow integration
test_mlflow.bat

# Start MLflow server
start_mlflow_server.bat

# Start backend server
start_backend.bat

# Rebuild Airflow with MLflow
rebuild_airflow_with_mlflow.bat

# Complete setup
setup_mlflow.bat
```
