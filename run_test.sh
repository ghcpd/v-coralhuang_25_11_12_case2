#!/bin/bash
# Test runner for Linux/macOS
# Detects OS and runs validation tests

set -e

START_TIME=$(date +%s)
START_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "=========================================="
echo "Chat UI Test Runner (Linux/macOS)"
echo "Start time: $START_TIMESTAMP"
echo "=========================================="

# Detect OS
OS_TYPE=$(uname -s)
echo "Detected OS: $OS_TYPE"

# Create artifacts directory
mkdir -p artifacts/screenshots

# Find Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python not found. Please install Python 3."
    exit 1
fi

echo "Using Python: $PYTHON_CMD"

# Check if Playwright browsers are installed
echo "Checking Playwright installation..."
$PYTHON_CMD -c "import playwright" 2>/dev/null || {
    echo "ERROR: Playwright not installed. Run: pip install -r requirements.txt && playwright install chromium"
    exit 1
}

# Start HTTP server in background
echo "Starting HTTP server on port 8080..."
$PYTHON_CMD -m http.server 8080 > artifacts/server.log 2>&1 &
SERVER_PID=$!

# Function to cleanup on exit
cleanup() {
    echo "Stopping HTTP server (PID: $SERVER_PID)..."
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
}

trap cleanup EXIT

# Wait for server to be ready
echo "Waiting for server to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8080/ui_fixed.html > /dev/null 2>&1; then
        echo "Server is ready!"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "ERROR: Server failed to start after $MAX_RETRIES seconds"
    exit 1
fi

# Run validator
echo ""
echo "Running test validator..."
$PYTHON_CMD test_validator.py
VALIDATOR_EXIT=$?

# Record end time
END_TIME=$(date +%s)
END_TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DURATION=$((END_TIME - START_TIME))

# Write runtime info
cat > artifacts/agent_runtime.txt << EOF
Start: $START_TIMESTAMP
End: $END_TIMESTAMP
Duration: ${DURATION}s
OS: $OS_TYPE
Python: $PYTHON_CMD
Exit Code: $VALIDATOR_EXIT
EOF

# Print final summary
echo ""
echo "=========================================="
echo "Test Run Complete"
echo "Duration: ${DURATION}s"
echo "Exit Code: $VALIDATOR_EXIT"
echo "=========================================="

# Exit with validator exit code
exit $VALIDATOR_EXIT

