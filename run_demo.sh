#!/usr/bin/env sh
# AEON developmental self-model: one-click hackathon demo (macOS/Linux).
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
"$PY" -m unittest tests.test_aeon_develop
( sleep 1; command -v xdg-open >/dev/null && xdg-open http://127.0.0.1:8770 || open http://127.0.0.1:8770 ) >/dev/null 2>&1 &
exec "$PY" -m aeon_develop serve --port 8770 --tps 20
