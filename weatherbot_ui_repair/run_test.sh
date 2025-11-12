#!/usr/bin/env bash
# Cross-platform runner for Linux/macOS
set -e
ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
cd "$ROOT_DIR"

# Start server according to available python
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python not found"
  exit 1
fi

# Start HTTP server in background
$PY -m http.server 8080 &
PID=$!
trap "echo 'Stopping server' ; kill $PID 2>/dev/null || true" EXIT

# Wait for server to be ready
for i in {1..10}; do
  if curl -s --head http://localhost:8080 | grep "200 OK" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

START=$(date +%s)
# Run the python test validator
if command -v python3 >/dev/null 2>&1; then
  python3 test_validator.py
else
  python test_validator.py
fi
STATUS=$?
END=$(date +%s)
mkdir -p artifacts
python - <<PY
import json
print('Writing artifacts/agent_runtime.txt')
open('artifacts/agent_runtime.txt','w').write('start:%s\nend:%s\n' % ($START,$END))
PY

exit $STATUS
