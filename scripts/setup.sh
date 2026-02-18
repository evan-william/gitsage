#!/usr/bin/env bash
# setup.sh — Install dependencies and start GitSage.
# Usage: ./scripts/setup.sh [--dev]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "==> GitSage setup"

# Check Python version
PYTHON=$(command -v python3 || command -v python)
PYTHON_VERSION=$("$PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED="3.11"

if ! "$PYTHON" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
  echo "ERROR: Python $REQUIRED+ required (found $PYTHON_VERSION)."
  exit 1
fi

echo "    Python $PYTHON_VERSION — OK"

# Check git
if ! command -v git &>/dev/null; then
  echo "ERROR: git is not installed."
  exit 1
fi

echo "    git $(git --version | awk '{print $3}') — OK"

# Create venv if missing
VENV="$ROOT_DIR/.venv"
if [ ! -d "$VENV" ]; then
  echo "==> Creating virtual environment..."
  "$PYTHON" -m venv "$VENV"
fi

# Activate
source "$VENV/bin/activate"

echo "==> Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "$ROOT_DIR/requirements.txt"

# Copy .env.example if .env is missing
if [ ! -f "$ROOT_DIR/.env" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo ""
  echo "  NOTE: A default .env file was created."
  echo "  Add your GEMINI_API_KEY to $ROOT_DIR/.env to enable AI features."
  echo ""
fi

if [ "${1:-}" = "--dev" ]; then
  echo "==> Starting in development mode..."
  export DEBUG=true
  exec uvicorn main:app --host 127.0.0.1 --port 8000 --reload
else
  echo "==> Starting GitSage at http://localhost:8000"
  exec uvicorn main:app --host 127.0.0.1 --port 8000
fi