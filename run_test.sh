#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

START_TS=$(date +%s)
mkdir -p artifacts

# Choose Python command
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python not found"
  exit 1
fi

# Install playwright browsers if needed
$PY -m pip install -r requirements.txt --user --upgrade
$PY -m playwright install >/dev/null 2>&1 || true

# Start server
# Try python -m http.server
if [ "$PY" = "python" ]; then
  $PY -m http.server 8080 >/dev/null 2>&1 &
  SERVER_PID=$!
else
  $PY -m http.server 8080 >/dev/null 2>&1 &
  SERVER_PID=$!
fi

# Wait for server
for i in {1..20}; do
  if curl -sSf http://localhost:8080/ui_fixed.html >/dev/null 2>&1; then
    echo "Server is up"
    break
  fi
  sleep 0.5
done

if ! curl -sSf http://localhost:8080/ui_fixed.html >/dev/null 2>&1; then
  echo "Server didn't start"
  kill $SERVER_PID || true
  exit 1
fi

# Run validator
$PY test_validator.py
STATUS=$?

END_TS=$(date +%s)

echo "start_ts=$START_TS" > artifacts/run_test_env.txt
echo "end_ts=$END_TS" >> artifacts/run_test_env.txt

# Stop server
kill $SERVER_PID || true

exit $STATUS
