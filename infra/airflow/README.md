# Airflow DAG Architecture - Enterprise Best Practices

## Overview

This directory contains Airflow DAGs following enterprise best practices for modularity, maintainability, and testability.

## Architecture

### Directory Structure

```
infra/airflow/
├── dags/                           # DAG files (orchestration only)
│   └── dag_primedata_simple.py    # Minimal DAG file
├── triggers/                       # Custom trigger modules (if any)
└── README.md                       # This file

backend/src/primedata/ingestion_pipeline/
├── dag_tasks.py                   # Task functions (business logic)
└── aird_stages/                   # AIRD pipeline stages
    ├── preprocess.py
    ├── scoring.py
    ├── fingerprint.py
    └── ...
```

### Key Principles

1. **Separation of Concerns**
   - DAG files contain only orchestration logic (task definitions and dependencies)
   - Business logic resides in `dag_tasks.py` module
   - Reusable components in `aird_stages/`

2. **Modularity**
   - Task functions are standalone and can be tested independently
   - Business logic changes don't require DAG file modifications
   - Easy to add/remove tasks or change dependencies

3. **Testability**
   - Task functions can be unit tested without Airflow
   - Mock Airflow context for testing
   - Integration tests can import and execute task functions directly

## How It Works

### Volume Mounts

The Docker Compose configuration mounts the backend source code:

```yaml
volumes:
  - ../backend/src:/opt/airflow/primedata/src:ro
```

### Python Path

The `PYTHONPATH` environment variable is set:
```yaml
PYTHONPATH: /opt/airflow/primedata/src
```

This allows importing modules like:
```python
from primedata.ingestion_pipeline.dag_tasks import task_preprocess
```

### DAG File (Minimal)

The DAG file (`dag_primedata_simple.py`) only contains:
- DAG definition and configuration
- Task definitions (PythonOperator instances)
- Task dependencies (DAG flow)

**Example:**
```python
from primedata.ingestion_pipeline.dag_tasks import task_preprocess

dag = DAG(...)

preprocess_task = PythonOperator(
    task_id='preprocess',
    python_callable=task_preprocess,
    dag=dag,
)
```

### Task Functions (Business Logic)

Task functions in `dag_tasks.py` contain:
- All business logic
- AIRD stage execution
- Database operations
- Error handling
- XCom communication

**Example:**
```python
def task_preprocess(**context) -> Dict[str, Any]:
    """Preprocess raw data using AIRD PreprocessStage."""
    params = get_dag_params(**context)
    # ... business logic ...
    return result
```

## Benefits

### 1. Maintainability
- **Single Responsibility**: DAG file only orchestrates, tasks handle logic
- **Easy Updates**: Change business logic without touching DAG files
- **Clear Structure**: Developers know where to find code

### 2. Testability
- **Unit Tests**: Test task functions directly with mock context
- **Integration Tests**: Test full pipeline without Airflow
- **Mocking**: Easy to mock dependencies (database, storage, etc.)

### 3. Reusability
- **Shared Functions**: Task functions can be used in multiple DAGs
- **Component Reuse**: AIRD stages are reusable across projects
- **Helper Functions**: Common utilities in `dag_tasks.py`

### 4. Version Control
- **Smaller Diffs**: DAG file changes are minimal
- **Better Reviews**: Business logic changes are separate from orchestration
- **Git History**: Clear separation of concerns in commit history

## Development Workflow

### Adding a New Task

1. **Add task function to `dag_tasks.py`**:
```python
def task_my_new_task(**context) -> Dict[str, Any]:
    """Description of what this task does."""
    params = get_dag_params(**context)
    # ... implementation ...
    return result
```

2. **Import and add to DAG file**:
```python
from primedata.ingestion_pipeline.dag_tasks import task_my_new_task

my_new_task = PythonOperator(
    task_id='my_new_task',
    python_callable=task_my_new_task,
    dag=dag,
)
```

3. **Define dependencies**:
```python
existing_task >> my_new_task >> other_task
```

### Testing Tasks

Test task functions directly:

```python
# test_dag_tasks.py
from unittest.mock import Mock
from primedata.ingestion_pipeline.dag_tasks import task_preprocess

def test_task_preprocess():
    # Mock Airflow context
    context = {
        'dag_run': Mock(conf={'product_id': '...', ...}),
        'task_instance': Mock(),
    }
    
    # Execute task function
    result = task_preprocess(**context)
    
    # Assert results
    assert result['status'] == 'succeeded'
```

## Configuration

### Environment Variables

Required environment variables (set in `docker-compose.yml`):

- `PYTHONPATH`: `/opt/airflow/primedata/src`
- `DATABASE_URL`: PostgreSQL connection string
- `MINIO_HOST`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`: MinIO configuration
- `QDRANT_HOST`, `QDRANT_PORT`: Qdrant configuration

### Volume Mounts

- `../backend/src:/opt/airflow/primedata/src:ro`: Read-only mount of backend source
- `./dags:/opt/airflow/dags:ro`: DAG files

## Best Practices Checklist

- ✅ DAG files are minimal (orchestration only)
- ✅ Business logic in separate modules
- ✅ Task functions are testable
- ✅ Clear separation of concerns
- ✅ Reusable components
- ✅ Proper error handling
- ✅ Logging throughout
- ✅ Type hints on functions
- ✅ Documentation strings

## Troubleshooting

### Import Errors

If you get import errors, verify:
1. Volume mount is correct in `docker-compose.yml`
2. `PYTHONPATH` is set correctly
3. Python package structure is correct (`__init__.py` files exist)

### Task Not Found

If Airflow can't find a task:
1. Check DAG file for correct import
2. Verify task function is exported from `dag_tasks.py`
3. Check Airflow logs for import errors

### Module Not Found

If modules can't be imported:
1. Restart Airflow containers after code changes
2. Verify the volume mount path is correct
3. Check file permissions (read-only mount is OK)

## Migration from Monolithic DAG

If migrating from a monolithic DAG file:

1. Extract task functions to `dag_tasks.py`
2. Keep only orchestration in DAG file
3. Update imports
4. Test each task function independently
5. Update documentation

## References

- [Airflow Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)
- [Python Module Structure](https://docs.python.org/3/tutorial/modules.html)
- [Docker Volume Mounts](https://docs.docker.com/storage/volumes/)


