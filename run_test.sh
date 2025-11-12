#!/bin/bash

# Chat UI Test Runner for Linux/macOS
# Auto-detects OS and starts local server, runs validation, and generates report

set -e

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "darwin"* ]]; then
    echo "[OS] Linux/macOS detected: $OSTYPE"
else
    echo "[ERROR] This script is for Linux/macOS. Use run_test.bat on Windows."
    exit 1
fi

# Create artifacts directory
mkdir -p artifacts

# Write start timestamp
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "Start time: $START_TIME" > artifacts/agent_runtime.txt

# Detect Python executable
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python not found. Please install Python 3."
    exit 1
fi

echo "[Python] Using: $PYTHON_CMD"
$PYTHON_CMD --version

# Install requirements
echo "[Setup] Installing dependencies..."
$PYTHON_CMD -m pip install -q -r requirements.txt 2>&1 | head -20 || true

# Start HTTP server in background
echo "[Server] Starting HTTP server on port 8080..."
PORT=8080

# Choose http.server command
if command -v python3 &> /dev/null; then
    HTTP_CMD="python3 -m http.server $PORT"
else
    HTTP_CMD="python -m http.server $PORT"
fi

$HTTP_CMD > /tmp/server.log 2>&1 &
SERVER_PID=$!
echo "[Server] PID: $SERVER_PID"

# Wait for server to be ready
echo "[Server] Waiting for server to be reachable on http://localhost:$PORT..."
MAX_WAIT=30
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -s "http://localhost:$PORT/ui_fixed.html" > /dev/null 2>&1; then
        echo "[Server] ✓ Server is ready"
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "[ERROR] Server did not become reachable after $MAX_WAIT seconds"
    kill $SERVER_PID 2>/dev/null || true
    exit 1
fi

# Run validator
echo "[Validator] Running test_validator.py..."
if $PYTHON_CMD test_validator.py; then
    TEST_RESULT=0
    echo "[Validator] ✓ All validations passed"
else
    TEST_RESULT=1
    echo "[Validator] ✗ Validations failed"
fi

# Write end timestamp
END_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "End time: $END_TIME" >> artifacts/agent_runtime.txt

# Kill server
kill $SERVER_PID 2>/dev/null || true
sleep 1
echo "[Server] Stopped"

# Exit with test result
exit $TEST_RESULT
