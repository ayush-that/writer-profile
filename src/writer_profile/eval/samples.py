from __future__ import annotations

from pathlib import Path

from writer_profile.corpus.models import Idea, Platform

ARCHETYPE_IDEAS: list[Idea] = [
    Idea(
        topic="product launch: new feature",
        angle="a specific capability is shipping today and it solves a long-standing pain",
    ),
    Idea(
        topic="acquisition",
        angle="announcing an acquisition that validates a strategic thesis",
    ),
    Idea(
        topic="earnings / milestone",
        angle="crossing a meaningful number, with context on how we got here",
    ),
    Idea(
        topic="personal reflection",
        angle="a lesson from this week's work, with a generalizable point",
    ),
    Idea(
        topic="industry commentary",
        angle="a provocative take on where the field is heading, based on observation",
    ),
]


def write_samples_sheet(
    *,
    root: str | Path,
    author: str,
    platform: Platform,
    samples: list[tuple[str, str]],
) -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{author}__{platform.value}.md"

    lines: list[str] = [f"# {author} — {platform.value}", ""]
    for i, (idea_label, post) in enumerate(samples, start=1):
        lines.append(f"## Sample {i}: {idea_label}")
        lines.append("")
        lines.append("```")
        lines.append(post)
        lines.append("```")
        lines.append("")
        lines.append("- Voice accuracy (1-5): ")
        lines.append("- Post quality (1-5): ")
        lines.append("- Naturalness (1-5): ")
        lines.append("- Notes:")
        lines.append("")

    path.write_text("\n".join(lines))
    return path
