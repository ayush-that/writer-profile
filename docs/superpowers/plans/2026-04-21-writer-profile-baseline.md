# Writer-Profile Baseline Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a working Python CLI that, given (a) a corpus of one author's past posts and (b) a topic, produces Twitter/X and LinkedIn posts in that author's voice using style-aware RAG + a single Self-Refine loop + platform-format validators.

**Architecture:** Two-stage pipeline — (1) one-shot metadata extraction over the corpus populates a Chroma exemplar store with `{topic, tone, length_bucket, platform}` metadata; (2) per-request, the generator retrieves 3–5 metadata-matched exemplars, few-shot prompts Claude Sonnet 4.6, validates against a per-platform `Constraint`, and runs a Self-Refine loop (max 2 iterations) that rewrites on validator failure or critic feedback. Models are routed: Haiku 4.5 for classification/extraction, Sonnet 4.6 for writing and critique. The LLM client is a `Protocol` so a deterministic stub can drive tests.

**Tech Stack:** Python 3.13, `uv` for packaging, `anthropic` SDK, `chromadb` for persistent vector store + metadata filter, `sentence-transformers` (all-MiniLM-L6-v2) for embeddings, `pydantic` v2 for typed schemas, `typer` for CLI, `pytest` + `pytest-anyio` for tests, `ruff` for lint/format.

---

## Scope (what this plan does NOT do)

- No CrewAI / LangGraph orchestration (Plan 2).
- No virality predictor or variant selection (Plan 3).
- No publishing APIs or engagement feedback (Plan 4).
- No LoRA fine-tuning (Plan 5).
- No Outlines integration (baseline uses retry-based validation; `Constraint` protocol leaves room to swap Outlines in later for local models).

## File Structure

```
writer-profile/
├── pyproject.toml
├── .python-version
├── .env.example
├── .gitignore
├── src/writer_profile/
│   ├── __init__.py
│   ├── config.py
│   ├── llm.py
│   ├── corpus/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── loader.py
│   │   └── extractor.py
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── embedder.py
│   │   └── store.py
│   ├── platforms/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── twitter.py
│   │   └── linkedin.py
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── prompts.py
│   │   ├── generator.py
│   │   └── refine.py
│   ├── pipeline.py
│   └── cli.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── fixtures/sample_posts.jsonl
    ├── corpus/{test_loader.py,test_extractor.py}
    ├── retrieval/{test_embedder.py,test_store.py}
    ├── platforms/{test_twitter.py,test_linkedin.py}
    ├── generation/{test_prompts.py,test_generator.py,test_refine.py}
    └── test_pipeline.py
```

**Responsibilities:**
- `corpus/models.py` — `Post`, `PostMetadata` pydantic types. Pure data.
- `corpus/loader.py` — read JSONL → `list[Post]`. No LLM calls.
- `corpus/extractor.py` — LLM pass that fills `PostMetadata` for one post.
- `llm.py` — `LLMClient` protocol + `AnthropicClient` impl + `StubLLMClient` for tests.
- `retrieval/embedder.py` — wraps `sentence-transformers`; one interface `embed(texts) -> np.ndarray`.
- `retrieval/store.py` — Chroma collection with `add(post, metadata)` / `query(text, filters, k) -> list[Post]`.
- `platforms/base.py` — `Constraint` protocol (`validate(text) -> ValidationResult`) + platform enum.
- `platforms/twitter.py` — 280-char, lowercase, no-hashtag, ≤1 URL validator.
- `platforms/linkedin.py` — line-count + words-per-line heuristic validator.
- `generation/prompts.py` — system + few-shot template strings.
- `generation/generator.py` — single-shot style-conditioned generation.
- `generation/refine.py` — 2-iteration Self-Refine over `generator` output using critic + validator feedback.
- `pipeline.py` — `generate_post(topic, platform) -> PostDraft` end-to-end orchestration.
- `cli.py` — `writer ingest <file>` and `writer generate --platform twitter --topic "..."`.

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/writer_profile/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `.python-version`**

```
3.13
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "writer-profile"
version = "0.1.0"
description = "Style-aware post generator for Twitter/X and LinkedIn"
requires-python = ">=3.13"
dependencies = [
    "anthropic>=0.40.0",
    "chromadb>=0.5.0",
    "sentence-transformers>=3.0.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",
    "typer>=0.12.0",
    "python-dotenv>=1.0.0",
    "numpy>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-anyio>=0.0.0",
    "anyio>=4.6.0",
    "ruff>=0.6.0",
]

[project.scripts]
writer = "writer_profile.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/writer_profile"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-ra --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
```

- [ ] **Step 3: Create `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.env
dist/
build/
*.egg-info/
.chroma/
```

- [ ] **Step 4: Create `.env.example`**

```
ANTHROPIC_API_KEY=sk-ant-...
WRITER_PROFILE_CHROMA_PATH=.chroma
WRITER_PROFILE_WRITING_MODEL=claude-sonnet-4-6
WRITER_PROFILE_CLASSIFIER_MODEL=claude-haiku-4-5-20251001
WRITER_PROFILE_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

- [ ] **Step 5: Create empty package markers**

```python
# src/writer_profile/__init__.py
__version__ = "0.1.0"
```

```python
# tests/__init__.py
```

- [ ] **Step 6: Create `tests/conftest.py` — shared fixtures dir + pythonpath hint**

```python
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
```

- [ ] **Step 7: Install and verify**

Run: `uv sync --extra dev`
Expected: resolves, creates `.venv/`, no errors.

Run: `uv run pytest -q`
Expected: `no tests ran` (0 collected, exit 5) — acceptable.

- [ ] **Step 8: Commit**

```bash
git init
git add .
git commit -m "chore: scaffold writer-profile project"
```

---

## Task 2: Corpus data model

**Files:**
- Create: `src/writer_profile/corpus/__init__.py`
- Create: `src/writer_profile/corpus/models.py`
- Create: `tests/corpus/__init__.py`
- Create: `tests/corpus/test_models.py`

- [ ] **Step 1: Create `tests/corpus/__init__.py`** (empty file)

- [ ] **Step 2: Write failing test for `Post` and `PostMetadata`**

```python
# tests/corpus/test_models.py
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from writer_profile.corpus.models import Platform, Post, PostMetadata, Tone


def test_post_requires_text_and_platform():
    post = Post(
        id="t1",
        platform=Platform.TWITTER,
        text="hello world",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    assert post.text == "hello world"
    assert post.platform is Platform.TWITTER


def test_post_rejects_empty_text():
    with pytest.raises(ValidationError):
        Post(
            id="t1",
            platform=Platform.TWITTER,
            text="",
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )


def test_post_metadata_bucket_length():
    meta = PostMetadata(
        topics=["ai", "tooling"],
        tone=Tone.OBSERVATIONAL,
        length_bucket="short",
        language="en",
    )
    assert meta.length_bucket == "short"


def test_post_metadata_rejects_unknown_length_bucket():
    with pytest.raises(ValidationError):
        PostMetadata(
            topics=["ai"],
            tone=Tone.OBSERVATIONAL,
            length_bucket="tiny",
            language="en",
        )
```

- [ ] **Step 3: Run failing test**

Run: `uv run pytest tests/corpus/test_models.py -v`
Expected: FAIL (`ModuleNotFoundError: writer_profile.corpus.models`).

- [ ] **Step 4: Create `src/writer_profile/corpus/__init__.py`** (empty file)

- [ ] **Step 5: Implement models**

```python
# src/writer_profile/corpus/models.py
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Platform(StrEnum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"


class Tone(StrEnum):
    OBSERVATIONAL = "observational"
    CONTRARIAN = "contrarian"
    TECHNICAL = "technical"
    STORY = "story"
    PROMOTIONAL = "promotional"
    QUESTION = "question"


LengthBucket = Literal["short", "medium", "long"]


class Post(BaseModel):
    id: str
    platform: Platform
    text: str = Field(min_length=1)
    created_at: datetime
    engagement: dict[str, int] | None = None


class PostMetadata(BaseModel):
    topics: list[str] = Field(min_length=1)
    tone: Tone
    length_bucket: LengthBucket
    language: str = Field(min_length=2, max_length=5)


class AnnotatedPost(BaseModel):
    post: Post
    metadata: PostMetadata
```

- [ ] **Step 6: Run test to verify it passes**

Run: `uv run pytest tests/corpus/test_models.py -v`
Expected: PASS (4 passed).

- [ ] **Step 7: Commit**

```bash
git add src/writer_profile/corpus/ tests/corpus/
git commit -m "feat(corpus): add Post and PostMetadata pydantic models"
```

---

## Task 3: JSONL corpus loader + sample fixture

**Files:**
- Create: `tests/fixtures/sample_posts.jsonl`
- Create: `src/writer_profile/corpus/loader.py`
- Create: `tests/corpus/test_loader.py`

- [ ] **Step 1: Create the fixture file**

```jsonl
{"id":"t1","platform":"twitter","text":"the bottleneck in ai agents moved from generation to evaluation","created_at":"2025-09-01T10:00:00Z"}
{"id":"t2","platform":"twitter","text":"most devrel writing fails because it optimizes for clarity instead of surprise","created_at":"2025-09-08T10:00:00Z"}
{"id":"l1","platform":"linkedin","text":"Three things I changed this quarter:\n\n1. Stopped writing docs for search engines.\n2. Started writing docs for skimmers.\n3. Measured read-through, not pageviews.\n\nReadership doubled.","created_at":"2025-09-15T10:00:00Z"}
```

- [ ] **Step 2: Write failing test**

```python
# tests/corpus/test_loader.py
from writer_profile.corpus.loader import load_posts_jsonl
from writer_profile.corpus.models import Platform


def test_load_posts_jsonl_reads_fixture(fixtures_dir):
    posts = load_posts_jsonl(fixtures_dir / "sample_posts.jsonl")
    assert len(posts) == 3
    assert posts[0].id == "t1"
    assert posts[0].platform is Platform.TWITTER
    assert posts[2].platform is Platform.LINKEDIN
    assert "Three things" in posts[2].text


def test_load_posts_jsonl_skips_blank_lines(tmp_path):
    f = tmp_path / "p.jsonl"
    f.write_text(
        '{"id":"a","platform":"twitter","text":"hi","created_at":"2025-01-01T00:00:00Z"}\n'
        "\n"
        '{"id":"b","platform":"twitter","text":"ho","created_at":"2025-01-02T00:00:00Z"}\n'
    )
    posts = load_posts_jsonl(f)
    assert [p.id for p in posts] == ["a", "b"]
```

- [ ] **Step 3: Run failing test**

Run: `uv run pytest tests/corpus/test_loader.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 4: Implement loader**

```python
# src/writer_profile/corpus/loader.py
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/corpus/test_loader.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add src/writer_profile/corpus/loader.py tests/corpus/test_loader.py tests/fixtures/
git commit -m "feat(corpus): add JSONL loader and sample fixture"
```

---

## Task 4: Config module

**Files:**
- Create: `src/writer_profile/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
from writer_profile.config import Settings


def test_settings_reads_defaults(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings()
    assert s.anthropic_api_key == "sk-test"
    assert s.writing_model.startswith("claude-sonnet")
    assert s.classifier_model.startswith("claude-haiku")
    assert s.chroma_path.endswith(".chroma")


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("WRITER_PROFILE_WRITING_MODEL", "claude-opus-4-7")
    s = Settings()
    assert s.writing_model == "claude-opus-4-7"
```

- [ ] **Step 2: Run failing test**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement config**

```python
# src/writer_profile/config.py
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="WRITER_PROFILE_",
        extra="ignore",
    )

    anthropic_api_key: str = Field(alias="ANTHROPIC_API_KEY")
    chroma_path: str = ".chroma"
    writing_model: str = "claude-sonnet-4-6"
    classifier_model: str = "claude-haiku-4-5-20251001"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    refine_max_iterations: int = 2
    retrieval_k: int = 5
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/writer_profile/config.py tests/test_config.py
git commit -m "feat(config): add pydantic settings with env overrides"
```

---

## Task 5: LLM client protocol + stub

**Files:**
- Create: `src/writer_profile/llm.py`
- Create: `tests/test_llm.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_llm.py
from writer_profile.llm import LLMMessage, StubLLMClient


def test_stub_returns_scripted_responses():
    client = StubLLMClient(responses=["first", "second"])
    r1 = client.complete(
        model="claude-sonnet-4-6",
        system="sys",
        messages=[LLMMessage(role="user", content="hi")],
    )
    r2 = client.complete(
        model="claude-sonnet-4-6",
        system="sys",
        messages=[LLMMessage(role="user", content="again")],
    )
    assert r1 == "first"
    assert r2 == "second"
    assert len(client.calls) == 2
    assert client.calls[0].system == "sys"
    assert client.calls[0].messages[0].content == "hi"


def test_stub_raises_when_exhausted():
    client = StubLLMClient(responses=["only"])
    client.complete(model="m", system="s", messages=[LLMMessage(role="user", content="x")])
    try:
        client.complete(model="m", system="s", messages=[LLMMessage(role="user", content="y")])
    except IndexError:
        return
    raise AssertionError("expected IndexError")
```

- [ ] **Step 2: Run failing test**

Run: `uv run pytest tests/test_llm.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement LLM module**

```python
# src/writer_profile/llm.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

import anthropic


@dataclass(frozen=True)
class LLMMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class LLMCall:
    model: str
    system: str
    messages: tuple[LLMMessage, ...]


class LLMClient(Protocol):
    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str: ...


class AnthropicClient:
    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        response = self._client.messages.create(
            model=model,
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        parts = [b.text for b in response.content if b.type == "text"]
        return "".join(parts)


@dataclass
class StubLLMClient:
    responses: list[str]
    calls: list[LLMCall] = field(default_factory=list)
    _idx: int = 0

    def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        self.calls.append(LLMCall(model=model, system=system, messages=tuple(messages)))
        response = self.responses[self._idx]
        self._idx += 1
        return response
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_llm.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/writer_profile/llm.py tests/test_llm.py
git commit -m "feat(llm): add LLMClient protocol with Anthropic and stub impls"
```

---

## Task 6: Metadata extractor

**Files:**
- Create: `src/writer_profile/corpus/extractor.py`
- Create: `tests/corpus/test_extractor.py`

- [ ] **Step 1: Write failing test**

```python
# tests/corpus/test_extractor.py
import json
from datetime import datetime, timezone

from writer_profile.corpus.extractor import extract_metadata
from writer_profile.corpus.models import Platform, Post, Tone
from writer_profile.llm import StubLLMClient


def _mk_post(text: str) -> Post:
    return Post(
        id="x",
        platform=Platform.TWITTER,
        text=text,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def test_extract_metadata_parses_json_response():
    payload = json.dumps(
        {
            "topics": ["ai", "evaluation"],
            "tone": "observational",
            "length_bucket": "short",
            "language": "en",
        }
    )
    llm = StubLLMClient(responses=[payload])
    meta = extract_metadata(
        _mk_post("the bottleneck in ai is evaluation"),
        llm=llm,
        model="claude-haiku-4-5-20251001",
    )
    assert meta.topics == ["ai", "evaluation"]
    assert meta.tone is Tone.OBSERVATIONAL
    assert meta.length_bucket == "short"
    assert llm.calls[0].model == "claude-haiku-4-5-20251001"


def test_extract_metadata_tolerates_fenced_json():
    payload = (
        "```json\n"
        '{"topics":["devrel"],"tone":"contrarian","length_bucket":"medium","language":"en"}\n'
        "```"
    )
    llm = StubLLMClient(responses=[payload])
    meta = extract_metadata(
        _mk_post("most devrel writing is wrong"),
        llm=llm,
        model="claude-haiku-4-5-20251001",
    )
    assert meta.tone is Tone.CONTRARIAN
```

- [ ] **Step 2: Run failing test**

Run: `uv run pytest tests/corpus/test_extractor.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement extractor**

```python
# src/writer_profile/corpus/extractor.py
from __future__ import annotations

import json
import re

from writer_profile.corpus.models import Post, PostMetadata
from writer_profile.llm import LLMClient, LLMMessage

_EXTRACT_SYSTEM = """You classify a single social post into structured metadata.

Return ONLY a JSON object with these exact keys:
- topics: array of 1-4 lowercase noun phrases (each 1-3 words)
- tone: one of "observational" | "contrarian" | "technical" | "story" | "promotional" | "question"
- length_bucket: one of "short" | "medium" | "long"
  - short: under 140 chars
  - medium: 140-500 chars
  - long: over 500 chars
- language: ISO 639-1 code (e.g. "en")

No prose. No explanation. Just the JSON object."""

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _strip_json_fence(raw: str) -> str:
    match = _FENCE_RE.search(raw)
    return match.group(1) if match else raw.strip()


def extract_metadata(post: Post, *, llm: LLMClient, model: str) -> PostMetadata:
    prompt = f"PLATFORM: {post.platform.value}\n\nPOST:\n{post.text}"
    raw = llm.complete(
        model=model,
        system=_EXTRACT_SYSTEM,
        messages=[LLMMessage(role="user", content=prompt)],
        max_tokens=256,
        temperature=0.0,
    )
    data = json.loads(_strip_json_fence(raw))
    return PostMetadata.model_validate(data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/corpus/test_extractor.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/writer_profile/corpus/extractor.py tests/corpus/test_extractor.py
git commit -m "feat(corpus): LLM metadata extractor with fenced-JSON tolerance"
```

---

## Task 7: Embedder wrapper

**Files:**
- Create: `src/writer_profile/retrieval/__init__.py`
- Create: `src/writer_profile/retrieval/embedder.py`
- Create: `tests/retrieval/__init__.py`
- Create: `tests/retrieval/test_embedder.py`

- [ ] **Step 1: Create package markers**

```python
# src/writer_profile/retrieval/__init__.py
```

```python
# tests/retrieval/__init__.py
```

- [ ] **Step 2: Write failing test**

```python
# tests/retrieval/test_embedder.py
import numpy as np
import pytest

from writer_profile.retrieval.embedder import Embedder


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    return Embedder(model_name="sentence-transformers/all-MiniLM-L6-v2")


def test_embed_single_returns_1d_vector(embedder):
    vec = embedder.embed_single("the bottleneck in ai is evaluation")
    assert isinstance(vec, np.ndarray)
    assert vec.ndim == 1
    assert vec.shape[0] == 384


def test_embed_batch_returns_2d_matrix(embedder):
    mat = embedder.embed(["hello", "world", "third post"])
    assert mat.shape == (3, 384)
```

- [ ] **Step 3: Run failing test**

Run: `uv run pytest tests/retrieval/test_embedder.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 4: Implement embedder**

```python
# src/writer_profile/retrieval/embedder.py
from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray(
            self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        )

    def embed_single(self, text: str) -> np.ndarray:
        return self.embed([text])[0]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/retrieval/test_embedder.py -v`
Expected: PASS (2 passed). First run may take 30–60s downloading the model.

- [ ] **Step 6: Commit**

```bash
git add src/writer_profile/retrieval/ tests/retrieval/
git commit -m "feat(retrieval): add sentence-transformers embedder wrapper"
```

---

## Task 8: Exemplar store (Chroma)

**Files:**
- Create: `src/writer_profile/retrieval/store.py`
- Create: `tests/retrieval/test_store.py`

- [ ] **Step 1: Write failing test**

```python
# tests/retrieval/test_store.py
from datetime import datetime, timezone

import pytest

from writer_profile.corpus.models import AnnotatedPost, Platform, Post, PostMetadata, Tone
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    return Embedder(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _ann(pid: str, platform: Platform, text: str, tone: Tone, topics: list[str]) -> AnnotatedPost:
    return AnnotatedPost(
        post=Post(
            id=pid,
            platform=platform,
            text=text,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
        metadata=PostMetadata(
            topics=topics, tone=tone, length_bucket="short", language="en"
        ),
    )


def test_store_roundtrip_with_platform_filter(tmp_path, embedder):
    store = ExemplarStore(path=str(tmp_path / "chroma"), embedder=embedder, collection="t")
    store.add_many([
        _ann("a", Platform.TWITTER, "ai evaluation is the new bottleneck",
             Tone.OBSERVATIONAL, ["ai"]),
        _ann("b", Platform.TWITTER, "unrelated post about sourdough bread",
             Tone.STORY, ["cooking"]),
        _ann("c", Platform.LINKEDIN, "ai evaluation is the new bottleneck",
             Tone.OBSERVATIONAL, ["ai"]),
    ])
    hits = store.query(
        text="how do we evaluate ai agents",
        platform=Platform.TWITTER,
        k=2,
    )
    assert len(hits) == 2
    assert all(h.post.platform is Platform.TWITTER for h in hits)
    assert hits[0].post.id == "a"


def test_store_persists_across_instances(tmp_path, embedder):
    path = str(tmp_path / "chroma")
    s1 = ExemplarStore(path=path, embedder=embedder, collection="persist")
    s1.add_many([
        _ann("x", Platform.TWITTER, "stored post about ai",
             Tone.OBSERVATIONAL, ["ai"]),
    ])
    s2 = ExemplarStore(path=path, embedder=embedder, collection="persist")
    hits = s2.query(text="ai", platform=Platform.TWITTER, k=1)
    assert len(hits) == 1
    assert hits[0].post.id == "x"
```

- [ ] **Step 2: Run failing test**

Run: `uv run pytest tests/retrieval/test_store.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement store**

```python
# src/writer_profile/retrieval/store.py
from __future__ import annotations

import json
from dataclasses import dataclass

import chromadb

from writer_profile.corpus.models import AnnotatedPost, Platform, Post, PostMetadata
from writer_profile.retrieval.embedder import Embedder


@dataclass
class ExemplarHit:
    post: Post
    metadata: PostMetadata
    score: float


class ExemplarStore:
    def __init__(self, *, path: str, embedder: Embedder, collection: str = "posts") -> None:
        self._client = chromadb.PersistentClient(path=path)
        self._col = self._client.get_or_create_collection(
            name=collection, metadata={"hnsw:space": "cosine"}
        )
        self._embedder = embedder

    def add_many(self, items: list[AnnotatedPost]) -> None:
        if not items:
            return
        ids = [i.post.id for i in items]
        docs = [i.post.text for i in items]
        vectors = self._embedder.embed(docs).tolist()
        metadatas = [
            {
                "platform": i.post.platform.value,
                "tone": i.metadata.tone.value,
                "length_bucket": i.metadata.length_bucket,
                "language": i.metadata.language,
                "topics_json": json.dumps(i.metadata.topics),
                "post_json": i.post.model_dump_json(),
            }
            for i in items
        ]
        self._col.upsert(ids=ids, embeddings=vectors, documents=docs, metadatas=metadatas)

    def query(
        self,
        *,
        text: str,
        platform: Platform,
        k: int = 5,
        tone: str | None = None,
    ) -> list[ExemplarHit]:
        vec = self._embedder.embed_single(text).tolist()
        where: dict[str, object] = {"platform": platform.value}
        if tone:
            where = {"$and": [{"platform": platform.value}, {"tone": tone}]}
        result = self._col.query(query_embeddings=[vec], n_results=k, where=where)
        hits: list[ExemplarHit] = []
        for meta, dist in zip(result["metadatas"][0], result["distances"][0], strict=True):
            post = Post.model_validate_json(meta["post_json"])
            pm = PostMetadata(
                topics=json.loads(meta["topics_json"]),
                tone=meta["tone"],
                length_bucket=meta["length_bucket"],
                language=meta["language"],
            )
            hits.append(ExemplarHit(post=post, metadata=pm, score=1.0 - float(dist)))
        return hits
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/retrieval/test_store.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/writer_profile/retrieval/store.py tests/retrieval/test_store.py
git commit -m "feat(retrieval): add Chroma-backed exemplar store with metadata filter"
```

---

## Task 9: Platform base (`Constraint` protocol + data types)

**Files:**
- Create: `src/writer_profile/platforms/__init__.py`
- Create: `src/writer_profile/platforms/base.py`
- Create: `tests/platforms/__init__.py`
- Create: `tests/platforms/test_base.py`

- [ ] **Step 1: Create package markers**

```python
# src/writer_profile/platforms/__init__.py
```

```python
# tests/platforms/__init__.py
```

- [ ] **Step 2: Write failing test**

```python
# tests/platforms/test_base.py
from writer_profile.platforms.base import ValidationResult


def test_validation_result_ok_truthy():
    assert bool(ValidationResult.ok()) is True


def test_validation_result_failure_has_issues():
    res = ValidationResult.fail(["too long by 10 chars", "hashtag forbidden"])
    assert bool(res) is False
    assert len(res.issues) == 2
    assert "too long" in res.issues[0]
```

- [ ] **Step 3: Run failing test**

Run: `uv run pytest tests/platforms/test_base.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 4: Implement base**

```python
# src/writer_profile/platforms/base.py
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
    def ok(cls) -> "ValidationResult":
        return cls(ok_=True)

    @classmethod
    def fail(cls, issues: list[str]) -> "ValidationResult":
        return cls(ok_=False, issues=tuple(issues))


class Constraint(Protocol):
    name: str

    def validate(self, text: str) -> ValidationResult: ...

    def describe_rules(self) -> str: ...
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/platforms/test_base.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add src/writer_profile/platforms/ tests/platforms/
git commit -m "feat(platforms): add Constraint protocol and ValidationResult"
```

---

## Task 10: Twitter constraint

**Files:**
- Create: `src/writer_profile/platforms/twitter.py`
- Create: `tests/platforms/test_twitter.py`

- [ ] **Step 1: Write failing test**

```python
# tests/platforms/test_twitter.py
from writer_profile.platforms.twitter import TwitterConstraint


def test_accepts_lowercase_no_hashtag_under_280():
    c = TwitterConstraint()
    r = c.validate("the bottleneck in ai agents moved from generation to evaluation")
    assert bool(r) is True


def test_rejects_over_280_chars():
    c = TwitterConstraint()
    r = c.validate("x" * 281)
    assert bool(r) is False
    assert any("280" in i for i in r.issues)


def test_rejects_hashtags():
    c = TwitterConstraint()
    r = c.validate("this has #ai which is not allowed")
    assert bool(r) is False
    assert any("hashtag" in i.lower() for i in r.issues)


def test_rejects_uppercase():
    c = TwitterConstraint()
    r = c.validate("This Has Uppercase Letters")
    assert bool(r) is False
    assert any("lowercase" in i.lower() for i in r.issues)


def test_allows_urls_up_to_limit():
    c = TwitterConstraint(max_urls=1)
    ok = c.validate("check this out https://example.com/x")
    bad = c.validate("two links https://a.example/1 and https://b.example/2")
    assert bool(ok) is True
    assert bool(bad) is False
```

- [ ] **Step 2: Run failing test**

Run: `uv run pytest tests/platforms/test_twitter.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement Twitter constraint**

```python
# src/writer_profile/platforms/twitter.py
from __future__ import annotations

import re
from dataclasses import dataclass

from writer_profile.platforms.base import ValidationResult

_URL_RE = re.compile(r"https?://\S+")
_HASHTAG_RE = re.compile(r"(?<!\w)#\w+")


@dataclass
class TwitterConstraint:
    max_chars: int = 280
    allow_hashtags: bool = False
    require_lowercase: bool = True
    max_urls: int = 1
    name: str = "twitter"

    def validate(self, text: str) -> ValidationResult:
        issues: list[str] = []

        if len(text) > self.max_chars:
            issues.append(f"exceeds {self.max_chars}-char limit by {len(text) - self.max_chars}")

        if not self.allow_hashtags and _HASHTAG_RE.search(text):
            issues.append("hashtag found; hashtags are forbidden for this author")

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
            rules.append("- absolutely no hashtags")
        rules.append(f"- at most {self.max_urls} url(s)")
        rules.append("- headline first, then a couple of short sentences if needed")
        rules.append("- simple english, no slop, no emojis")
        return "\n".join(rules)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/platforms/test_twitter.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add src/writer_profile/platforms/twitter.py tests/platforms/test_twitter.py
git commit -m "feat(platforms): add Twitter constraint (280 chars, no hashtags, lowercase)"
```

---

## Task 11: LinkedIn constraint

**Files:**
- Create: `src/writer_profile/platforms/linkedin.py`
- Create: `tests/platforms/test_linkedin.py`

- [ ] **Step 1: Write failing test**

```python
# tests/platforms/test_linkedin.py
from writer_profile.platforms.linkedin import LinkedInConstraint


def test_accepts_short_lines_within_limit():
    c = LinkedInConstraint()
    post = (
        "Three things I changed this quarter:\n\n"
        "1. Stopped writing for search.\n"
        "2. Started writing for skimmers.\n"
        "3. Measured read-through only.\n\n"
        "Readership doubled."
    )
    r = c.validate(post)
    assert bool(r) is True, r.issues


def test_rejects_over_char_limit():
    c = LinkedInConstraint(max_chars=100)
    r = c.validate("x " * 200)
    assert bool(r) is False
    assert any("character" in i.lower() for i in r.issues)


def test_flags_lines_that_exceed_max_words_per_line():
    c = LinkedInConstraint(max_words_per_nonempty_line=9)
    long_line = " ".join(["word"] * 15)
    r = c.validate(long_line)
    assert bool(r) is False
    assert any("words per line" in i.lower() or "exceed" in i.lower() for i in r.issues)


def test_allows_long_post_if_lines_short():
    c = LinkedInConstraint()
    lines = ["a short punchy line." for _ in range(20)]
    r = c.validate("\n\n".join(lines))
    assert bool(r) is True, r.issues
```

- [ ] **Step 2: Run failing test**

Run: `uv run pytest tests/platforms/test_linkedin.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement LinkedIn constraint**

```python
# src/writer_profile/platforms/linkedin.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/platforms/test_linkedin.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/writer_profile/platforms/linkedin.py tests/platforms/test_linkedin.py
git commit -m "feat(platforms): add LinkedIn constraint (char cap + line-length heuristic)"
```

---

## Task 12: Prompt templates

**Files:**
- Create: `src/writer_profile/generation/__init__.py`
- Create: `src/writer_profile/generation/prompts.py`
- Create: `tests/generation/__init__.py`
- Create: `tests/generation/test_prompts.py`

- [ ] **Step 1: Create package markers**

```python
# src/writer_profile/generation/__init__.py
```

```python
# tests/generation/__init__.py
```

- [ ] **Step 2: Write failing test**

```python
# tests/generation/test_prompts.py
from datetime import datetime, timezone

from writer_profile.corpus.models import Platform, Post
from writer_profile.generation.prompts import (
    build_critic_prompt,
    build_generator_prompt,
    build_refine_prompt,
)
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.retrieval.store import ExemplarHit


def _hit(pid: str, text: str) -> ExemplarHit:
    from writer_profile.corpus.models import PostMetadata, Tone
    return ExemplarHit(
        post=Post(
            id=pid,
            platform=Platform.TWITTER,
            text=text,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
        metadata=PostMetadata(
            topics=["ai"], tone=Tone.OBSERVATIONAL, length_bucket="short", language="en"
        ),
        score=0.9,
    )


def test_generator_prompt_includes_exemplars_and_rules():
    exemplars = [_hit("a", "ai evaluation is the new bottleneck")]
    sys, user = build_generator_prompt(
        topic="why multi-agent debate beats self-critique",
        platform=Platform.TWITTER,
        exemplars=exemplars,
        constraint=TwitterConstraint(),
    )
    assert "voice" in sys.lower()
    assert "ai evaluation is the new bottleneck" in sys
    assert "multi-agent debate" in user
    assert "280" in sys


def test_critic_prompt_includes_draft_and_rules():
    sys, user = build_critic_prompt(
        draft="some draft",
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
    )
    assert "some draft" in user
    assert "hashtag" in sys.lower() or "hashtag" in user.lower()


def test_refine_prompt_includes_feedback_and_validator_issues():
    sys, user = build_refine_prompt(
        draft="some draft",
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
        critic_feedback="too generic, no surprise",
        validator_issues=["uppercase letters found; post must be all lowercase"],
    )
    assert "too generic" in user
    assert "lowercase" in user.lower()
```

- [ ] **Step 3: Run failing test**

Run: `uv run pytest tests/generation/test_prompts.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 4: Implement prompts**

```python
# src/writer_profile/generation/prompts.py
from __future__ import annotations

from writer_profile.corpus.models import Platform
from writer_profile.platforms.base import Constraint
from writer_profile.retrieval.store import ExemplarHit


def _format_exemplars(exemplars: list[ExemplarHit]) -> str:
    if not exemplars:
        return "(none available)"
    blocks = []
    for i, h in enumerate(exemplars, start=1):
        blocks.append(
            f"EXAMPLE {i} (tone={h.metadata.tone.value}, "
            f"length={h.metadata.length_bucket}):\n{h.post.text}"
        )
    return "\n\n".join(blocks)


def build_generator_prompt(
    *,
    topic: str,
    platform: Platform,
    exemplars: list[ExemplarHit],
    constraint: Constraint,
) -> tuple[str, str]:
    system = (
        f"You write {platform.value} posts in the exact voice of a specific author. "
        "Mimic their cadence, sentence length, punctuation, and word choice. "
        "Do not invent a new voice.\n\n"
        f"AUTHOR VOICE EXAMPLES (study these carefully):\n\n{_format_exemplars(exemplars)}\n\n"
        f"PLATFORM RULES ({platform.value}):\n{constraint.describe_rules()}\n\n"
        "Output ONLY the post text. No preamble, no quotes, no explanation."
    )
    user = f"Write one post on this topic: {topic}"
    return system, user


def build_critic_prompt(
    *,
    draft: str,
    platform: Platform,
    constraint: Constraint,
) -> tuple[str, str]:
    system = (
        "You are a terse editor critiquing one draft post. "
        "You do not rewrite. You give at most 3 concrete, actionable bullet points "
        "on what to improve — focus on voice fidelity, hook strength, and whether "
        "the post earns its length. If the draft is already strong, reply exactly: OK.\n\n"
        f"PLATFORM RULES ({platform.value}):\n{constraint.describe_rules()}"
    )
    user = f"DRAFT:\n{draft}\n\nYour critique:"
    return system, user


def build_refine_prompt(
    *,
    draft: str,
    platform: Platform,
    constraint: Constraint,
    critic_feedback: str,
    validator_issues: list[str],
) -> tuple[str, str]:
    validator_block = (
        "\n".join(f"- {i}" for i in validator_issues)
        if validator_issues
        else "(validator passed)"
    )
    system = (
        f"You revise a {platform.value} post based on explicit feedback. "
        "Keep the author's voice. Output ONLY the revised post text — no preamble, "
        "no quotes, no explanation.\n\n"
        f"PLATFORM RULES ({platform.value}):\n{constraint.describe_rules()}"
    )
    user = (
        f"ORIGINAL DRAFT:\n{draft}\n\n"
        f"CRITIC FEEDBACK:\n{critic_feedback}\n\n"
        f"HARD VALIDATOR ISSUES (must fix):\n{validator_block}\n\n"
        "Revised post:"
    )
    return system, user
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/generation/test_prompts.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add src/writer_profile/generation/ tests/generation/
git commit -m "feat(generation): add generator, critic, and refine prompt builders"
```

---

## Task 13: Generator (single-shot)

**Files:**
- Create: `src/writer_profile/generation/generator.py`
- Create: `tests/generation/test_generator.py`

- [ ] **Step 1: Write failing test**

```python
# tests/generation/test_generator.py
from datetime import datetime, timezone

from writer_profile.corpus.models import Platform, Post, PostMetadata, Tone
from writer_profile.generation.generator import generate_draft
from writer_profile.llm import StubLLMClient
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.retrieval.store import ExemplarHit


def _hit(text: str) -> ExemplarHit:
    return ExemplarHit(
        post=Post(
            id="x",
            platform=Platform.TWITTER,
            text=text,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
        metadata=PostMetadata(
            topics=["ai"], tone=Tone.OBSERVATIONAL, length_bucket="short", language="en"
        ),
        score=0.9,
    )


def test_generate_draft_strips_surrounding_quotes_and_whitespace():
    llm = StubLLMClient(responses=['  "the bottleneck moved to evaluation"  '])
    out = generate_draft(
        topic="ai bottlenecks",
        platform=Platform.TWITTER,
        exemplars=[_hit("ai is a bottleneck")],
        constraint=TwitterConstraint(),
        llm=llm,
        model="claude-sonnet-4-6",
    )
    assert out == "the bottleneck moved to evaluation"
    assert llm.calls[0].model == "claude-sonnet-4-6"


def test_generate_draft_passes_exemplars_into_system():
    llm = StubLLMClient(responses=["some draft"])
    generate_draft(
        topic="topic",
        platform=Platform.TWITTER,
        exemplars=[_hit("memorable exemplar text")],
        constraint=TwitterConstraint(),
        llm=llm,
        model="claude-sonnet-4-6",
    )
    assert "memorable exemplar text" in llm.calls[0].system
```

- [ ] **Step 2: Run failing test**

Run: `uv run pytest tests/generation/test_generator.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement generator**

```python
# src/writer_profile/generation/generator.py
from __future__ import annotations

from writer_profile.corpus.models import Platform
from writer_profile.generation.prompts import build_generator_prompt
from writer_profile.llm import LLMClient, LLMMessage
from writer_profile.platforms.base import Constraint
from writer_profile.retrieval.store import ExemplarHit


def _unwrap(raw: str) -> str:
    text = raw.strip()
    if len(text) >= 2 and text[0] in {'"', "'"} and text[-1] == text[0]:
        text = text[1:-1].strip()
    return text


def generate_draft(
    *,
    topic: str,
    platform: Platform,
    exemplars: list[ExemplarHit],
    constraint: Constraint,
    llm: LLMClient,
    model: str,
    temperature: float = 0.8,
) -> str:
    system, user = build_generator_prompt(
        topic=topic, platform=platform, exemplars=exemplars, constraint=constraint
    )
    raw = llm.complete(
        model=model,
        system=system,
        messages=[LLMMessage(role="user", content=user)],
        max_tokens=1024,
        temperature=temperature,
    )
    return _unwrap(raw)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/generation/test_generator.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/writer_profile/generation/generator.py tests/generation/test_generator.py
git commit -m "feat(generation): add single-shot style-conditioned generator"
```

---

## Task 14: Self-Refine loop

**Files:**
- Create: `src/writer_profile/generation/refine.py`
- Create: `tests/generation/test_refine.py`

- [ ] **Step 1: Write failing test**

```python
# tests/generation/test_refine.py
from writer_profile.corpus.models import Platform
from writer_profile.generation.refine import refine
from writer_profile.llm import StubLLMClient
from writer_profile.platforms.twitter import TwitterConstraint


def test_refine_short_circuits_on_ok_critique_and_valid_draft():
    initial = "the bottleneck in ai moved from generation to evaluation"
    llm = StubLLMClient(responses=["OK"])
    result = refine(
        draft=initial,
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
        llm=llm,
        model="claude-sonnet-4-6",
        max_iterations=2,
    )
    assert result.final_draft == initial
    assert result.iterations == 1
    assert len(llm.calls) == 1


def test_refine_retries_when_validator_fails():
    bad = "This Has Uppercase"
    llm = StubLLMClient(
        responses=[
            "uppercase is banned",
            "this has uppercase fixed",
        ]
    )
    result = refine(
        draft=bad,
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
        llm=llm,
        model="claude-sonnet-4-6",
        max_iterations=2,
    )
    assert result.final_draft == "this has uppercase fixed"
    assert result.iterations == 2
    assert len(llm.calls) == 2


def test_refine_retries_when_critic_non_ok_even_if_validator_passes():
    initial = "the bottleneck in ai moved from generation to evaluation"
    llm = StubLLMClient(
        responses=[
            "- hook is weak, sharpen it",
            "evaluation is the new bottleneck in ai",
            "OK",
        ]
    )
    result = refine(
        draft=initial,
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
        llm=llm,
        model="claude-sonnet-4-6",
        max_iterations=3,
    )
    assert result.final_draft == "evaluation is the new bottleneck in ai"
    assert result.iterations == 3


def test_refine_caps_at_max_iterations():
    llm = StubLLMClient(
        responses=[
            "- weak hook",
            "new draft 1",
            "- still weak",
            "new draft 2",
        ]
    )
    result = refine(
        draft="starting draft",
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
        llm=llm,
        model="claude-sonnet-4-6",
        max_iterations=2,
    )
    assert result.iterations == 2
    assert result.final_draft == "new draft 1"
```

- [ ] **Step 2: Run failing test**

Run: `uv run pytest tests/generation/test_refine.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement refine loop**

```python
# src/writer_profile/generation/refine.py
from __future__ import annotations

from dataclasses import dataclass, field

from writer_profile.corpus.models import Platform
from writer_profile.generation.generator import _unwrap
from writer_profile.generation.prompts import build_critic_prompt, build_refine_prompt
from writer_profile.llm import LLMClient, LLMMessage
from writer_profile.platforms.base import Constraint


@dataclass
class RefineStep:
    draft: str
    critic_feedback: str
    validator_issues: tuple[str, ...]


@dataclass
class RefineResult:
    final_draft: str
    iterations: int
    history: list[RefineStep] = field(default_factory=list)


def _critique(
    *,
    draft: str,
    platform: Platform,
    constraint: Constraint,
    llm: LLMClient,
    model: str,
) -> str:
    system, user = build_critic_prompt(
        draft=draft, platform=platform, constraint=constraint
    )
    return llm.complete(
        model=model,
        system=system,
        messages=[LLMMessage(role="user", content=user)],
        max_tokens=256,
        temperature=0.2,
    ).strip()


def _rewrite(
    *,
    draft: str,
    platform: Platform,
    constraint: Constraint,
    critic_feedback: str,
    validator_issues: list[str],
    llm: LLMClient,
    model: str,
) -> str:
    system, user = build_refine_prompt(
        draft=draft,
        platform=platform,
        constraint=constraint,
        critic_feedback=critic_feedback,
        validator_issues=validator_issues,
    )
    raw = llm.complete(
        model=model,
        system=system,
        messages=[LLMMessage(role="user", content=user)],
        max_tokens=1024,
        temperature=0.6,
    )
    return _unwrap(raw)


def refine(
    *,
    draft: str,
    platform: Platform,
    constraint: Constraint,
    llm: LLMClient,
    model: str,
    max_iterations: int = 2,
) -> RefineResult:
    current = draft
    history: list[RefineStep] = []
    iterations = 0

    for _ in range(max_iterations):
        iterations += 1
        validator = constraint.validate(current)
        validator_issues = list(validator.issues) if not validator else []

        if validator:
            critic_feedback = _critique(
                draft=current,
                platform=platform,
                constraint=constraint,
                llm=llm,
                model=model,
            )
        else:
            critic_feedback = "validator reported issues"

        history.append(
            RefineStep(
                draft=current,
                critic_feedback=critic_feedback,
                validator_issues=tuple(validator_issues),
            )
        )

        critic_ok = critic_feedback.strip().upper() == "OK"
        if validator and critic_ok:
            break
        if iterations >= max_iterations:
            break

        current = _rewrite(
            draft=current,
            platform=platform,
            constraint=constraint,
            critic_feedback=critic_feedback,
            validator_issues=validator_issues,
            llm=llm,
            model=model,
        )
        iterations += 1
        if iterations >= max_iterations:
            break

    return RefineResult(final_draft=current, iterations=iterations, history=history)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/generation/test_refine.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/writer_profile/generation/refine.py tests/generation/test_refine.py
git commit -m "feat(generation): add Self-Refine loop with critic + validator feedback"
```

---

## Task 15: Pipeline composition

**Files:**
- Create: `src/writer_profile/pipeline.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_pipeline.py
from datetime import datetime, timezone

import pytest

from writer_profile.corpus.models import AnnotatedPost, Platform, Post, PostMetadata, Tone
from writer_profile.llm import StubLLMClient
from writer_profile.pipeline import GenerationPipeline, PostDraft
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    return Embedder(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _ann(pid: str, text: str) -> AnnotatedPost:
    return AnnotatedPost(
        post=Post(
            id=pid,
            platform=Platform.TWITTER,
            text=text,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ),
        metadata=PostMetadata(
            topics=["ai"], tone=Tone.OBSERVATIONAL, length_bucket="short", language="en"
        ),
    )


def test_pipeline_end_to_end_with_stub(tmp_path, embedder):
    store = ExemplarStore(path=str(tmp_path / "c"), embedder=embedder, collection="p")
    store.add_many([_ann("a", "ai evaluation is the new bottleneck")])

    llm = StubLLMClient(
        responses=[
            "the bottleneck in ai agents moved from generation to evaluation",
            "OK",
        ]
    )
    pipe = GenerationPipeline(
        store=store,
        llm=llm,
        writing_model="claude-sonnet-4-6",
        constraints={Platform.TWITTER: TwitterConstraint()},
        retrieval_k=3,
        refine_max_iterations=2,
    )
    out = pipe.generate(topic="ai evaluation bottlenecks", platform=Platform.TWITTER)
    assert isinstance(out, PostDraft)
    assert out.platform is Platform.TWITTER
    assert "evaluation" in out.text
    assert out.validation_ok is True
    assert len(out.exemplars_used) == 1


def test_pipeline_rejects_unknown_platform(tmp_path, embedder):
    store = ExemplarStore(path=str(tmp_path / "c2"), embedder=embedder, collection="p2")
    llm = StubLLMClient(responses=[])
    pipe = GenerationPipeline(
        store=store,
        llm=llm,
        writing_model="claude-sonnet-4-6",
        constraints={Platform.TWITTER: TwitterConstraint()},
    )
    with pytest.raises(KeyError):
        pipe.generate(topic="x", platform=Platform.LINKEDIN)
```

- [ ] **Step 2: Run failing test**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement pipeline**

```python
# src/writer_profile/pipeline.py
from __future__ import annotations

from dataclasses import dataclass, field

from writer_profile.corpus.models import Platform
from writer_profile.generation.generator import generate_draft
from writer_profile.generation.refine import RefineStep, refine
from writer_profile.llm import LLMClient
from writer_profile.platforms.base import Constraint
from writer_profile.retrieval.store import ExemplarHit, ExemplarStore


@dataclass
class PostDraft:
    text: str
    platform: Platform
    topic: str
    exemplars_used: list[ExemplarHit]
    refine_history: list[RefineStep]
    validation_ok: bool
    validation_issues: list[str] = field(default_factory=list)


class GenerationPipeline:
    def __init__(
        self,
        *,
        store: ExemplarStore,
        llm: LLMClient,
        writing_model: str,
        constraints: dict[Platform, Constraint],
        retrieval_k: int = 5,
        refine_max_iterations: int = 2,
    ) -> None:
        self._store = store
        self._llm = llm
        self._writing_model = writing_model
        self._constraints = constraints
        self._retrieval_k = retrieval_k
        self._refine_max_iterations = refine_max_iterations

    def generate(self, *, topic: str, platform: Platform) -> PostDraft:
        if platform not in self._constraints:
            raise KeyError(f"no constraint registered for platform {platform.value}")

        constraint = self._constraints[platform]
        exemplars = self._store.query(text=topic, platform=platform, k=self._retrieval_k)

        initial = generate_draft(
            topic=topic,
            platform=platform,
            exemplars=exemplars,
            constraint=constraint,
            llm=self._llm,
            model=self._writing_model,
        )

        refined = refine(
            draft=initial,
            platform=platform,
            constraint=constraint,
            llm=self._llm,
            model=self._writing_model,
            max_iterations=self._refine_max_iterations,
        )

        final_validation = constraint.validate(refined.final_draft)
        return PostDraft(
            text=refined.final_draft,
            platform=platform,
            topic=topic,
            exemplars_used=exemplars,
            refine_history=refined.history,
            validation_ok=bool(final_validation),
            validation_issues=list(final_validation.issues),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/writer_profile/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): compose retrieval + generate + refine into end-to-end pipeline"
```

---

## Task 16: Ingestion helper (corpus → store)

**Files:**
- Create: `src/writer_profile/corpus/ingest.py`
- Create: `tests/corpus/test_ingest.py`

- [ ] **Step 1: Write failing test**

```python
# tests/corpus/test_ingest.py
import json
from datetime import datetime, timezone

import pytest

from writer_profile.corpus.ingest import ingest_file
from writer_profile.corpus.models import Platform, Post
from writer_profile.llm import StubLLMClient
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    return Embedder(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _post_to_line(p: Post) -> str:
    return p.model_dump_json()


def test_ingest_file_populates_store_with_extracted_metadata(tmp_path, embedder):
    src = tmp_path / "posts.jsonl"
    p1 = Post(
        id="p1",
        platform=Platform.TWITTER,
        text="ai evaluation is the new bottleneck",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    src.write_text(_post_to_line(p1))

    meta_json = json.dumps(
        {
            "topics": ["ai", "evaluation"],
            "tone": "observational",
            "length_bucket": "short",
            "language": "en",
        }
    )
    llm = StubLLMClient(responses=[meta_json])
    store = ExemplarStore(path=str(tmp_path / "c"), embedder=embedder, collection="i")

    count = ingest_file(
        path=src,
        store=store,
        llm=llm,
        classifier_model="claude-haiku-4-5-20251001",
    )
    assert count == 1

    hits = store.query(text="ai evaluation", platform=Platform.TWITTER, k=1)
    assert len(hits) == 1
    assert hits[0].post.id == "p1"
    assert "ai" in hits[0].metadata.topics
```

- [ ] **Step 2: Run failing test**

Run: `uv run pytest tests/corpus/test_ingest.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement ingest**

```python
# src/writer_profile/corpus/ingest.py
from __future__ import annotations

from pathlib import Path

from writer_profile.corpus.extractor import extract_metadata
from writer_profile.corpus.loader import load_posts_jsonl
from writer_profile.corpus.models import AnnotatedPost
from writer_profile.llm import LLMClient
from writer_profile.retrieval.store import ExemplarStore


def ingest_file(
    *,
    path: str | Path,
    store: ExemplarStore,
    llm: LLMClient,
    classifier_model: str,
) -> int:
    posts = load_posts_jsonl(path)
    annotated: list[AnnotatedPost] = []
    for post in posts:
        meta = extract_metadata(post, llm=llm, model=classifier_model)
        annotated.append(AnnotatedPost(post=post, metadata=meta))
    store.add_many(annotated)
    return len(annotated)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/corpus/test_ingest.py -v`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add src/writer_profile/corpus/ingest.py tests/corpus/test_ingest.py
git commit -m "feat(corpus): add ingest_file (load + extract metadata + upsert to store)"
```

---

## Task 17: CLI

**Files:**
- Create: `src/writer_profile/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_cli.py
import json
from datetime import datetime, timezone

import pytest
from typer.testing import CliRunner

from writer_profile.cli import app
from writer_profile.corpus.models import Platform, Post


@pytest.fixture
def sample_jsonl(tmp_path):
    p = tmp_path / "posts.jsonl"
    post = Post(
        id="p1",
        platform=Platform.TWITTER,
        text="ai evaluation is the new bottleneck",
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    p.write_text(post.model_dump_json())
    return p


def test_cli_help_lists_commands():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "generate" in result.stdout


def test_cli_generate_dry_run_does_not_require_api_key(tmp_path, sample_jsonl, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("WRITER_PROFILE_CHROMA_PATH", str(tmp_path / "c"))

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "generate",
            "--platform",
            "twitter",
            "--topic",
            "ai evaluation",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["platform"] == "twitter"
    assert payload["topic"] == "ai evaluation"
    assert payload["dry_run"] is True
```

- [ ] **Step 2: Run failing test**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 3: Implement CLI**

```python
# src/writer_profile/cli.py
from __future__ import annotations

import json
from pathlib import Path

import typer

from writer_profile.config import Settings
from writer_profile.corpus.ingest import ingest_file
from writer_profile.corpus.models import Platform
from writer_profile.llm import AnthropicClient
from writer_profile.pipeline import GenerationPipeline
from writer_profile.platforms.linkedin import LinkedInConstraint
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore

app = typer.Typer(help="Writer-profile: style-aware post generator for Twitter/X and LinkedIn.")


def _default_constraints() -> dict[Platform, object]:
    return {
        Platform.TWITTER: TwitterConstraint(),
        Platform.LINKEDIN: LinkedInConstraint(),
    }


@app.command()
def ingest(
    path: Path = typer.Argument(..., exists=True, readable=True, help="JSONL of posts"),
) -> None:
    """Ingest a JSONL corpus of past posts into the exemplar store."""
    settings = Settings()
    embedder = Embedder(model_name=settings.embedding_model)
    store = ExemplarStore(path=settings.chroma_path, embedder=embedder)
    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    count = ingest_file(path=path, store=store, llm=llm, classifier_model=settings.classifier_model)
    typer.echo(f"ingested {count} posts into {settings.chroma_path}")


@app.command()
def generate(
    platform: Platform = typer.Option(..., case_sensitive=False),
    topic: str = typer.Option(..., help="What to write about"),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Do not call the LLM; emit echoed config as JSON (for smoke tests).",
    ),
) -> None:
    """Generate a post for PLATFORM on TOPIC."""
    settings = Settings()

    if dry_run:
        typer.echo(
            json.dumps(
                {
                    "platform": platform.value,
                    "topic": topic,
                    "writing_model": settings.writing_model,
                    "dry_run": True,
                }
            )
        )
        raise typer.Exit(0)

    embedder = Embedder(model_name=settings.embedding_model)
    store = ExemplarStore(path=settings.chroma_path, embedder=embedder)
    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    pipe = GenerationPipeline(
        store=store,
        llm=llm,
        writing_model=settings.writing_model,
        constraints=_default_constraints(),  # type: ignore[arg-type]
        retrieval_k=settings.retrieval_k,
        refine_max_iterations=settings.refine_max_iterations,
    )
    draft = pipe.generate(topic=topic, platform=platform)
    typer.echo(draft.text)
    if not draft.validation_ok:
        typer.echo(f"[warning] validator issues: {draft.validation_issues}", err=True)


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/writer_profile/cli.py tests/test_cli.py
git commit -m "feat(cli): add ingest and generate commands with --dry-run"
```

---

## Task 18: Full test sweep + lint

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -q`
Expected: all tests pass, 0 failures. If a test fails, fix the offending code (not the test) until green.

- [ ] **Step 2: Run lint**

Run: `uv run ruff check src tests`
Expected: `All checks passed!`

- [ ] **Step 3: Run format check**

Run: `uv run ruff format --check src tests`
Expected: no files would be reformatted. If any would, run `uv run ruff format src tests` and commit.

- [ ] **Step 4: Commit any formatting fixes**

```bash
git add -A
git commit -m "chore: ruff format pass"
```

(Skip this commit if there were no changes.)

---

## Task 19: Live smoke test (requires ANTHROPIC_API_KEY)

This task is **manual verification** — not automated. Run it once to confirm end-to-end behavior against the real API.

- [ ] **Step 1: Set API key and ingest the fixture**

```bash
export ANTHROPIC_API_KEY=<your key>
cp tests/fixtures/sample_posts.jsonl /tmp/posts.jsonl
uv run writer ingest /tmp/posts.jsonl
```

Expected stdout: `ingested 3 posts into .chroma`

- [ ] **Step 2: Generate a Twitter post**

```bash
uv run writer generate --platform twitter --topic "why evaluation beats model size in 2026"
```

Expected: a single line of lowercase text, ≤280 chars, no hashtags.
If the validator prints a warning, the post violated a rule — Self-Refine should have fixed it. Investigate `refine_history` by re-running with a debugger hook or adding a `--verbose` flag (out of scope here; file it as a follow-up).

- [ ] **Step 3: Generate a LinkedIn post**

```bash
uv run writer generate --platform linkedin --topic "why evaluation beats model size in 2026"
```

Expected: multi-line post, each non-empty line ≤12 words, total ≤3000 chars.

- [ ] **Step 4: Note observations in a commit**

```bash
git commit --allow-empty -m "smoke: live twitter+linkedin generation verified against real api"
```

---

## Self-Review (executed before handoff)

**1. Spec coverage:**

| Spec requirement | Task(s) |
|---|---|
| Few-shot style-aware RAG over author corpus | T6 (extractor), T7 (embedder), T8 (Chroma store w/ platform filter), T12 (prompt injects exemplars) |
| Topic/length/tone metadata filter | T2 (PostMetadata), T6 (extractor), T8 (store filter) |
| Self-Refine loop (2-3 iterations) | T14 (configurable, default 2) |
| Platform format constraints (Twitter 280 + lowercase/no-hashtag; LinkedIn line conventions) | T10, T11 |
| Retry-based validator integration (Outlines pluggable) | T9 (`Constraint` protocol), T14 (validator feedback in refine prompt) |
| Per-request end-to-end generation | T15 (pipeline), T17 (CLI) |
| Model routing (Haiku for classification, Sonnet for writing) | T4 (config splits `writing_model` / `classifier_model`), T6 + T17 wiring |
| Corpus ingestion from file | T16, T17 (`writer ingest`) |

Not covered (intentional, deferred to follow-on plans): CrewAI/LangGraph orchestration, virality scoring, publishing APIs, feedback loop, LoRA. Scope box at top of plan documents this.

**2. Placeholder scan:** No TBDs, no "add error handling", no "similar to Task N". Every test body is concrete code. Every expected output is stated.

**3. Type consistency:** `ExemplarHit`, `AnnotatedPost`, `Platform`, `PostMetadata`, `Constraint`, `ValidationResult`, `LLMClient`, `LLMMessage`, `StubLLMClient`, `GenerationPipeline`, `PostDraft`, `RefineResult`, `RefineStep`, `ExemplarStore`, `Embedder` — each defined once and referenced consistently. Method names match across tasks (`generate_draft`, `refine`, `extract_metadata`, `ingest_file`, `load_posts_jsonl`, `embed`/`embed_single`, `add_many`/`query`).

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-21-writer-profile-baseline.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
