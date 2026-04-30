#!/usr/bin/env python3
"""Scrape interviews, podcasts, and keynotes for CEO profiles using Exa API.

This script:
1. Loads existing LinkedIn profiles
2. Searches Exa for interviews/podcasts/keynotes (excludes LinkedIn to get NEW content)
3. Merges new posts with existing example_posts (deduplicates)
4. Saves updated profiles
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from exa_py import Exa

# Load environment variables from .env
load_dotenv(Path(__file__).parent.parent / ".env")

EXA_API_KEY = os.environ.get("EXA_API_KEY")
PROFILES_DIR = Path(__file__).parent.parent / "packages" / "api" / "data" / "profiles"

CEO_PROFILES = {
    "sam_altman": {"name": "Sam Altman", "company": "OpenAI"},
    "elon_musk": {"name": "Elon Musk", "company": "Tesla SpaceX X"},
    "brian_chesky": {"name": "Brian Chesky", "company": "Airbnb"},
    "guillermo_rauch": {"name": "Guillermo Rauch", "company": "Vercel"},
    "dario_amodei": {"name": "Dario Amodei", "company": "Anthropic"},
    "satya_nadella": {"name": "Satya Nadella", "company": "Microsoft"},
    "patrick_collison": {"name": "Patrick Collison", "company": "Stripe"},
    "tobi_lutke": {"name": "Tobi Lutke", "company": "Shopify"},
    "aravind_srinivas": {"name": "Aravind Srinivas", "company": "Perplexity"},
    "ali_ghodsi": {"name": "Ali Ghodsi", "company": "Databricks"},
}

# Search queries to find different types of content
SEARCH_TEMPLATES = [
    "{name} interview transcript",
    "{name} podcast appearance",
    "{name} keynote speech",
]


def load_existing_profile(author: str) -> dict | None:
    """Load existing LinkedIn profile JSON."""
    filepath = PROFILES_DIR / f"{author}__linkedin.json"
    if not filepath.exists():
        print(f"  Profile not found: {filepath}")
        return None

    with open(filepath) as f:
        return json.load(f)


def save_profile(profile: dict, author: str) -> None:
    """Save profile to JSON file."""
    filepath = PROFILES_DIR / f"{author}__linkedin.json"
    with open(filepath, "w") as f:
        json.dump(profile, f, indent=2)
    print(f"  Saved to {filepath.name}")


def search_additional_content(
    exa: Exa,
    name: str,
    company: str,
    results_per_query: int = 10
) -> list[str]:
    """Search for interviews, podcasts, and keynotes using Exa."""
    all_texts: list[str] = []

    for template in SEARCH_TEMPLATES:
        query = template.format(name=name)
        print(f"    Searching: {query}")

        try:
            results = exa.search_and_contents(
                query=query,
                type="auto",
                num_results=results_per_query,
                exclude_domains=["linkedin.com"],  # Exclude LinkedIn to get NEW content
                text=True,
            )

            for r in results.results:
                if r.text and len(r.text.strip()) > 200:
                    # Clean and extract the meaningful content
                    text = clean_content(r.text, name)
                    if text and len(text) > 100:
                        all_texts.append(text)

            print(f"      Found {len(results.results)} results")

        except Exception as e:
            print(f"      Error: {e}")

    return all_texts


def clean_content(text: str, name: str) -> str:
    """Clean scraped content to extract meaningful quotes and statements."""
    # Skip if the text doesn't actually contain the person's name
    name_parts = name.lower().split()
    text_lower = text.lower()
    if not any(part in text_lower for part in name_parts):
        return ""

    lines = text.split("\n")
    cleaned = []

    # Phrases to skip (common web boilerplate)
    skip_phrases = [
        "cookie",
        "privacy policy",
        "terms of service",
        "subscribe",
        "newsletter",
        "sign up",
        "log in",
        "copyright",
        "all rights reserved",
        "advertisement",
        "sponsored",
        "click here",
        "follow us",
        "share this",
    ]

    for line in lines:
        line_lower = line.lower().strip()

        # Skip short lines
        if len(line.strip()) < 20:
            continue

        # Skip boilerplate
        if any(phrase in line_lower for phrase in skip_phrases):
            continue

        cleaned.append(line.strip())

    result = "\n".join(cleaned)

    # Truncate very long content to most relevant parts
    if len(result) > 3000:
        result = result[:3000] + "..."

    return result


def normalize_text(text: str) -> str:
    """Normalize text for deduplication comparison."""
    # Lowercase, remove extra whitespace, strip punctuation
    import re
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()[:500]  # Compare first 500 chars to handle truncation


def deduplicate_posts(existing: list[str], new: list[str]) -> tuple[list[str], int]:
    """Merge new posts with existing, removing duplicates.

    Returns (merged_list, count_of_new_unique_posts)
    """
    # Create normalized versions of existing posts for comparison
    existing_normalized = {normalize_text(p) for p in existing}

    new_unique = []
    for post in new:
        normalized = normalize_text(post)
        # Check if this post (or something very similar) already exists
        if normalized not in existing_normalized:
            # Also check if the first 200 chars match any existing post
            short_normalized = normalized[:200]
            if not any(short_normalized in norm or norm[:200] == short_normalized
                       for norm in existing_normalized):
                new_unique.append(post)
                existing_normalized.add(normalized)

    # Merge: existing + new unique posts
    merged = existing + new_unique
    return merged, len(new_unique)


def process_profile(exa: Exa, author: str, info: dict) -> int:
    """Process a single CEO profile, adding new content.

    Returns the number of new posts added.
    """
    print(f"\nProcessing {info['name']} ({author})...")

    # Load existing profile
    profile = load_existing_profile(author)
    if profile is None:
        return 0

    existing_posts = profile.get("example_posts", [])
    print(f"  Existing posts: {len(existing_posts)}")

    # Search for new content
    print("  Searching for interviews/podcasts/keynotes...")
    new_content = search_additional_content(exa, info["name"], info["company"])
    print(f"  Raw new content found: {len(new_content)}")

    # Deduplicate and merge
    merged_posts, new_count = deduplicate_posts(existing_posts, new_content)

    if new_count > 0:
        profile["example_posts"] = merged_posts
        save_profile(profile, author)
        print(f"  Added {new_count} NEW unique posts (total now: {len(merged_posts)})")
    else:
        print(f"  No new unique posts to add")

    return new_count


def main():
    if not EXA_API_KEY:
        print("Error: EXA_API_KEY not set in .env file")
        sys.exit(1)

    if not PROFILES_DIR.exists():
        print(f"Error: Profiles directory not found: {PROFILES_DIR}")
        sys.exit(1)

    exa = Exa(api_key=EXA_API_KEY)

    print("=" * 60)
    print("Scraping additional content for CEO profiles")
    print("=" * 60)

    results: dict[str, int] = {}

    for author, info in CEO_PROFILES.items():
        new_count = process_profile(exa, author, info)
        results[author] = new_count

    # Summary report
    print("\n" + "=" * 60)
    print("SUMMARY: New posts added per profile")
    print("=" * 60)

    total_new = 0
    for author, count in results.items():
        name = CEO_PROFILES[author]["name"]
        print(f"  {name}: {count} new posts")
        total_new += count

    print("-" * 60)
    print(f"  TOTAL: {total_new} new posts added")
    print("=" * 60)


if __name__ == "__main__":
    main()
