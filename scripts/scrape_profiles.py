#!/usr/bin/env python3
"""Scrape tweets from twitterapi.io and build voice profiles."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import httpx

TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
TWITTER_API_BASE = "https://api.twitterapi.io/twitter"
PROFILES_DIR = Path(__file__).parent.parent / "data" / "profiles"

TWITTER_HANDLES = {
    "sam_altman": "sama",
    "elon_musk": "elonmusk",
    "brian_chesky": "bchesky",
    "guillermo_rauch": "rauchg",
    "dario_amodei": "DarioAmodei",
    "satya_nadella": "satyanadella",
    "patrick_collison": "patrickc",
    "tobi_lutke": "tobi",
    "aravind_srinivas": "AravSrinivas",
    "ali_ghodsi": "alighodsi",
}


def fetch_tweets(handle: str, count: int = 50) -> list[dict]:
    """Fetch recent tweets for a Twitter handle."""
    if not TWITTER_API_KEY:
        print("Error: TWITTER_API_KEY not set")
        sys.exit(1)

    headers = {"X-API-Key": TWITTER_API_KEY}

    try:
        resp = httpx.get(
            f"{TWITTER_API_BASE}/user/last_tweets",
            params={"userName": handle, "count": count},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("tweets", [])
    except httpx.HTTPError as e:
        print(f"Error fetching tweets for @{handle}: {e}")
        return []


def analyze_voice(tweets: list[dict]) -> dict:
    """Analyze tweets to extract voice patterns."""
    if not tweets:
        return {}

    texts = [t.get("text", "") for t in tweets if t.get("text")]

    if not texts:
        return {}

    word_counts: dict[str, int] = {}
    total_sentences = 0
    total_words = 0
    phrases: list[str] = []

    for text in texts:
        words = text.split()
        total_words += len(words)
        sentences = text.replace("!", ".").replace("?", ".").split(".")
        total_sentences += len([s for s in sentences if s.strip()])

        for word in words:
            clean = word.lower().strip(".,!?\"'")
            if len(clean) > 3:
                word_counts[clean] = word_counts.get(clean, 0) + 1

    avg_sentence_len = total_words / max(total_sentences, 1)

    top_words = sorted(word_counts.items(), key=lambda x: -x[1])[:10]
    recurring = [w for w, c in top_words if c >= 3]

    example_posts = texts[:5]

    return {
        "avg_sentence_length": round(avg_sentence_len, 1),
        "recurring_phrases": recurring,
        "example_posts": example_posts,
    }


def build_profile(author: str, handle: str) -> dict | None:
    """Build a voice profile for an author."""
    print(f"Fetching tweets for @{handle} ({author})...")
    tweets = fetch_tweets(handle)

    if not tweets:
        print(f"  No tweets found for @{handle}")
        return None

    print(f"  Found {len(tweets)} tweets")
    analysis = analyze_voice(tweets)

    profile = {
        "author": author,
        "platform": "twitter",
        "lexical": {
            "vocabulary_level": "professional",
            "recurring_phrases": analysis.get("recurring_phrases", []),
            "word_preferences": {},
            "jargon_usage": "moderate",
            "technicality_level": "accessible",
        },
        "structural": {
            "avg_sentence_length": analysis.get("avg_sentence_length", 15),
            "paragraph_style": "short",
            "opening_patterns": [],
            "closing_patterns": [],
            "uses_lists": False,
            "uses_questions": True,
        },
        "tonal": {
            "warmth_level": "moderate",
            "humor_usage": "occasional",
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
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    for author, handle in TWITTER_HANDLES.items():
        profile = build_profile(author, handle)
        if profile:
            save_profile(profile)
        print()

    print("Done!")


if __name__ == "__main__":
    main()
