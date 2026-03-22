# Copilot Instructions

For AI coding agents working on this repository.

> **Quick Reference — most frequently missed rules:**
> 1. Never commit secrets. API keys live in `.env` (gitignored) or GitHub Secrets.
> 2. Never edit `.github/skills/` — it is a read-only submodule. All skill changes go to `davidamitchell/Skills`.
> 3. Never assume credentials or capabilities exist — STOP and ask if not listed in the credentials table.
> 4. Keep routes thin: all business logic lives in the app module files, not in `app/main.py`.

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
└── search.py       # Semantic search over research notes

static/
├── index.html      # Single-page frontend
├── app.js          # Frontend logic
└── style.css       # Styles

data/               # Runtime data (gitignored content; .gitkeep tracks the dir)

research/           # Git submodule: davidamitchell/Research (markdown notes)

.github/
├── copilot-instructions.md  # Agent instructions (this file)
├── mcp.json                 # MCP servers for GitHub Copilot Agent
├── agents/                  # Custom agent definitions
├── instructions/            # Reusable instruction files
├── skills/                  # Agent skills (submodule: davidamitchell/Skills, read-only)
└── workflows/
    ├── ci.yml               # Lint and test on every push/PR
    └── sync-skills.yml      # Weekly auto-update of the skills submodule

requirements.txt    # Python runtime dependencies
setup.sh            # One-command environment setup
run.py              # Top-level entry point
.env.example        # Template for local .env
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

## Using Skills

Skills live in `.github/skills/` (read-only submodule from `davidamitchell/Skills`). To invoke a skill:

1. Open the relevant `SKILL.md` inside `.github/skills/<skill-name>/`
2. Follow the skill's process step by step as the agent

Available skills include `swe`, `code-review`, `technical-writer`, `research`, and others. See `.github/skills/README.md` for the full list.

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
