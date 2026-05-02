#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIRS = [
    REPO_ROOT / "data" / "profiles",
    REPO_ROOT / "packages" / "api" / "data" / "profiles",
]
REPORT_PATH = REPO_ROOT / "data" / "audit_report.json"

BOILERPLATE_MARKERS = [
    "Source: http",
    "Agree & Join LinkedIn",
    "Sign in to LinkedIn",
    "Show me more content",
    "Subscribe to",
    "Cookie Policy",
    "# ",
    "## ",
]

URL_RE = re.compile(r"Source:\s*(https?://\S+)")
FIRST_PERSON_RE = re.compile(r"\b(I|we|my|our|i'm|i've)\b", re.IGNORECASE)
WS_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    return WS_RE.sub(" ", text.lower()).strip()


def load_profile(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def audit_profile(path: Path, profile: dict) -> dict:
    posts = profile.get("example_posts") or []
    posts = [p for p in posts if isinstance(p, str) and p.strip()]

    seen: dict[str, int] = {}
    dup_count = 0
    for p in posts:
        n = normalize(p)
        if n in seen:
            dup_count += 1
        else:
            seen[n] = 1

    boilerplate_total = 0
    boilerplate_per_marker: dict[str, int] = {m: 0 for m in BOILERPLATE_MARKERS}
    for p in posts:
        for marker in BOILERPLATE_MARKERS:
            if marker in p:
                boilerplate_total += 1
                boilerplate_per_marker[marker] += 1

    url_counts: Counter[str] = Counter()
    for p in posts:
        for m in URL_RE.finditer(p):
            url_counts[m.group(1)] += 1
    top_urls = url_counts.most_common(10)

    fp_hits = sum(1 for p in posts if FIRST_PERSON_RE.search(p))
    fp_rate = fp_hits / len(posts) if posts else 0.0

    lengths = [len(p) for p in posts]
    if lengths:
        sorted_len = sorted(lengths)
        p95 = sorted_len[int(0.95 * (len(sorted_len) - 1))]
        length_stats = {
            "min": min(lengths),
            "median": int(statistics.median(lengths)),
            "p95": int(p95),
            "max": max(lengths),
        }
    else:
        length_stats = {"min": 0, "median": 0, "p95": 0, "max": 0}

    return {
        "file": str(path.relative_to(REPO_ROOT)),
        "author": profile.get("author"),
        "platform": profile.get("platform"),
        "post_count": len(posts),
        "duplicate_count": dup_count,
        "boilerplate_marker_hits": boilerplate_total,
        "boilerplate_per_marker": boilerplate_per_marker,
        "top_source_urls": top_urls,
        "first_person_rate": round(fp_rate, 3),
        "length_stats": length_stats,
    }


def run_audit() -> dict:
    per_file = []
    for d in PROFILE_DIRS:
        if not d.exists():
            continue
        for path in sorted(d.glob("*.json")):
            prof = load_profile(path)
            if not prof:
                continue
            per_file.append(audit_profile(path, prof))

    by_author_platform: dict[tuple[str, str], dict] = defaultdict(lambda: {
        "post_count": 0,
        "duplicate_count": 0,
        "boilerplate_marker_hits": 0,
        "files": [],
    })
    for r in per_file:
        key = (r["author"] or "?", r["platform"] or "?")
        agg = by_author_platform[key]
        agg["post_count"] += r["post_count"]
        agg["duplicate_count"] += r["duplicate_count"]
        agg["boilerplate_marker_hits"] += r["boilerplate_marker_hits"]
        agg["files"].append(r["file"])

    totals = {
        "files": len(per_file),
        "posts": sum(r["post_count"] for r in per_file),
        "duplicates": sum(r["duplicate_count"] for r in per_file),
        "boilerplate_hits": sum(r["boilerplate_marker_hits"] for r in per_file),
    }

    return {
        "totals": totals,
        "by_author_platform": {
            f"{a}__{p}": v for (a, p), v in sorted(by_author_platform.items())
        },
        "per_file": per_file,
    }


def print_table(report: dict) -> None:
    print(f"\n{'='*100}")
    print(f"{'author__platform':<35} {'posts':>7} {'dups':>6} {'boiler':>7} {'fp_rate':>8} {'med_len':>8}")
    print(f"{'-'*100}")
    for r in report["per_file"]:
        key = f"{r['author']}__{r['platform']}"
        print(
            f"{key:<35} {r['post_count']:>7} {r['duplicate_count']:>6} "
            f"{r['boilerplate_marker_hits']:>7} {r['first_person_rate']:>8.3f} "
            f"{r['length_stats']['median']:>8}"
        )
    t = report["totals"]
    print(f"{'-'*100}")
    print(f"TOTALS  files={t['files']}  posts={t['posts']}  dups={t['duplicates']}  boiler={t['boilerplate_hits']}")
    print(f"{'='*100}\n")


def main() -> int:
    report = run_audit()
    print_table(report)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if REPORT_PATH.exists():
        try:
            existing = json.loads(REPORT_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            existing = {}

    label = sys.argv[1] if len(sys.argv) > 1 else "latest"
    existing[label] = report
    REPORT_PATH.write_text(json.dumps(existing, indent=2))
    print(f"Saved report under key '{label}' to {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
