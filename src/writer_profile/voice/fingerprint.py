from __future__ import annotations

import re
import statistics
from collections import Counter
from dataclasses import dataclass

from writer_profile.corpus.models import Post

_PUNCTUATION = set(".,!?;:\"'()-")


def _char_trigrams(text: str) -> list[str]:
    text = text.lower()
    return [text[i : i + 3] for i in range(len(text) - 2)]


def _word_lengths(text: str) -> list[int]:
    words = re.findall(r"\b\w+\b", text)
    return [len(w) for w in words]


def _type_token_ratio(text: str) -> float:
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def _punctuation_rates(text: str) -> dict[str, float]:
    total = len(text) or 1
    counts: Counter[str] = Counter()
    for ch in text:
        if ch in _PUNCTUATION:
            counts[ch] += 1
    return {ch: count / total for ch, count in counts.items()}


@dataclass
class StyleFingerprint:
    avg_word_length: float
    word_length_std: float
    vocabulary_richness: float
    punctuation_rates: dict[str, float]
    char_trigram_top10: list[tuple[str, float]]
    avg_sentence_length: float
    sentence_length_std: float

    def deviation_from(self, other: StyleFingerprint) -> float:
        diffs = []
        diffs.append(
            abs(self.avg_word_length - other.avg_word_length) / max(self.avg_word_length, 1)
        )
        diffs.append(abs(self.vocabulary_richness - other.vocabulary_richness))
        diffs.append(
            abs(self.avg_sentence_length - other.avg_sentence_length)
            / max(self.avg_sentence_length, 1)
        )

        all_puncts = set(self.punctuation_rates.keys()) | set(other.punctuation_rates.keys())
        if all_puncts:
            punct_diff = sum(
                abs(self.punctuation_rates.get(p, 0) - other.punctuation_rates.get(p, 0))
                for p in all_puncts
            ) / len(all_puncts)
            diffs.append(punct_diff * 10)

        return min(1.0, sum(diffs) / len(diffs))


def compute_fingerprint(posts: list[Post]) -> StyleFingerprint:
    if not posts:
        raise ValueError("Cannot compute fingerprint from empty corpus")

    all_text = " ".join(p.text for p in posts)

    word_lens = _word_lengths(all_text)
    avg_word_length = statistics.mean(word_lens) if word_lens else 0.0
    word_length_std = statistics.stdev(word_lens) if len(word_lens) > 1 else 0.0

    vocabulary_richness = _type_token_ratio(all_text)
    punctuation_rates = _punctuation_rates(all_text)

    trigrams = _char_trigrams(all_text)
    trigram_counts = Counter(trigrams)
    total_trigrams = len(trigrams) or 1
    char_trigram_top10 = [
        (tg, count / total_trigrams) for tg, count in trigram_counts.most_common(10)
    ]

    sentences = re.split(r"[.!?]+", all_text)
    sent_lens = [len(s.split()) for s in sentences if s.strip()]
    avg_sentence_length = statistics.mean(sent_lens) if sent_lens else 0.0
    sentence_length_std = statistics.stdev(sent_lens) if len(sent_lens) > 1 else 0.0

    return StyleFingerprint(
        avg_word_length=avg_word_length,
        word_length_std=word_length_std,
        vocabulary_richness=vocabulary_richness,
        punctuation_rates=punctuation_rates,
        char_trigram_top10=char_trigram_top10,
        avg_sentence_length=avg_sentence_length,
        sentence_length_std=sentence_length_std,
    )
