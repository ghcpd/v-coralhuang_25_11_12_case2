#!/usr/bin/env bash
set -e
ROOT=$(dirname "$0")
ART=${ROOT}/artifacts
mkdir -p "$ART"

# start server
if command -v python3 &>/dev/null; then
  nohup python3 -m http.server 8080 > "$ART/html_server.log" 2>&1 &
  SERVER_PID=$!
  echo "server started (pid=$SERVER_PID)"
else
  echo "python3 not found"
  exit 2
fi

# Allow server to start
sleep 1

# run tests
echo "Running tests..."
python3 "$ROOT/test_validator.py"
TEST_EXIT=$?

# collect logs
echo "Logs and screenshots saved under $ART"
exit $TEST_EXIT
