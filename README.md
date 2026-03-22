# Research Assistant

A private single-user research management web app.

## What it does

| Feature | Description |
|---------|-------------|
| **Semantic search** | Natural-language search over your [Research](https://github.com/davidamitchell/Research) notes using neural embeddings (`all-MiniLM-L6-v2`). |
| **Issue tracker** | Create, edit, and close research tasks with labels and markdown bodies. Stored in a local SQLite database. |
| **Apple Sign In** | Secure authentication via Sign In with Apple. Dev-bypass mode lets you skip auth during development with a single env-var. |
| **Zero-build frontend** | Plain HTML, CSS, and JavaScript – no framework, no build step. |
| **Codespaces-ready** | One command to set up, one command to run. Port 8000 opens automatically in the browser. |

## Quick start (GitHub Codespaces)

1. Open this repo in a Codespace – the devcontainer will run `setup.sh` automatically.
2. Start the app:

```bash
source .venv/bin/activate
DEV_AUTH_BYPASS=1 python run.py
```

3. Codespaces will prompt you to open port 8000 in the browser.

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
│   ├── main.py             Routes and app entry point
│   ├── auth.py             Apple Sign In + dev bypass
│   ├── search.py           Semantic search engine
│   ├── issues.py           Issue tracker (SQLite)
│   └── db.py               Database initialisation
├── static/                 Frontend (plain HTML/CSS/JS)
│   ├── index.html          Single-page app shell
│   ├── app.js              All frontend logic
│   └── style.css           Stylesheet
├── data/                   Runtime data (gitignored)
│   ├── search_embeddings.npy
│   ├── search_chunks.json
│   └── issues.db
├── research/               Git submodule – Research notes
├── skills/                 Git submodule – Shared agent skills
├── .devcontainer/          GitHub Codespaces configuration
├── setup.sh                Automated setup script
├── requirements.txt        Python dependencies
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
| `skills/` | [davidamitchell/Skills](https://github.com/davidamitchell/Skills) | Shared agent skills |
