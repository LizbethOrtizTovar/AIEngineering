"""Compare two texts via OpenAI embeddings (cosine similarity, stdlib only).

Usage (from the repo root):
    uv run python scripts/compare.py --text-a "..." --text-b "..."
    uv run python scripts/compare.py --sanity-check   # runs the 3 official pairs
                                                       # and writes SANITY_CHECK.md
"""
import argparse
import math
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # allow `from app...` when run as a script

from app.embedding_pipeline.embedder import EMBEDDING_MODEL, OpenAIEmbedder  # noqa: E402

SANITY_FILE = ROOT / "app" / "embedding_pipeline" / "SANITY_CHECK.md"
AUTH_TEXT = "OAuth 2.0 authentication backend with JWT tokens for fintech mobile app"
SANITY_PAIRS = [
    ("A", "Semantically close (expected > 0.6)", AUTH_TEXT,
     "Authorization service using JSON Web Tokens for a banking application"),
    ("B", "Unrelated (expected < 0.4)", AUTH_TEXT,
     "Database migration from MySQL to PostgreSQL with zero downtime"),
    ("C", "Generic / ambiguous (no fixed expectation)", "Backend services", "API development"),
]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """dot(A, B) / (||A|| * ||B||)."""
    if len(vec_a) != len(vec_b):
        raise ValueError("Vectors must have the same dimensionality")
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        raise ValueError("Cannot compute similarity for zero-norm vectors")
    return dot / (norm_a * norm_b)


def compare(embedder: OpenAIEmbedder, text_a: str, text_b: str) -> float:
    return cosine_similarity(embedder.embed_one(text_a), embedder.embed_one(text_b))


def run_sanity_check(embedder: OpenAIEmbedder) -> None:
    rows = []
    for pair_id, label, text_a, text_b in SANITY_PAIRS:
        sim = compare(embedder, text_a, text_b)
        rows.append((pair_id, label, text_a, text_b, sim))
        print(f"Pair {pair_id}: {sim:.4f}  ({label})")

    table = "\n".join(
        f"| {pid} | {label} | {a} | {b} | **{sim:.4f}** |" for pid, label, a, b, sim in rows
    )
    SANITY_FILE.write_text(
        f"# Sanity check — embeddings\n\n"
        f"**Date:** {date.today().isoformat()} · **Model:** `{EMBEDDING_MODEL}` (1536d) · "
        f"**Metric:** cosine similarity\n\n"
        f"| Pair | Type | Text 1 | Text 2 | Cosine |\n|---|---|---|---|---|\n{table}\n\n"
        f"## Comentario\n\n_TODO: 3-5 líneas sobre si los resultados encajan con la intuición "
        f"y qué llama la atención._\n",
        encoding="utf-8",
    )
    print(f"\nWritten: {SANITY_FILE.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cosine similarity between two texts.")
    parser.add_argument("--text-a")
    parser.add_argument("--text-b")
    parser.add_argument("--sanity-check", action="store_true",
                        help="Run the 3 official pairs and write SANITY_CHECK.md")
    args = parser.parse_args()

    embedder = OpenAIEmbedder()
    if args.sanity_check:
        run_sanity_check(embedder)
        return
    if not (args.text_a and args.text_b):
        parser.error("--text-a and --text-b are required (or use --sanity-check)")

    sim = compare(embedder, args.text_a, args.text_b)
    print(f"Text A: {args.text_a}")
    print(f"Text B: {args.text_b}")
    print(f"Cosine similarity: {sim:.4f}")


if __name__ == "__main__":
    main()
