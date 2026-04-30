#!/usr/bin/env python3
"""Scrape YouTube video transcripts using Exa API and add to existing profiles."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from exa_py import Exa

EXA_API_KEY = os.environ.get("EXA_API_KEY")
PROFILES_DIR = Path(__file__).parent.parent / "packages" / "api" / "data" / "profiles"

CEOS = {
    "sam_altman": {"name": "Sam Altman", "role": "CEO OpenAI"},
    "elon_musk": {"name": "Elon Musk", "role": "CEO Tesla SpaceX X"},
    "brian_chesky": {"name": "Brian Chesky", "role": "CEO Airbnb"},
    "guillermo_rauch": {"name": "Guillermo Rauch", "role": "CEO Vercel"},
    "dario_amodei": {"name": "Dario Amodei", "role": "CEO Anthropic"},
    "satya_nadella": {"name": "Satya Nadella", "role": "CEO Microsoft"},
    "patrick_collison": {"name": "Patrick Collison", "role": "CEO Stripe"},
    "tobi_lutke": {"name": "Tobi Lutke", "role": "CEO Shopify"},
    "aravind_srinivas": {"name": "Aravind Srinivas", "role": "CEO Perplexity"},
    "ali_ghodsi": {"name": "Ali Ghodsi", "role": "CEO Databricks"},
}

# Domains that commonly host video transcripts
TRANSCRIPT_DOMAINS = [
    "youtube.com",
    "rev.com",
    "podscribe.ai",
    "podcastnotes.org",
    "listen-notes.com",
    "descript.com",
    "otter.ai",
    "scribd.com",
    "medium.com",
]


def fetch_youtube_transcripts(exa: Exa, name: str, count: int = 30) -> list[dict]:
    """Fetch YouTube/video transcripts for a person using Exa API."""
    all_results = []

    queries = [
        f"{name} interview youtube transcript",
        f"{name} video transcript",
        f"{name} youtube appearance interview",
        f"{name} podcast transcript full",
    ]

    for query in queries:
        try:
            results = exa.search_and_contents(
                query=query,
                type="auto",
                num_results=count,
                include_domains=TRANSCRIPT_DOMAINS,
                text=True,
            )
            for r in results.results:
                if r.text and len(r.text.strip()) > 200:
                    all_results.append({
                        "text": r.text,
                        "title": r.title or "",
                        "url": r.url or "",
                        "published_date": r.published_date,
                    })
        except Exception as e:
            print(f"  Error with query '{query}': {e}")

    return all_results


def clean_transcript_text(text: str) -> str:
    """Remove common boilerplate from transcript text."""
    lines = text.split("\n")
    cleaned = []
    skip_phrases = [
        "subscribe",
        "like and subscribe",
        "click the bell",
        "notification",
        "sign up",
        "sign in",
        "advertisement",
        "sponsor",
        "this video is sponsored",
        "cookie",
        "privacy policy",
        "terms of service",
        "[music]",
        "[applause]",
    ]

    for line in lines:
        line_lower = line.lower().strip()
        if any(phrase in line_lower for phrase in skip_phrases):
            continue
        if line.strip():
            cleaned.append(line.strip())

    return "\n".join(cleaned)


def dedupe_posts(existing: list[str], new_posts: list[dict]) -> list[str]:
    """Deduplicate posts by checking text similarity."""
    existing_set = set()
    for post in existing:
        # Use first 100 chars as key for deduplication
        key = post[:100].lower().strip() if len(post) > 100 else post.lower().strip()
        existing_set.add(key)

    added = []
    for post in new_posts:
        text = clean_transcript_text(post.get("text", ""))
        if len(text) < 200:
            continue

        key = text[:100].lower().strip()
        if key not in existing_set:
            existing_set.add(key)
            added.append(text)

    return added


def load_profile(author: str) -> dict | None:
    """Load existing profile from JSON file."""
    filepath = PROFILES_DIR / f"{author}__linkedin.json"
    if not filepath.exists():
        print(f"  Profile not found: {filepath}")
        return None

    with open(filepath) as f:
        return json.load(f)


def save_profile(profile: dict) -> None:
    """Save profile to JSON file."""
    author = profile["author"]
    platform = profile["platform"]
    filepath = PROFILES_DIR / f"{author}__{platform}.json"

    with open(filepath, "w") as f:
        json.dump(profile, f, indent=2)

    print(f"  Saved to {filepath.name}")


def process_author(author: str, info: dict, exa: Exa) -> int:
    """Process a single author and return count of new posts added."""
    print(f"\nProcessing {info['name']} ({author})...")

    # Load existing profile
    profile = load_profile(author)
    if not profile:
        return 0

    existing_posts = profile.get("example_posts", [])
    original_count = len(existing_posts)
    print(f"  Existing posts: {original_count}")

    # Fetch YouTube transcripts
    print(f"  Fetching YouTube/video transcripts...")
    new_results = fetch_youtube_transcripts(exa, info["name"])
    print(f"  Found {len(new_results)} results from Exa")

    # Deduplicate and add new posts
    new_posts = dedupe_posts(existing_posts, new_results)
    print(f"  New unique posts after deduplication: {len(new_posts)}")

    if new_posts:
        profile["example_posts"] = existing_posts + new_posts
        save_profile(profile)

    return len(new_posts)


def main():
    if not EXA_API_KEY:
        print("Error: EXA_API_KEY not set")
        sys.exit(1)

    exa = Exa(api_key=EXA_API_KEY)

    results = {}
    total_added = 0

    for author, info in CEOS.items():
        added = process_author(author, info, exa)
        results[info["name"]] = added
        total_added += added

    print("\n" + "=" * 50)
    print("SUMMARY: New posts added per profile")
    print("=" * 50)
    for name, count in results.items():
        print(f"  {name}: {count} new posts")
    print(f"\nTotal new posts added: {total_added}")


if __name__ == "__main__":
    main()
