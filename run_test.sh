#!/bin/bash

# Chat UI Test Runner - Linux/macOS
# Auto-detects OS and runs complete validation suite

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PORT=8080
LOG_DIR="$SCRIPT_DIR/artifacts"
SERVER_LOG="$LOG_DIR/server.log"
TEST_REPORT="$LOG_DIR/test-report.json"

# Create artifacts directory
mkdir -p "$LOG_DIR"

echo "================================"
echo "Chat UI Validator - Test Suite"
echo "================================"
echo "OS: $(uname -s)"
echo "Script directory: $SCRIPT_DIR"
echo ""

# Step 1: Check dependencies
echo "[1/4] Checking dependencies..."

if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "  ✓ Python $PYTHON_VERSION found"

# Step 2: Install requirements
echo "[2/4] Installing Python dependencies..."

if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    python3 -m venv "$SCRIPT_DIR/.venv"
fi

source "$SCRIPT_DIR/.venv/bin/activate"
pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo "  ✓ Dependencies installed"

# Step 3: Start HTTP server
echo "[3/4] Starting HTTP server on port $PORT..."

# Kill any existing server on this port
pkill -f "http.server $PORT" 2>/dev/null || true
sleep 1

# Start new server
cd "$SCRIPT_DIR"
nohup python3 -m http.server $PORT > "$SERVER_LOG" 2>&1 &
SERVER_PID=$!

# Wait for server to start
sleep 2

if ! ps -p $SERVER_PID > /dev/null 2>&1; then
    echo "ERROR: Failed to start HTTP server"
    cat "$SERVER_LOG"
    exit 1
fi

echo "  ✓ Server started (PID: $SERVER_PID)"

# Step 4: Run tests
echo "[4/4] Running validation tests..."
echo ""

python3 "$SCRIPT_DIR/test_validator.py"
TEST_EXIT_CODE=$?

# Cleanup
echo ""
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

# Print results
echo ""
echo "================================"
if [ -f "$TEST_REPORT" ]; then
    echo "Test Report: $TEST_REPORT"
    echo "Server Log: $SERVER_LOG"
fi

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ ALL TESTS PASSED"
else
    echo "✗ SOME TESTS FAILED"
fi

exit $TEST_EXIT_CODE
