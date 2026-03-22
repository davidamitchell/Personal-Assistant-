#!/usr/bin/env bash
# .devcontainer/install.sh
#
# Runs automatically after a Codespace is created (postCreateCommand).
# Sets up the complete environment without any user interaction.
#
# What it does, in order:
#   1. Initialise git submodules
#   2. Install uv and Python dependencies
#   3. Install OpenCode (terminal AI agent)
#   4. Install zsh + oh-my-zsh with a Termius-safe prompt
#   5. Add shell aliases to ~/.zshrc
#   6. Create the data/ directory structure
#   7. Initialise the SQLite database
#   8. Build the semantic search index (if research notes are present)
#   9. Print the first-run checklist

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Helpers ───────────────────────────────────────────────────────────────────
step() { echo ""; echo "[${1}] ${2}"; }
ok()   { echo "  ok  ${1}"; }
warn() { echo "  --  ${1}"; }

echo ""
echo "==========================================="
echo " Personal Assistant -- Codespace setup"
echo "==========================================="

# ── 1. Git submodules ─────────────────────────────────────────────────────────
step "1/8" "Initialising git submodules..."
git submodule update --init --recursive 2>/dev/null && ok "Submodules ready." || \
  warn "Could not populate submodules (network unavailable). Run: git submodule update --init --recursive"

# ── 2. Python dependencies via uv ─────────────────────────────────────────────
step "2/8" "Installing Python dependencies via uv..."
if ! command -v uv &>/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Make uv available for the rest of this script
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi
uv venv .venv --python python3.12 --quiet
uv pip install --quiet -r requirements.txt
uv pip install --quiet -r requirements-dev.txt
ok "Python dependencies installed (.venv)."

# ── 3. OpenCode ───────────────────────────────────────────────────────────────
step "3/8" "Installing OpenCode..."
if ! command -v opencode &>/dev/null; then
  npm install --global opencode-ai --silent 2>/dev/null && ok "OpenCode installed." || \
    warn "OpenCode install failed. Run: npm install -g opencode-ai"
else
  ok "OpenCode already installed ($(opencode --version 2>/dev/null || echo 'version unknown'))."
fi

# ── 4. Zsh + oh-my-zsh ────────────────────────────────────────────────────────
step "4/8" "Setting up zsh with oh-my-zsh..."
if ! command -v zsh &>/dev/null; then
  sudo apt-get update -qq && sudo apt-get install -y -qq zsh
fi

if [ ! -d "$HOME/.oh-my-zsh" ]; then
  RUNZSH=no CHSH=no \
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" \
    "" --unattended 2>/dev/null
  ok "oh-my-zsh installed."
else
  ok "oh-my-zsh already present."
fi

# Change default shell to zsh for the vscode/codespace user
TARGET_USER="${USER:-codespace}"
sudo chsh -s "$(command -v zsh)" "$TARGET_USER" 2>/dev/null && ok "Default shell set to zsh." || \
  warn "Could not change default shell -- run: sudo chsh -s \$(which zsh) $TARGET_USER"

# ── 4a. Termius-safe prompt (no powerline, no Unicode box-drawing) ─────────────
# Writes a custom theme that renders correctly in any standard terminal.
THEME_DIR="$HOME/.oh-my-zsh/custom/themes"
mkdir -p "$THEME_DIR"
cat > "$THEME_DIR/termius.zsh-theme" << 'THEME'
# termius.zsh-theme
# ASCII-only prompt. No powerline glyphs, no box-drawing characters.
# Safe for Termius, standard SSH clients, and any terminal emulator.

PROMPT='%n@%m %~ %# '
RPROMPT='$(git_prompt_info)'

ZSH_THEME_GIT_PROMPT_PREFIX="["
ZSH_THEME_GIT_PROMPT_SUFFIX="]"
ZSH_THEME_GIT_PROMPT_DIRTY="*"
ZSH_THEME_GIT_PROMPT_CLEAN=""
THEME
ok "Termius-safe prompt theme written."

# ── 4b. Write ~/.zshrc ────────────────────────────────────────────────────────
ZSHRC="$HOME/.zshrc"

# Preserve an existing .zshrc if oh-my-zsh already created one;
# otherwise write from scratch.
if grep -q "ZSH_THEME" "$ZSHRC" 2>/dev/null; then
  # Patch the theme line
  sed -i 's/^ZSH_THEME=.*/ZSH_THEME="termius"/' "$ZSHRC"
else
  cat > "$ZSHRC" << 'ZSHRC_CONTENT'
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="termius"
plugins=(git)
source "$ZSH/oh-my-zsh.sh"
ZSHRC_CONTENT
fi

# Ensure uv is on PATH in interactive zsh sessions
grep -q 'cargo/bin\|\.local/bin' "$ZSHRC" 2>/dev/null || \
  echo 'export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"' >> "$ZSHRC"

# Activate the project venv automatically when entering the workspace
VENV_LINE="[ -f /workspaces/Personal-Assistant-/.venv/bin/activate ] && source /workspaces/Personal-Assistant-/.venv/bin/activate"
grep -qF '.venv/bin/activate' "$ZSHRC" 2>/dev/null || echo "$VENV_LINE" >> "$ZSHRC"

# ── 5. Shell aliases ──────────────────────────────────────────────────────────
step "5/8" "Adding shell aliases..."

ALIASES_MARKER="# --- Personal Assistant aliases (managed by install.sh) ---"
if ! grep -qF "$ALIASES_MARKER" "$ZSHRC" 2>/dev/null; then
  cat >> "$ZSHRC" << 'ALIASES'

# --- Personal Assistant aliases (managed by install.sh) ---
REPO="/workspaces/Personal-Assistant-"

# Run the app
alias run='cd $REPO && DEV_AUTH_BYPASS=1 python run.py'
alias runprod='cd $REPO && python run.py'

# Tests and linting
alias test='cd $REPO && python -m pytest tests/'
alias lint='cd $REPO && ruff check . && ruff format --check .'
alias fix='cd $REPO && ruff check --fix . && ruff format .'

# Rebuild the search index
alias index='cd $REPO && python3 -c "from app.search import build_index; build_index()"'

# Submodule helpers
alias sub-pull='cd $REPO && git submodule update --remote --merge'
alias sub-init='cd $REPO && git submodule update --init --recursive'

# Git shortcuts (commit directly to main, no PR by default)
alias gs='git status'
alias gd='git diff'
alias ga='git add -A'
alias gc='git commit -m'
alias gp='git push'
alias gl='git log --oneline -20'

# Quick edit via agent (assumes opencode is authenticated)
alias agent='cd $REPO && opencode'

# Tail app logs (if redirected to file)
alias logs='tail -f /tmp/pa.log 2>/dev/null || echo "No log file at /tmp/pa.log -- pipe run output there"'

# Print this alias list
alias aliases='grep "^alias" ~/.zshrc | sed "s/alias //"'
# --- end Personal Assistant aliases ---
ALIASES
fi
ok "Aliases written to $ZSHRC."

# ── 6. Data directory structure ───────────────────────────────────────────────
step "6/8" "Creating data/ directory structure..."
mkdir -p data
# Ensure .gitkeep is present so the empty dir is tracked
touch data/.gitkeep
ok "data/ directory ready."

# ── 7. Initialise SQLite database ─────────────────────────────────────────────
step "7/8" "Initialising SQLite database..."
source .venv/bin/activate
python3 -c "from app.db import init_db; init_db()" && ok "Database initialised." || \
  warn "Database init failed -- run: python3 -c 'from app.db import init_db; init_db()'"

# ── 8. Build search index ─────────────────────────────────────────────────────
step "8/8" "Building semantic search index..."
if [ -d "research" ] && [ "$(ls -A research 2>/dev/null)" ]; then
  python3 -c "from app.search import build_index; count = build_index(); print(f'  ok  Indexed {count} chunks.')" || \
    warn "Index build failed -- run: index (alias) or python3 -c 'from app.search import build_index; build_index()'"
else
  warn "research/ submodule is empty -- run 'sub-init' or 'sub-pull' then 'index' to build the search index."
fi

# ── First-run checklist ───────────────────────────────────────────────────────
echo ""
echo "==========================================="
echo " Setup complete!"
echo "==========================================="
echo ""
echo " FIRST-RUN CHECKLIST"
echo " ==================="
echo ""
echo " Step 1 -- Authenticate GitHub CLI"
echo "   gh auth login"
echo "   (Choose: GitHub.com > HTTPS > browser or token)"
echo ""
echo " Step 2 -- Authenticate Copilot / OpenCode"
echo "   opencode auth"
echo "   (Follow the prompts to connect your Copilot Pro+ account)"
echo ""
echo " Step 3 -- Start the app"
echo "   run"
echo "   (Short for: DEV_AUTH_BYPASS=1 python run.py)"
echo "   Port 8000 will open automatically in your browser."
echo ""
echo " Step 4 -- (Optional) Pull latest research notes"
echo "   sub-pull"
echo "   index"
echo ""
echo " Useful aliases (type 'aliases' to see them all):"
echo "   run       Start the app (dev mode)"
echo "   test      Run the test suite"
echo "   lint      Check code style"
echo "   fix       Auto-fix code style"
echo "   agent     Open OpenCode AI terminal"
echo "   gs        git status"
echo "   ga        git add -A"
echo "   gc        git commit -m '...'"
echo "   gp        git push"
echo ""
echo "==========================================="
