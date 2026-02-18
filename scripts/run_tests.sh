#!/usr/bin/env bash
# run_tests.sh — Run the full test suite with coverage.
# Usage: ./scripts/run_tests.sh [--fast]

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV="$ROOT_DIR/.venv"
if [ -d "$VENV" ]; then
  source "$VENV/bin/activate"
fi

echo "==> Running GitSage tests"

if [ "${1:-}" = "--fast" ]; then
  # Skip coverage for quick iteration
  python -m pytest tests/ -v -x
else
  python -m pytest tests/ -v \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-fail-under=70
  echo ""
  echo "Coverage report: htmlcov/index.html"
fi