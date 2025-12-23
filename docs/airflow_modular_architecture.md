# Airflow Modular Architecture - Implementation Guide

## Summary

This document describes the enterprise-grade modular architecture for Airflow DAGs, where business logic is separated from orchestration.

## Architecture Overview

### ✅ What We've Implemented

1. **Modular Task Functions** (`backend/src/primedata/ingestion_pipeline/dag_tasks.py`)
   - All task functions are in a separate module
   - Each function is standalone and testable
   - Functions can be reused across multiple DAGs

2. **Minimal DAG File** (`infra/airflow/dags/dag_primedata_simple.py`)
   - Only contains orchestration logic
   - Task definitions and dependencies
   - ~100 lines vs ~800+ lines previously

3. **Reusable AIRD Stages** (`backend/src/primedata/ingestion_pipeline/aird_stages/`)
   - Business logic encapsulated in stage classes
   - Used by task functions
   - Fully testable independently

## File Structure

```
backend/src/primedata/ingestion_pipeline/
├── dag_tasks.py              # ✅ Task functions (NEW)
├── aird_stages/              # ✅ AIRD stage implementations
│   ├── preprocess.py
│   ├── scoring.py
│   ├── fingerprint.py
│   └── ...

infra/airflow/dags/
└── dag_primedata_simple.py   # ✅ Minimal DAG file (REFACTORED)
```

## How It Works

### 1. Volume Mounting

Docker Compose mounts the backend source:
```yaml
volumes:
  - ../backend/src:/opt/airflow/primedata/src:ro
```

### 2. Python Path Configuration

Environment variable set:
```yaml
PYTHONPATH: /opt/airflow/primedata/src
```

### 3. Import Path

DAG imports from the mounted module:
```python
from primedata.ingestion_pipeline.dag_tasks import (
    task_preprocess,
    task_scoring,
    ...
)
```

## Benefits Achieved

### ✅ Maintainability
- **Before**: 800+ line monolithic DAG file
- **After**: ~100 line DAG + modular task functions
- Business logic changes don't require DAG file changes

### ✅ Testability
- Task functions can be unit tested independently
- No Airflow dependency for testing business logic
- Easy to mock Airflow context

### ✅ Reusability
- Task functions can be used in multiple DAGs
- AIRD stages are reusable components
- Shared helper functions

### ✅ Version Control
- Smaller, focused commits
- Clear separation in git history
- Easier code reviews

## Configuration

### ✅ No Additional Airflow Config Needed

The existing configuration is sufficient:

1. **Volume Mount** (already configured):
   ```yaml
   - ../backend/src:/opt/airflow/primedata/src:ro
   ```

2. **PYTHONPATH** (already configured):
   ```yaml
   PYTHONPATH: /opt/airflow/primedata/src
   ```

3. **Import Structure** (Python standard):
   ```python
   from primedata.ingestion_pipeline.dag_tasks import task_preprocess
   ```

## Example: Adding a New Task

### Step 1: Add Task Function
```python
# backend/src/primedata/ingestion_pipeline/dag_tasks.py

def task_my_new_task(**context) -> Dict[str, Any]:
    """Description of new task."""
    params = get_dag_params(**context)
    # ... business logic ...
    return result
```

### Step 2: Import and Add to DAG
```python
# infra/airflow/dags/dag_primedata_simple.py

from primedata.ingestion_pipeline.dag_tasks import task_my_new_task

my_new_task = PythonOperator(
    task_id='my_new_task',
    python_callable=task_my_new_task,
    dag=dag,
)
```

### Step 3: Define Dependencies
```python
existing_task >> my_new_task >> other_task
```

## Testing Example

```python
# tests/test_dag_tasks.py

from unittest.mock import Mock, MagicMock
from primedata.ingestion_pipeline.dag_tasks import task_preprocess

def test_task_preprocess():
    # Mock Airflow context
    context = {
        'dag_run': Mock(conf={
            'workspace_id': '550e8400-e29b-41d4-a716-446655440001',
            'product_id': '8ff76148-1871-418e-9eb1-8f89944c44e3',
            'version': 1,
        }),
        'task_instance': Mock(),
    }
    
    # Execute task function
    result = task_preprocess(**context)
    
    # Assert results
    assert result['status'] in ['succeeded', 'skipped']
```

## Migration Completed

### ✅ What Changed

1. **Created** `backend/src/primedata/ingestion_pipeline/dag_tasks.py`
   - All task functions moved here
   - Helper functions (get_dag_params, get_aird_context) included
   - Proper error handling and logging

2. **Refactored** `infra/airflow/dags/dag_primedata_simple.py`
   - Reduced from ~800 lines to ~100 lines
   - Only orchestration logic remains
   - Clean imports from dag_tasks module

3. **No Changes Needed** to:
   - Docker Compose configuration
   - Airflow configuration
   - AIRD stages
   - Volume mounts

## Verification

### ✅ How to Verify It Works

1. **Check Imports**:
   ```bash
   docker exec primedata-airflow-scheduler python -c \
     "from primedata.ingestion_pipeline.dag_tasks import task_preprocess; print('OK')"
   ```

2. **Check DAG Loading**:
   - Open Airflow UI: http://localhost:8080
   - Verify DAG appears and can be parsed
   - Check for any import errors in logs

3. **Test Task Execution**:
   - Trigger a test DAG run
   - Verify tasks execute correctly
   - Check logs for any errors

## Best Practices Followed

- ✅ **Separation of Concerns**: DAG orchestration vs business logic
- ✅ **Single Responsibility**: Each module has one clear purpose
- ✅ **DRY Principle**: Reusable functions and stages
- ✅ **Testability**: Functions can be tested independently
- ✅ **Documentation**: Clear docstrings and README
- ✅ **Type Hints**: Function signatures include types
- ✅ **Error Handling**: Proper exception handling throughout

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'primedata'`

**Solution**:
1. Verify volume mount: `../backend/src:/opt/airflow/primedata/src:ro`
2. Check PYTHONPATH: `/opt/airflow/primedata/src`
3. Restart Airflow containers after code changes

### Task Not Found

**Problem**: Task doesn't appear in Airflow UI

**Solution**:
1. Check DAG file imports task function correctly
2. Verify task function is defined in `dag_tasks.py`
3. Check Airflow scheduler logs for errors

### Code Changes Not Reflecting

**Problem**: Code changes not picked up by Airflow

**Solution**:
1. Restart Airflow scheduler: `docker-compose restart airflow-scheduler`
2. Verify volume mount is not read-only (it is, but that's OK - restart needed)
3. Check file permissions

## Conclusion

✅ **Modular architecture successfully implemented**

- DAG files are minimal and focused on orchestration
- Business logic is in reusable, testable modules
- No additional Airflow configuration required
- Follows enterprise best practices
- Easy to extend and maintain


