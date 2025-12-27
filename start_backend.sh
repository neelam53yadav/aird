#!/bin/bash

# Start PrimeData Backend Server (macOS/Linux)
echo "Starting PrimeData backend server..."

# Check if virtual environment exists (try .venv first, then venv)
if [ -d ".venv" ]; then
    VENV_PATH=".venv"
elif [ -d "venv" ]; then
    VENV_PATH="venv"
else
    echo "Error: Virtual environment not found. Please create one first:"
    echo "  python -m venv venv"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment from $VENV_PATH..."
source "$VENV_PATH/bin/activate"

if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment"
    exit 1
fi

echo "Virtual environment activated."
echo ""

# Navigate to backend directory
echo "Starting backend server..."
cd backend

# Set PYTHONPATH to include the src directory
export PYTHONPATH="$PWD/src"

# Start the FastAPI server
python -m uvicorn src.primedata.api.app:app --reload --host 0.0.0.0 --port 8000

# If the server stops, print a message
echo ""
echo "Backend server stopped."





