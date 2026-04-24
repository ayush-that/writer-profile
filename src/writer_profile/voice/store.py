from __future__ import annotations

import re
from pathlib import Path

from writer_profile.corpus.models import Platform
from writer_profile.voice.profile import VoiceProfile

_VALID_AUTHOR_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_author(author: str) -> None:
    if not author or not _VALID_AUTHOR_RE.match(author):
        raise ValueError(f"Invalid author name: {author!r}. Must match [a-zA-Z0-9_-]+")


class VoiceProfileStore:
    def __init__(self, *, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, *, author: str, platform: Platform) -> Path:
        _validate_author(author)
        return self._root / f"{author}__{platform.value}.json"

    def save(self, profile: VoiceProfile) -> Path:
        p = self._path(author=profile.author, platform=profile.platform)
        p.write_text(profile.model_dump_json(indent=2))
        return p

    def load(self, *, author: str, platform: Platform) -> VoiceProfile:
        p = self._path(author=author, platform=platform)
        if not p.exists():
            raise FileNotFoundError(f"no profile at {p}")
        return VoiceProfile.model_validate_json(p.read_text())

    def list_profiles(self) -> list[tuple[str, Platform]]:
        out: list[tuple[str, Platform]] = []
        for p in self._root.glob("*__*.json"):
            stem = p.stem
            if "__" not in stem:
                continue
            author, platform_str = stem.rsplit("__", 1)
            try:
                out.append((author, Platform(platform_str)))
            except ValueError:
                continue
        return out
