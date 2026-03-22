"""
Database initialisation.

We use SQLite for everything that needs persistence except the search index
(which lives in data/ as numpy arrays).  SQLite requires no server and the
database is a single file that can be backed up with a plain file copy.

Schema
------
issues  – the task/issue tracker (see issues.py for field descriptions)
"""

import sqlite3
from pathlib import Path

# Place the database next to the other runtime data so it is gitignored.
DB_PATH = Path(__file__).parent.parent / "data" / "issues.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set to Row.

    Row objects behave like both tuples and dicts, which makes it easy to
    serialise rows to JSON with ``dict(row)``.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # safe for concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create the database schema if it does not already exist.

    Safe to call repeatedly – all statements use CREATE IF NOT EXISTS.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS issues (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                body        TEXT    NOT NULL DEFAULT '',
                labels      TEXT    NOT NULL DEFAULT '[]',
                status      TEXT    NOT NULL DEFAULT 'open'
                                    CHECK (status IN ('open', 'closed')),
                created_at  TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            );
        """)
