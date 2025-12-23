@echo off
echo Installing MLflow in PrimeData virtual environment...
call .venv\Scripts\activate.bat
echo Virtual environment activated.
echo.
echo Installing MLflow...
pip install mlflow
echo.
echo MLflow installation complete!
echo.
echo You can now test the MLflow integration by running:
echo python backend\test_mlflow_integration.py
echo.
pause
