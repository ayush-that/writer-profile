from __future__ import annotations

import re
from dataclasses import dataclass

EM_DASH_CHARS = ("—", "–", "--")
EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF"
    r"\U00002700-\U000027BF"
    r"\U0001F600-\U0001F64F"
    r"\U0001F680-\U0001F6FF]"
)

EM_DASH_THRESHOLD = 0.05
EMOJI_THRESHOLD = 0.05


@dataclass
class VoiceTells:
    em_dash_rate: float
    emoji_rate: float
    em_dash_forbidden: bool
    emoji_forbidden: bool
    sample_size: int


def extract_tells(posts: list[str]) -> VoiceTells:
    cleaned = [p for p in posts if p and p.strip()]
    if not cleaned:
        return VoiceTells(
            em_dash_rate=0.0,
            emoji_rate=0.0,
            em_dash_forbidden=True,
            emoji_forbidden=True,
            sample_size=0,
        )
    em = sum(1 for p in cleaned if any(t in p for t in EM_DASH_CHARS))
    emj = sum(1 for p in cleaned if EMOJI_RE.search(p))
    em_rate = em / len(cleaned)
    emj_rate = emj / len(cleaned)
    return VoiceTells(
        em_dash_rate=em_rate,
        emoji_rate=emj_rate,
        em_dash_forbidden=em_rate < EM_DASH_THRESHOLD,
        emoji_forbidden=emj_rate < EMOJI_THRESHOLD,
        sample_size=len(cleaned),
    )


def sanitize_output(text: str, tells: VoiceTells) -> str:
    if not text:
        return text
    out = text
    if tells.em_dash_forbidden:
        out = re.sub(r"\s+—\s+", ", ", out)
        out = re.sub(r"\s+–\s+", ", ", out)
        out = re.sub(r"(?<=\s)--(?=\s)", ",", out)
        out = out.replace("—", ",")
        out = out.replace("–", "-")
    if tells.emoji_forbidden:
        out = EMOJI_RE.sub("", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r" +([,.;:!?])", r"\1", out)
    out = re.sub(r",{2,}", ",", out)
    return out.strip()
