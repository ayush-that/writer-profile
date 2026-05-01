from __future__ import annotations

import os
from pathlib import Path


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".env"
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            break


_load_env()

# Ensure required env vars exist so Settings instantiation doesn't fail at import.
os.environ.setdefault("EXA_API_KEY", "test-exa-key")
