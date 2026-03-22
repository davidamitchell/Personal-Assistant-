# Copilot Instructions

For AI coding agents working on this repository.

> **Quick Reference — most frequently missed rules:**
> 1. Never commit secrets. API keys live in `.env` (gitignored) or GitHub Secrets.
> 2. Never edit `.github/skills/` — it is a read-only submodule. All skill changes go to `davidamitchell/Skills`.
> 3. Never assume credentials or capabilities exist — STOP and ask if not listed in the credentials table.
> 4. Keep routes thin: all business logic lives in the app module files, not in `app/main.py`.
> 5. **Always read `.memory/` at the start of a task and write new insights back after completing it.**
> 6. **Always read `.github/agents/learnings.md` at the start of a task** — check for OPEN findings relevant to the current context.
> 7. **Always look for ways to improve the system** — record findings in `learnings.md` and push fixes at the root cause, not the symptom.

---

## Project Overview

A private single-user personal assistant web app built with Flask. It provides:

1. **Semantic search** — natural-language search over Research notes (git submodule at `research/`) using neural embeddings (`sentence-transformers`).
2. **Issue tracker** — create, edit, and close personal tasks stored in a local SQLite database.
3. **Apple Sign In** — secure authentication via Sign In with Apple; dev-bypass mode skips auth with `DEV_AUTH_BYPASS=1`.
4. **Zero-build frontend** — plain HTML, CSS, and JavaScript in `static/`.

---

## Non-Negotiable Constraints

- **Never commit secrets.** API keys and credentials live in environment variables / GitHub Secrets. The `.env` file is gitignored.
- **Every code slice must be end-to-end runnable** before being marked complete.
- **DO NOT ASSUME OR GUESS facts about the environment.** If you do not know whether a credential exists, whether a service is available, or whether a tool is capable of something — **STOP. Ask the owner before proceeding.**
- **DO NOT introduce new external services or credentials without explicit owner approval.**
- **`.github/skills/` is a read-only submodule.** Never edit files inside `.github/skills/`. All skill changes go to `davidamitchell/Skills` (open a PR there). Then advance the submodule pointer in this repo after the Skills PR merges.
- **Keep routes thin.** Route handlers in `app/main.py` should delegate immediately to module functions — no business logic inline.

---

## Self-Improvement Mandate

Agents working on this repository are expected to actively improve the system over time. This means:

1. **Read memories first.** At the start of every task, call `app/memory.read_relevant(query)` (or browse `.memory/` directly) to surface relevant facts, preferences, and procedures learned from prior sessions.

2. **Write insights back.** After completing a task, use `app/memory.write_memory(type, content, ...)` to record:
   - New facts discovered about the codebase
   - Preferences or constraints demonstrated by the owner's feedback
   - Procedures that worked well (or failed) and why

   **Only write a memory when the fact is unequivocally verified** — not planned, hypothetical, or inferred. If in doubt, do not write.

3. **Surface improvement opportunities.** If you notice a recurring problem, a missing abstraction, a gap in the test suite, or a way to make the system faster or cleaner, open a GitHub Issue describing it. Do not silently accept a poor status quo.

4. **Update memories when the system changes.** If you change how the app works, update or supersede the relevant memory files so future agents start with accurate context.

5. **Use memory to avoid repeating mistakes.** Before writing code, check whether a similar approach was tried and failed (look for `confidence < 0.5` entries with relevant tags).

---

## Agent Memory System (`.memory/`)

The `.memory/` directory is the agent's persistent, human-readable knowledge store. It survives across sessions because the files are committed to the repository.

### Directory layout

```
.memory/
  facts/           # Stable facts about the codebase, architecture, and project
  preferences/     # Owner/agent style preferences and constraints
  procedures/      # Learned workflows: what to do and in what order
  index.md         # Auto-maintained index; tracks interaction_count for compaction
```

### Memory file format

Each file is a Markdown document with YAML front-matter:

```markdown
---
id: mem_fact_001
type: fact            # fact | preference | procedure
confidence: 0.95      # 0.0–1.0  (below 0.3 + stale → deleted by compaction)
created_at: YYYY-MM-DD
last_updated: YYYY-MM-DD
tags: [flask, routes]
supersedes: null      # id of the entry this replaces, or null
---

One atomic statement here. Max ~200 tokens. No transcripts or code blobs.
```

### Using memory in code

```python
from app.memory import read_relevant, write_memory, compact, load_context_for_prompt

# 1. Retrieve relevant context (returns ≤5 ranked entries)
entries = read_relevant("flask authentication")

# 2. Inject into prompt
context_str = load_context_for_prompt("flask authentication")

# 3. Write a new insight after completing a task
write_memory(
    memory_type="fact",
    content="The /api/me route returns 401 when no session cookie is present.",
    confidence=0.95,
    tags=["api", "auth"],
)

# 4. Run compaction manually (normally triggered automatically every 20 writes)
compact()
```

### Write rules

| Condition | Action |
|---|---|
| Content is empty or > 1000 chars | Reject |
| > 80% keyword overlap with existing entry, same or lower confidence | Reject (duplicate) |
| > 80% keyword overlap, higher confidence or `supersedes` set | Update in place |
| No similar entry exists | Create new file |

### Retrieval ranking

Score = `keyword_similarity × confidence × recency_factor`

- `keyword_similarity` — Jaccard overlap between query tokens and memory body + tags
- `confidence` — 0.0–1.0 from the file's front-matter
- `recency_factor` — 1.0 today, decays to 0.5 over 2 years

### Compaction

Compaction runs automatically every 20 writes. It:
1. Deletes entries with `confidence < 0.3` that haven't been updated in 30+ days
2. Merges pairs of entries in the same subdirectory with > 80% keyword overlap (keeps the higher-confidence one)

---

## Working Environment

- **The owner interacts exclusively via the GitHub website or iOS GitHub app.** There is no local IDE, no `git clone`, and no terminal.
- **All coding is done by the agent.** The owner does not write or edit code directly.
- **Agent interactions happen via PR comments, issue comments, or by starting a new agent task/session.**

### Available credentials and services

| Credential / Service | Available | Notes |
|---|---|---|
| `GITHUB_TOKEN` | ✅ Yes | Auto-provided by GitHub Actions; scoped to the current repo |
| `APPLE_CLIENT_ID` | ✅ Yes | Apple Services ID for Sign In with Apple |
| `APPLE_TEAM_ID` | ✅ Yes | Apple Developer Team ID |
| `SECRET_KEY` | ✅ Yes | Flask session secret |
| Any other credential | ❓ Unknown | **STOP. Ask the owner before designing anything that requires it.** |

---

## Repository Layout

```
app/
├── __init__.py
├── main.py         # Flask app: routes only — no business logic
├── auth.py         # Apple Sign In verification + session helpers
├── db.py           # SQLite schema and connection helper
├── issues.py       # Issue CRUD operations
├── memory.py       # Agent memory: read/write/compact .memory/ files
└── search.py       # Semantic search over research notes

static/
├── index.html      # Single-page frontend
├── app.js          # Frontend logic
└── style.css       # Styles

data/               # Runtime data (gitignored content; .gitkeep tracks the dir)

research/           # Git submodule: davidamitchell/Research (markdown notes)

.memory/            # Agent memory store (Markdown files, committed to repo)
├── facts/          # Factual memories about the codebase
├── preferences/    # Style and constraint preferences
├── procedures/     # Learned workflows
└── index.md        # Auto-maintained index

.github/
├── copilot-instructions.md  # Agent instructions (this file)
├── mcp.json                 # MCP servers for GitHub Copilot Agent
├── agents/                  # Custom agent definitions
│   └── learnings.md         # Persistent RCA/FIX log (read at session open)
├── instructions/            # Reusable instruction files
├── skills/                  # Agent skills (submodule: davidamitchell/Skills, read-only)
└── workflows/
    └── ci.yml               # Lint and test on every push/PR

requirements.txt      # Python runtime dependencies
requirements-dev.txt  # Dev/CI tools (ruff, pytest)
setup.sh              # One-command environment setup
run.py                # Top-level entry point
.env.example          # Template for local .env
```

---

## Coding Standards

### Language & Runtime
- Python 3.11+
- Type hints on all public functions and class methods

### Style
- `ruff` for linting and formatting (line length 100)
- No unused imports; no bare `except:` clauses

### Logging
- Use Python's built-in `logging` module — never `print()` in production code
- Log levels: `DEBUG` for per-item detail, `INFO` for pipeline stages, `WARNING` for skipped/degraded paths, `ERROR` for failures

### Error Handling
- Route handlers must return structured JSON errors, not raw Python exceptions
- Network errors must be retried with exponential backoff (max 3 attempts)

### Testing
- Tests live in `tests/`; use `pytest`
- Mock all network calls
- **Bug fixes must start with a failing test.** Write the test first, confirm it fails, then fix and confirm it passes.

---

## Continuous Improvement

This procedure runs on **every** agent session — not as an optional mode.

### Session open

Read `.github/agents/learnings.md` (create it from the schema below if absent). Check for any OPEN findings relevant to the current task context before writing a single line of code.

### Session close

After completing any task, scan every file you touched — and their neighbouring instruction, agent, or skill files — for defects. For each finding:

1. **Root cause analysis — minimum three levels of why.** Do not stop at the symptom.
2. **Classify** using one of: `STRUCTURAL` · `SCOPE_LEAK` · `TRIGGER_AMBIGUITY` · `BEHAVIOR_VAGUENESS` · `MISSING_GOVERNANCE` · `STALE_REFERENCE` · `REDUNDANCY`
3. **Fix the root cause.** If a pattern spans multiple files, create or update the governance artifact that prevents recurrence rather than patching each file individually.
4. **Update `learnings.md`** — new findings get an `RCA-NNN` ID, applied fixes get a `FIX-NNN` ID. A finding moves to `RESOLVED` only when the preventive governance artifact is in place. Anything requiring a human design decision goes to **Open Questions**.

This instruction file is itself in scope. If you find a defect in `copilot-instructions.md` or in any agent file, fix it as part of the session.

### `.github/agents/learnings.md` schema

```markdown
# Copilot Customisation Learnings

## Persistent Findings

| ID | Category | Root Cause | Scope | Status | First Seen | Last Seen |
|----|----------|------------|-------|--------|------------|-----------|

## Applied Fixes

| ID | File | Change Summary | Root Cause ID | Date |
|----|------|----------------|---------------|------|

## Ecosystem Reference Updates

| Date | Change | Source |
|------|--------|--------|

## Open Questions

- (questions requiring human design decisions go here)
```

---

## Using Skills

Skills live in `.github/skills/` (read-only submodule from `davidamitchell/Skills`). To invoke a skill:

1. Open the relevant `SKILL.md` inside `.github/skills/<skill-name>/`
2. Follow the skill's process step by step as the agent

Available skills include `swe`, `code-review`, `technical-writer`, `research`, `backlog-manager`, and others. See `.github/skills/README.md` for the full list.

### Mandatory skill usage

These skills are **required** for every relevant session — not optional:

| When | Skill | What to do |
|---|---|---|
| Any development work (code changes) | `swe` | Open `.github/skills/swe/SKILL.md` and follow the process before writing code |
| After any code change | `code-review` | Open `.github/skills/code-review/SKILL.md` and run a review before marking work complete |
| Creating or updating tasks / tracking work | `backlog-manager` | Open `.github/skills/backlog-manager/SKILL.md` to log and prioritise work items |

---

## Using MCP Tools

MCP server configuration is in `.github/mcp.json`. Available tools include:

- `fetch` — retrieve full page content from a URL
- `sequential_thinking` — plan complex multi-step work before executing
- `time` — get the current date/time
- `memory` — persist state across sessions
- `git` — read repo history and file contents
- `filesystem` — read and write files directly
- `github` — interact with GitHub APIs (issues, PRs, etc.)

