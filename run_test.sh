#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
ARTIFACTS="$ROOT/artifacts"
mkdir -p "$ARTIFACTS"

if [[ "$(uname)" == "Darwin" || "$(uname)" == "Linux" ]]; then
  PY=python3
else
  PY=python
fi

# Start server
nohup $PY -m http.server 8080 > "$ARTIFACTS/html_server.log" 2>&1 &
SERVER_PID=$!
sleep 1

# Run validator
$PY test_validator.py > "$ARTIFACTS/validator.log" 2>&1 || VAL_RC=$?

# save server logs
kill $SERVER_PID || true

# show summary
echo "Validator exit code: ${VAL_RC:-0}"
cat "$ARTIFACTS/test-report.json" || true

exit ${VAL_RC:-0}
