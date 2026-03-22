"""
Semantic search over the Research submodule.

How it works
------------
1. ``build_index()`` walks every ``.md`` file under ``RESEARCH_DIR``, splits
   each file into sections (one per heading), and uses a sentence-transformer
   model to compute a vector embedding for each section.  The embeddings and
   accompanying metadata are saved to ``data/``.

2. ``search(query, top_k)`` embeds the query with the same model, computes
   cosine similarity against all stored embeddings, and returns the top-K
   matching sections with file path, heading, and a short excerpt.

Storage
-------
data/search_embeddings.npy   float32 array  (n_chunks × embedding_dim)
data/search_chunks.json      list of {path, heading, text} dicts

Both files are gitignored.  Run ``setup.sh`` (or POST /api/index/rebuild)
to populate them after cloning the repo.

Model
-----
all-MiniLM-L6-v2 (~80 MB, downloaded from HuggingFace on first use).
Swap the MODEL_NAME constant to use any sentence-transformers-compatible model.
"""

import json
import re
from pathlib import Path
from typing import Optional

import numpy as np

REPO_ROOT = Path(__file__).parent.parent
RESEARCH_DIR = REPO_ROOT / "research"
DATA_DIR = REPO_ROOT / "data"
EMBEDDINGS_PATH = DATA_DIR / "search_embeddings.npy"
CHUNKS_PATH = DATA_DIR / "search_chunks.json"

MODEL_NAME = "all-MiniLM-L6-v2"

# Lazy-loaded model – imported and instantiated only when first needed so that
# the app starts instantly and the heavy import happens in the background.
_model = None


def _get_model():
    """Return the SentenceTransformer model, loading it on first call."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


# ---------------------------------------------------------------------------
# Markdown chunking
# ---------------------------------------------------------------------------

def _split_markdown(text: str, file_path: str) -> list[dict]:
    """Split a markdown document into sections at each heading boundary.

    Each returned chunk has:
        path     – relative path to the source file
        heading  – the section heading (empty string for pre-heading content)
        text     – the full section text (heading + body)

    Sections shorter than MIN_CHUNK_CHARS are merged into the previous section
    to avoid indexing near-empty entries.
    """
    MIN_CHUNK_CHARS = 40

    lines = text.splitlines(keepends=True)
    sections: list[dict] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in lines:
        heading_match = re.match(r"^(#{1,3})\s+(.*)", line)
        if heading_match:
            # Flush the current section
            body = "".join(current_lines).strip()
            if body or current_heading:
                sections.append({
                    "path": file_path,
                    "heading": current_heading,
                    "text": (f"# {current_heading}\n\n" if current_heading else "") + body,
                })
            current_heading = heading_match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Flush the last section
    body = "".join(current_lines).strip()
    if body or current_heading:
        sections.append({
            "path": file_path,
            "heading": current_heading,
            "text": (f"# {current_heading}\n\n" if current_heading else "") + body,
        })

    # Merge tiny sections into the previous one
    merged: list[dict] = []
    for sec in sections:
        if merged and len(sec["text"]) < MIN_CHUNK_CHARS:
            merged[-1]["text"] += "\n\n" + sec["text"]
        else:
            merged.append(sec)

    return merged


def _collect_chunks() -> list[dict]:
    """Return all chunks from every .md file under RESEARCH_DIR."""
    if not RESEARCH_DIR.exists():
        return []

    chunks: list[dict] = []
    for md_file in sorted(RESEARCH_DIR.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel_path = str(md_file.relative_to(REPO_ROOT))
        chunks.extend(_split_markdown(text, rel_path))

    return chunks


# ---------------------------------------------------------------------------
# Index build / load
# ---------------------------------------------------------------------------

def build_index() -> int:
    """(Re)build the search index from the Research submodule.

    Returns the number of chunks indexed.
    Raises RuntimeError if the research directory is missing.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    chunks = _collect_chunks()
    if not chunks:
        # Write empty index so search() can run without crashing
        np.save(EMBEDDINGS_PATH, np.zeros((0, 384), dtype=np.float32))
        CHUNKS_PATH.write_text("[]", encoding="utf-8")
        return 0

    model = _get_model()
    texts = [c["text"] for c in chunks]

    print(f"[search] Embedding {len(chunks)} chunks …")
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # pre-normalise so dot product == cosine sim
    )

    np.save(EMBEDDINGS_PATH, embeddings.astype(np.float32))
    CHUNKS_PATH.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[search] Index saved ({len(chunks)} chunks).")
    return len(chunks)


def _load_index() -> tuple[Optional[np.ndarray], list[dict]]:
    """Load embeddings and chunk metadata from disk.

    Returns (None, []) if the index has not been built yet.
    """
    if not EMBEDDINGS_PATH.exists() or not CHUNKS_PATH.exists():
        return None, []

    embeddings = np.load(EMBEDDINGS_PATH)
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    return embeddings, chunks


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def search(query: str, top_k: int = 10) -> list[dict]:
    """Return up to ``top_k`` chunks most semantically similar to ``query``.

    Each result dict contains:
        path     – relative file path
        heading  – section heading
        excerpt  – first 300 characters of the section body
        score    – cosine similarity in [0, 1]

    Returns an empty list when the index is empty or does not exist.
    """
    embeddings, chunks = _load_index()
    if embeddings is None or len(embeddings) == 0:
        return []

    model = _get_model()
    query_vec = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0]  # shape: (dim,)

    # Cosine similarity (embeddings are already L2-normalised)
    scores = embeddings @ query_vec  # shape: (n_chunks,)

    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        chunk = chunks[idx]
        body = chunk["text"]
        # Strip the heading line from the excerpt to avoid repetition
        body_lines = body.splitlines()
        excerpt_lines = [l for l in body_lines if not l.startswith("#")]
        excerpt = " ".join(excerpt_lines).strip()[:300]
        results.append({
            "path": chunk["path"],
            "heading": chunk["heading"],
            "excerpt": excerpt,
            "score": float(round(scores[idx], 4)),
        })

    return results


def index_status() -> dict:
    """Return a summary of the current index state for display in the UI."""
    embeddings, chunks = _load_index()
    if embeddings is None:
        return {"built": False, "chunks": 0}
    return {"built": True, "chunks": len(chunks)}
