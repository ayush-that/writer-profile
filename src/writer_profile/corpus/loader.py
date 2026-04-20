from __future__ import annotations

import json
from pathlib import Path

from writer_profile.corpus.models import Post


def load_posts_jsonl(path: str | Path) -> list[Post]:
    path = Path(path)
    posts: list[Post] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            posts.append(Post.model_validate(json.loads(line)))
    return posts
