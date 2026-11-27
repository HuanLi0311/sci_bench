#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json /logs/verifier/metrics.json
Xvfb :0 -screen 0 1600x1000x24 -ac >/tmp/xvfb.log 2>&1 &
XVFB_PID=$!
trap 'kill "$XVFB_PID" 2>/dev/null || true' EXIT
sleep 1
# Fixture/driver errors propagate without writing a candidate reward.
python3 /tests/grade.py
