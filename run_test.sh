#!/bin/bash
# Test runner for Linux/macOS
# Auto-detects OS and runs appropriate commands

set -e  # Exit on error

echo "=========================================="
echo "Chat UI Test Runner (Linux/macOS)"
echo "=========================================="

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS_TYPE="Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macOS"
else
    OS_TYPE="Unknown"
fi

echo "Detected OS: $OS_TYPE"
echo ""

# Create artifacts directory
mkdir -p artifacts

# Check for Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"
echo ""

# Check if server is already running on port 8080
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "Port 8080 already in use, attempting to use existing server..."
    SERVER_PID=""
else
    echo "Starting HTTP server on port 8080..."
    $PYTHON_CMD -m http.server 8080 > artifacts/server.log 2>&1 &
    SERVER_PID=$!
    echo "Server started with PID: $SERVER_PID"
    sleep 2  # Wait for server to start
fi

# Install dependencies if needed
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "Installing dependencies..."
    $PYTHON_CMD -m pip install --user -q beautifulsoup4 html5lib playwright
    $PYTHON_CMD -m playwright install chromium 2>&1 | tee artifacts/playwright-install.log || true
fi

# Run tests
echo ""
echo "Running tests..."
echo ""

$PYTHON_CMD test_validator.py 2>&1 | tee artifacts/test-output.log
TEST_EXIT_CODE=${PIPESTATUS[0]}

# Stop server if we started it
if [ ! -z "$SERVER_PID" ]; then
    echo ""
    echo "Stopping server (PID: $SERVER_PID)..."
    kill $SERVER_PID 2>/dev/null || true
fi

# Print summary
echo ""
echo "=========================================="
echo "Test execution complete"
echo "=========================================="
echo "Logs saved to artifacts/"
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed!"
    exit 0
else
    echo "✗ Some tests failed. Check artifacts/test-report.json for details."
    exit 1
fi

