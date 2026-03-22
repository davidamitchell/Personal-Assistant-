# Personal Assistant

A private single-user research management and productivity web app.

## What it does

| Feature | Description |
|---------|-------------|
| **Semantic search** | Natural-language search over your [Research](https://github.com/davidamitchell/Research) notes using neural embeddings (`all-MiniLM-L6-v2`). |
| **Issue tracker** | Create, edit, and close research tasks with labels and markdown bodies. Stored in a local SQLite database. |
| **Apple Sign In** | Secure authentication via Sign In with Apple. Dev-bypass mode lets you skip auth during development with a single env-var. |
| **Zero-build frontend** | Plain HTML, CSS, and JavaScript – no framework, no build step. |
| **Codespaces-ready** | Fully configured devcontainer. Port 8000 opens automatically in the browser. |

## Quick start (GitHub Codespaces)

### Automatic setup

When you open this repo in a Codespace, `.devcontainer/install.sh` runs automatically.
It sets up everything without interaction: submodules, Python dependencies, OpenCode, zsh with
oh-my-zsh, shell aliases, and the database. When it finishes, it prints a first-run checklist.

### First-time auth (run once after setup completes)

These two steps are required the first time you start a new Codespace. After that, credentials
are cached for the lifetime of the Codespace.

**Step 1 — Authenticate GitHub CLI**

```bash
gh auth login
```

Choose: GitHub.com → HTTPS → Authenticate with a web browser (or paste a token).

**Step 2 — Authenticate OpenCode / Copilot**

```bash
opencode auth
```

Follow the prompts to connect your Copilot Pro+ account.

### Start the app

```bash
run
```

This is a shell alias for `DEV_AUTH_BYPASS=1 python run.py`. Port 8000 opens automatically
in the browser via the Codespaces forwarded-port URL.

## Quick start (local)

```bash
git clone --recurse-submodules https://github.com/davidamitchell/Personal-Assistant-
cd Personal-Assistant-
bash setup.sh
source .venv/bin/activate
DEV_AUTH_BYPASS=1 python run.py
# Open http://localhost:8000
```

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Description |
|----------|-------------|
| `DEV_AUTH_BYPASS` | Set to `1` to skip Apple Sign In during development. |
| `SECRET_KEY` | Flask session secret – generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`. |
| `PORT` | Port to listen on (default `8000`). |
| `FLASK_DEBUG` | Set to `1` to enable Flask auto-reload. |
| `APPLE_CLIENT_ID` | Apple Services ID (production only). |
| `APPLE_TEAM_ID` | Apple Team ID (production only). |

## Repository layout

```
.
├── app/                    Python backend (Flask)
│   ├── __init__.py         Package documentation
│   ├── main.py             Routes (thin – delegates to modules)
│   ├── auth.py             Apple Sign In + dev bypass
│   ├── search.py           Semantic search engine
│   ├── issues.py           Issue tracker (SQLite)
│   ├── db.py               Database initialisation
│   └── memory.py           Agent memory read/write/compact
├── static/                 Frontend (plain HTML/CSS/JS)
│   ├── index.html          Single-page app shell
│   ├── app.js              All frontend logic
│   └── style.css           Stylesheet
├── data/                   Runtime data (gitignored)
│   ├── search_embeddings.npy
│   ├── search_chunks.json
│   └── issues.db
├── research/               Git submodule – Research notes
├── .devcontainer/          GitHub Codespaces configuration
│   ├── devcontainer.json   Container definition (Python 3.12, Node LTS, gh CLI)
│   ├── install.sh          Automated setup (runs on postCreate)
│   └── mcp.json            MCP servers for Copilot CLI / OpenCode
├── .github/
│   ├── mcp.json            MCP servers for Copilot in VS Code/web
│   └── skills/             Git submodule – Shared agent skills (read-only)
├── .memory/                Agent memory store (committed Markdown files)
├── AGENTS.md               Agent briefing – read this before writing code
├── setup.sh                Legacy local setup helper
├── requirements.txt        Python runtime dependencies
├── requirements-dev.txt    Dev/CI tools (ruff, pytest)
├── run.py                  Entry point
└── .env.example            Environment variable template
```

## Rebuilding the search index

Pull new research notes and rebuild:

```bash
cd research && git pull && cd ..
python3 -c "from app.search import build_index; build_index()"
```

Or use the **Rebuild index** button in the app's Search tab.

## Extending the app

The codebase follows a deliberate pattern:

- **Routes stay thin** – `app/main.py` delegates immediately to a module.
- **One module per concern** – `search.py`, `issues.py`, `auth.py` each own their domain.
- **Configuration via env vars** – no hard-coded values.
- **No magic** – plain Python, plain SQL, plain fetch().

To add a new feature:
1. Add business logic to an existing module or a new one.
2. Add routes in `main.py`.
3. Add the UI in `static/app.js` using the same `api.*` / render pattern.

## Submodules

| Submodule | Repo | Purpose |
|-----------|------|---------|
| `research/` | [davidamitchell/Research](https://github.com/davidamitchell/Research) | Markdown research notes |
| `.github/skills/` | [davidamitchell/Skills](https://github.com/davidamitchell/Skills) | Shared agent skills (read-only) |

In a Codespace, aliases handle submodule operations:

```bash
sub-init   # initialise unpopulated submodules
sub-pull   # pull latest commits from all submodule remotes
```
