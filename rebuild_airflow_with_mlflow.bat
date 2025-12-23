@echo off
echo ========================================
echo Rebuilding Airflow Container with MLflow
echo ========================================
echo.

echo This will rebuild the Airflow Docker container with MLflow support.
echo Make sure Docker is running before proceeding.
echo.
pause

echo Step 1: Stopping existing Airflow containers...
docker-compose -f infra\docker-compose.yml down airflow

echo.
echo Step 2: Rebuilding Airflow container with MLflow...
docker-compose -f infra\docker-compose.yml build airflow

echo.
echo Step 3: Starting Airflow with MLflow support...
docker-compose -f infra\docker-compose.yml up -d airflow

echo.
echo ========================================
echo Airflow Container Rebuilt Successfully!
echo ========================================
echo.
echo The Airflow container now includes MLflow support.
echo You can now run pipelines with MLflow tracking.
echo.
echo Next steps:
echo 1. Check Airflow UI for DAG import errors (should be resolved)
echo 2. Start MLflow server: start_mlflow_server.bat
echo 3. Run a pipeline to test MLflow integration
echo.
pause
