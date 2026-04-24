from __future__ import annotations

from dataclasses import dataclass

CRITICS = [
    {
        "name": "voice_fidelity",
        "system": (
            "You are a voice fidelity critic. Check if the draft sounds like {author}. "
            "Evaluate: sentence rhythm, word choice, opener style, tonal register. "
            "If it matches well, reply exactly: OK. "
            "Otherwise, give 1-2 specific, actionable bullet points."
        ),
    },
    {
        "name": "engagement",
        "system": (
            "You are an engagement critic for {platform}. Check if the draft will get engagement. "
            "Evaluate: hook strength, pacing, call-to-action, shareability. "
            "If it's engaging, reply exactly: OK. "
            "Otherwise, give 1-2 specific, actionable bullet points."
        ),
    },
    {
        "name": "platform_native",
        "system": (
            "You are a {platform} native critic. Check if the draft feels native to {platform}. "
            "Evaluate: formatting, length, conventions, use of hashtags/mentions/emojis. "
            "If it's platform-native, reply exactly: OK. "
            "Otherwise, give 1-2 specific, actionable bullet points."
        ),
    },
]


@dataclass
class CriticFeedback:
    name: str
    feedback: str
    is_ok: bool


def _is_ok(feedback: str) -> bool:
    stripped = feedback.strip().lstrip("-* ").strip()
    if not stripped:
        return False
    first_token = stripped.split()[0].strip(".,!:;").upper()
    return first_token == "OK"


def parse_critic_response(name: str, response: str) -> CriticFeedback:
    return CriticFeedback(name=name, feedback=response.strip(), is_ok=_is_ok(response))


def synthesize_feedback(feedbacks: list[CriticFeedback]) -> str:
    non_ok = [f for f in feedbacks if not f.is_ok]
    if not non_ok:
        return "OK"

    parts = []
    for f in non_ok:
        parts.append(f"[{f.name}]: {f.feedback}")
    return "\n\n".join(parts)
