---
applyTo: "**"
---

# Default Instructions

These instructions apply to all Copilot interactions in this repository.

- Follow all rules in `.github/copilot-instructions.md`.
- Keep Flask route handlers thin — delegate business logic to the `app/` modules.
- Always use type hints on public functions and class methods.
- Use `ruff` style: line length 100, no unused imports, no bare `except:`.
- Never commit secrets or credentials to the repository.
- Never edit files inside `.github/skills/` — it is a read-only submodule.
