"""One-shot script: scan local profile JSONs, embed every example_post,
and upsert into the configured Chroma collection.

Run from the repo root:

    python scripts/index_posts.py --dry-run
    python scripts/index_posts.py --author sam_altman
    python scripts/index_posts.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_SRC = REPO_ROOT / "packages" / "api" / "src"
sys.path.insert(0, str(API_SRC))


PROFILE_DIRS: list[Path] = [
    # Order matters for de-dupe: later entries WIN when keys collide. The
    # packages/api/data dir holds the larger scraped sets, so list it last.
    REPO_ROOT / "data" / "profiles",
    REPO_ROOT / "packages" / "api" / "data" / "profiles",
]


def _load_profile(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  ! skip {path.name}: {exc}", file=sys.stderr)
        return None


def collect_posts(author_filter: str | None = None) -> list:
    """Walk profile dirs and build a deduped list of IndexedPost.

    De-dupe key is (author, platform, post_index). When the same key exists in
    multiple source dirs, the file from the later directory in PROFILE_DIRS wins
    (so packages/api/data/profiles overrides data/profiles when both have it).
    """
    from writer_api.services.chroma_store import IndexedPost

    deduped: dict[tuple[str, str, int], IndexedPost] = {}

    for profile_dir in PROFILE_DIRS:
        if not profile_dir.exists():
            continue
        for json_path in sorted(profile_dir.glob("*.json")):
            profile = _load_profile(json_path)
            if not profile:
                continue

            author = profile.get("author")
            platform = profile.get("platform")
            if not author or not platform:
                continue
            if author_filter and author != author_filter:
                continue

            posts = profile.get("example_posts") or []
            for i, post_text in enumerate(posts):
                if not isinstance(post_text, str):
                    continue
                if not post_text.strip():
                    continue
                key = (author, platform, i)
                deduped[key] = IndexedPost(
                    id=f"{author}__{platform}__{i}",
                    text=post_text,
                    author=author,
                    platform=platform,
                    source_type="scraped",
                )

    return list(deduped.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Index profile posts into Chroma")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count + show summary without embedding or uploading.",
    )
    parser.add_argument(
        "--author",
        type=str,
        default=None,
        help="Only index posts for this author (e.g. sam_altman).",
    )
    args = parser.parse_args()

    posts = collect_posts(author_filter=args.author)

    by_author: dict[str, int] = {}
    for p in posts:
        by_author[p.author] = by_author.get(p.author, 0) + 1

    print(f"Loaded {len(posts)} posts across {len(by_author)} authors.")
    for author in sorted(by_author):
        print(f"  - {author}: {by_author[author]}")

    if args.dry_run:
        print("\n[dry-run] Skipping embedding + upsert.")
        return 0

    if not posts:
        print("No posts to index.")
        return 0

    from writer_api.services.chroma_store import ChromaStore

    store = ChromaStore()
    # Smaller batches to stay under Chroma free-tier per-request size limits.
    indexed = 0
    batch_size = 25
    for start in range(0, len(posts), batch_size):
        chunk = posts[start : start + batch_size]
        n = store.upsert_posts(chunk, batch_size=batch_size)
        indexed += n
        print(f"  upserted {indexed}/{len(posts)}", flush=True)
    total = store.count()
    print(
        f"\nIndexed {indexed} posts across {len(by_author)} authors. "
        f"Collection now has {total} docs."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
