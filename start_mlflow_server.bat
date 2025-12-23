@echo off
echo Starting MLflow server...
call .venv\Scripts\activate.bat
echo Virtual environment activated.
echo.

echo Setting environment variables...
set MLFLOW_BACKEND_STORE_URI=postgresql://primedata:primedata123@localhost:5432/primedata
set MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://mlflow-artifacts
set MLFLOW_TRACKING_URI=http://localhost:5000

echo Starting MLflow server on http://localhost:5000...
mlflow server --backend-store-uri %MLFLOW_BACKEND_STORE_URI% --default-artifact-root %MLFLOW_DEFAULT_ARTIFACT_ROOT% --host 0.0.0.0 --port 5000

echo.
echo MLflow server stopped.
pause
