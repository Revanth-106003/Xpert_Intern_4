#!/usr/bin/env bash
# AI Test Case Generator Agent - Linux / macOS launcher
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "  ====================================================="
echo "    AI Test Case Generator Agent - Linux/macOS launcher"
echo "  ====================================================="
echo

# 1. Locate Python 3.10+
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
    PY="$c"; break
  fi
done
if [ ! -x ".venv/bin/python" ]; then
  if [ -z "$PY" ]; then
    echo "  [ERROR] Python 3.10+ not found. Install it (e.g. sudo apt install python3 python3-venv)."; exit 1
  fi
  echo "  [1/4] Creating virtual environment with $PY ..."
  "$PY" -m venv .venv || { echo "  [ERROR] venv creation failed. On Debian/Ubuntu: sudo apt install python3-venv"; exit 1; }
fi
VPY=".venv/bin/python"

# 2. Dependencies (re-installed only when requirements.txt changes)
STAMP=".venv/.requirements.installed"
if [ -f "$STAMP" ] && cmp -s requirements.txt "$STAMP"; then
  echo "  [2/4] Dependencies already installed."
else
  echo "  [2/4] Installing dependencies - first run can take a few minutes ..."
  "$VPY" -m pip install --upgrade pip --quiet --disable-pip-version-check
  "$VPY" -m pip install -r requirements.txt --quiet --disable-pip-version-check
  cp requirements.txt "$STAMP"
fi

# 3. Environment file
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "  [3/4] Created .env from .env.example - add GEMINI_API_KEY there if you use Gemini."
else
  echo "  [3/4] Using existing .env configuration."
fi

# 4. Pre-flight checks and launch
echo "  [4/4] Running pre-flight checks ..."
"$VPY" setup_check.py
echo "  Starting the application at http://localhost:8501  (Ctrl+C to stop)"
exec "$VPY" -m streamlit run app.py --server.headless false --server.port 8501
