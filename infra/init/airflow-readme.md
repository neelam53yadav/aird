# Airflow Setup

## Overview

Airflow is configured with LocalExecutor for development. The webserver runs on port 8080 and the scheduler runs as a separate container.

## Access

- **Web UI**: http://localhost:8080
- **Username**: admin (default)
- **Password**: admin (default)

## DAGs

DAGs are mounted from `infra/airflow/dags/` directory. Create your DAGs there and they will be automatically loaded.

## Configuration

Key configuration settings:
- **Executor**: LocalExecutor (single machine)
- **Database**: PostgreSQL (shared with other services)
- **DAGs**: Paused at creation by default
- **Examples**: Disabled for clean setup

## Development

1. Create DAGs in `infra/airflow/dags/`
2. Access the web UI to monitor and trigger DAGs
3. Check logs in the Airflow UI or container logs

## Production Notes

For production deployment:
- Use CeleryExecutor or KubernetesExecutor
- Set up proper authentication
- Configure email notifications
- Use external database
- Set up monitoring and alerting
