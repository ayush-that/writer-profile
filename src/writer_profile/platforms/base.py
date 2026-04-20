from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ValidationResult:
    ok_: bool
    issues: tuple[str, ...] = field(default=())

    def __bool__(self) -> bool:
        return self.ok_

    @classmethod
    def ok(cls) -> ValidationResult:
        return cls(ok_=True)

    @classmethod
    def fail(cls, issues: list[str]) -> ValidationResult:
        return cls(ok_=False, issues=tuple(issues))


class Constraint(Protocol):
    name: str

    def validate(self, text: str) -> ValidationResult: ...

    def describe_rules(self) -> str: ...
