#!/usr/bin/env bash
# One command: rule tests, API tests, rules report, and the two-browser
# Playwright end-to-end meeting sync test, all against seed data and a fixed clock.
set -e
cd "$(dirname "$0")/.."

if [ -x "./.venv/Scripts/python.exe" ]; then
  PY="./.venv/Scripts/python.exe"          # Windows virtualenv
elif [ -x "./.venv/bin/python" ]; then
  PY="./.venv/bin/python"                  # POSIX virtualenv
else
  PY="${PYTHON:-python}"
fi

exec "$PY" scripts/test_all.py "$@"
