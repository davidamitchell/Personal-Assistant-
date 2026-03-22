#!/usr/bin/env bash
# setup.sh – one-time environment setup for the Research Assistant.
#
# Run this after cloning (or opening a new Codespace):
#
#   bash setup.sh
#
# What it does
# ------------
# 1. Initialises git submodules (Research notes + Skills library)
# 2. Installs Python dependencies into a virtual environment
# 3. Initialises the SQLite database schema
# 4. Builds the semantic search index from the research notes
#    (downloads the embedding model on first run – ~80 MB)
#
# After setup, start the app with:
#
#   source .venv/bin/activate
#   python app/main.py
#
# Or in dev-bypass mode (no Apple credentials needed):
#
#   DEV_AUTH_BYPASS=1 python app/main.py

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "──────────────────────────────────────────────────"
echo " Research Assistant – setup"
echo "──────────────────────────────────────────────────"

# ── 1. Submodules ─────────────────────────────────────────────────────────────
echo ""
echo "[1/4] Initialising git submodules…"
git submodule update --init --recursive || {
  echo "  ⚠  Could not populate submodules (network may be unavailable)."
  echo "     Run 'git submodule update --init --recursive' when connected."
}

# ── 2. Virtual environment + dependencies ────────────────────────────────────
echo ""
echo "[2/4] Installing Python dependencies…"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "  ✓  Dependencies installed."

# ── 3. Database ───────────────────────────────────────────────────────────────
echo ""
echo "[3/4] Initialising database…"
mkdir -p data
python3 -c "from app.db import init_db; init_db(); print('  ✓  Database ready.')"

# ── 4. Search index ──────────────────────────────────────────────────────────
echo ""
echo "[4/4] Building search index…"
if [ -d "research" ] && [ "$(ls -A research 2>/dev/null)" ]; then
  python3 -c "from app.search import build_index; count = build_index(); print(f'  ✓  Indexed {count} chunks from research notes.')"
else
  echo "  ⚠  research/ submodule is empty – skipping index build."
  echo "     Run 'python3 -c \"from app.search import build_index; build_index()\"'"
  echo "     after populating the submodule."
fi

# ── .env reminder ─────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo ""
  echo "──────────────────────────────────────────────────"
  echo " No .env file found.  Creating one from .env.example…"
  cp .env.example .env
  echo " Edit .env to add your Apple credentials, or set"
  echo " DEV_AUTH_BYPASS=1 to skip auth during development."
  echo "──────────────────────────────────────────────────"
fi

echo ""
echo "──────────────────────────────────────────────────"
echo " Setup complete!  Start the app with:"
echo ""
echo "   source .venv/bin/activate"
echo "   python run.py"
echo ""
echo " Or with dev auth bypass (no Apple account needed):"
echo ""
echo "   DEV_AUTH_BYPASS=1 python run.py"
echo "──────────────────────────────────────────────────"
