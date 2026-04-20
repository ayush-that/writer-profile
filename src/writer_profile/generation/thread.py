from __future__ import annotations

import re
from dataclasses import dataclass

from writer_profile.platforms.base import Constraint, ValidationResult

_SEPARATOR = re.compile(r"\n\s*---+\s*\n")
_ENUMERATION = re.compile(r"^\s*(?:\d+[./)]\s*|🧵\s*)")


@dataclass(frozen=True)
class Thread:
    posts: list[str]


def split_thread(raw: str) -> Thread:
    parts = _SEPARATOR.split(raw.strip())
    cleaned = [_ENUMERATION.sub("", p).strip() for p in parts if p.strip()]
    return Thread(posts=cleaned)


def validate_thread(
    thread: Thread, constraint: Constraint, *, max_posts: int = 5
) -> ValidationResult:
    issues: list[str] = []
    if len(thread.posts) > max_posts:
        issues.append(f"thread exceeds {max_posts} posts (got {len(thread.posts)})")

    for idx, p in enumerate(thread.posts[:max_posts], start=1):
        per_post = constraint.validate(p)
        if not per_post:
            issues.extend(f"post {idx}: {i}" for i in per_post.issues)

    return ValidationResult.ok() if not issues else ValidationResult.fail(issues)
