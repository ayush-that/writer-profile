#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

from exa_py import Exa

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = REPO_ROOT / "packages" / "api" / "data" / "profiles"

EXA_API_KEY = os.environ.get("EXA_API_KEY")

AUTHOR_SOURCES: dict[str, dict] = {
    "sam_altman": {
        "name": "Sam Altman",
        "domains": ["blog.samaltman.com", "samaltman.com", "ia.samaltman.com", "lexfridman.com"],
        "queries": [
            "Sam Altman blog post essay personal",
            "Sam Altman Lex Fridman podcast transcript",
            "Sam Altman All-In podcast quotes",
        ],
    },
    "tobi_lutke": {
        "name": "Tobi Lutke",
        "domains": ["tobi.lutke.com", "lexfridman.com", "shopify.com"],
        "queries": [
            "Tobi Lutke blog essay",
            "Tobi Lutke Lex Fridman podcast transcript",
            "Tobi Lutke interview Shopify founder",
        ],
    },
    "patrick_collison": {
        "name": "Patrick Collison",
        "domains": ["patrickcollison.com", "stripe.com", "paulgraham.com", "lexfridman.com"],
        "queries": [
            "Patrick Collison essay blog",
            "Patrick Collison Lex Fridman podcast transcript",
            "Patrick Collison interview Stripe founder quotes",
        ],
    },
    "brian_chesky": {
        "name": "Brian Chesky",
        "domains": ["paulgraham.com", "airbnb.com", "lexfridman.com", "ycombinator.com"],
        "queries": [
            "Brian Chesky founder mode essay quotes",
            "Brian Chesky Lex Fridman podcast transcript",
            "Brian Chesky interview Airbnb founder",
        ],
    },
    "dario_amodei": {
        "name": "Dario Amodei",
        "domains": ["darioamodei.com", "anthropic.com", "lexfridman.com"],
        "queries": [
            "Dario Amodei essay machines of loving grace",
            "Dario Amodei Lex Fridman podcast transcript",
            "Dario Amodei interview Anthropic interpretability",
        ],
    },
    "matei_zaharia": {
        "name": "Matei Zaharia",
        "domains": ["databricks.com", "people.csail.mit.edu", "cs.stanford.edu", "spark.apache.org"],
        "queries": [
            "Matei Zaharia Databricks blog post",
            "Matei Zaharia interview Spark Databricks",
            "Matei Zaharia compound AI systems essay",
            "Matei Zaharia talk transcript",
        ],
    },
    "elon_musk": {
        "name": "Elon Musk",
        "domains": ["tesla.com", "spacex.com", "lexfridman.com"],
        "queries": [
            "Elon Musk Tesla master plan blog",
            "Elon Musk Lex Fridman podcast transcript",
        ],
    },
    "guillermo_rauch": {
        "name": "Guillermo Rauch",
        "domains": ["rauchg.com", "vercel.com", "nextjs.org"],
        "queries": [
            "Guillermo Rauch blog essay rauchg",
            "Guillermo Rauch Vercel Next.js post",
        ],
    },
    "satya_nadella": {
        "name": "Satya Nadella",
        "domains": ["microsoft.com", "lexfridman.com", "blogs.microsoft.com"],
        "queries": [
            "Satya Nadella Microsoft annual letter",
            "Satya Nadella Lex Fridman podcast transcript",
        ],
    },
    "aravind_srinivas": {
        "name": "Aravind Srinivas",
        "domains": ["perplexity.ai", "lexfridman.com"],
        "queries": [
            "Aravind Srinivas Perplexity blog interview",
            "Aravind Srinivas Lex Fridman podcast transcript",
        ],
    },
    "ali_ghodsi": {
        "name": "Ali Ghodsi",
        "domains": ["databricks.com"],
        "queries": [
            "Ali Ghodsi Databricks blog interview",
            "Ali Ghodsi data lakehouse essay",
        ],
    },
}

WS = re.compile(r"\s+")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def normalize(text: str) -> str:
    return WS.sub(" ", text.lower()).strip()


def chunk_text(text: str, target_min: int = 200, target_max: int = 500) -> list[str]:
    text = WS.sub(" ", text).strip()
    if len(text) <= target_max:
        return [text] if len(text) >= target_min else []

    sents = SENT_SPLIT.split(text)
    chunks: list[str] = []
    cur = ""
    for s in sents:
        s = s.strip()
        if not s:
            continue
        if len(cur) + len(s) + 1 <= target_max:
            cur = (cur + " " + s).strip()
        else:
            if len(cur) >= target_min:
                chunks.append(cur)
            cur = s
    if len(cur) >= target_min:
        chunks.append(cur)
    return chunks


def load_profile(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_profile(path: Path, profile: dict) -> None:
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False))


def existing_norms(profile: dict) -> set[str]:
    out: set[str] = set()
    for p in profile.get("example_posts") or []:
        if isinstance(p, str):
            out.add(normalize(p)[:200])
    return out


def fetch(exa: Exa, query: str, domains: list[str], num: int = 10) -> list[dict]:
    try:
        res = exa.search_and_contents(
            query=query,
            type="auto",
            num_results=num,
            include_domains=domains,
            text=True,
        )
    except Exception as exc:
        print(f"    ! exa error: {exc}")
        return []

    out = []
    for r in res.results:
        if r.text and len(r.text.strip()) > 200:
            out.append({"text": r.text, "url": r.url or "", "title": r.title or ""})
    return out


def scrape_author(exa: Exa, author: str, info: dict, target_dirs: list[str]) -> int:
    added_total = 0
    for platform in target_dirs:
        path = PROFILES_DIR / f"{author}__{platform}.json"
        if not path.exists():
            continue
        profile = load_profile(path)
        if not profile:
            continue

        seen = existing_norms(profile)
        new_chunks: list[str] = []

        for q in info["queries"]:
            print(f"  query: {q}")
            results = fetch(exa, q, info["domains"], num=8)
            print(f"    got {len(results)} results")
            for r in results:
                for ch in chunk_text(r["text"]):
                    nrm = normalize(ch)[:200]
                    if nrm in seen:
                        continue
                    seen.add(nrm)
                    new_chunks.append(ch)
            time.sleep(1.0)

        if not new_chunks:
            print(f"  no new chunks for {author}__{platform}")
            continue

        max_add = 80 if platform == "linkedin" else 60
        new_chunks = new_chunks[:max_add]

        profile["example_posts"] = (profile.get("example_posts") or []) + new_chunks
        save_profile(path, profile)
        print(f"  + added {len(new_chunks)} chunks to {path.name}")
        added_total += len(new_chunks)
    return added_total


def main() -> int:
    if not EXA_API_KEY:
        print("Error: EXA_API_KEY not set")
        return 1

    only = sys.argv[1] if len(sys.argv) > 1 else None
    exa = Exa(api_key=EXA_API_KEY)

    grand = 0
    for author, info in AUTHOR_SOURCES.items():
        if only and author != only:
            continue
        print(f"\n=== {info['name']} ({author}) ===")
        added = scrape_author(exa, author, info, target_dirs=["linkedin", "twitter"])
        grand += added
    print(f"\nTotal new chunks added: {grand}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
