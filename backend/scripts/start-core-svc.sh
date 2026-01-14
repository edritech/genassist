#!/bin/bash

# WebSocket Service Startup Script

set -e

echo "Starting Core Service..."

# Activate genassist_env
source genassist_env/bin/activate

# Change to core directory
cd services/core

# Check if an argument was provided
if [ "$1" = "dev" ]; then
    echo "Running in development mode with reload..."
    python run.py
elif [ "$1" = "prod" ]; then
    echo "Running in production mode without reload..."
    uvicorn run.py --host 0.0.0.0 --port 8000
elif [ "$1" = "uvicorn" ]; then
    echo "Running with uvicorn directly..."
    uvicorn run.py --host 0.0.0.0 --port 8000 --reload
else
    echo "No mode specified. Defaulting to Python module..."
    python run.py
fi