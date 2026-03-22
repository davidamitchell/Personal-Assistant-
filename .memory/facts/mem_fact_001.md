---
id: mem_fact_001
type: fact
confidence: 0.95
created_at: 2026-03-22
last_updated: 2026-03-22
tags: [flask, architecture, routes]
supersedes: null
---

Flask route handlers in `app/main.py` must delegate to module functions immediately — no business logic inline. All business logic lives in `app/auth.py`, `app/issues.py`, `app/search.py`, and `app/db.py`.
