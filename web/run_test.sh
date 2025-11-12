#!/usr/bin/env bash
set -e
ROOTDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOTDIR"
mkdir -p artifacts
LOGFILE=artifacts/html_server.log
# Start server
if command -v python3 >/dev/null 2>&1; then
  echo "Starting Python3 server on 8080..." | tee "$LOGFILE"
  nohup python3 -m http.server 8080 > "$LOGFILE" 2>&1 &
  SERVER_PID=$!
else
  echo "python3 not found" | tee -a "$LOGFILE"
  exit 1
fi
# Give server time to start
sleep 2
# Run validator
echo "Running validator..." | tee -a "$LOGFILE"
python3 test_validator.py 2>&1 | tee -a "$LOGFILE"
RES=$?
if [ $RES -eq 0 ]; then
  echo "Validation passed" | tee -a "$LOGFILE"
else
  echo "Validation failed" | tee -a "$LOGFILE"
fi
# Collect small log snapshot
echo "Server PID: $SERVER_PID" >> "$LOGFILE"
kill "$SERVER_PID" || true
exit $RES
