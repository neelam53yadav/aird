# Infrastructure Initialization

This directory contains initialization scripts and documentation for PrimeData services.

## Files

- `minio-buckets.sh` - Creates required MinIO buckets
- `airflow-readme.md` - Airflow setup and configuration guide
- `mlflow-init.md` - MLflow setup and configuration guide

## Services

### MinIO
- **Console**: http://localhost:9001
- **API**: http://localhost:9000
- **Buckets**: Automatically created on startup

### Airflow
- **Web UI**: http://localhost:8080
- **Default credentials**: admin/admin

### MLflow
- **Web UI**: http://localhost:5000
- **Backend**: PostgreSQL
- **Artifacts**: MinIO

## Setup

1. Copy environment files from `env/` directory
2. Start services with `docker compose up -d`
3. Access service UIs using the URLs above
4. Check service health and logs as needed

## Development

- All services are configured for local development
- Data persists in Docker volumes
- Health checks ensure services are ready before dependencies start
