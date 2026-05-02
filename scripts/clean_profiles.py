#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = REPO_ROOT / "packages" / "api" / "data" / "profiles"
API_SRC = REPO_ROOT / "packages" / "api" / "src"
sys.path.insert(0, str(API_SRC))

LINE_PATTERNS = [
    re.compile(r"^Source:\s*https?://\S+\s*$", re.MULTILINE),
    re.compile(r"^Published:\s*\S+.*$", re.MULTILINE),
    re.compile(r"^#{1,6}\s+.+$", re.MULTILINE),
]

INLINE_PATTERNS = [
    re.compile(r"Agree & Join LinkedIn.*", re.IGNORECASE),
    re.compile(r"Sign in to LinkedIn.*", re.IGNORECASE),
    re.compile(r"Show me more content from.*", re.IGNORECASE),
    re.compile(r"Cookie Policy.*", re.IGNORECASE),
    re.compile(r"By clicking Continue.*", re.IGNORECASE),
    re.compile(r"To view or add a comment,\s*sign in.*", re.IGNORECASE),
    re.compile(r"Subscribe to.*newsletter.*", re.IGNORECASE),
]

MULTI_NL = re.compile(r"\n{3,}")
WS = re.compile(r"\s+")
FIRST_PERSON = re.compile(r"\b(I|we|my|our|i'm|i've|me|us|mine|ours)\b", re.IGNORECASE)


def normalize(text: str) -> str:
    return WS.sub(" ", text.lower()).strip()


def strip_boilerplate(text: str) -> str:
    out = text
    for pat in LINE_PATTERNS:
        out = pat.sub("", out)
    for pat in INLINE_PATTERNS:
        out = pat.sub("", out)
    out = MULTI_NL.sub("\n\n", out)
    return out.strip()


def first_name(author: str) -> str:
    return author.split("_")[0]


def is_about_author(text: str, author: str) -> bool:
    if len(text) <= 300:
        return False
    fn = first_name(author).lower()
    third = len(re.findall(rf"\b{re.escape(fn)}\b", text, re.IGNORECASE))
    first = len(FIRST_PERSON.findall(text))
    return third > 1.5 * max(first, 1) and third >= 2


def load_profile(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  ! skip {path.name}: {exc}", file=sys.stderr)
        return None


def save_profile(path: Path, profile: dict) -> None:
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False))


def clean_profile(path: Path) -> dict:
    profile = load_profile(path)
    if not profile:
        return {"file": path.name, "error": "load_failed"}

    author = profile.get("author") or ""
    posts = profile.get("example_posts") or []

    before_n = len(posts)

    cleaned: list[str] = []
    flags: list[bool] = []
    for raw in posts:
        if not isinstance(raw, str):
            continue
        stripped = strip_boilerplate(raw)
        if len(stripped) < 30:
            continue
        cleaned.append(stripped)
        flags.append(is_about_author(stripped, author))

    by_count = sum(1 for f in flags if not f)
    about_count = sum(1 for f in flags if f)

    if by_count > 50:
        kept = [p for p, f in zip(cleaned, flags) if not f]
        about_kept = []
    else:
        kept = [p for p, f in zip(cleaned, flags) if not f]
        about_kept = [p for p, f in zip(cleaned, flags) if f]

    seen: dict[str, int] = {}
    deduped: list[str] = []
    dups_dropped = 0
    for p in kept + about_kept:
        n = normalize(p)
        if n in seen:
            dups_dropped += 1
            continue
        seen[n] = 1
        deduped.append(p)

    profile["example_posts"] = deduped
    save_profile(path, profile)

    return {
        "file": path.name,
        "before": before_n,
        "after": len(deduped),
        "by_kept": by_count,
        "about_kept": len(about_kept),
        "dups_dropped": dups_dropped,
    }


def cosine(a: list[float], b: list[float]) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def near_dedup_and_source_cap(rate_sleep: float = 1.5) -> dict:
    from writer_api.services.embeddings import EmbeddingClient

    client = EmbeddingClient()
    summary: dict[str, dict] = {}

    by_author: dict[str, list[Path]] = {}
    for path in sorted(PROFILES_DIR.glob("*.json")):
        prof = load_profile(path)
        if not prof:
            continue
        author = prof.get("author")
        if author:
            by_author.setdefault(author, []).append(path)

    for author, paths in by_author.items():
        author_summary = {"near_dups_dropped": 0, "source_capped": 0}
        for path in paths:
            prof = load_profile(path)
            if not prof:
                continue
            posts: list[str] = prof.get("example_posts") or []
            if len(posts) <= 1:
                continue

            url_re = re.compile(r"(https?://\S+)")
            url_groups: dict[str, list[int]] = {}
            for i, p in enumerate(posts):
                m = url_re.search(p)
                if m:
                    url_groups.setdefault(m.group(1), []).append(i)

            drop_idx: set[int] = set()
            for url, idxs in url_groups.items():
                if len(idxs) <= 10:
                    continue
                ranked = sorted(idxs, key=lambda i: -len(posts[i]))
                for i in ranked[10:]:
                    drop_idx.add(i)
                    author_summary["source_capped"] += 1

            kept_posts = [p for i, p in enumerate(posts) if i not in drop_idx]

            embeddings: list[list[float]] = []
            batch = 25
            for start in range(0, len(kept_posts), batch):
                chunk = kept_posts[start : start + batch]
                truncated = [t[:8000] for t in chunk]
                try:
                    embs = client.embed(truncated)
                except Exception as exc:
                    print(f"  ! embed failed for {path.name} batch {start}: {exc}", file=sys.stderr)
                    embs = [[0.0] * client.dimension for _ in chunk]
                embeddings.extend(embs)
                time.sleep(rate_sleep)

            n = len(kept_posts)
            drop2: set[int] = set()
            for i in range(n):
                if i in drop2:
                    continue
                for j in range(i + 1, n):
                    if j in drop2:
                        continue
                    sim = cosine(embeddings[i], embeddings[j])
                    if sim > 0.92:
                        if len(kept_posts[i]) >= len(kept_posts[j]):
                            drop2.add(j)
                        else:
                            drop2.add(i)
                            break
            final_posts = [p for i, p in enumerate(kept_posts) if i not in drop2]
            author_summary["near_dups_dropped"] += len(drop2)

            prof["example_posts"] = final_posts
            save_profile(path, prof)
            print(f"  {path.name}: kept={len(final_posts)} (near_dups dropped={len(drop2)}, source_capped={len(drop_idx)})")

        summary[author] = author_summary
    return summary


def run_basic_cleanup() -> list[dict]:
    results = []
    for path in sorted(PROFILES_DIR.glob("*.json")):
        r = clean_profile(path)
        results.append(r)
        if "error" not in r:
            print(f"  {r['file']}: {r['before']} -> {r['after']} (dups={r['dups_dropped']}, about_kept={r['about_kept']})")
    return results


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "basic"
    if mode == "basic":
        print("Phase A: boilerplate strip + about-vs-by + exact dedup")
        results = run_basic_cleanup()
        total_before = sum(r.get("before", 0) for r in results)
        total_after = sum(r.get("after", 0) for r in results)
        print(f"\nTotal: {total_before} -> {total_after}")
    elif mode == "near":
        print("Phase B: near-dup detection + source cap (uses embeddings)")
        rate_sleep = float(os.environ.get("EMBED_RATE_SLEEP", "1.5"))
        summary = near_dedup_and_source_cap(rate_sleep=rate_sleep)
        for a, s in summary.items():
            print(f"  {a}: near_dups={s['near_dups_dropped']}, source_capped={s['source_capped']}")
    else:
        print(f"unknown mode: {mode}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
