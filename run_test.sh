#!/usr/bin/env bash
# One-click test for Linux/macOS
set -e
START=$(date +%s)
ART_DIR=artifacts
mkdir -p "$ART_DIR"
PY=python3
# choose python executable
if ! command -v $PY >/dev/null 2>&1; then
  PY=python
fi
PORT=8080
# Start server in background
$PY -m http.server $PORT >/dev/null 2>&1 &
SERVER_PID=$!
trap "kill $SERVER_PID 2>/dev/null || true" EXIT
# wait for server
echo "Waiting for http://localhost:$PORT"
for i in {1..30}; do
  if $PY -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:$PORT/ui_fixed.html').read()" >/dev/null 2>&1; then
    echo "Server ready"
    break
  fi
  sleep 0.5
done
# Run validator
if $PY test_validator.py; then
  echo 'All checks passed'
  STATUS=0
else
  echo 'Checks failed'
  STATUS=1
fi
# write runtime
END=$(date +%s)
echo "{\"start\":$START, \"end\":$END, \"duration\":$((END-START))}" > "$ART_DIR/agent_runtime.txt"
# ensure we keep the exit code
exit $STATUS
