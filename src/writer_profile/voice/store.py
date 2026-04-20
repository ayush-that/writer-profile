from __future__ import annotations

from pathlib import Path

from writer_profile.corpus.models import Platform
from writer_profile.voice.profile import VoiceProfile


class VoiceProfileStore:
    def __init__(self, *, root: str | Path) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, *, author: str, platform: Platform) -> Path:
        safe_author = author.replace("/", "_")
        return self._root / f"{safe_author}__{platform.value}.json"

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
