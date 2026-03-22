---
id: mem_fact_002
type: fact
confidence: 0.95
created_at: 2026-03-22
last_updated: 2026-03-22
tags: [auth, apple, dev]
supersedes: null
---

Authentication uses Apple Sign In. During development, set `DEV_AUTH_BYPASS=1` to skip auth entirely. The `@_auth.require_auth` decorator guards all `/api/` routes that need a session.
