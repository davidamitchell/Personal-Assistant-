# AGENTS.md

Agent briefing for the Personal Assistant repository.
This file is the primary context source. Read it before writing any code.

---

## Stack and Why

| Component | Choice | Reason |
|-----------|--------|--------|
| **Backend** | Python 3.12 + Flask | Minimal, no magic. Easy to reason about for an agent. |
| **Database** | SQLite via `sqlite3` stdlib | Single-user app; no server to manage. |
| **Semantic search** | `sentence-transformers` (`all-MiniLM-L6-v2`) | ~80 MB model; runs locally; no API key needed. |
| **Frontend** | Plain HTML + CSS + JS | Zero build step. No framework overhead. |
| **Auth** | Sign In with Apple + dev-bypass mode | Owner uses Apple ecosystem exclusively. |
| **Environment** | GitHub Codespaces (Python 3.12 devcontainer) | Owner works from iPad + Termius SSH; no local IDE. |
| **Dependency management** | `uv` | Fast, reproducible installs; used instead of pip in the Codespace. |
| **Terminal agent** | OpenCode | Terminal-based AI interface; connects to Copilot Pro+. |
| **Package tooling** | Node LTS (in devcontainer) | Required by OpenCode and MCP npm packages. |
| **Linting** | `ruff` | Fast; handles both linting and formatting. |

---

## Application Structure

```
/workspaces/Personal-Assistant-/
├── app/                    Python backend (Flask)
│   ├── __init__.py         Package docstring only
│   ├── main.py             Routes ONLY — no business logic here
│   ├── auth.py             Apple Sign In verification + dev-bypass
│   ├── search.py           Semantic search engine (build_index, query)
│   ├── issues.py           Issue CRUD (SQLite)
│   ├── db.py               Schema + connection helper
│   └── memory.py           Agent memory: read_relevant, write_memory, compact
├── static/                 Frontend (no build step)
│   ├── index.html          Single-page app shell
│   ├── app.js              All frontend logic (fetch-based api.* helpers)
│   └── style.css           Styles
├── data/                   Runtime data — gitignored content
│   ├── issues.db           SQLite database
│   ├── search_embeddings.npy
│   └── search_chunks.json
├── research/               Git submodule — Markdown research notes
├── .github/
│   ├── skills/             Git submodule — shared agent skills (READ-ONLY)
│   ├── copilot-instructions.md
│   ├── agents/learnings.md RCA/FIX log — read at session open
│   └── mcp.json            MCP config used by Copilot in VS Code/web
├── .devcontainer/
│   ├── devcontainer.json   Codespace configuration
│   ├── install.sh          Full automated setup (runs on container create)
│   └── mcp.json            MCP config used by Copilot CLI / OpenCode
├── .memory/                Agent memory store (Markdown files, committed)
│   ├── facts/
│   ├── preferences/
│   ├── procedures/
│   └── index.md
├── requirements.txt        Runtime Python deps
├── requirements-dev.txt    Dev/CI deps (ruff, pytest)
├── run.py                  Entry point
├── setup.sh                Legacy setup helper (kept for local use)
└── .env.example            Environment variable template
```

### Where things live — quick reference

| Thing you want to change | File |
|--------------------------|------|
| Add/change a route | `app/main.py` |
| Business logic for issues | `app/issues.py` |
| Business logic for search | `app/search.py` |
| Auth logic | `app/auth.py` |
| Database schema | `app/db.py` |
| UI layout | `static/index.html` |
| UI behaviour | `static/app.js` |
| Styles | `static/style.css` |
| Python dependencies | `requirements.txt` |
| Dev/CI dependencies | `requirements-dev.txt` |
| Codespace setup | `.devcontainer/install.sh` |
| MCP servers (CLI) | `.devcontainer/mcp.json` |
| MCP servers (VS Code) | `.github/mcp.json` |

---

## Coding Conventions

### Python

- **Type hints on every public function and class method.** No exceptions.
- **Routes stay thin.** `app/main.py` handlers must delegate immediately to a module function. No business logic inline.
- **One module per concern.** Do not mix domains.
- **Logging, not print.** Use Python's `logging` module at the correct level: `DEBUG` for per-item detail, `INFO` for pipeline stages, `WARNING` for skipped/degraded paths, `ERROR` for failures.
- **No bare `except:`.** Catch specific exceptions.
- **Structured JSON errors from routes.** Never let a raw Python exception reach the HTTP response.
- **Configuration via env vars.** No hard-coded values.
- Line length: 100. Enforced by `ruff`.

### JavaScript

- Plain `fetch()` calls, no framework.
- All API calls go through the `api.*` helper pattern in `app.js`.
- No transpilation, no bundling — code must run as-is in a modern browser.

### Tests

- Live in `tests/`. Use `pytest`.
- **Bug fixes must start with a failing test.** Write → confirm fail → fix → confirm pass.
- Mock all network calls.

---

## How to Run the App

```bash
# Dev mode (no Apple credentials needed)
run

# Which expands to:
DEV_AUTH_BYPASS=1 python run.py

# Production mode (Apple Sign In active)
runprod
```

The app listens on port 8000. In a Codespace, this is forwarded automatically and opened in the browser.

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DEV_AUTH_BYPASS` | unset | Set to `1` to skip Apple Sign In |
| `SECRET_KEY` | required | Flask session secret |
| `PORT` | `8000` | Port to listen on |
| `FLASK_DEBUG` | unset | Set to `1` for auto-reload |
| `APPLE_CLIENT_ID` | required in prod | Apple Services ID |
| `APPLE_TEAM_ID` | required in prod | Apple Team ID |

Copy `.env.example` to `.env` and fill in values for production. Dev mode only needs `DEV_AUTH_BYPASS=1`.

---

## Supporting Scripts and Commands

| Alias | Expands to | Purpose |
|-------|-----------|---------|
| `run` | `DEV_AUTH_BYPASS=1 python run.py` | Start app in dev mode |
| `runprod` | `python run.py` | Start app in production mode |
| `test` | `python -m pytest tests/` | Run test suite |
| `lint` | `ruff check . && ruff format --check .` | Check code style |
| `fix` | `ruff check --fix . && ruff format .` | Auto-fix code style |
| `index` | `python3 -c "from app.search import build_index; build_index()"` | Rebuild search index |
| `sub-pull` | `git submodule update --remote --merge` | Pull latest submodule commits |
| `sub-init` | `git submodule update --init --recursive` | Initialise unpopulated submodules |
| `agent` | `opencode` | Open OpenCode AI terminal agent |
| `gs` | `git status` | Git status |
| `gd` | `git diff` | Git diff |
| `ga` | `git add -A` | Stage all changes |
| `gc` | `git commit -m` | Commit with message |
| `gp` | `git push` | Push to origin |
| `gl` | `git log --oneline -20` | Last 20 commits |
| `logs` | `tail -f /tmp/pa.log` | Tail app log file |
| `aliases` | (prints alias list) | Show all aliases |

All aliases are defined in `~/.zshrc` by `install.sh`. They are available in every new zsh terminal session.

---

## Submodule Rules

The repository has two git submodules:

| Path | Repo | Rules |
|------|------|-------|
| `research/` | `davidamitchell/Research` | Read/write. Pull updates with `sub-pull`. Rebuild index with `index` after pulling. |
| `.github/skills/` | `davidamitchell/Skills` | **READ-ONLY. Never edit files inside here.** Changes to skills go to the Skills repo via a PR there. Advance the pointer in this repo only after a Skills PR merges. |

To update research notes and rebuild the search index:

```bash
sub-pull   # pulls latest commits in all submodules
index      # rebuilds search_embeddings.npy + search_chunks.json
```

---

## Agent Memory System

The `.memory/` directory is the agent's persistent knowledge store. Files are committed so they survive across sessions.

- **Read first:** call `app.memory.read_relevant(query)` or read `.memory/` files directly before writing code.
- **Write back:** call `app.memory.write_memory(type, content, ...)` after completing a task to record verified facts.
- **Only write verified facts.** Do not record planned, hypothetical, or inferred information.
- Compaction runs automatically every 20 writes and removes stale low-confidence entries.

---

## First-Time Auth (after Codespace starts)

After `install.sh` completes, run these two commands once:

```bash
# 1. Authenticate GitHub CLI
gh auth login

# 2. Authenticate OpenCode / Copilot
opencode auth
```

Everything else is already configured. Port 8000 opens automatically in the browser.

---

## What NOT to Do Without Asking the Owner

1. **Do not introduce new external services or credentials.** The available credentials are listed in `.github/copilot-instructions.md`. If you need something not on that list, stop and ask.
2. **Do not edit `.github/skills/`.** It is a read-only submodule. All skill changes go to `davidamitchell/Skills`.
3. **Do not commit secrets or credentials.** All sensitive values live in `.env` (gitignored) or GitHub Secrets.
4. **Do not create pull requests unless explicitly asked.** The owner commits directly to main by default.
5. **Do not add new Python packages without checking `requirements.txt` first.** Use `uv pip install` and add to `requirements.txt`.
6. **Do not put business logic in route handlers.** Keep `app/main.py` thin.
7. **Do not use `print()` in production code.** Use the `logging` module.
8. **Do not add powerline glyphs, Unicode box-drawing characters, or colour escape sequences** to terminal output or prompt configuration. The owner uses Termius on iPad — these render incorrectly.
9. **Do not run `setup.sh` in a Codespace.** Use `install.sh` instead (it is the Codespace-optimised replacement).
10. **Do not assume a credential or service exists.** If unsure, stop and ask before designing anything that depends on it.
