@echo off
echo ========================================
echo PrimeData MLflow Integration Setup
echo ========================================
echo.

echo Step 1: Activating virtual environment...
call .venv\Scripts\activate.bat
echo Virtual environment activated.
echo.

echo Step 2: Installing MLflow...
pip install mlflow
echo MLflow installed successfully.
echo.

echo Step 3: Testing MLflow integration...
python backend\test_mlflow_integration.py
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Start MLflow server: mlflow server --backend-store-uri postgresql://primedata:primedata123@localhost:5432/primedata --default-artifact-root s3://mlflow-artifacts --host 0.0.0.0 --port 5000
echo 2. Start backend server: start_backend.bat
echo 3. Run a pipeline to generate MLflow metrics
echo 4. View metrics in MLflow UI: http://localhost:5000
echo.
pause
