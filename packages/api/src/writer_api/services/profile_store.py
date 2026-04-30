from __future__ import annotations

import contextlib
import json
from pathlib import Path

from writer_api.config import settings
from writer_api.models.voice import Platform, VoiceProfile


class ProfileStore:
    def __init__(self, profiles_path: str | None = None) -> None:
        path_str = profiles_path or settings.profiles_path
        if not Path(path_str).is_absolute():
            base = Path(__file__).parent.parent
            self._path = (base / path_str).resolve()
        else:
            self._path = Path(path_str)
        self._path.mkdir(parents=True, exist_ok=True)

    def load(self, author: str, platform: Platform | str) -> VoiceProfile | None:
        plat_val = platform.value if isinstance(platform, Platform) else platform
        filename = f"{author}__{plat_val}.json"
        filepath = self._path / filename

        if not filepath.exists():
            return None

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
                return VoiceProfile(**data)
        except (json.JSONDecodeError, OSError, ValueError):
            return None

    def save(self, profile: dict) -> bool:
        if "author" not in profile or "platform" not in profile:
            raise ValueError("Profile must contain 'author' and 'platform' keys")

        author = profile["author"]
        platform = profile["platform"]
        filename = f"{author}__{platform}.json"
        filepath = self._path / filename

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
            return True
        except OSError:
            return False

    def delete(self, author: str, platform: str) -> bool:
        filename = f"{author}__{platform}.json"
        filepath = self._path / filename

        if not filepath.exists():
            return False

        try:
            filepath.unlink()
            return True
        except OSError:
            return False

    def list_profiles(self) -> list[tuple[str, Platform]]:
        profiles: list[tuple[str, Platform]] = []

        for filepath in self._path.glob("*.json"):
            stem = filepath.stem
            parts = stem.rsplit("__", 1)
            if len(parts) == 2:
                author, plat_str = parts
                with contextlib.suppress(ValueError):
                    profiles.append((author, Platform(plat_str)))

        return sorted(profiles)

    def exists(self, author: str, platform: str) -> bool:
        filename = f"{author}__{platform}.json"
        filepath = self._path / filename
        return filepath.exists()
