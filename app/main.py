"""
Flask application – entry point and route definitions.

Run with:
    python app/main.py          (development)
    gunicorn app.main:app       (production)

All business logic lives in the other modules; routes stay thin.

API surface
-----------
GET  /                          Serve the single-page frontend
GET  /api/me                    Current user info (or 401)
POST /auth/apple/verify         Validate Apple identity token, open session
POST /auth/logout               Clear session

GET  /api/search?q=<query>      Semantic search over research notes
POST /api/index/rebuild         Rebuild the search index (slow, runs in bg)
GET  /api/index/status          Index stats (chunk count, built flag)

GET    /api/issues              List issues (?status=open|closed)
POST   /api/issues              Create issue
GET    /api/issues/<id>         Get one issue
PUT    /api/issues/<id>         Update issue fields
DELETE /api/issues/<id>         Delete issue
"""

import os
import threading
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session

# Load .env (if present) before anything else reads os.environ
load_dotenv(Path(__file__).parent.parent / ".env")

from . import auth as _auth
from . import issues as _issues
from . import search as _search
from .db import init_db

REPO_ROOT = Path(__file__).parent.parent
STATIC_DIR = REPO_ROOT / "static"

app = Flask(__name__, static_folder=None)

# SECRET_KEY must be set in production; fall back to a random value in dev.
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.get("/api/me")
def me():
    if not _auth.is_authenticated():
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "user": _auth.current_user()})


@app.post("/auth/apple/verify")
def apple_verify():
    """Receive an Apple identity token from the frontend and open a session."""
    if _auth.dev_bypass_active():
        return jsonify({"ok": True, "user": _auth.current_user()})

    data = request.get_json(silent=True) or {}
    identity_token = data.get("identity_token", "")
    user_info = data.get("user") or {}

    if not identity_token:
        return jsonify({"error": "identity_token is required"}), 400

    try:
        claims = _auth.verify_apple_token(identity_token)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401

    session["user_sub"] = claims["sub"]
    # Apple only sends name/email on the very first sign-in; persist them.
    if user_info.get("email"):
        session["user_email"] = user_info["email"]
    if user_info.get("name"):
        name_obj = user_info["name"]
        full = f"{name_obj.get('firstName', '')} {name_obj.get('lastName', '')}".strip()
        if full:
            session["user_name"] = full

    return jsonify({"ok": True, "user": _auth.current_user()})


@app.post("/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@app.get("/api/search")
@_auth.require_auth
def search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "query parameter 'q' is required"}), 400

    top_k = min(int(request.args.get("k", 10)), 50)
    results = _search.search(q, top_k=top_k)
    return jsonify({"query": q, "results": results})


@app.post("/api/index/rebuild")
@_auth.require_auth
def rebuild_index():
    """Trigger a background index rebuild and return immediately."""
    def _run():
        try:
            count = _search.build_index()
            print(f"[index] Rebuild complete: {count} chunks")
        except Exception as exc:
            print(f"[index] Rebuild failed: {exc}")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"ok": True, "message": "Index rebuild started in background"})


@app.get("/api/index/status")
@_auth.require_auth
def index_status():
    return jsonify(_search.index_status())


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

@app.get("/api/issues")
@_auth.require_auth
def list_issues():
    status_filter = request.args.get("status")
    return jsonify(_issues.list_issues(status=status_filter))


@app.post("/api/issues")
@_auth.require_auth
def create_issue():
    data = request.get_json(silent=True) or {}
    try:
        issue = _issues.create_issue(
            title=data.get("title", ""),
            body=data.get("body", ""),
            labels=data.get("labels", []),
            status=data.get("status", "open"),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(issue), 201


@app.get("/api/issues/<int:issue_id>")
@_auth.require_auth
def get_issue(issue_id: int):
    issue = _issues.get_issue(issue_id)
    if issue is None:
        return jsonify({"error": "Issue not found"}), 404
    return jsonify(issue)


@app.put("/api/issues/<int:issue_id>")
@_auth.require_auth
def update_issue(issue_id: int):
    data = request.get_json(silent=True) or {}
    try:
        issue = _issues.update_issue(issue_id, **data)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if issue is None:
        return jsonify({"error": "Issue not found"}), 404
    return jsonify(issue)


@app.delete("/api/issues/<int:issue_id>")
@_auth.require_auth
def delete_issue(issue_id: int):
    deleted = _issues.delete_issue(issue_id)
    if not deleted:
        return jsonify({"error": "Issue not found"}), 404
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def _startup():
    """Initialise the database on first run."""
    init_db()


if __name__ == "__main__":
    _startup()
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_DEBUG", "0") in ("1", "true")
    app.run(host="0.0.0.0", port=port, debug=debug)
