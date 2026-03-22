"""
Research Assistant – application package.

Layout
------
main.py    Flask app and routes (the entry point)
auth.py    Authentication: Apple Sign In + DEV_AUTH_BYPASS
search.py  Semantic search engine over the Research submodule
issues.py  Lightweight issue tracker backed by SQLite
db.py      Database initialisation and connection helpers

Conventions
-----------
* All route handlers live in main.py.
* Business logic is kept in the other modules so routes stay thin.
* Configuration is read from environment variables (see .env.example).
* Paths are resolved relative to the repository root (REPO_ROOT).
"""
