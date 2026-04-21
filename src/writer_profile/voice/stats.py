from __future__ import annotations

import re
import statistics
from collections import Counter

from pydantic import BaseModel, Field

from writer_profile.corpus.models import Post

_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF]")
_HASHTAG_RE = re.compile(r"(?<!\w)#\w+")
_URL_RE = re.compile(r"https?://\S+")
_MENTION_RE = re.compile(r"(?<!\w)@\w+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


class VoiceStats(BaseModel):
    post_count: int
    avg_words_per_sentence: float
    sentence_length_p25_p50_p75: tuple[float, float, float]
    length_chars_p25_p50_p75: tuple[float, float, float]
    emoji_rate: float
    hashtag_rate: float
    avg_hashtags_per_post: float
    url_rate: float
    question_rate: float
    mention_rate: float
    line_break_rate: float
    top_openers: list[str] = Field(default_factory=list)
    top_closers: list[str] = Field(default_factory=list)
    top_bigrams: list[tuple[str, int]] = Field(default_factory=list)
    top_trigrams: list[tuple[str, int]] = Field(default_factory=list)
    thread_rate: float = 0.0


def _percentiles(xs: list[float]) -> tuple[float, float, float]:
    if not xs:
        return (0.0, 0.0, 0.0)
    xs_sorted = sorted(xs)
    q = (
        statistics.quantiles(xs_sorted, n=4)
        if len(xs_sorted) >= 4
        else [
            xs_sorted[0],
            xs_sorted[len(xs_sorted) // 2],
            xs_sorted[-1],
        ]
    )
    return (float(q[0]), float(q[1]), float(q[2]))


def _sentence_word_counts(text: str) -> list[int]:
    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(text) if p.strip()]
    counts = [len(p.split()) for p in parts if any(ch.isalpha() for ch in p)]
    return counts or [len(text.split())]


def _first_words(text: str, n: int = 6) -> str:
    words = text.strip().split()[:n]
    return " ".join(w.lower() for w in words)


def _last_words(text: str, n: int = 6) -> str:
    words = text.strip().split()
    return " ".join(w.lower() for w in words[-n:]) if words else ""


def _ngrams(tokens: list[str], n: int) -> list[str]:
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def compute_stats(posts: list[Post]) -> VoiceStats:
    if not posts:
        raise ValueError("cannot compute stats from empty corpus")

    total = len(posts)
    sent_counts_all: list[int] = []
    char_lens: list[int] = []
    emoji_hits = 0
    hashtag_hits = 0
    total_hashtags = 0
    url_hits = 0
    question_hits = 0
    mention_hits = 0
    line_break_hits = 0
    openers: Counter[str] = Counter()
    closers: Counter[str] = Counter()
    bigrams: Counter[str] = Counter()
    trigrams: Counter[str] = Counter()
    thread_hits = 0

    for p in posts:
        t = p.text
        char_lens.append(len(t))
        sent_counts_all.extend(_sentence_word_counts(t))
        if _EMOJI_RE.search(t):
            emoji_hits += 1
        tags = _HASHTAG_RE.findall(t)
        if tags:
            hashtag_hits += 1
            total_hashtags += len(tags)
        if _URL_RE.search(t):
            url_hits += 1
        if "?" in t:
            question_hits += 1
        if _MENTION_RE.search(t):
            mention_hits += 1
        if "\n\n" in t:
            line_break_hits += 1
        if re.search(r"(?:^|\n)\s*(?:1[./)]|🧵)", t):
            thread_hits += 1

        openers[_first_words(t)] += 1
        closers[_last_words(t)] += 1
        toks = [w.lower().strip(".,!?;:") for w in t.split() if w.strip()]
        for bg in _ngrams(toks, 2):
            bigrams[bg] += 1
        for tg in _ngrams(toks, 3):
            trigrams[tg] += 1

    return VoiceStats(
        post_count=total,
        avg_words_per_sentence=(sum(sent_counts_all) / len(sent_counts_all))
        if sent_counts_all
        else 0.0,
        sentence_length_p25_p50_p75=_percentiles([float(x) for x in sent_counts_all]),
        length_chars_p25_p50_p75=_percentiles([float(x) for x in char_lens]),
        emoji_rate=emoji_hits / total,
        hashtag_rate=hashtag_hits / total,
        avg_hashtags_per_post=total_hashtags / total,
        url_rate=url_hits / total,
        question_rate=question_hits / total,
        mention_rate=mention_hits / total,
        line_break_rate=line_break_hits / total,
        top_openers=[o for o, _ in openers.most_common(10)],
        top_closers=[c for c, _ in closers.most_common(10)],
        top_bigrams=bigrams.most_common(20),
        top_trigrams=trigrams.most_common(20),
        thread_rate=thread_hits / total,
    )
