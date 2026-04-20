from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from writer_profile.corpus.models import Platform


@dataclass(frozen=True)
class Hook:
    id: str
    platform: Platform
    pattern_type: str
    template: str


class HookLibrary:
    def __init__(self, hooks: list[Hook]) -> None:
        self._hooks = hooks

    @classmethod
    def load(cls, path: str | Path) -> HookLibrary:
        hooks: list[Hook] = []
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            hooks.append(
                Hook(
                    id=data["id"],
                    platform=Platform(data["platform"]),
                    pattern_type=data["pattern_type"],
                    template=data["template"],
                )
            )
        return cls(hooks)

    def all(self) -> list[Hook]:
        return list(self._hooks)

    def for_platform(self, platform: Platform) -> list[Hook]:
        return [h for h in self._hooks if h.platform is platform]

    def suggest(self, *, platform: Platform, k: int = 5, seed: int | None = None) -> list[Hook]:
        pool = self.for_platform(platform)
        by_type: dict[str, list[Hook]] = defaultdict(list)
        for h in pool:
            by_type[h.pattern_type].append(h)

        rng = random.Random(seed)
        types = list(by_type.keys())
        rng.shuffle(types)

        out: list[Hook] = []
        for t in types:
            if len(out) >= k:
                break
            out.append(rng.choice(by_type[t]))

        while len(out) < k and pool:
            cand = rng.choice(pool)
            if cand.id not in {h.id for h in out}:
                out.append(cand)
            if len({h.id for h in out}) == len(pool):
                break
        return out[:k]

    @staticmethod
    def render_injection(hooks: list[Hook], *, virality_strength: float) -> str:
        if virality_strength <= 0.0:
            return "(Ignore structural suggestions. Write entirely in the author's natural style.)"

        bullet_list = "\n".join(
            f"- [{h.pattern_type}] {h.template}" for h in hooks
        )

        if virality_strength < 0.3:
            tone = (
                "These are optional structural patterns. You MAY consider one, but only if it "
                "fits the author's natural voice. Do not force a pattern. Voice > structure."
            )
        elif virality_strength < 0.7:
            tone = (
                "Consider adopting one of these structural patterns if it fits the author's "
                "voice. Voice fidelity still comes first, but a stronger hook is welcome."
            )
        else:
            tone = (
                "Strongly prefer adopting one of these high-performing structural patterns. "
                "Adapt the template to the author's voice, but lean into the structural shape."
            )

        return (
            f"STRUCTURAL PATTERN SUGGESTIONS (strength={virality_strength:.2f}):\n"
            f"{bullet_list}\n\n{tone}"
        )
