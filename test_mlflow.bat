@echo off
echo Testing MLflow integration...
call .venv\Scripts\activate.bat
echo Virtual environment activated.
echo.
echo Running MLflow integration test...
python backend\test_mlflow_integration.py
echo.
echo Test completed!
pause
