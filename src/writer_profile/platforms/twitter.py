from __future__ import annotations

import re
from dataclasses import dataclass

from writer_profile.platforms.base import ValidationResult

_URL_RE = re.compile(r"https?://\S+")
_HASHTAG_RE = re.compile(r"(?<!\w)#\w+")


@dataclass
class TwitterConstraint:
    max_chars: int = 280
    allow_hashtags: bool = True
    require_lowercase: bool = False
    max_hashtags: int = 3
    max_urls: int = 2
    name: str = "twitter"

    def validate(self, text: str) -> ValidationResult:
        issues: list[str] = []

        if len(text) > self.max_chars:
            issues.append(f"exceeds {self.max_chars}-char limit by {len(text) - self.max_chars}")

        hashtag_count = len(_HASHTAG_RE.findall(text))
        if not self.allow_hashtags and hashtag_count:
            issues.append("hashtags not allowed for this author's voice")
        elif hashtag_count > self.max_hashtags:
            issues.append(f"{hashtag_count} hashtags; max is {self.max_hashtags}")

        if self.require_lowercase:
            letters = [c for c in text if c.isalpha()]
            if letters and any(c.isupper() for c in letters):
                issues.append("uppercase letters found; post must be all lowercase")

        url_count = len(_URL_RE.findall(text))
        if url_count > self.max_urls:
            issues.append(f"{url_count} urls found; max is {self.max_urls}")

        return ValidationResult.ok() if not issues else ValidationResult.fail(issues)

    def describe_rules(self) -> str:
        rules = [f"- total length <= {self.max_chars} characters"]
        if self.require_lowercase:
            rules.append("- all lowercase (no capital letters)")
        if not self.allow_hashtags:
            rules.append("- no hashtags")
        else:
            rules.append(f"- at most {self.max_hashtags} hashtag(s)")
        rules.append(f"- at most {self.max_urls} url(s)")
        return "\n".join(rules)
