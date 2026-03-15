#!/usr/bin/env bash
# ============================================================
# FinSight — Development Environment Setup
# Usage: bash scripts/setup.sh
# ============================================================
set -euo pipefail

PYTHON=${PYTHON:-python3.11}
VENV_DIR=".venv"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║      FinSight  ·  Dev Setup          ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Check Python version ──────────────────────────────────────
echo "▶ Checking Python version…"
$PYTHON --version || { echo "ERROR: $PYTHON not found"; exit 1; }

# ── Virtual environment ───────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "▶ Creating virtual environment at $VENV_DIR…"
    $PYTHON -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
echo "▶ Activated: $VIRTUAL_ENV"

# ── Upgrade pip ───────────────────────────────────────────────
pip install --upgrade pip setuptools wheel -q

# ── Install dependencies ──────────────────────────────────────
echo "▶ Installing dependencies…"
pip install -r requirements.txt -q

# ── Env file ─────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "▶ Created .env from .env.example — add your ANTHROPIC_API_KEY"
fi

# ── Data directories ──────────────────────────────────────────
mkdir -p data/documents data/faiss_index

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Add your ANTHROPIC_API_KEY to .env"
echo "  2. Activate the venv:  source .venv/bin/activate"
echo "  3. Run the app:        streamlit run app/Home.py"
echo "  4. Run tests:          pytest"
echo ""
