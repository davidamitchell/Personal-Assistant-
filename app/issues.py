"""
Issue tracker backed by SQLite.

An issue models a research task or question.  It is deliberately lightweight:
there is no project board, milestone, or assignee – just enough structure to
track what needs doing and what is done.

Fields
------
id          Auto-assigned integer.
title       Short, mandatory summary (used as the heading everywhere).
body        Markdown text – any amount of detail.  Empty by default.
labels      JSON-encoded list of strings, e.g. ``["todo", "question"]``.
status      ``"open"`` or ``"closed"``.
created_at  ISO-8601 UTC timestamp set on creation.
updated_at  ISO-8601 UTC timestamp updated on every write.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from .db import get_connection


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row) -> dict:
    """Convert a sqlite3.Row to a plain dict, deserialising the labels JSON."""
    d = dict(row)
    d["labels"] = json.loads(d.get("labels") or "[]")
    return d


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def list_issues(status: Optional[str] = None) -> list[dict]:
    """Return all issues, optionally filtered by status.

    Issues are ordered newest-first.
    """
    with get_connection() as conn:
        if status in ("open", "closed"):
            rows = conn.execute(
                "SELECT * FROM issues WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM issues ORDER BY created_at DESC"
            ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_issue(issue_id: int) -> Optional[dict]:
    """Return a single issue by id, or None if it does not exist."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM issues WHERE id = ?", (issue_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def create_issue(title: str, body: str = "", labels: list[str] = None, status: str = "open") -> dict:
    """Insert a new issue and return it as a dict."""
    if not title or not title.strip():
        raise ValueError("Issue title is required")
    if status not in ("open", "closed"):
        raise ValueError("status must be 'open' or 'closed'")

    labels_json = json.dumps(labels or [])
    now = _now()

    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO issues (title, body, labels, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title.strip(), body, labels_json, status, now, now),
        )
        new_id = cursor.lastrowid

    return get_issue(new_id)


def update_issue(issue_id: int, **fields) -> Optional[dict]:
    """Update specific fields of an issue and return the updated row.

    Accepted keyword arguments: title, body, labels, status.
    Unknown keys are silently ignored to make partial updates easy.
    """
    allowed = {"title", "body", "labels", "status"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return get_issue(issue_id)

    if "status" in updates and updates["status"] not in ("open", "closed"):
        raise ValueError("status must be 'open' or 'closed'")
    if "title" in updates and not updates["title"].strip():
        raise ValueError("Issue title cannot be empty")
    if "labels" in updates:
        updates["labels"] = json.dumps(updates["labels"] or [])

    updates["updated_at"] = _now()

    set_clause = ", ".join(f"{col} = ?" for col in updates)
    values = list(updates.values()) + [issue_id]

    with get_connection() as conn:
        conn.execute(
            f"UPDATE issues SET {set_clause} WHERE id = ?",  # noqa: S608
            values,
        )

    return get_issue(issue_id)


def delete_issue(issue_id: int) -> bool:
    """Delete an issue. Returns True if a row was deleted, False otherwise."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
        return cursor.rowcount > 0
