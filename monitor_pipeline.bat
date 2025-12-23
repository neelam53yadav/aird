@echo off
echo ========================================
echo PrimeData Pipeline Monitor
echo ========================================
echo.
echo This will monitor the pipeline execution and MLflow integration.
echo.
echo Please run a pipeline in the PrimeData UI now.
echo.
echo Monitoring Airflow logs for MLflow integration...
echo.

:monitor_loop
echo [%time%] Checking for pipeline activity...
docker-compose -f infra\docker-compose.yml logs airflow-scheduler --tail=5 | findstr -i "mlflow\|primedata_simple\|task.*success\|task.*failed"

timeout /t 10 /nobreak >nul
goto monitor_loop
