"""
Lightweight memory and learning loop for the Personal Assistant agent.

Storage layout
--------------
.memory/
  facts/         One .md file per factual memory about the project/codebase.
  preferences/   One .md file per user/agent style preference.
  procedures/    One .md file per learned workflow or procedure.
  index.md       Human-readable index; also tracks interaction_count for compaction.

Each memory file uses YAML front-matter + a short Markdown body (≤200 tokens):

    ---
    id: mem_fact_001
    type: fact          # fact | preference | procedure
    confidence: 0.95    # 0.0–1.0
    created_at: YYYY-MM-DD
    last_updated: YYYY-MM-DD
    tags: [tag1, tag2]
    supersedes: null    # id of the entry this one replaces, or null
    ---

    One atomic statement here.

Runtime loop (how an agent uses this module)
--------------------------------------------
1. Call ``read_relevant(query)``        → get ≤5 files relevant to the task
2. Inject their content into the prompt
3. After generating a response, call ``write_memory(...)`` for each new insight
4. Every COMPACTION_INTERVAL interactions, call ``compact()``

Rules
-----
- One idea per file.  Do not write compound statements.
- Maximum ~200 tokens of body content.
- Do not store full transcripts, code blobs, or long prose.
- Reject writes that duplicate existing content (>80 % keyword overlap).
- Supersede, don't duplicate, when updating an existing memory.
"""

import logging
import re
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
MEMORY_DIR = REPO_ROOT / ".memory"
INDEX_PATH = MEMORY_DIR / "index.md"

SUBDIRS = ("facts", "preferences", "procedures")

# Trigger a compaction run after this many recorded interactions.
COMPACTION_INTERVAL = 20

# Drop memories whose confidence has fallen below this threshold AND that
# haven't been updated in STALE_DAYS days.
COMPACTION_MIN_CONFIDENCE = 0.3
STALE_DAYS = 30

# Maximum number of memory files to inject into a single prompt.
MAX_RETRIEVAL = 5

# If two memories share this fraction of keyword tokens, treat them as similar.
SIMILARITY_THRESHOLD = 0.80


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_dirs() -> None:
    """Create the .memory/ tree if it doesn't exist yet."""
    for sub in SUBDIRS:
        (MEMORY_DIR / sub).mkdir(parents=True, exist_ok=True)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML front-matter from Markdown body.

    Returns (meta_dict, body_text).  If no front-matter is found, returns
    ({}, text).
    """
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta: dict = {}
    for line in parts[1].splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            raw = val.strip()
            # Parse lists like [a, b, c]
            if raw.startswith("[") and raw.endswith("]"):
                meta[key.strip()] = [
                    t.strip() for t in raw[1:-1].split(",") if t.strip()
                ]
            elif raw.lower() == "null":
                meta[key.strip()] = None
            else:
                # Try numeric
                try:
                    meta[key.strip()] = float(raw) if "." in raw else int(raw)
                except ValueError:
                    meta[key.strip()] = raw

    return meta, parts[2].strip()


def _render_frontmatter(meta: dict, body: str) -> str:
    """Serialize meta dict + body back to a Markdown file string."""

    def _val(v: object) -> str:
        if v is None:
            return "null"
        if isinstance(v, list):
            return "[" + ", ".join(str(x) for x in v) + "]"
        return str(v)

    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {_val(v)}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    lines.append("")
    return "\n".join(lines)


def _keyword_tokens(text: str) -> set[str]:
    """Return a set of lowercase alphabetic tokens from text."""
    return {w.lower() for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 2}


def _similarity(a: str, b: str) -> float:
    """Jaccard similarity between keyword token sets of two strings."""
    ta, tb = _keyword_tokens(a), _keyword_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _all_memory_files() -> list[Path]:
    """Return all .md files in .memory/ subdirectories, sorted by path."""
    files: list[Path] = []
    for sub in SUBDIRS:
        files.extend(sorted((MEMORY_DIR / sub).glob("*.md")))
    return files


def _load_file(path: Path) -> tuple[dict, str]:
    """Read a memory file and return (meta, body)."""
    try:
        return _parse_frontmatter(path.read_text(encoding="utf-8"))
    except OSError as exc:
        logger.warning("Could not read memory file %s: %s", path, exc)
        return {}, ""


def _next_id(memory_type: str) -> str:
    """Generate the next sequential ID for a given memory type.

    Scans existing IDs to find the highest numeric suffix, then increments.
    """
    prefix_map = {"fact": "mem_fact", "preference": "mem_pref", "procedure": "mem_proc"}
    prefix = prefix_map.get(memory_type, "mem_misc")

    existing: list[int] = []
    for path in _all_memory_files():
        meta, _ = _load_file(path)
        mid = meta.get("id", "")
        if isinstance(mid, str) and mid.startswith(prefix + "_"):
            try:
                existing.append(int(mid[len(prefix) + 1 :]))
            except ValueError:
                pass

    next_num = max(existing, default=0) + 1
    return f"{prefix}_{next_num:03d}"


# ---------------------------------------------------------------------------
# Interaction counter (used to trigger compaction)
# ---------------------------------------------------------------------------


def _get_interaction_count() -> int:
    """Read the interaction_count from index.md."""
    if not INDEX_PATH.exists():
        return 0
    text = INDEX_PATH.read_text(encoding="utf-8")
    match = re.search(r"<!--\s*interaction_count:\s*(\d+)\s*-->", text)
    return int(match.group(1)) if match else 0


def _increment_interaction_count() -> int:
    """Increment the interaction_count in index.md and return the new value."""
    if not INDEX_PATH.exists():
        return 0
    text = INDEX_PATH.read_text(encoding="utf-8")
    count = _get_interaction_count() + 1
    text = re.sub(
        r"<!--\s*interaction_count:\s*\d+\s*-->",
        f"<!-- interaction_count: {count} -->",
        text,
    )
    INDEX_PATH.write_text(text, encoding="utf-8")
    return count


# ---------------------------------------------------------------------------
# Index update
# ---------------------------------------------------------------------------


def _rebuild_index() -> None:
    """Rewrite index.md to reflect the current set of memory files."""
    if not INDEX_PATH.exists():
        return  # index will be created by the repo; don't clobber setup

    existing = INDEX_PATH.read_text(encoding="utf-8")
    count = _get_interaction_count()
    last_compaction_match = re.search(
        r"<!--\s*last_compaction:\s*([^-]+?)\s*-->", existing
    )
    last_compaction = (
        last_compaction_match.group(1).strip() if last_compaction_match else "never"
    )

    rows: dict[str, list[str]] = {sub: [] for sub in SUBDIRS}
    for path in _all_memory_files():
        meta, _ = _load_file(path)
        if not meta:
            continue
        sub = path.parent.name
        if sub not in rows:
            continue
        tags = (
            ", ".join(meta.get("tags", []))
            if isinstance(meta.get("tags"), list)
            else ""
        )
        rel = f"{sub}/{path.name}"
        rows[sub].append(
            f"| {meta.get('id', '?')} | {rel} | {tags} "
            f"| {meta.get('confidence', '?')} | {meta.get('last_updated', '?')} |"
        )

    header = (
        "# .memory Index\n\n"
        "Auto-maintained index of all memory entries. Updated by `app/memory.py` on every "
        "write and compaction run.\n\n"
        f"<!-- interaction_count: {count} -->\n"
        f"<!-- last_compaction: {last_compaction} -->\n"
    )

    section_titles = {
        "facts": "Facts",
        "preferences": "Preferences",
        "procedures": "Procedures",
    }
    sections = []
    for sub, title in section_titles.items():
        table_rows = rows[sub]
        section = f"\n## {title}\n\n"
        if table_rows:
            section += "| ID | File | Tags | Confidence | Last Updated |\n"
            section += "|---|---|---|---|---|\n"
            section += "\n".join(table_rows) + "\n"
        else:
            section += "_No entries yet._\n"
        sections.append(section)

    INDEX_PATH.write_text(header + "".join(sections), encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def read_relevant(query: str, max_results: int = MAX_RETRIEVAL) -> list[dict]:
    """Return the top N memory entries most relevant to ``query``.

    Relevance score = keyword_similarity × confidence × recency_factor.

    Recency factor decays linearly: 1.0 for today, 0.5 after 365 days.

    Each returned dict has:
        id           – memory ID
        type         – fact | preference | procedure
        content      – body text
        confidence   – 0–1
        tags         – list of tag strings
        path         – Path object of the source file
        score        – composite relevance score
    """
    _ensure_dirs()
    today = date.today()
    results = []

    for path in _all_memory_files():
        meta, body = _load_file(path)
        if not meta or not body:
            continue

        sim = _similarity(query, body + " " + " ".join(meta.get("tags", [])))
        if sim == 0.0:
            continue

        confidence = float(meta.get("confidence", 0.5))

        # Recency factor
        try:
            updated = date.fromisoformat(str(meta.get("last_updated", today)))
            age_days = (today - updated).days
            recency = max(0.5, 1.0 - age_days / 730)  # halves over 2 years
        except (ValueError, TypeError):
            recency = 1.0

        score = sim * confidence * recency

        results.append(
            {
                "id": meta.get("id"),
                "type": meta.get("type"),
                "content": body,
                "confidence": confidence,
                "tags": meta.get("tags", []),
                "path": path,
                "score": score,
            }
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:max_results]


def write_memory(
    memory_type: str,
    content: str,
    confidence: float = 0.8,
    tags: Optional[list[str]] = None,
    supersedes: Optional[str] = None,
) -> Optional[str]:
    """Write a new memory entry or update an existing similar one.

    Returns the ID of the written or updated entry, or None if the write was
    rejected (e.g. duplicate content).

    Rules
    -----
    - Reject if ``content`` is empty or > 1000 characters.
    - Reject if an existing entry has > SIMILARITY_THRESHOLD keyword overlap
      with ``content`` AND its confidence is equal-or-higher (nothing new).
    - If an existing entry is highly similar but this one is an update
      (``supersedes`` is set, or confidence is higher), update in place.
    - Otherwise create a new file.
    """
    _ensure_dirs()

    content = content.strip()
    if not content:
        logger.debug("write_memory: rejected empty content")
        return None
    if len(content) > 1000:
        logger.debug(
            "write_memory: rejected — content too long (%d chars)", len(content)
        )
        return None

    type_to_dir = {
        "fact": "facts",
        "preference": "preferences",
        "procedure": "procedures",
    }
    subdir = type_to_dir.get(memory_type)
    if subdir is None:
        logger.warning("write_memory: unknown type %r", memory_type)
        return None

    today_str = date.today().isoformat()

    # Scan for similar existing entries
    for path in (MEMORY_DIR / subdir).glob("*.md"):
        meta, body = _load_file(path)
        if not meta:
            continue
        sim = _similarity(content, body)
        if sim >= SIMILARITY_THRESHOLD:
            existing_confidence = float(meta.get("confidence", 0.0))
            if supersedes is not None or confidence > existing_confidence:
                # Update in place
                meta["confidence"] = round(min(1.0, confidence), 2)
                meta["last_updated"] = today_str
                if supersedes:
                    meta["supersedes"] = supersedes
                path.write_text(_render_frontmatter(meta, content), encoding="utf-8")
                _rebuild_index()
                logger.info("write_memory: updated %s (sim=%.2f)", meta.get("id"), sim)
                return str(meta.get("id"))
            else:
                logger.debug(
                    "write_memory: rejected — duplicate of %s (sim=%.2f)",
                    meta.get("id"),
                    sim,
                )
                return None

    # Create new file
    new_id = _next_id(memory_type)
    meta = {
        "id": new_id,
        "type": memory_type,
        "confidence": round(min(1.0, max(0.0, confidence)), 2),
        "created_at": today_str,
        "last_updated": today_str,
        "tags": tags or [],
        "supersedes": supersedes,
    }
    filename = f"{new_id}.md"
    dest = MEMORY_DIR / subdir / filename
    dest.write_text(_render_frontmatter(meta, content), encoding="utf-8")

    count = _increment_interaction_count()
    _rebuild_index()
    logger.info("write_memory: created %s", new_id)

    if count > 0 and count % COMPACTION_INTERVAL == 0:
        logger.info("write_memory: interaction count %d — running compaction", count)
        compact()

    return new_id


def compact() -> dict:
    """Run a compaction pass over all memory files.

    Steps
    -----
    1. Delete entries with confidence < COMPACTION_MIN_CONFIDENCE that haven't
       been updated in STALE_DAYS days.
    2. Merge pairs of files with > SIMILARITY_THRESHOLD keyword overlap: keep
       the higher-confidence one, delete the other.

    Returns a summary dict: {deleted: int, merged: int}.
    """
    _ensure_dirs()
    today = date.today()
    deleted = 0
    merged = 0

    all_files = _all_memory_files()

    # Step 1 — remove stale low-confidence entries
    for path in all_files:
        meta, body = _load_file(path)
        if not meta:
            continue
        conf = float(meta.get("confidence", 1.0))
        try:
            updated = date.fromisoformat(str(meta.get("last_updated", today)))
            age = (today - updated).days
        except (ValueError, TypeError):
            age = 0

        if conf < COMPACTION_MIN_CONFIDENCE and age >= STALE_DAYS:
            path.unlink()
            deleted += 1
            logger.info(
                "compact: deleted stale entry %s (conf=%.2f, age=%d days)",
                meta.get("id"),
                conf,
                age,
            )

    # Step 2 — merge near-duplicates (re-scan after deletions)
    remaining = _all_memory_files()
    merged_ids: set[str] = set()

    for i, path_a in enumerate(remaining):
        if str(path_a) in merged_ids:
            continue
        meta_a, body_a = _load_file(path_a)
        if not meta_a:
            continue

        for path_b in remaining[i + 1 :]:
            if str(path_b) in merged_ids:
                continue
            meta_b, body_b = _load_file(path_b)
            if not meta_b:
                continue
            if path_a.parent != path_b.parent:  # only merge within same subdir
                continue

            sim = _similarity(body_a, body_b)
            if sim >= SIMILARITY_THRESHOLD:
                # Keep the higher-confidence entry; delete the other
                conf_a = float(meta_a.get("confidence", 0.0))
                conf_b = float(meta_b.get("confidence", 0.0))
                keep, drop = (path_a, path_b) if conf_a >= conf_b else (path_b, path_a)
                drop.unlink()
                merged_ids.add(str(drop))
                merged += 1
                logger.info(
                    "compact: merged %s into %s (sim=%.2f)", drop.name, keep.name, sim
                )

    # Update last_compaction timestamp in index
    if INDEX_PATH.exists():
        text = INDEX_PATH.read_text(encoding="utf-8")
        text = re.sub(
            r"<!--\s*last_compaction:\s*[^-]+?-->",
            f"<!-- last_compaction: {today.isoformat()} -->",
            text,
        )
        INDEX_PATH.write_text(text, encoding="utf-8")

    _rebuild_index()
    logger.info("compact: done — deleted=%d merged=%d", deleted, merged)
    return {"deleted": deleted, "merged": merged}


def load_context_for_prompt(query: str) -> str:
    """Return a formatted string ready to inject into an LLM prompt.

    Format
    ------
    <memory>
    [fact] content... (confidence: 0.95)
    [preference] content... (confidence: 0.9)
    </memory>

    Returns an empty string when no relevant memories are found.
    """
    entries = read_relevant(query)
    if not entries:
        return ""

    lines = ["<memory>"]
    for entry in entries:
        lines.append(
            f"[{entry['type']}] {entry['content']} (confidence: {entry['confidence']})"
        )
    lines.append("</memory>")
    return "\n".join(lines)
