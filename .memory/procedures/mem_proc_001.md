---
id: mem_proc_001
type: procedure
confidence: 0.95
created_at: 2026-03-22
last_updated: 2026-03-22
tags: [workflow, ci, dependencies]
supersedes: null
---

To add a new Python dependency: (1) add it to `requirements.txt` with a minimum version pin, (2) add dev/test tools to `requirements-dev.txt` instead, (3) run `pip install -r requirements.txt` to verify it resolves, (4) update `setup.sh` if the dep needs a one-time setup step.
