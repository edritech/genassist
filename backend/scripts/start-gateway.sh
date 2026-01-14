#!/bin/bash

# Gateway Service Startup Script

set -e

echo "Starting Gateway Service..."

# Activate genassist_env
source genassist_env/bin/activate

# Change to gateway directory
cd services/gateway

# Check if an argument was provided
if [ "$1" = "dev" ]; then
    echo "Running in development mode with reload..."
    python -m app.main
elif [ "$1" = "prod" ]; then
    echo "Running in production mode without reload..."
    uvicorn app.main:app --host 0.0.0.0 --port 9000
elif [ "$1" = "uvicorn" ]; then
    echo "Running with uvicorn directly..."
    uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
else
    echo "No mode specified. Defaulting to Python module..."
    python -m app.main
fi