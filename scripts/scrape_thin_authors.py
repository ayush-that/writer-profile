#!/usr/bin/env python3
"""Scrape more posts for the thinnest-data authors using Exa.

Currently targeting:
- matei_zaharia (only 3 posts total, has no linkedin profile at all)
- dario_amodei twitter (only 6 posts)

Reuses the existing scrape patterns: searches with Exa, cleans, dedupes against
existing example_posts, and appends. Writes back to packages/api/data/profiles.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from exa_py import Exa

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")

EXA_API_KEY = os.environ.get("EXA_API_KEY")
PROFILES_DIR = REPO_ROOT / "packages" / "api" / "data" / "profiles"

# Per-author scraping plan: queries + (optional) include_domains.
# Each entry produces additional example_posts on top of the existing file.
PLAN: dict[str, dict] = {
    "matei_zaharia__twitter": {
        "name": "Matei Zaharia",
        "company": "Databricks Spark MLflow",
        "queries": [
            "Matei Zaharia interview Databricks AI systems",
            "Matei Zaharia quote compound AI systems",
            "Matei Zaharia keynote talk MLflow Spark",
            "Matei Zaharia podcast interview",
            "Matei Zaharia blog post Databricks AI",
        ],
        "include_domains": None,
        "min_text_len": 200,
        "max_text_len": 2500,
    },
    "matei_zaharia__linkedin": {
        # No existing file: we'll create one from scratch using the same scrape
        # patterns, then attach the standard voice profile boilerplate.
        "name": "Matei Zaharia",
        "company": "Databricks Spark MLflow",
        "queries": [
            "Matei Zaharia LinkedIn post Databricks",
            "Matei Zaharia CTO Databricks talk transcript",
            "Matei Zaharia AI systems essay blog",
            "Matei Zaharia keynote Spark Summit Data AI",
            "Matei Zaharia interview thoughts on AI",
            "Matei Zaharia podcast appearance transcript",
        ],
        "include_domains": None,
        "min_text_len": 250,
        "max_text_len": 3000,
        "create_if_missing": True,
    },
    "dario_amodei__twitter": {
        "name": "Dario Amodei",
        "company": "Anthropic",
        "queries": [
            "Dario Amodei tweet AI safety",
            "Dario Amodei quote interview Anthropic",
            "Dario Amodei essay machines of loving grace",
            "Dario Amodei interview transcript",
            "Dario Amodei statement on AI policy",
        ],
        "include_domains": None,
        "min_text_len": 150,
        "max_text_len": 2000,
    },
    "brian_chesky__twitter": {
        "name": "Brian Chesky",
        "company": "Airbnb",
        "queries": [
            "Brian Chesky quote leadership Airbnb",
            "Brian Chesky tweet design product",
            "Brian Chesky interview founder mode",
            "Brian Chesky keynote Airbnb release",
        ],
        "include_domains": None,
        "min_text_len": 150,
        "max_text_len": 2000,
    },
    "sam_altman__twitter": {
        "name": "Sam Altman",
        "company": "OpenAI",
        "queries": [
            "Sam Altman tweet OpenAI",
            "Sam Altman quote AGI safety",
            "Sam Altman blog post startups",
            "Sam Altman statement ChatGPT",
        ],
        "include_domains": None,
        "min_text_len": 150,
        "max_text_len": 2000,
    },
    "tobi_lutke__twitter": {
        "name": "Tobi Lutke",
        "company": "Shopify",
        "queries": [
            "Tobi Lutke tweet Shopify",
            "Tobi Lutke quote founder commerce",
            "Tobi Lutke interview leadership",
            "Tobi Lutke memo employees AI",
        ],
        "include_domains": None,
        "min_text_len": 150,
        "max_text_len": 2000,
    },
}


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()[:300]


def clean_content(text: str, name: str) -> str:
    name_parts = [p.lower() for p in name.split()]
    if not any(p in text.lower() for p in name_parts):
        return ""
    skip = (
        "cookie", "privacy policy", "terms of service", "subscribe",
        "newsletter", "sign up", "log in", "copyright", "all rights reserved",
        "advertisement", "sponsored", "click here", "follow us", "share this",
        "[music]", "[applause]",
    )
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if len(s) < 20:
            continue
        sl = s.lower()
        if any(p in sl for p in skip):
            continue
        out.append(s)
    return "\n".join(out)


def scrape_for(exa: Exa, cfg: dict, max_per_query: int = 10) -> list[str]:
    name = cfg["name"]
    out: list[str] = []
    for q in cfg["queries"]:
        try:
            kwargs = dict(query=q, type="auto", num_results=max_per_query, text=True)
            if cfg.get("include_domains"):
                kwargs["include_domains"] = cfg["include_domains"]
            results = exa.search_and_contents(**kwargs)
            for r in results.results:
                if not r.text:
                    continue
                cleaned = clean_content(r.text, name)
                if not cleaned:
                    continue
                if len(cleaned) < cfg.get("min_text_len", 200):
                    continue
                max_len = cfg.get("max_text_len", 3000)
                if len(cleaned) > max_len:
                    cleaned = cleaned[:max_len] + "..."
                out.append(cleaned)
            print(f"    [{q!r}] -> {len(results.results)} hits")
        except Exception as e:
            print(f"    [{q!r}] error: {e}")
    return out


def dedupe_append(existing: list[str], new: list[str]) -> tuple[list[str], int]:
    seen = {normalize(p) for p in existing}
    added: list[str] = []
    for post in new:
        n = normalize(post)
        if n in seen or len(n) < 20:
            continue
        seen.add(n)
        added.append(post)
    return existing + added, len(added)


DEFAULT_PROFILE_TEMPLATE = {
    "lexical": {
        "vocabulary_level": "professional",
        "recurring_phrases": [],
        "word_preferences": {},
        "jargon_usage": "moderate",
        "technicality_level": "accessible",
    },
    "structural": {
        "avg_sentence_length": 15,
        "paragraph_style": "medium",
        "opening_patterns": [],
        "closing_patterns": [],
        "uses_lists": True,
        "uses_questions": True,
    },
    "tonal": {
        "warmth_level": "professional",
        "humor_usage": "rare",
        "personal_disclosure": "moderate",
        "conviction_style": "confident",
    },
}


def load_or_init(file_key: str, cfg: dict) -> dict | None:
    path = PROFILES_DIR / f"{file_key}.json"
    if path.exists():
        with path.open() as f:
            return json.load(f)
    if cfg.get("create_if_missing"):
        author, platform = file_key.split("__", 1)
        prof = {"author": author, "platform": platform, **DEFAULT_PROFILE_TEMPLATE,
                "example_posts": []}
        return prof
    print(f"  ! {path.name} missing and create_if_missing=False")
    return None


def save(file_key: str, profile: dict) -> None:
    path = PROFILES_DIR / f"{file_key}.json"
    with path.open("w") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print(f"  saved {path.name}")


def main() -> int:
    if not EXA_API_KEY:
        print("ERROR: EXA_API_KEY not set")
        return 1
    exa = Exa(api_key=EXA_API_KEY)
    summary: dict[str, tuple[int, int]] = {}
    for file_key, cfg in PLAN.items():
        print(f"\n=== {file_key} ===")
        prof = load_or_init(file_key, cfg)
        if prof is None:
            continue
        before = len(prof.get("example_posts", []))
        new = scrape_for(exa, cfg)
        merged, added = dedupe_append(prof.get("example_posts", []), new)
        prof["example_posts"] = merged
        save(file_key, prof)
        after = len(merged)
        summary[file_key] = (before, after)
        print(f"  before={before}  added={added}  after={after}")
    print("\n=== SUMMARY ===")
    for k, (b, a) in summary.items():
        print(f"  {k}: {b} -> {a}  (+{a - b})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
