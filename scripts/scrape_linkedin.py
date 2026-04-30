#!/usr/bin/env python3
"""Scrape LinkedIn posts using Exa API and build voice profiles."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from exa_py import Exa

EXA_API_KEY = os.environ.get("EXA_API_KEY")
PROFILES_DIR = Path(__file__).parent.parent / "data" / "profiles"

LINKEDIN_PROFILES = {
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


def fetch_linkedin_posts(exa: Exa, name: str, role: str, count: int = 50) -> list[dict]:
    """Fetch LinkedIn posts for a person using Exa API."""
    query = f"{name} {role} LinkedIn posts thoughts leadership insights"

    try:
        results = exa.search_and_contents(
            query=query,
            type="auto",
            num_results=count,
            include_domains=["linkedin.com"],
            text=True,
        )
        return [
            {
                "text": r.text or "",
                "title": r.title or "",
                "url": r.url or "",
                "published_date": r.published_date,
            }
            for r in results.results
            if r.text and len(r.text.strip()) > 50
        ]
    except Exception as e:
        print(f"Error fetching LinkedIn posts for {name}: {e}")
        return []


def clean_linkedin_text(text: str) -> str:
    """Remove LinkedIn boilerplate from text."""
    lines = text.split("\n")
    cleaned = []
    skip_phrases = [
        "sign in",
        "to view or add a comment",
        "report this",
        "linkedin *",
        "* linkedin",
        "* facebook",
        "show more",
        "show less",
        "see translation",
        "copy *",
        "share *",
    ]

    for line in lines:
        line_lower = line.lower().strip()
        if any(phrase in line_lower for phrase in skip_phrases):
            continue
        if line.strip():
            cleaned.append(line.strip())

    return "\n".join(cleaned)


def analyze_voice(posts: list[dict]) -> dict:
    """Analyze posts to extract voice patterns."""
    if not posts:
        return {}

    texts = [clean_linkedin_text(p.get("text", "")) for p in posts if p.get("text")]
    texts = [t for t in texts if len(t) > 100]

    if not texts:
        return {}

    word_counts: dict[str, int] = {}
    total_sentences = 0
    total_words = 0

    for text in texts:
        words = text.split()
        total_words += len(words)
        sentences = text.replace("!", ".").replace("?", ".").split(".")
        total_sentences += len([s for s in sentences if s.strip()])

        for word in words:
            clean = word.lower().strip(".,!?\"'():;")
            if len(clean) > 4:
                word_counts[clean] = word_counts.get(clean, 0) + 1

    avg_sentence_len = total_words / max(total_sentences, 1)

    top_words = sorted(word_counts.items(), key=lambda x: -x[1])[:15]
    recurring = [w for w, c in top_words if c >= 2]

    example_posts = texts[:30]

    return {
        "avg_sentence_length": round(avg_sentence_len, 1),
        "recurring_phrases": recurring[:10],
        "example_posts": example_posts,
    }


def build_profile(author: str, info: dict, exa: Exa) -> dict | None:
    """Build a voice profile for an author using Exa."""
    print(f"Fetching LinkedIn posts for {info['name']} ({author})...")
    posts = fetch_linkedin_posts(exa, info["name"], info["role"])

    if not posts:
        print(f"  No posts found for {info['name']}")
        return None

    print(f"  Found {len(posts)} posts")
    analysis = analyze_voice(posts)

    if not analysis:
        print(f"  Could not analyze posts for {info['name']}")
        return None

    profile = {
        "author": author,
        "platform": "linkedin",
        "lexical": {
            "vocabulary_level": "professional",
            "recurring_phrases": analysis.get("recurring_phrases", []),
            "word_preferences": {},
            "jargon_usage": "moderate",
            "technicality_level": "accessible",
        },
        "structural": {
            "avg_sentence_length": analysis.get("avg_sentence_length", 15),
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
        "example_posts": analysis.get("example_posts", []),
    }

    return profile


def save_profile(profile: dict) -> None:
    """Save profile to JSON file."""
    author = profile["author"]
    platform = profile["platform"]
    filepath = PROFILES_DIR / f"{author}__{platform}.json"

    with open(filepath, "w") as f:
        json.dump(profile, f, indent=2)

    print(f"  Saved to {filepath.name}")


def main():
    if not EXA_API_KEY:
        print("Error: EXA_API_KEY not set")
        sys.exit(1)

    exa = Exa(api_key=EXA_API_KEY)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    for author, info in LINKEDIN_PROFILES.items():
        profile = build_profile(author, info, exa)
        if profile:
            save_profile(profile)
        print()

    print("Done!")


if __name__ == "__main__":
    main()
