# MLflow Setup

## Overview

MLflow is configured to use PostgreSQL as the backend store and MinIO for artifact storage.

## Access

- **Web UI**: http://localhost:5000
- **API**: http://localhost:5000/api

## Configuration

- **Backend Store**: PostgreSQL (shared with other services)
- **Artifact Store**: MinIO S3-compatible storage
- **Tracking URI**: http://localhost:5000

## Usage

### Python Client

```python
import mlflow

# Set tracking URI
mlflow.set_tracking_uri("http://localhost:5000")

# Start experiment
with mlflow.start_run():
    mlflow.log_param("param1", 5)
    mlflow.log_metric("metric1", 0.85)
    mlflow.log_artifact("model.pkl")
```

### Environment Variables

The following environment variables are configured:
- `MLFLOW_BACKEND_STORE_URI`: PostgreSQL connection
- `MLFLOW_DEFAULT_ARTIFACT_ROOT`: MinIO S3 bucket
- `AWS_ACCESS_KEY_ID`: MinIO access key
- `AWS_SECRET_ACCESS_KEY`: MinIO secret key
- `MLFLOW_S3_ENDPOINT_URL`: MinIO endpoint

## Development

1. Access the web UI to view experiments
2. Use the MLflow Python API in your code
3. Artifacts are stored in MinIO and accessible via the UI

## Production Notes

For production deployment:
- Use external PostgreSQL instance
- Configure S3-compatible storage (AWS S3, etc.)
- Set up authentication and authorization
- Configure monitoring and alerting
- Use MLflow Model Registry for model management
