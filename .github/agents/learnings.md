# Copilot Customisation Learnings

Maintained by the agent per the **Continuous Improvement** procedure in `.github/copilot-instructions.md`. Updated at the close of every session that touches `.github/` files.

## Persistent Findings

Findings that recur across sessions or represent systemic root causes not yet fully resolved.

| ID | Category | Root Cause | Scope | Status | First Seen | Last Seen |
|----|----------|------------|-------|--------|------------|-----------|
| RCA-001 | MISSING_GOVERNANCE | No authoring standard mandating use of `swe`, `code-review`, and `backlog-manager` skills; agents were free to skip them entirely | `copilot-instructions.md` | RESOLVED | 2026-03-22 | 2026-03-22 |
| RCA-002 | BEHAVIOR_VAGUENESS | Memory write rule did not specify that facts must be unequivocally verified before recording; allowed speculative or planned facts to pollute the store | `copilot-instructions.md` | RESOLVED | 2026-03-22 | 2026-03-22 |
| RCA-003 | REDUNDANCY | `sync-skills.yml` workflow auto-bumped the submodule pointer weekly but the skills submodule is intentionally pinned; the auto-sync conflicted with deliberate version control | `.github/workflows/sync-skills.yml` | RESOLVED | 2026-03-22 | 2026-03-22 |

## Applied Fixes

Changes implemented. Records what was changed and why, so future sessions do not redo or undo them without cause.

| ID | File | Change Summary | Root Cause ID | Date |
|----|------|----------------|---------------|------|
| FIX-001 | `.github/copilot-instructions.md` | Added **Mandatory skill usage** table to Using Skills section requiring `swe` before coding, `code-review` after changes, and `backlog-manager` for task tracking | RCA-001 | 2026-03-22 |
| FIX-002 | `.github/copilot-instructions.md` | Added verified-only constraint to Self-Improvement Mandate write rule: "Only write a memory when the fact is unequivocally verified — not planned, hypothetical, or inferred." | RCA-002 | 2026-03-22 |
| FIX-003 | `.github/workflows/sync-skills.yml` | Deleted the sync workflow; submodule pointer is now advanced manually when a Skills update is intentionally adopted | RCA-003 | 2026-03-22 |

## Ecosystem Reference Updates

When a Copilot ecosystem standard changes (new frontmatter field, deprecated tool name, new file format), record it here.

| Date | Change | Source |
|------|--------|--------|
| 2026-03-22 | `.agent.md` file format supported alongside `.yml` for custom agent definitions | GitHub Copilot docs |

## Open Questions

- Should `personal-assistant.yml` be converted to `.agent.md` format to align with the current Copilot agent spec, or kept as YAML for backwards compatibility? (Requires owner decision before rename.)
