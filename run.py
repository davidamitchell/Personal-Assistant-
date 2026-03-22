"""
Top-level entry point for running the Research Assistant.

Usage:
    python run.py                        # production (reads .env)
    DEV_AUTH_BYPASS=1 python run.py      # development (no auth required)
    FLASK_DEBUG=1 python run.py          # auto-reload on code changes

Alternatively, run as a module:
    python -m app.main
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from app.db import init_db
from app.main import app

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_DEBUG", "0") in ("1", "true")
    app.run(host="0.0.0.0", port=port, debug=debug)
