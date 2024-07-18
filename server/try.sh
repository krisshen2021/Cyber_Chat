#!/bin/bash
# Source the virtual environment
source ../venv/bin/activate

# Start the FastAPI service in the background
python sd_progress.py &

# Store the PID of the FastAPI service
FASTAPI_PID=$!

# Run the client application
python sd_client.py

# Trap the exit signal to clean up
trap 'kill $FASTAPI_PID; deactivate' EXIT

# Wait for the FastAPI service to finish
wait $FASTAPI_PID

deactivate
