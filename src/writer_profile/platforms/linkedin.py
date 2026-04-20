from __future__ import annotations

from dataclasses import dataclass

from writer_profile.platforms.base import ValidationResult


@dataclass
class LinkedInConstraint:
    max_chars: int = 3000
    max_words_per_nonempty_line: int = 12
    name: str = "linkedin"

    def validate(self, text: str) -> ValidationResult:
        issues: list[str] = []

        if len(text) > self.max_chars:
            issues.append(
                f"exceeds {self.max_chars}-character limit by {len(text) - self.max_chars}"
            )

        long_lines: list[int] = []
        for idx, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            words = stripped.split()
            if len(words) > self.max_words_per_nonempty_line:
                long_lines.append(idx)

        if long_lines:
            issues.append(
                f"lines {long_lines} exceed {self.max_words_per_nonempty_line} words per line; "
                "break them up for scannability"
            )

        return ValidationResult.ok() if not issues else ValidationResult.fail(issues)

    def describe_rules(self) -> str:
        return (
            f"- total length <= {self.max_chars} characters\n"
            f"- each non-empty line <= {self.max_words_per_nonempty_line} words\n"
            "- use blank lines generously to create visual rhythm\n"
            "- hook in the first line; 1-2 supporting lines; a kicker at the end"
        )
