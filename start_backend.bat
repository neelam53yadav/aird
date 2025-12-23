@echo off
echo Starting PrimeData backend server...
call .venv\Scripts\activate.bat
echo Virtual environment activated.
echo.
echo Starting backend server...
cd backend
set PYTHONPATH=%CD%\src
python -m uvicorn src.primedata.api.app:app --reload --host 0.0.0.0 --port 8000
echo.
echo Backend server stopped.
pause
