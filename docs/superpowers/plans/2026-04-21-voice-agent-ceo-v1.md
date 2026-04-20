# CEO Voice Agent V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `writer-profile` into a multi-author CEO Voice Agent that produces X posts, X threads, and LinkedIn posts in a target CEO's authentic voice, supports human-edit re-voicing, ships with an LLM-judge eval harness, and exposes a minimal Streamlit UI.

**Architecture:** Additive extension of the existing package. Multi-tenancy via new `author` field across `Post` / `ExemplarStore` / ingest. Voice Profile Engine is a hybrid of deterministic statistics (sentence-length histograms, opener/closer top-k, emoji/hashtag rates, n-gram fingerprint) fed into an LLM synthesis pass that produces a structured JSON profile covering lexical / structural / rhetorical / tonal / platform dimensions. Generator is extended to accept idea/angle + author + platform + virality-strength dial, injects the profile + retrieved exemplars + hook suggestions into the prompt, and can emit single posts or short X threads. Re-voicing reuses the existing refine loop with a structural-preservation prompt. Author-specific platform constraints are derived from the statistical profile at build time, killing the hardcoded personal-style rules in the current `TwitterConstraint`.

**Tech Stack:** Python 3.13, pydantic v2, pydantic-settings, typer, chromadb (persistent), sentence-transformers `all-MiniLM-L6-v2`, anthropic SDK (Sonnet 4.6 for writing/judging, Haiku 4.5 for classification), pytest, ruff, streamlit (UI).

**Data inputs (out of scope for this plan — provided as JSONL on disk):**
- `data/posts/<author>.jsonl` — one `Post` per line, with `author`, `platform`, `text`, `created_at`, optional `engagement: {"likes": N, "reposts": N}`.
- `data/hooks.jsonl` — hand-curated hook patterns (Task 11 ships 40 seed entries).

---

## File Structure

**New files:**
```
src/writer_profile/voice/__init__.py
src/writer_profile/voice/stats.py              # deterministic statistical profiler
src/writer_profile/voice/profile.py            # VoiceProfile pydantic schema
src/writer_profile/voice/extractor.py          # LLM synthesis over stats + samples
src/writer_profile/voice/store.py              # JSON file storage per (author, platform)
src/writer_profile/platforms/author_derived.py # per-author Constraint from stats
src/writer_profile/generation/thread.py        # X thread splitter + validator
src/writer_profile/generation/revoice.py       # re-voice entry point
src/writer_profile/virality/__init__.py
src/writer_profile/virality/hooks.py           # HookLibrary with dialable injection
src/writer_profile/eval/__init__.py
src/writer_profile/eval/judge.py               # LLM-as-judge
src/writer_profile/eval/samples.py             # sample generator for manual scoring
data/hooks.jsonl                               # 40 seed hook patterns
docs/architecture.md                           # technical documentation
app.py                                         # Streamlit UI entrypoint
tests/voice/__init__.py
tests/voice/test_stats.py
tests/voice/test_profile.py
tests/voice/test_extractor.py
tests/voice/test_store.py
tests/platforms/test_author_derived.py
tests/virality/__init__.py
tests/virality/test_hooks.py
tests/generation/test_thread.py
tests/generation/test_revoice.py
tests/eval/__init__.py
tests/eval/test_judge.py
tests/eval/test_samples.py
```

**Modified files:**
```
src/writer_profile/corpus/models.py            # add author to Post, add Idea model
src/writer_profile/corpus/ingest.py            # require author
src/writer_profile/retrieval/store.py          # author in metadata + query
src/writer_profile/platforms/twitter.py        # de-personalize — remove hardcoded rules
src/writer_profile/generation/generator.py     # promote _unwrap → unwrap, accept profile + idea
src/writer_profile/generation/prompts.py       # inject profile + hooks + idea
src/writer_profile/generation/refine.py        # fix OK-check brittleness; import unwrap
src/writer_profile/pipeline.py                 # accept author + idea + virality; return Draft
src/writer_profile/cli.py                      # new commands: profile, revoice, evaluate, samples
src/writer_profile/config.py                   # profiles_path, hooks_path
```

---

## Task Index

1. Add `author` to corpus schema + Chroma store + ingest
2. De-personalize `TwitterConstraint` (remove hardcoded lowercase/hashtag rules)
3. Promote `unwrap`; harden critic OK-check
4. `VoiceStats` deterministic profiler
5. `VoiceProfile` pydantic schema
6. LLM voice-profile extractor (synthesis over stats + samples)
7. `VoiceProfileStore` (JSON file per author/platform)
8. Author-derived `Constraint` builder
9. Seed `data/hooks.jsonl` + `HookLibrary`
10. Generator prompt injection (profile + hooks + idea)
11. Generator + pipeline signature overhaul
12. X thread splitter + validator
13. Re-voice module (reuses refine internals)
14. Pipeline `revoice` method
15. LLM-as-judge
16. Sample generator
17. CLI: `profile build` / `profile show`
18. CLI: `generate` / `revoice`
19. CLI: `evaluate` / `samples`
20. Streamlit UI
21. Architecture doc + live smoke test

---

## Task 1: Multi-tenancy — `author` field end-to-end

**Files:**
- Modify: `src/writer_profile/corpus/models.py`
- Modify: `src/writer_profile/retrieval/store.py`
- Modify: `src/writer_profile/corpus/ingest.py`
- Test: `tests/corpus/test_models.py`
- Test: `tests/retrieval/test_store.py`
- Test: `tests/corpus/test_ingest.py`

- [ ] **Step 1: Write failing test for `Post.author`**

Append to `tests/corpus/test_models.py`:

```python
def test_post_requires_author():
    import pytest
    from datetime import datetime, UTC
    from pydantic import ValidationError
    from writer_profile.corpus.models import Platform, Post

    with pytest.raises(ValidationError):
        Post(
            id="p1",
            platform=Platform.TWITTER,
            text="hi",
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        )


def test_post_accepts_author():
    from datetime import datetime, UTC
    from writer_profile.corpus.models import Platform, Post

    p = Post(
        id="p1",
        author="ali_ghodsi",
        platform=Platform.TWITTER,
        text="hi",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    assert p.author == "ali_ghodsi"
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/corpus/test_models.py -q`
Expected: 2 failures — `author` field missing.

- [ ] **Step 3: Add `author` to `Post`**

Edit `src/writer_profile/corpus/models.py`:

```python
class Post(BaseModel):
    id: str
    author: str = Field(min_length=1)
    platform: Platform
    text: str = Field(min_length=1)
    created_at: datetime
    engagement: dict[str, int] | None = None
```

- [ ] **Step 4: Run test — expect pass**

Run: `uv run pytest tests/corpus/test_models.py -q`
Expected: PASS.

- [ ] **Step 5: Write failing test for author-filtered store query**

Edit `tests/retrieval/test_store.py`, add:

```python
def test_store_filters_by_author(tmp_path, embedder):
    from datetime import datetime, UTC
    from writer_profile.corpus.models import AnnotatedPost, Platform, Post, PostMetadata, Tone
    from writer_profile.retrieval.store import ExemplarStore

    def ann(pid: str, author: str, text: str) -> AnnotatedPost:
        return AnnotatedPost(
            post=Post(
                id=pid, author=author, platform=Platform.TWITTER,
                text=text, created_at=datetime(2025, 1, 1, tzinfo=UTC),
            ),
            metadata=PostMetadata(
                topics=["ai"], tone=Tone.OBSERVATIONAL,
                length_bucket="short", language="en",
            ),
        )

    store = ExemplarStore(path=str(tmp_path / "c"), embedder=embedder, collection="author_filter")
    store.add_many([
        ann("a1", "ali", "iceberg is the future of open data"),
        ann("m1", "matei", "spark 4 is shipping vectorized execution"),
    ])

    hits = store.query(text="open data formats", platform=Platform.TWITTER, author="ali", k=5)
    assert len(hits) == 1
    assert hits[0].post.author == "ali"
```

- [ ] **Step 6: Run test — expect fail**

Run: `uv run pytest tests/retrieval/test_store.py::test_store_filters_by_author -q`
Expected: FAIL — `query()` has no `author` kwarg.

- [ ] **Step 7: Add `author` to store metadata + query**

Edit `src/writer_profile/retrieval/store.py`:

```python
    def add_many(self, items: list[AnnotatedPost]) -> None:
        if not items:
            return
        ids = [i.post.id for i in items]
        docs = [i.post.text for i in items]
        vectors = self._embedder.embed(docs).tolist()
        metadatas = [
            {
                "author": i.post.author,
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
        author: str | None = None,
        k: int = 5,
        tone: str | None = None,
    ) -> list[ExemplarHit]:
        vec = self._embedder.embed_single(text).tolist()
        clauses: list[dict[str, object]] = [{"platform": platform.value}]
        if author:
            clauses.append({"author": author})
        if tone:
            clauses.append({"tone": tone})
        where = clauses[0] if len(clauses) == 1 else {"$and": clauses}
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

- [ ] **Step 8: Update existing ingest test fixture**

Edit `tests/corpus/test_ingest.py`, change the `Post(...)` construction to include `author="ali"`:

```python
    p1 = Post(
        id="p1",
        author="ali",
        platform=Platform.TWITTER,
        text="ai evaluation is the new bottleneck",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
```

- [ ] **Step 9: Update existing pipeline test fixture**

Edit `tests/test_pipeline.py` in `_ann` helper:

```python
def _ann(pid: str, text: str) -> AnnotatedPost:
    return AnnotatedPost(
        post=Post(
            id=pid,
            author="ali",
            platform=Platform.TWITTER,
            text=text,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        ),
        metadata=PostMetadata(
            topics=["ai"], tone=Tone.OBSERVATIONAL, length_bucket="short", language="en"
        ),
    )
```

- [ ] **Step 10: Update existing CLI test fixture**

Edit `tests/test_cli.py`:

```python
    post = Post(
        id="p1",
        author="ali",
        platform=Platform.TWITTER,
        text="ai evaluation is the new bottleneck",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
```

- [ ] **Step 11: Run full suite — expect all green**

Run: `uv run pytest -q`
Expected: all tests pass including the new `test_store_filters_by_author`.

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "feat(corpus): add author field for multi-tenant voice storage"
```

---

## Task 2: De-personalize `TwitterConstraint`

**Files:**
- Modify: `src/writer_profile/platforms/twitter.py`
- Test: `tests/platforms/test_twitter.py`

Rationale: current defaults (`require_lowercase=True`, `allow_hashtags=False`, "no emojis" rule) are baked to the author of the original repo. For CEO voice mimicry these must come from the voice profile.

- [ ] **Step 1: Write failing test for neutral defaults**

Append to `tests/platforms/test_twitter.py`:

```python
def test_twitter_default_allows_hashtags_and_case_and_emoji():
    from writer_profile.platforms.twitter import TwitterConstraint

    c = TwitterConstraint()
    r = c.validate("Excited to announce 🎉 #databricks is acquiring Tabular")
    assert bool(r), r.issues

def test_twitter_describe_rules_no_hardcoded_style():
    from writer_profile.platforms.twitter import TwitterConstraint

    rules = TwitterConstraint().describe_rules()
    lowered = rules.lower()
    assert "lowercase" not in lowered
    assert "no slop" not in lowered
    assert "no emojis" not in lowered
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/platforms/test_twitter.py -q`
Expected: FAIL — default `require_lowercase=True` rejects capitals.

- [ ] **Step 3: Rewrite `TwitterConstraint`**

Replace `src/writer_profile/platforms/twitter.py`:

```python
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
```

- [ ] **Step 4: Run full suite — expect pass**

Run: `uv run pytest -q`
Expected: all green (existing Twitter tests continue to pass because they construct `TwitterConstraint(require_lowercase=True)` explicitly or don't exercise uppercase).

If any pre-existing test assumed lowercase-by-default, update it to set `require_lowercase=True` explicitly.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "fix(platforms): twitter constraint defaults to neutral; author voice drives style"
```

---

## Task 3: Promote `unwrap`; harden critic OK-check

**Files:**
- Modify: `src/writer_profile/generation/generator.py`
- Modify: `src/writer_profile/generation/refine.py`
- Test: `tests/generation/test_refine.py`
- Test: `tests/generation/test_generator.py`

- [ ] **Step 1: Write failing test for critic OK variants**

Append to `tests/generation/test_refine.py`:

```python
def test_refine_short_circuits_on_ok_with_punctuation():
    from writer_profile.corpus.models import Platform
    from writer_profile.generation.refine import refine
    from writer_profile.llm import StubLLMClient
    from writer_profile.platforms.twitter import TwitterConstraint

    initial = "the bottleneck in ai moved from generation to evaluation"
    llm = StubLLMClient(responses=["OK."])
    result = refine(
        draft=initial,
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(require_lowercase=True, allow_hashtags=False),
        llm=llm,
        model="claude-sonnet-4-6",
        max_iterations=3,
    )
    assert result.iterations == 1
    assert len(llm.calls) == 1


def test_refine_short_circuits_on_lowercase_ok():
    from writer_profile.corpus.models import Platform
    from writer_profile.generation.refine import refine
    from writer_profile.llm import StubLLMClient
    from writer_profile.platforms.twitter import TwitterConstraint

    initial = "the bottleneck in ai moved from generation to evaluation"
    llm = StubLLMClient(responses=["ok, looks strong to me"])
    result = refine(
        draft=initial,
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(require_lowercase=True, allow_hashtags=False),
        llm=llm,
        model="claude-sonnet-4-6",
        max_iterations=3,
    )
    assert result.iterations == 1
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/generation/test_refine.py::test_refine_short_circuits_on_ok_with_punctuation -q`
Expected: FAIL — current check is `==` against exact `"OK"`.

- [ ] **Step 3: Edit `refine.py`**

Change the short-circuit check and promote `unwrap`:

In `src/writer_profile/generation/refine.py`, top of file:

```python
from writer_profile.generation.generator import unwrap
```

(replace `_unwrap` references with `unwrap`).

Replace the OK-check line:

```python
            if bool(validator) and _is_ok(critic_feedback):
                break
```

Add at module level:

```python
def _is_ok(feedback: str) -> bool:
    stripped = feedback.strip().lstrip("-* ").strip()
    if not stripped:
        return False
    first_token = stripped.split()[0].strip(".,!:;").upper()
    return first_token == "OK"
```

- [ ] **Step 4: Rename `_unwrap` to `unwrap` in `generator.py`**

Edit `src/writer_profile/generation/generator.py`:

```python
def unwrap(raw: str) -> str:
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
    return unwrap(raw)
```

- [ ] **Step 5: Run full suite — expect pass**

Run: `uv run pytest -q`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(generation): promote unwrap; accept OK-variants in refine critic check"
```

---

## Task 4: `VoiceStats` — deterministic statistical profiler

**Files:**
- Create: `src/writer_profile/voice/__init__.py` (empty)
- Create: `src/writer_profile/voice/stats.py`
- Create: `tests/voice/__init__.py` (empty)
- Create: `tests/voice/test_stats.py`

Computes deterministic stats from a list of `Post`s for a single (author, platform).

- [ ] **Step 1: Write failing test**

Create `tests/voice/__init__.py` as empty file.

Create `tests/voice/test_stats.py`:

```python
from datetime import datetime, UTC

from writer_profile.corpus.models import Platform, Post
from writer_profile.voice.stats import compute_stats


def _p(pid: str, text: str) -> Post:
    return Post(
        id=pid, author="ali", platform=Platform.TWITTER,
        text=text, created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def test_compute_stats_basic_shape():
    posts = [
        _p("1", "AI is eating software. Again."),
        _p("2", "Open source wins. Always did. Always will."),
        _p("3", "Spark 4 ships vectorized execution today! 🚀"),
    ]
    s = compute_stats(posts)

    assert s.post_count == 3
    assert 3.0 <= s.avg_words_per_sentence <= 6.0
    assert 0.0 <= s.emoji_rate <= 1.0
    assert 0.0 <= s.hashtag_rate <= 1.0
    assert s.emoji_rate > 0.0  # one of the posts has an emoji
    assert len(s.top_openers) > 0
    assert len(s.top_closers) > 0
    assert len(s.length_chars_p25_p50_p75) == 3


def test_compute_stats_empty_corpus_errors():
    import pytest
    with pytest.raises(ValueError):
        compute_stats([])


def test_compute_stats_detects_hashtag_rate():
    posts = [
        _p("1", "launching today #databricks #ai"),
        _p("2", "no hashtags here"),
    ]
    s = compute_stats(posts)
    assert s.hashtag_rate == 0.5
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/voice/test_stats.py -q`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Create `src/writer_profile/voice/__init__.py`** (empty file)

- [ ] **Step 4: Implement `src/writer_profile/voice/stats.py`**

```python
from __future__ import annotations

import re
import statistics
from collections import Counter
from dataclasses import dataclass, field

from writer_profile.corpus.models import Post

_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F900-\U0001F9FF]"
)
_HASHTAG_RE = re.compile(r"(?<!\w)#\w+")
_URL_RE = re.compile(r"https?://\S+")
_MENTION_RE = re.compile(r"(?<!\w)@\w+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class VoiceStats:
    post_count: int
    avg_words_per_sentence: float
    sentence_length_p25_p50_p75: tuple[float, float, float]
    length_chars_p25_p50_p75: tuple[float, float, float]
    emoji_rate: float                    # fraction of posts containing >=1 emoji
    hashtag_rate: float                  # fraction of posts containing >=1 hashtag
    avg_hashtags_per_post: float
    url_rate: float
    question_rate: float
    mention_rate: float
    line_break_rate: float               # fraction of posts with >=1 blank line
    top_openers: list[str] = field(default_factory=list)    # first ~6 words, top 10
    top_closers: list[str] = field(default_factory=list)    # last ~6 words, top 10
    top_bigrams: list[tuple[str, int]] = field(default_factory=list)
    top_trigrams: list[tuple[str, int]] = field(default_factory=list)
    thread_rate: float = 0.0             # fraction of posts that look like thread starters


def _percentiles(xs: list[float]) -> tuple[float, float, float]:
    if not xs:
        return (0.0, 0.0, 0.0)
    xs_sorted = sorted(xs)
    q = statistics.quantiles(xs_sorted, n=4) if len(xs_sorted) >= 4 else [
        xs_sorted[0],
        xs_sorted[len(xs_sorted) // 2],
        xs_sorted[-1],
    ]
    return (float(q[0]), float(q[1]), float(q[2]))


def _sentence_word_counts(text: str) -> list[int]:
    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(text) if p.strip()]
    return [len(p.split()) for p in parts] or [len(text.split())]


def _first_words(text: str, n: int = 6) -> str:
    words = text.strip().split()[:n]
    return " ".join(w.lower() for w in words)


def _last_words(text: str, n: int = 6) -> str:
    words = text.strip().split()
    return " ".join(w.lower() for w in words[-n:]) if words else ""


def _ngrams(tokens: list[str], n: int) -> list[str]:
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def compute_stats(posts: list[Post]) -> VoiceStats:
    if not posts:
        raise ValueError("cannot compute stats from empty corpus")

    total = len(posts)
    sent_counts_all: list[int] = []
    char_lens: list[int] = []
    emoji_hits = 0
    hashtag_hits = 0
    total_hashtags = 0
    url_hits = 0
    question_hits = 0
    mention_hits = 0
    line_break_hits = 0
    openers: Counter[str] = Counter()
    closers: Counter[str] = Counter()
    bigrams: Counter[str] = Counter()
    trigrams: Counter[str] = Counter()
    thread_hits = 0

    for p in posts:
        t = p.text
        char_lens.append(len(t))
        sent_counts_all.extend(_sentence_word_counts(t))
        if _EMOJI_RE.search(t):
            emoji_hits += 1
        tags = _HASHTAG_RE.findall(t)
        if tags:
            hashtag_hits += 1
            total_hashtags += len(tags)
        if _URL_RE.search(t):
            url_hits += 1
        if "?" in t:
            question_hits += 1
        if _MENTION_RE.search(t):
            mention_hits += 1
        if "\n\n" in t:
            line_break_hits += 1
        if re.search(r"(?:^|\n)\s*(?:1[./)]|🧵)", t):
            thread_hits += 1

        openers[_first_words(t)] += 1
        closers[_last_words(t)] += 1
        toks = [w.lower().strip(".,!?;:") for w in t.split() if w.strip()]
        for bg in _ngrams(toks, 2):
            bigrams[bg] += 1
        for tg in _ngrams(toks, 3):
            trigrams[tg] += 1

    return VoiceStats(
        post_count=total,
        avg_words_per_sentence=(sum(sent_counts_all) / len(sent_counts_all))
        if sent_counts_all
        else 0.0,
        sentence_length_p25_p50_p75=_percentiles([float(x) for x in sent_counts_all]),
        length_chars_p25_p50_p75=_percentiles([float(x) for x in char_lens]),
        emoji_rate=emoji_hits / total,
        hashtag_rate=hashtag_hits / total,
        avg_hashtags_per_post=total_hashtags / total,
        url_rate=url_hits / total,
        question_rate=question_hits / total,
        mention_rate=mention_hits / total,
        line_break_rate=line_break_hits / total,
        top_openers=[o for o, _ in openers.most_common(10)],
        top_closers=[c for c, _ in closers.most_common(10)],
        top_bigrams=bigrams.most_common(20),
        top_trigrams=trigrams.most_common(20),
        thread_rate=thread_hits / total,
    )
```

- [ ] **Step 5: Run test — expect pass**

Run: `uv run pytest tests/voice/test_stats.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(voice): deterministic statistical profiler"
```

---

## Task 5: `VoiceProfile` pydantic schema

**Files:**
- Create: `src/writer_profile/voice/profile.py`
- Create: `tests/voice/test_profile.py`

- [ ] **Step 1: Write failing test**

Create `tests/voice/test_profile.py`:

```python
import json
from pathlib import Path

from writer_profile.corpus.models import Platform
from writer_profile.voice.profile import (
    LexicalProfile,
    RhetoricalProfile,
    StructuralProfile,
    TonalProfile,
    VoiceProfile,
)
from writer_profile.voice.stats import VoiceStats


def _stats_stub() -> VoiceStats:
    return VoiceStats(
        post_count=100,
        avg_words_per_sentence=14.2,
        sentence_length_p25_p50_p75=(7.0, 12.0, 20.0),
        length_chars_p25_p50_p75=(90.0, 170.0, 260.0),
        emoji_rate=0.05,
        hashtag_rate=0.10,
        avg_hashtags_per_post=0.15,
        url_rate=0.22,
        question_rate=0.18,
        mention_rate=0.30,
        line_break_rate=0.12,
        top_openers=["at databricks we", "open source is"],
        top_closers=["what do you think?", "let me know"],
        top_bigrams=[("open source", 20)],
        top_trigrams=[("open source wins", 10)],
        thread_rate=0.08,
    )


def test_voice_profile_roundtrip(tmp_path: Path):
    vp = VoiceProfile(
        author="ali_ghodsi",
        platform=Platform.LINKEDIN,
        stats=_stats_stub(),
        lexical=LexicalProfile(
            recurring_phrases=["open source", "compound ai"],
            word_preferences={"team": 1, "folks": 0},
            jargon_level="medium",
            notes="light on jargon, heavy on conviction words",
        ),
        structural=StructuralProfile(
            typical_opener_patterns=["declarative one-liner", "contrarian hook"],
            typical_closer_patterns=["forward-looking statement"],
            paragraph_shape="3-5 short paragraphs with blank lines between",
            list_usage="rarely uses bullet lists",
            question_usage="occasional audience question at close",
        ),
        rhetorical=RhetoricalProfile(
            uses_analogies=True,
            uses_personal_anecdotes=True,
            uses_data_points=True,
            attribution_style="credits team + external contributors by name",
            name_drop_rate="moderate",
        ),
        tonal=TonalProfile(
            warmth="warm",
            humor="dry",
            conviction="high",
            disclosure="moderate",
            vulnerability="rare",
        ),
        examples=["open source wins. it always has.", "today we ship..."],
    )

    # roundtrip via JSON
    raw = vp.model_dump_json()
    restored = VoiceProfile.model_validate_json(raw)
    assert restored.author == "ali_ghodsi"
    assert restored.platform is Platform.LINKEDIN
    assert restored.stats.post_count == 100
    assert "open source" in restored.lexical.recurring_phrases
    assert restored.tonal.conviction == "high"

    # writable to disk and reloadable
    p = tmp_path / "profile.json"
    p.write_text(raw)
    reloaded = VoiceProfile.model_validate_json(p.read_text())
    assert reloaded == restored
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/voice/test_profile.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `src/writer_profile/voice/profile.py`**

```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from writer_profile.corpus.models import Platform
from writer_profile.voice.stats import VoiceStats

JargonLevel = Literal["low", "medium", "high"]
Intensity = Literal["rare", "occasional", "moderate", "frequent"]
Register = Literal["warm", "neutral", "distant"]
HumorStyle = Literal["none", "dry", "playful", "sharp"]
ConvictionLevel = Literal["low", "medium", "high"]


class LexicalProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    recurring_phrases: list[str]
    word_preferences: dict[str, int]   # {"team": 1, "folks": 0} — 1 means preferred
    jargon_level: JargonLevel
    notes: str = ""


class StructuralProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    typical_opener_patterns: list[str]
    typical_closer_patterns: list[str]
    paragraph_shape: str
    list_usage: str
    question_usage: str


class RhetoricalProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    uses_analogies: bool
    uses_personal_anecdotes: bool
    uses_data_points: bool
    attribution_style: str
    name_drop_rate: Intensity


class TonalProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    warmth: Register
    humor: HumorStyle
    conviction: ConvictionLevel
    disclosure: Intensity
    vulnerability: Intensity


class VoiceProfile(BaseModel):
    author: str
    platform: Platform
    stats: VoiceStats
    lexical: LexicalProfile
    structural: StructuralProfile
    rhetorical: RhetoricalProfile
    tonal: TonalProfile
    examples: list[str]  # 3-5 canonical posts
```

Note: `VoiceStats` is a `dataclass`, not a `BaseModel`. Pydantic supports embedding dataclasses in `BaseModel` via `ConfigDict(arbitrary_types_allowed=True)`. Simpler: convert `VoiceStats` to a pydantic model. To keep this change small, add `model_config = ConfigDict(arbitrary_types_allowed=True)` to `VoiceProfile` and provide a `to_dict()` on stats:

Update `src/writer_profile/voice/stats.py` — add at end of `VoiceStats`:

```python
    def model_dump(self) -> dict:
        """Pydantic-compatible serialization helper."""
        from dataclasses import asdict
        return asdict(self)
```

Update `VoiceProfile` model config:

```python
class VoiceProfile(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    author: str
    platform: Platform
    stats: VoiceStats
    ...
```

This fails for JSON roundtrip. Cleaner fix: convert `VoiceStats` to `BaseModel`.

Edit `src/writer_profile/voice/stats.py` — replace the `@dataclass` with a BaseModel:

```python
from pydantic import BaseModel, Field


class VoiceStats(BaseModel):
    post_count: int
    avg_words_per_sentence: float
    sentence_length_p25_p50_p75: tuple[float, float, float]
    length_chars_p25_p50_p75: tuple[float, float, float]
    emoji_rate: float
    hashtag_rate: float
    avg_hashtags_per_post: float
    url_rate: float
    question_rate: float
    mention_rate: float
    line_break_rate: float
    top_openers: list[str] = Field(default_factory=list)
    top_closers: list[str] = Field(default_factory=list)
    top_bigrams: list[tuple[str, int]] = Field(default_factory=list)
    top_trigrams: list[tuple[str, int]] = Field(default_factory=list)
    thread_rate: float = 0.0
```

(Remove the `@dataclass` decorator and `field(default_factory=...)` syntax; keep `compute_stats` implementation the same — it constructs `VoiceStats(...)` by kwargs, which works identically.)

Remove the `from dataclasses import dataclass, field` import at the top of `stats.py` (no longer needed).

- [ ] **Step 4: Run both tests — expect pass**

Run: `uv run pytest tests/voice/ -q`
Expected: `test_stats.py` + `test_profile.py` all pass.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(voice): VoiceProfile schema with pydantic stats"
```

---

## Task 6: LLM voice-profile extractor

**Files:**
- Create: `src/writer_profile/voice/extractor.py`
- Create: `tests/voice/test_extractor.py`

Builds the qualitative layer of the profile by synthesizing from stats + sample posts via Sonnet.

- [ ] **Step 1: Write failing test**

Create `tests/voice/test_extractor.py`:

```python
import json
from datetime import datetime, UTC

from writer_profile.corpus.models import Platform, Post
from writer_profile.llm import StubLLMClient
from writer_profile.voice.extractor import build_voice_profile


def _p(pid: str, text: str) -> Post:
    return Post(
        id=pid, author="ali", platform=Platform.LINKEDIN,
        text=text, created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def test_build_voice_profile_wires_llm_and_stats():
    posts = [
        _p("1", "open source wins. it always has."),
        _p("2", "databricks is acquiring tabular today. bringing spark and iceberg together."),
        _p("3", "what do you think about the future of open data formats?"),
    ]

    qualitative_json = json.dumps({
        "lexical": {
            "recurring_phrases": ["open source", "data formats"],
            "word_preferences": {"team": 1},
            "jargon_level": "medium",
            "notes": "uses conviction words",
        },
        "structural": {
            "typical_opener_patterns": ["declarative one-liner"],
            "typical_closer_patterns": ["audience question"],
            "paragraph_shape": "short punchy paragraphs",
            "list_usage": "rare",
            "question_usage": "frequent close",
        },
        "rhetorical": {
            "uses_analogies": True,
            "uses_personal_anecdotes": False,
            "uses_data_points": True,
            "attribution_style": "credits teams",
            "name_drop_rate": "moderate",
        },
        "tonal": {
            "warmth": "warm",
            "humor": "dry",
            "conviction": "high",
            "disclosure": "occasional",
            "vulnerability": "rare",
        },
        "examples": [
            "open source wins. it always has.",
            "databricks is acquiring tabular today.",
        ],
    })

    llm = StubLLMClient(responses=[qualitative_json])
    profile = build_voice_profile(
        author="ali",
        platform=Platform.LINKEDIN,
        posts=posts,
        llm=llm,
        model="claude-sonnet-4-6",
    )

    assert profile.author == "ali"
    assert profile.platform is Platform.LINKEDIN
    assert profile.stats.post_count == 3
    assert "open source" in profile.lexical.recurring_phrases
    assert profile.tonal.conviction == "high"
    assert len(llm.calls) == 1
    # prompt must include the stats block so the LLM is grounded
    system = llm.calls[0].system
    assert "avg_words_per_sentence" in system or "stats" in system.lower()


def test_build_voice_profile_strips_json_fence():
    posts = [_p("1", "hello world")]
    wrapped = "```json\n" + json.dumps({
        "lexical": {"recurring_phrases": [], "word_preferences": {}, "jargon_level": "low", "notes": ""},
        "structural": {
            "typical_opener_patterns": [], "typical_closer_patterns": [],
            "paragraph_shape": "", "list_usage": "", "question_usage": "",
        },
        "rhetorical": {
            "uses_analogies": False, "uses_personal_anecdotes": False,
            "uses_data_points": False, "attribution_style": "", "name_drop_rate": "rare",
        },
        "tonal": {
            "warmth": "neutral", "humor": "none",
            "conviction": "low", "disclosure": "rare", "vulnerability": "rare",
        },
        "examples": ["hello world"],
    }) + "\n```"

    llm = StubLLMClient(responses=[wrapped])
    profile = build_voice_profile(
        author="ali", platform=Platform.LINKEDIN, posts=posts,
        llm=llm, model="claude-sonnet-4-6",
    )
    assert profile.author == "ali"
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/voice/test_extractor.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `src/writer_profile/voice/extractor.py`**

```python
from __future__ import annotations

import json
import re

from writer_profile.corpus.models import Platform, Post
from writer_profile.llm import LLMClient, LLMMessage
from writer_profile.voice.profile import (
    LexicalProfile,
    RhetoricalProfile,
    StructuralProfile,
    TonalProfile,
    VoiceProfile,
)
from writer_profile.voice.stats import compute_stats

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)

_SYSTEM_TEMPLATE = """You are an expert voice analyst. Given statistical fingerprints AND sample posts from one author on one platform, produce a structured JSON voice profile.

GROUND YOUR ANALYSIS IN THE STATS. Do not invent traits the numbers contradict.

STATS:
{stats_block}

SAMPLE POSTS (representative of this author on {platform}):
{samples_block}

Return ONLY a JSON object with these exact top-level keys:
- lexical: {{recurring_phrases: [str], word_preferences: {{word: 1|0}}, jargon_level: "low"|"medium"|"high", notes: str}}
- structural: {{typical_opener_patterns: [str], typical_closer_patterns: [str], paragraph_shape: str, list_usage: str, question_usage: str}}
- rhetorical: {{uses_analogies: bool, uses_personal_anecdotes: bool, uses_data_points: bool, attribution_style: str, name_drop_rate: "rare"|"occasional"|"moderate"|"frequent"}}
- tonal: {{warmth: "warm"|"neutral"|"distant", humor: "none"|"dry"|"playful"|"sharp", conviction: "low"|"medium"|"high", disclosure: "rare"|"occasional"|"moderate"|"frequent", vulnerability: "rare"|"occasional"|"moderate"|"frequent"}}
- examples: [str]  (3-5 verbatim posts that most exemplify the voice)

No prose. No explanation. Just the JSON."""


def _strip_fence(raw: str) -> str:
    m = _FENCE_RE.search(raw)
    return m.group(1) if m else raw.strip()


def _stats_block(stats) -> str:
    return json.dumps(stats.model_dump(), indent=2, default=str)


def _samples_block(posts: list[Post], limit: int = 40) -> str:
    # trim aggressively to fit in context; prefer longer posts (more signal)
    sorted_posts = sorted(posts, key=lambda p: len(p.text), reverse=True)[:limit]
    return "\n\n---\n\n".join(p.text for p in sorted_posts)


def build_voice_profile(
    *,
    author: str,
    platform: Platform,
    posts: list[Post],
    llm: LLMClient,
    model: str,
) -> VoiceProfile:
    stats = compute_stats(posts)
    system = _SYSTEM_TEMPLATE.format(
        stats_block=_stats_block(stats),
        platform=platform.value,
        samples_block=_samples_block(posts),
    )
    raw = llm.complete(
        model=model,
        system=system,
        messages=[LLMMessage(role="user", content="Produce the JSON voice profile now.")],
        max_tokens=2048,
        temperature=0.1,
    )
    data = json.loads(_strip_fence(raw))

    return VoiceProfile(
        author=author,
        platform=platform,
        stats=stats,
        lexical=LexicalProfile.model_validate(data["lexical"]),
        structural=StructuralProfile.model_validate(data["structural"]),
        rhetorical=RhetoricalProfile.model_validate(data["rhetorical"]),
        tonal=TonalProfile.model_validate(data["tonal"]),
        examples=list(data.get("examples", [])),
    )
```

- [ ] **Step 4: Run test — expect pass**

Run: `uv run pytest tests/voice/test_extractor.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(voice): LLM synthesis extractor grounded in VoiceStats"
```

---

## Task 7: `VoiceProfileStore` — JSON file per author/platform

**Files:**
- Create: `src/writer_profile/voice/store.py`
- Create: `tests/voice/test_store.py`

- [ ] **Step 1: Write failing test**

Create `tests/voice/test_store.py`:

```python
from pathlib import Path

from writer_profile.corpus.models import Platform
from writer_profile.voice.profile import (
    LexicalProfile, RhetoricalProfile, StructuralProfile, TonalProfile, VoiceProfile,
)
from writer_profile.voice.stats import VoiceStats
from writer_profile.voice.store import VoiceProfileStore


def _profile(author: str, platform: Platform) -> VoiceProfile:
    return VoiceProfile(
        author=author,
        platform=platform,
        stats=VoiceStats(
            post_count=10, avg_words_per_sentence=12.0,
            sentence_length_p25_p50_p75=(6.0, 11.0, 18.0),
            length_chars_p25_p50_p75=(80.0, 150.0, 220.0),
            emoji_rate=0.1, hashtag_rate=0.0, avg_hashtags_per_post=0.0,
            url_rate=0.2, question_rate=0.1, mention_rate=0.3,
            line_break_rate=0.05, top_openers=["hi"], top_closers=["bye"],
            top_bigrams=[("hi there", 2)], top_trigrams=[], thread_rate=0.0,
        ),
        lexical=LexicalProfile(recurring_phrases=["x"], word_preferences={"a": 1},
                               jargon_level="low", notes=""),
        structural=StructuralProfile(typical_opener_patterns=[], typical_closer_patterns=[],
                                     paragraph_shape="", list_usage="", question_usage=""),
        rhetorical=RhetoricalProfile(uses_analogies=False, uses_personal_anecdotes=False,
                                     uses_data_points=False, attribution_style="",
                                     name_drop_rate="rare"),
        tonal=TonalProfile(warmth="neutral", humor="none", conviction="low",
                           disclosure="rare", vulnerability="rare"),
        examples=["hi"],
    )


def test_store_save_and_load_roundtrip(tmp_path: Path):
    store = VoiceProfileStore(root=tmp_path)
    p = _profile("ali", Platform.TWITTER)
    store.save(p)

    out = store.load(author="ali", platform=Platform.TWITTER)
    assert out == p


def test_store_missing_profile_raises(tmp_path: Path):
    import pytest
    store = VoiceProfileStore(root=tmp_path)
    with pytest.raises(FileNotFoundError):
        store.load(author="nobody", platform=Platform.TWITTER)


def test_store_list_profiles(tmp_path: Path):
    store = VoiceProfileStore(root=tmp_path)
    store.save(_profile("ali", Platform.TWITTER))
    store.save(_profile("ali", Platform.LINKEDIN))
    store.save(_profile("matei", Platform.TWITTER))

    entries = sorted(store.list_profiles())
    assert entries == [("ali", Platform.LINKEDIN), ("ali", Platform.TWITTER), ("matei", Platform.TWITTER)]
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/voice/test_store.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `src/writer_profile/voice/store.py`**

```python
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
```

- [ ] **Step 4: Run test — expect pass**

Run: `uv run pytest tests/voice/test_store.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(voice): JSON file store per author/platform"
```

---

## Task 8: Author-derived `Constraint` builder

**Files:**
- Create: `src/writer_profile/platforms/author_derived.py`
- Create: `tests/platforms/test_author_derived.py`

Converts a `VoiceProfile` into a platform-appropriate `Constraint` with params pulled from the author's own statistical fingerprint.

- [ ] **Step 1: Write failing test**

Create `tests/platforms/test_author_derived.py`:

```python
from writer_profile.corpus.models import Platform
from writer_profile.platforms.author_derived import constraint_for
from writer_profile.platforms.linkedin import LinkedInConstraint
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.voice.profile import (
    LexicalProfile, RhetoricalProfile, StructuralProfile, TonalProfile, VoiceProfile,
)
from writer_profile.voice.stats import VoiceStats


def _profile_with(hashtag_rate: float, platform: Platform) -> VoiceProfile:
    return VoiceProfile(
        author="x", platform=platform,
        stats=VoiceStats(
            post_count=100, avg_words_per_sentence=12.0,
            sentence_length_p25_p50_p75=(6.0, 11.0, 18.0),
            length_chars_p25_p50_p75=(80.0, 150.0, 220.0),
            emoji_rate=0.0, hashtag_rate=hashtag_rate, avg_hashtags_per_post=0.5,
            url_rate=0.1, question_rate=0.1, mention_rate=0.2,
            line_break_rate=0.1, top_openers=[], top_closers=[],
            top_bigrams=[], top_trigrams=[], thread_rate=0.0,
        ),
        lexical=LexicalProfile(recurring_phrases=[], word_preferences={}, jargon_level="low", notes=""),
        structural=StructuralProfile(typical_opener_patterns=[], typical_closer_patterns=[],
                                     paragraph_shape="", list_usage="", question_usage=""),
        rhetorical=RhetoricalProfile(uses_analogies=False, uses_personal_anecdotes=False,
                                     uses_data_points=False, attribution_style="",
                                     name_drop_rate="rare"),
        tonal=TonalProfile(warmth="neutral", humor="none", conviction="low",
                           disclosure="rare", vulnerability="rare"),
        examples=[],
    )


def test_twitter_constraint_allows_hashtags_when_author_uses_them():
    p = _profile_with(hashtag_rate=0.20, platform=Platform.TWITTER)
    c = constraint_for(p)
    assert isinstance(c, TwitterConstraint)
    assert c.allow_hashtags is True
    assert c.require_lowercase is False


def test_twitter_constraint_blocks_hashtags_when_author_never_uses():
    p = _profile_with(hashtag_rate=0.01, platform=Platform.TWITTER)
    c = constraint_for(p)
    assert isinstance(c, TwitterConstraint)
    assert c.allow_hashtags is False


def test_linkedin_constraint_for_linkedin_profile():
    p = _profile_with(hashtag_rate=0.0, platform=Platform.LINKEDIN)
    c = constraint_for(p)
    assert isinstance(c, LinkedInConstraint)
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/platforms/test_author_derived.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `src/writer_profile/platforms/author_derived.py`**

```python
from __future__ import annotations

from writer_profile.corpus.models import Platform
from writer_profile.platforms.base import Constraint
from writer_profile.platforms.linkedin import LinkedInConstraint
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.voice.profile import VoiceProfile

HASHTAG_TOLERANCE_THRESHOLD = 0.05  # if author uses hashtags in >=5% of posts, allow them


def constraint_for(profile: VoiceProfile) -> Constraint:
    if profile.platform is Platform.TWITTER:
        allow_hashtags = profile.stats.hashtag_rate >= HASHTAG_TOLERANCE_THRESHOLD
        avg_tags = profile.stats.avg_hashtags_per_post
        max_hashtags = max(1, int(round(avg_tags * 2))) if allow_hashtags else 0
        return TwitterConstraint(
            max_chars=280,
            allow_hashtags=allow_hashtags,
            require_lowercase=False,
            max_hashtags=max_hashtags if allow_hashtags else 3,
            max_urls=2,
        )
    if profile.platform is Platform.LINKEDIN:
        return LinkedInConstraint(max_chars=3000, max_words_per_nonempty_line=12)
    raise ValueError(f"no constraint mapping for platform {profile.platform}")
```

- [ ] **Step 4: Run test — expect pass**

Run: `uv run pytest tests/platforms/test_author_derived.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(platforms): derive per-author constraint from voice profile stats"
```

---

## Task 9: Seed `data/hooks.jsonl` + `HookLibrary`

**Files:**
- Create: `data/hooks.jsonl`
- Create: `src/writer_profile/virality/__init__.py` (empty)
- Create: `src/writer_profile/virality/hooks.py`
- Create: `tests/virality/__init__.py` (empty)
- Create: `tests/virality/test_hooks.py`

- [ ] **Step 1: Create seed hooks file**

Write `data/hooks.jsonl` (40 entries, one per line — representative, platform-tagged). Full content:

```jsonl
{"id": "h001", "platform": "twitter", "pattern_type": "hot_take", "template": "Unpopular opinion: {claim}."}
{"id": "h002", "platform": "twitter", "pattern_type": "hot_take", "template": "{claim}. And I'll die on this hill."}
{"id": "h003", "platform": "twitter", "pattern_type": "contrarian", "template": "Everyone says {consensus}. They're wrong."}
{"id": "h004", "platform": "twitter", "pattern_type": "contrarian", "template": "{conventional_wisdom} is a myth. Here's why:"}
{"id": "h005", "platform": "twitter", "pattern_type": "data_point", "template": "{number} says {claim}."}
{"id": "h006", "platform": "twitter", "pattern_type": "data_point", "template": "We ran the numbers. {surprising_finding}."}
{"id": "h007", "platform": "twitter", "pattern_type": "personal_story", "template": "{year} ago I {action}. Today {outcome}."}
{"id": "h008", "platform": "twitter", "pattern_type": "personal_story", "template": "A lesson I learned the hard way: {lesson}."}
{"id": "h009", "platform": "twitter", "pattern_type": "thread_opener", "template": "{topic}. A thread 🧵"}
{"id": "h010", "platform": "twitter", "pattern_type": "thread_opener", "template": "How we {achievement} in {timeframe}. 1/"}
{"id": "h011", "platform": "twitter", "pattern_type": "question", "template": "Why does {observation}? Asking for a friend."}
{"id": "h012", "platform": "twitter", "pattern_type": "question", "template": "Genuine question: {question}"}
{"id": "h013", "platform": "twitter", "pattern_type": "observation", "template": "{observation}. That's it. That's the tweet."}
{"id": "h014", "platform": "twitter", "pattern_type": "observation", "template": "Funny how {observation}."}
{"id": "h015", "platform": "twitter", "pattern_type": "announcement", "template": "Shipping {thing} today."}
{"id": "h016", "platform": "twitter", "pattern_type": "announcement", "template": "Today we're launching {thing}. Here's the idea:"}
{"id": "h017", "platform": "twitter", "pattern_type": "reframing", "template": "{thing} isn't about {common_framing}. It's about {real_framing}."}
{"id": "h018", "platform": "twitter", "pattern_type": "reframing", "template": "Stop thinking of {X} as {Y}. Start thinking of it as {Z}."}
{"id": "h019", "platform": "twitter", "pattern_type": "list", "template": "{number} things I wish I knew about {topic}:"}
{"id": "h020", "platform": "twitter", "pattern_type": "list", "template": "Top {number} mistakes people make with {topic}:"}
{"id": "h021", "platform": "linkedin", "pattern_type": "personal_story", "template": "{timeframe} ago, I {setback}.\n\nToday, {outcome}.\n\nHere's what I learned."}
{"id": "h022", "platform": "linkedin", "pattern_type": "personal_story", "template": "I used to believe {old_belief}.\n\nThen {event} happened.\n\nEverything changed."}
{"id": "h023", "platform": "linkedin", "pattern_type": "lesson", "template": "The hardest lesson of my career: {lesson}."}
{"id": "h024", "platform": "linkedin", "pattern_type": "lesson", "template": "Here's what {year} years of {experience} taught me: {lesson}"}
{"id": "h025", "platform": "linkedin", "pattern_type": "contrarian", "template": "Everyone is talking about {trend}.\n\nFew are talking about {counter_trend}."}
{"id": "h026", "platform": "linkedin", "pattern_type": "contrarian", "template": "Hot take: {claim}.\n\nHere's why I think so."}
{"id": "h027", "platform": "linkedin", "pattern_type": "announcement", "template": "Big news: {announcement}."}
{"id": "h028", "platform": "linkedin", "pattern_type": "announcement", "template": "I'm thrilled to share: {announcement}."}
{"id": "h029", "platform": "linkedin", "pattern_type": "gratitude", "template": "A huge thank you to {people}."}
{"id": "h030", "platform": "linkedin", "pattern_type": "gratitude", "template": "Grateful for {people_or_event}."}
{"id": "h031", "platform": "linkedin", "pattern_type": "data_point", "template": "{statistic}.\n\nLet that sink in."}
{"id": "h032", "platform": "linkedin", "pattern_type": "data_point", "template": "By the numbers: {stats}."}
{"id": "h033", "platform": "linkedin", "pattern_type": "question_open", "template": "What if {provocative_question}?"}
{"id": "h034", "platform": "linkedin", "pattern_type": "question_open", "template": "Why is {observation} so common?\n\nI think it's because {explanation}."}
{"id": "h035", "platform": "linkedin", "pattern_type": "industry_commentary", "template": "The {industry} industry has a problem.\n\n{problem_statement}"}
{"id": "h036", "platform": "linkedin", "pattern_type": "industry_commentary", "template": "{industry} is at an inflection point.\n\nHere's what I'm seeing:"}
{"id": "h037", "platform": "linkedin", "pattern_type": "reflection", "template": "On {anniversary}: {reflection}."}
{"id": "h038", "platform": "linkedin", "pattern_type": "reflection", "template": "Spent the weekend thinking about {topic}.\n\nHere's what I came away with:"}
{"id": "h039", "platform": "linkedin", "pattern_type": "framework", "template": "My {adjective} framework for {problem}:\n\n1. {step1}\n2. {step2}\n3. {step3}"}
{"id": "h040", "platform": "linkedin", "pattern_type": "framework", "template": "{N} questions I ask every time I {activity}:"}
```

- [ ] **Step 2: Write failing test**

Create `tests/virality/__init__.py` (empty).

Create `tests/virality/test_hooks.py`:

```python
from pathlib import Path

from writer_profile.corpus.models import Platform
from writer_profile.virality.hooks import HookLibrary


def test_load_and_filter_by_platform():
    lib = HookLibrary.load(Path("data/hooks.jsonl"))
    assert len(lib.all()) >= 40
    x_hooks = lib.for_platform(Platform.TWITTER)
    li_hooks = lib.for_platform(Platform.LINKEDIN)
    assert len(x_hooks) > 0
    assert len(li_hooks) > 0
    assert all(h.platform is Platform.TWITTER for h in x_hooks)
    assert all(h.platform is Platform.LINKEDIN for h in li_hooks)


def test_suggest_returns_mix_of_pattern_types():
    lib = HookLibrary.load(Path("data/hooks.jsonl"))
    suggestions = lib.suggest(platform=Platform.TWITTER, k=5)
    assert len(suggestions) == 5
    # should span at least 3 distinct pattern types
    types = {h.pattern_type for h in suggestions}
    assert len(types) >= 3


def test_render_injection_block_respects_strength():
    lib = HookLibrary.load(Path("data/hooks.jsonl"))
    suggestions = lib.suggest(platform=Platform.TWITTER, k=3, seed=42)

    subtle = lib.render_injection(suggestions, virality_strength=0.15)
    aggressive = lib.render_injection(suggestions, virality_strength=1.0)
    off = lib.render_injection(suggestions, virality_strength=0.0)

    assert "optional" in subtle.lower() or "may" in subtle.lower()
    assert "prefer" in aggressive.lower() or "adopt" in aggressive.lower()
    assert off.strip() == "" or "ignore" in off.lower()
```

- [ ] **Step 3: Run test — expect fail**

Run: `uv run pytest tests/virality/test_hooks.py -q`
Expected: FAIL — module missing.

- [ ] **Step 4: Implement `src/writer_profile/virality/hooks.py`**

Create `src/writer_profile/virality/__init__.py` as empty file.

Create `src/writer_profile/virality/hooks.py`:

```python
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

        # fill remainder from pool if diversity ran out
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

        return f"STRUCTURAL PATTERN SUGGESTIONS (strength={virality_strength:.2f}):\n{bullet_list}\n\n{tone}"
```

- [ ] **Step 5: Run test — expect pass**

Run: `uv run pytest tests/virality/test_hooks.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(virality): HookLibrary with 40 seed patterns and dialable injection"
```

---

## Task 10: Generator prompt injection (profile + hooks + idea)

**Files:**
- Modify: `src/writer_profile/generation/prompts.py`
- Modify: `src/writer_profile/corpus/models.py` (add `Idea` model)
- Test: `tests/generation/test_prompts.py`

- [ ] **Step 1: Add `Idea` model**

Append to `src/writer_profile/corpus/models.py`:

```python
class Idea(BaseModel):
    topic: str = Field(min_length=1)
    angle: str = ""          # free-form narrative direction
    constraints: list[str] = Field(default_factory=list)  # e.g. ["mention Tabular acquisition"]

    def render(self) -> str:
        parts = [f"TOPIC: {self.topic}"]
        if self.angle:
            parts.append(f"ANGLE: {self.angle}")
        if self.constraints:
            parts.append("MUST INCLUDE:\n" + "\n".join(f"- {c}" for c in self.constraints))
        return "\n\n".join(parts)
```

- [ ] **Step 2: Write failing test**

Append to `tests/generation/test_prompts.py`:

```python
def test_build_generator_prompt_injects_profile_and_hooks_and_idea():
    from writer_profile.corpus.models import Idea, Platform
    from writer_profile.generation.prompts import build_generator_prompt
    from writer_profile.platforms.twitter import TwitterConstraint
    from writer_profile.virality.hooks import Hook
    from writer_profile.voice.profile import (
        LexicalProfile, RhetoricalProfile, StructuralProfile, TonalProfile, VoiceProfile,
    )
    from writer_profile.voice.stats import VoiceStats

    profile = VoiceProfile(
        author="ali_ghodsi",
        platform=Platform.TWITTER,
        stats=VoiceStats(
            post_count=50, avg_words_per_sentence=10.0,
            sentence_length_p25_p50_p75=(5.0, 9.0, 16.0),
            length_chars_p25_p50_p75=(80.0, 150.0, 230.0),
            emoji_rate=0.0, hashtag_rate=0.05, avg_hashtags_per_post=0.2,
            url_rate=0.1, question_rate=0.1, mention_rate=0.2,
            line_break_rate=0.0,
            top_openers=["open source is", "today we ship"],
            top_closers=["let's go", "always has"],
            top_bigrams=[("open source", 15)], top_trigrams=[],
            thread_rate=0.05,
        ),
        lexical=LexicalProfile(recurring_phrases=["open source"],
                               word_preferences={"team": 1},
                               jargon_level="medium", notes="conviction language"),
        structural=StructuralProfile(typical_opener_patterns=["declarative one-liner"],
                                     typical_closer_patterns=["brief forward-looking line"],
                                     paragraph_shape="1-3 sentences",
                                     list_usage="rarely", question_usage="rarely"),
        rhetorical=RhetoricalProfile(uses_analogies=False, uses_personal_anecdotes=True,
                                     uses_data_points=True, attribution_style="credits team",
                                     name_drop_rate="moderate"),
        tonal=TonalProfile(warmth="warm", humor="dry", conviction="high",
                           disclosure="moderate", vulnerability="rare"),
        examples=["open source wins. it always has.", "today we ship spark 4."],
    )

    idea = Idea(
        topic="databricks acquires tabular",
        angle="validates open-source approach to data",
        constraints=["mention spark + iceberg teams"],
    )

    hooks = [Hook(id="h1", platform=Platform.TWITTER, pattern_type="hot_take",
                  template="Unpopular opinion: {claim}.")]

    system, user = build_generator_prompt(
        profile=profile,
        idea=idea,
        exemplars=[],
        constraint=TwitterConstraint(),
        hooks=hooks,
        virality_strength=0.15,
    )

    assert "ali_ghodsi" in system
    assert "open source" in system
    assert "conviction" in system.lower()
    assert "Unpopular opinion" in system
    assert "mention spark + iceberg teams" in user
    assert "databricks acquires tabular" in user
```

- [ ] **Step 3: Run test — expect fail**

Run: `uv run pytest tests/generation/test_prompts.py::test_build_generator_prompt_injects_profile_and_hooks_and_idea -q`
Expected: FAIL — signature mismatch.

- [ ] **Step 4: Rewrite `src/writer_profile/generation/prompts.py`**

```python
from __future__ import annotations

from writer_profile.corpus.models import Idea, Platform
from writer_profile.platforms.base import Constraint
from writer_profile.retrieval.store import ExemplarHit
from writer_profile.virality.hooks import Hook, HookLibrary
from writer_profile.voice.profile import VoiceProfile


def _format_exemplars(exemplars: list[ExemplarHit]) -> str:
    if not exemplars:
        return "(no retrieved exemplars — rely on profile + canonical examples)"
    blocks = []
    for i, h in enumerate(exemplars, start=1):
        blocks.append(
            f"EXAMPLE {i} (tone={h.metadata.tone.value}, "
            f"length={h.metadata.length_bucket}):\n{h.post.text}"
        )
    return "\n\n".join(blocks)


def _format_profile(profile: VoiceProfile) -> str:
    s = profile.stats
    lex = profile.lexical
    struct = profile.structural
    rhet = profile.rhetorical
    tone = profile.tonal

    return (
        f"AUTHOR: {profile.author} on {profile.platform.value}\n\n"
        "STATISTICAL FINGERPRINT:\n"
        f"- sentence length: avg {s.avg_words_per_sentence:.1f} words "
        f"(p25/p50/p75 = {s.sentence_length_p25_p50_p75[0]:.0f}/"
        f"{s.sentence_length_p25_p50_p75[1]:.0f}/"
        f"{s.sentence_length_p25_p50_p75[2]:.0f})\n"
        f"- post length chars p25/p50/p75: {s.length_chars_p25_p50_p75[0]:.0f}/"
        f"{s.length_chars_p25_p50_p75[1]:.0f}/"
        f"{s.length_chars_p25_p50_p75[2]:.0f}\n"
        f"- emoji usage: {s.emoji_rate*100:.0f}% of posts\n"
        f"- hashtag usage: {s.hashtag_rate*100:.0f}% of posts "
        f"(avg {s.avg_hashtags_per_post:.2f} per post)\n"
        f"- asks questions: {s.question_rate*100:.0f}% of posts\n"
        f"- mentions others: {s.mention_rate*100:.0f}% of posts\n"
        f"- typical openers (lowercased): {', '.join(s.top_openers[:5])}\n"
        f"- typical closers (lowercased): {', '.join(s.top_closers[:5])}\n\n"
        "LEXICAL:\n"
        f"- recurring phrases: {', '.join(lex.recurring_phrases[:8])}\n"
        f"- jargon level: {lex.jargon_level}\n"
        f"- notes: {lex.notes}\n\n"
        "STRUCTURAL:\n"
        f"- openers: {', '.join(struct.typical_opener_patterns)}\n"
        f"- closers: {', '.join(struct.typical_closer_patterns)}\n"
        f"- paragraph shape: {struct.paragraph_shape}\n"
        f"- list usage: {struct.list_usage}\n"
        f"- question usage: {struct.question_usage}\n\n"
        "RHETORICAL:\n"
        f"- analogies: {rhet.uses_analogies}, anecdotes: {rhet.uses_personal_anecdotes}, "
        f"data points: {rhet.uses_data_points}\n"
        f"- attribution: {rhet.attribution_style}\n"
        f"- name drops: {rhet.name_drop_rate}\n\n"
        "TONAL:\n"
        f"- warmth: {tone.warmth} / humor: {tone.humor} / "
        f"conviction: {tone.conviction} / disclosure: {tone.disclosure} / "
        f"vulnerability: {tone.vulnerability}\n\n"
        "CANONICAL EXAMPLES (most representative of this voice):\n"
        + "\n\n".join(f"- {e}" for e in profile.examples[:5])
    )


def build_generator_prompt(
    *,
    profile: VoiceProfile,
    idea: Idea,
    exemplars: list[ExemplarHit],
    constraint: Constraint,
    hooks: list[Hook],
    virality_strength: float = 0.15,
) -> tuple[str, str]:
    hook_block = HookLibrary.render_injection(hooks, virality_strength=virality_strength)

    system = (
        f"You write {profile.platform.value} posts in the EXACT voice of {profile.author}. "
        "Mimic cadence, sentence length, punctuation, and word choice. "
        "Do not invent a new voice. Do not sound like a corporate announcement.\n\n"
        f"{_format_profile(profile)}\n\n"
        f"RETRIEVED AUTHOR EXAMPLES (study these):\n{_format_exemplars(exemplars)}\n\n"
        f"PLATFORM RULES ({profile.platform.value}):\n{constraint.describe_rules()}\n\n"
        f"{hook_block}\n\n"
        "Output ONLY the post text. No preamble, no quotes, no explanation."
    )
    user = f"Write one post based on this brief.\n\n{idea.render()}"
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
        "\n".join(f"- {i}" for i in validator_issues) if validator_issues else "(validator passed)"
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


def build_revoice_prompt(
    *,
    profile: VoiceProfile,
    edited_draft: str,
    constraint: Constraint,
) -> tuple[str, str]:
    system = (
        f"A human editor has structured a {profile.platform.value} post for {profile.author}. "
        "Your ONLY job is to refine the voice — word choice, cadence, phrasing — to match this "
        "author's profile. You MUST preserve:\n"
        "- paragraph count and relative order\n"
        "- key noun phrases / entities the editor included\n"
        "- the editor's structural intent (list vs prose, question vs statement, hook location)\n\n"
        "You MUST NOT:\n"
        "- reorder paragraphs\n"
        "- add or remove points\n"
        "- change the narrative arc\n\n"
        f"{_format_profile(profile)}\n\n"
        f"PLATFORM RULES ({profile.platform.value}):\n{constraint.describe_rules()}\n\n"
        "Output ONLY the revoiced post. No preamble."
    )
    user = f"EDITED DRAFT TO REVOICE:\n{edited_draft}\n\nRevoiced post:"
    return system, user
```

- [ ] **Step 5: Update existing test fixture that uses old signature**

Edit `tests/generation/test_prompts.py` — remove or update any existing `test_build_generator_prompt_*` tests that used the old signature. Keep the new test added in Step 2. Delete any old test that exercises the `topic`-only signature.

Run `uv run pytest tests/generation/test_prompts.py -q` to see what breaks; remove broken tests (they exercised the old API) rather than patch them. This is a deliberate API break.

- [ ] **Step 6: Run test — expect pass**

Run: `uv run pytest tests/generation/test_prompts.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(generation): generator prompt injects voice profile, hooks, and idea/angle"
```

---

## Task 11: Generator + pipeline signature overhaul

**Files:**
- Modify: `src/writer_profile/generation/generator.py`
- Modify: `src/writer_profile/pipeline.py`
- Test: `tests/generation/test_generator.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing test for new generator signature**

Replace contents of `tests/generation/test_generator.py`:

```python
from datetime import datetime, UTC

from writer_profile.corpus.models import Idea, Platform
from writer_profile.generation.generator import generate_draft
from writer_profile.llm import StubLLMClient
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.virality.hooks import Hook
from writer_profile.voice.profile import (
    LexicalProfile, RhetoricalProfile, StructuralProfile, TonalProfile, VoiceProfile,
)
from writer_profile.voice.stats import VoiceStats


def _profile() -> VoiceProfile:
    return VoiceProfile(
        author="ali", platform=Platform.TWITTER,
        stats=VoiceStats(
            post_count=20, avg_words_per_sentence=10.0,
            sentence_length_p25_p50_p75=(5.0, 9.0, 14.0),
            length_chars_p25_p50_p75=(70.0, 150.0, 220.0),
            emoji_rate=0.0, hashtag_rate=0.0, avg_hashtags_per_post=0.0,
            url_rate=0.1, question_rate=0.1, mention_rate=0.2,
            line_break_rate=0.0, top_openers=[], top_closers=[],
            top_bigrams=[], top_trigrams=[], thread_rate=0.0,
        ),
        lexical=LexicalProfile(recurring_phrases=[], word_preferences={},
                               jargon_level="low", notes=""),
        structural=StructuralProfile(typical_opener_patterns=[], typical_closer_patterns=[],
                                     paragraph_shape="", list_usage="", question_usage=""),
        rhetorical=RhetoricalProfile(uses_analogies=False, uses_personal_anecdotes=False,
                                     uses_data_points=False, attribution_style="",
                                     name_drop_rate="rare"),
        tonal=TonalProfile(warmth="neutral", humor="none", conviction="medium",
                           disclosure="rare", vulnerability="rare"),
        examples=["open source wins"],
    )


def test_generate_draft_uses_profile_and_idea():
    llm = StubLLMClient(responses=["open source just acquired iceberg. welcome to the family."])
    out = generate_draft(
        profile=_profile(),
        idea=Idea(topic="databricks acquires tabular", angle="open source validation"),
        exemplars=[],
        constraint=TwitterConstraint(),
        hooks=[],
        llm=llm,
        model="claude-sonnet-4-6",
        virality_strength=0.0,
    )
    assert "open source" in out
    assert len(llm.calls) == 1


def test_generate_draft_strips_wrapping_quotes():
    llm = StubLLMClient(responses=['"quoted draft"'])
    out = generate_draft(
        profile=_profile(),
        idea=Idea(topic="x"),
        exemplars=[],
        constraint=TwitterConstraint(),
        hooks=[],
        llm=llm,
        model="claude-sonnet-4-6",
    )
    assert out == "quoted draft"
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/generation/test_generator.py -q`
Expected: FAIL — signature mismatch.

- [ ] **Step 3: Rewrite `src/writer_profile/generation/generator.py`**

```python
from __future__ import annotations

from writer_profile.corpus.models import Idea
from writer_profile.generation.prompts import build_generator_prompt
from writer_profile.llm import LLMClient, LLMMessage
from writer_profile.platforms.base import Constraint
from writer_profile.retrieval.store import ExemplarHit
from writer_profile.virality.hooks import Hook
from writer_profile.voice.profile import VoiceProfile


def unwrap(raw: str) -> str:
    text = raw.strip()
    if len(text) >= 2 and text[0] in {'"', "'"} and text[-1] == text[0]:
        text = text[1:-1].strip()
    return text


def generate_draft(
    *,
    profile: VoiceProfile,
    idea: Idea,
    exemplars: list[ExemplarHit],
    constraint: Constraint,
    hooks: list[Hook],
    llm: LLMClient,
    model: str,
    virality_strength: float = 0.15,
    temperature: float = 0.8,
) -> str:
    system, user = build_generator_prompt(
        profile=profile,
        idea=idea,
        exemplars=exemplars,
        constraint=constraint,
        hooks=hooks,
        virality_strength=virality_strength,
    )
    raw = llm.complete(
        model=model,
        system=system,
        messages=[LLMMessage(role="user", content=user)],
        max_tokens=1024,
        temperature=temperature,
    )
    return unwrap(raw)
```

- [ ] **Step 4: Overhaul `src/writer_profile/pipeline.py`**

Replace the file:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from writer_profile.corpus.models import Idea, Platform
from writer_profile.generation.generator import generate_draft
from writer_profile.generation.refine import RefineStep, refine
from writer_profile.llm import LLMClient
from writer_profile.platforms.author_derived import constraint_for
from writer_profile.retrieval.store import ExemplarHit, ExemplarStore
from writer_profile.virality.hooks import HookLibrary
from writer_profile.voice.profile import VoiceProfile
from writer_profile.voice.store import VoiceProfileStore


@dataclass
class PostDraft:
    text: str
    author: str
    platform: Platform
    idea: Idea
    exemplars_used: list[ExemplarHit]
    refine_history: list[RefineStep]
    validation_ok: bool
    validation_issues: list[str] = field(default_factory=list)


class GenerationPipeline:
    def __init__(
        self,
        *,
        store: ExemplarStore,
        profiles: VoiceProfileStore,
        hooks: HookLibrary,
        llm: LLMClient,
        writing_model: str,
        retrieval_k: int = 5,
        refine_max_iterations: int = 2,
        hook_suggestion_k: int = 5,
    ) -> None:
        self._store = store
        self._profiles = profiles
        self._hooks = hooks
        self._llm = llm
        self._writing_model = writing_model
        self._retrieval_k = retrieval_k
        self._refine_max_iterations = refine_max_iterations
        self._hook_k = hook_suggestion_k

    def _profile(self, author: str, platform: Platform) -> VoiceProfile:
        return self._profiles.load(author=author, platform=platform)

    def generate(
        self,
        *,
        author: str,
        platform: Platform,
        idea: Idea,
        virality_strength: float = 0.15,
        hook_seed: int | None = None,
    ) -> PostDraft:
        profile = self._profile(author, platform)
        constraint = constraint_for(profile)
        exemplars = self._store.query(
            text=f"{idea.topic}\n{idea.angle}".strip(),
            platform=platform,
            author=author,
            k=self._retrieval_k,
        )
        hook_suggestions = self._hooks.suggest(platform=platform, k=self._hook_k, seed=hook_seed)

        initial = generate_draft(
            profile=profile,
            idea=idea,
            exemplars=exemplars,
            constraint=constraint,
            hooks=hook_suggestions,
            llm=self._llm,
            model=self._writing_model,
            virality_strength=virality_strength,
        )

        refined = refine(
            draft=initial,
            platform=platform,
            constraint=constraint,
            llm=self._llm,
            model=self._writing_model,
            max_iterations=self._refine_max_iterations,
        )

        final = constraint.validate(refined.final_draft)
        return PostDraft(
            text=refined.final_draft,
            author=author,
            platform=platform,
            idea=idea,
            exemplars_used=exemplars,
            refine_history=refined.history,
            validation_ok=bool(final),
            validation_issues=list(final.issues),
        )
```

- [ ] **Step 5: Update `tests/test_pipeline.py`**

Replace the file:

```python
from datetime import datetime, UTC

import pytest

from writer_profile.corpus.models import AnnotatedPost, Idea, Platform, Post, PostMetadata, Tone
from writer_profile.llm import StubLLMClient
from writer_profile.pipeline import GenerationPipeline, PostDraft
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore
from writer_profile.virality.hooks import HookLibrary
from writer_profile.voice.profile import (
    LexicalProfile, RhetoricalProfile, StructuralProfile, TonalProfile, VoiceProfile,
)
from writer_profile.voice.stats import VoiceStats
from writer_profile.voice.store import VoiceProfileStore


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    return Embedder(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _ann(pid: str, text: str, author: str = "ali") -> AnnotatedPost:
    return AnnotatedPost(
        post=Post(
            id=pid, author=author, platform=Platform.TWITTER,
            text=text, created_at=datetime(2025, 1, 1, tzinfo=UTC),
        ),
        metadata=PostMetadata(
            topics=["ai"], tone=Tone.OBSERVATIONAL, length_bucket="short", language="en",
        ),
    )


def _profile(author: str = "ali", platform: Platform = Platform.TWITTER) -> VoiceProfile:
    return VoiceProfile(
        author=author, platform=platform,
        stats=VoiceStats(
            post_count=10, avg_words_per_sentence=10.0,
            sentence_length_p25_p50_p75=(5.0, 9.0, 14.0),
            length_chars_p25_p50_p75=(70.0, 150.0, 220.0),
            emoji_rate=0.0, hashtag_rate=0.0, avg_hashtags_per_post=0.0,
            url_rate=0.1, question_rate=0.1, mention_rate=0.2,
            line_break_rate=0.0, top_openers=[], top_closers=[],
            top_bigrams=[], top_trigrams=[], thread_rate=0.0,
        ),
        lexical=LexicalProfile(recurring_phrases=[], word_preferences={},
                               jargon_level="low", notes=""),
        structural=StructuralProfile(typical_opener_patterns=[], typical_closer_patterns=[],
                                     paragraph_shape="", list_usage="", question_usage=""),
        rhetorical=RhetoricalProfile(uses_analogies=False, uses_personal_anecdotes=False,
                                     uses_data_points=False, attribution_style="",
                                     name_drop_rate="rare"),
        tonal=TonalProfile(warmth="neutral", humor="none", conviction="medium",
                           disclosure="rare", vulnerability="rare"),
        examples=["open source wins"],
    )


def test_pipeline_end_to_end_with_stub(tmp_path, embedder):
    from pathlib import Path

    store = ExemplarStore(path=str(tmp_path / "c"), embedder=embedder, collection="pipe")
    store.add_many([_ann("a", "ai evaluation is the new bottleneck")])

    profiles = VoiceProfileStore(root=tmp_path / "profiles")
    profiles.save(_profile())

    hooks = HookLibrary.load(Path("data/hooks.jsonl"))

    llm = StubLLMClient(
        responses=[
            "the bottleneck in ai agents moved from generation to evaluation",
            "OK",
        ]
    )
    pipe = GenerationPipeline(
        store=store,
        profiles=profiles,
        hooks=hooks,
        llm=llm,
        writing_model="claude-sonnet-4-6",
        retrieval_k=3,
        refine_max_iterations=2,
    )
    out = pipe.generate(
        author="ali",
        platform=Platform.TWITTER,
        idea=Idea(topic="ai evaluation bottlenecks", angle="generation is easy, eval is hard"),
    )
    assert isinstance(out, PostDraft)
    assert out.platform is Platform.TWITTER
    assert out.author == "ali"
    assert "evaluation" in out.text
    assert out.validation_ok is True
    assert len(out.exemplars_used) == 1


def test_pipeline_missing_profile_raises(tmp_path, embedder):
    from pathlib import Path

    store = ExemplarStore(path=str(tmp_path / "c2"), embedder=embedder, collection="pipe2")
    profiles = VoiceProfileStore(root=tmp_path / "profiles")
    hooks = HookLibrary.load(Path("data/hooks.jsonl"))
    llm = StubLLMClient(responses=[])
    pipe = GenerationPipeline(
        store=store, profiles=profiles, hooks=hooks, llm=llm,
        writing_model="claude-sonnet-4-6",
    )
    with pytest.raises(FileNotFoundError):
        pipe.generate(
            author="nobody", platform=Platform.TWITTER,
            idea=Idea(topic="x"),
        )
```

- [ ] **Step 6: Run full suite — expect pass**

Run: `uv run pytest -q`
Expected: green. (Some legacy CLI tests may break — address in Task 18.)

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(pipeline): accept author + idea + virality_strength; load profile from store"
```

---

## Task 12: X thread splitter + validator

**Files:**
- Create: `src/writer_profile/generation/thread.py`
- Create: `tests/generation/test_thread.py`

A thread is a sequence of 2–5 tweets, each ≤ 280 chars. Splitting strategy: the LLM emits the thread with explicit `\n\n---\n\n` separators when prompted for a thread; we split on that separator, strip enumeration if present, validate each.

- [ ] **Step 1: Write failing test**

Create `tests/generation/test_thread.py`:

```python
from writer_profile.generation.thread import Thread, split_thread, validate_thread
from writer_profile.platforms.twitter import TwitterConstraint


def test_split_thread_basic():
    raw = (
        "1/ the bottleneck in ai moved from generation to evaluation.\n\n---\n\n"
        "2/ eval is hard because you can't unit-test taste.\n\n---\n\n"
        "3/ we're building eval tooling first, model work second."
    )
    thread = split_thread(raw)
    assert isinstance(thread, Thread)
    assert len(thread.posts) == 3
    assert thread.posts[0].startswith("the bottleneck")
    assert not thread.posts[1].startswith("2/")


def test_split_thread_single_post_returns_single_element_thread():
    raw = "just a single thought no threading"
    thread = split_thread(raw)
    assert len(thread.posts) == 1


def test_validate_thread_reports_per_post_violations():
    c = TwitterConstraint(max_chars=20)
    thread = Thread(posts=["short one", "this one is way way way too long to fit"])
    result = validate_thread(thread, c)
    assert not bool(result)
    assert any("post 2" in i for i in result.issues)


def test_validate_thread_caps_at_5_posts():
    c = TwitterConstraint()
    thread = Thread(posts=["a", "b", "c", "d", "e", "f"])
    result = validate_thread(thread, c, max_posts=5)
    assert not bool(result)
    assert any("thread exceeds 5 posts" in i for i in result.issues)
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/generation/test_thread.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `src/writer_profile/generation/thread.py`**

```python
from __future__ import annotations

import re
from dataclasses import dataclass

from writer_profile.platforms.base import Constraint, ValidationResult

_SEPARATOR = re.compile(r"\n\s*---+\s*\n")
_ENUMERATION = re.compile(r"^\s*(?:\d+[./)]\s*|🧵\s*)")


@dataclass(frozen=True)
class Thread:
    posts: list[str]


def split_thread(raw: str) -> Thread:
    parts = _SEPARATOR.split(raw.strip())
    cleaned = [_ENUMERATION.sub("", p).strip() for p in parts if p.strip()]
    return Thread(posts=cleaned)


def validate_thread(
    thread: Thread, constraint: Constraint, *, max_posts: int = 5
) -> ValidationResult:
    issues: list[str] = []
    if len(thread.posts) > max_posts:
        issues.append(f"thread exceeds {max_posts} posts (got {len(thread.posts)})")

    for idx, p in enumerate(thread.posts[:max_posts], start=1):
        per_post = constraint.validate(p)
        if not per_post:
            issues.extend(f"post {idx}: {i}" for i in per_post.issues)

    return ValidationResult.ok() if not issues else ValidationResult.fail(issues)
```

- [ ] **Step 4: Run test — expect pass**

Run: `uv run pytest tests/generation/test_thread.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(generation): Thread splitter + per-post validator"
```

---

## Task 13: Re-voice module (reuses refine internals)

**Files:**
- Create: `src/writer_profile/generation/revoice.py`
- Create: `tests/generation/test_revoice.py`

- [ ] **Step 1: Write failing test**

Create `tests/generation/test_revoice.py`:

```python
from datetime import datetime, UTC

from writer_profile.corpus.models import Platform
from writer_profile.generation.revoice import revoice
from writer_profile.llm import StubLLMClient
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.voice.profile import (
    LexicalProfile, RhetoricalProfile, StructuralProfile, TonalProfile, VoiceProfile,
)
from writer_profile.voice.stats import VoiceStats


def _profile() -> VoiceProfile:
    return VoiceProfile(
        author="ali", platform=Platform.TWITTER,
        stats=VoiceStats(
            post_count=10, avg_words_per_sentence=10.0,
            sentence_length_p25_p50_p75=(5.0, 9.0, 14.0),
            length_chars_p25_p50_p75=(70.0, 150.0, 220.0),
            emoji_rate=0.0, hashtag_rate=0.0, avg_hashtags_per_post=0.0,
            url_rate=0.1, question_rate=0.1, mention_rate=0.2,
            line_break_rate=0.0, top_openers=[], top_closers=[],
            top_bigrams=[], top_trigrams=[], thread_rate=0.0,
        ),
        lexical=LexicalProfile(recurring_phrases=[], word_preferences={},
                               jargon_level="low", notes=""),
        structural=StructuralProfile(typical_opener_patterns=[], typical_closer_patterns=[],
                                     paragraph_shape="", list_usage="", question_usage=""),
        rhetorical=RhetoricalProfile(uses_analogies=False, uses_personal_anecdotes=False,
                                     uses_data_points=False, attribution_style="",
                                     name_drop_rate="rare"),
        tonal=TonalProfile(warmth="neutral", humor="none", conviction="medium",
                           disclosure="rare", vulnerability="rare"),
        examples=["open source wins"],
    )


def test_revoice_produces_refined_output_via_llm():
    edited = (
        "Last week I met the Tabular team in person.\n\n"
        "Brilliant engineers. They built Iceberg from the ground up.\n\n"
        "Today, we're bringing them into the Databricks family."
    )
    llm = StubLLMClient(responses=[
        "Last week I sat down with the Tabular team.\n\n"
        "Brilliant engineers. They built iceberg.\n\n"
        "Today they join databricks. spark + iceberg under one roof. open source wins."
    ])

    out = revoice(
        profile=_profile(),
        edited_draft=edited,
        constraint=TwitterConstraint(max_chars=1000),
        llm=llm,
        model="claude-sonnet-4-6",
    )

    # paragraph count preserved
    assert out.count("\n\n") == edited.count("\n\n")
    assert len(llm.calls) == 1


def test_revoice_strips_wrapping_quotes():
    llm = StubLLMClient(responses=['"revoiced draft"'])
    out = revoice(
        profile=_profile(),
        edited_draft="draft",
        constraint=TwitterConstraint(max_chars=1000),
        llm=llm,
        model="claude-sonnet-4-6",
    )
    assert out == "revoiced draft"
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/generation/test_revoice.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `src/writer_profile/generation/revoice.py`**

```python
from __future__ import annotations

from writer_profile.generation.generator import unwrap
from writer_profile.generation.prompts import build_revoice_prompt
from writer_profile.llm import LLMClient, LLMMessage
from writer_profile.platforms.base import Constraint
from writer_profile.voice.profile import VoiceProfile


def revoice(
    *,
    profile: VoiceProfile,
    edited_draft: str,
    constraint: Constraint,
    llm: LLMClient,
    model: str,
    temperature: float = 0.4,
) -> str:
    system, user = build_revoice_prompt(
        profile=profile, edited_draft=edited_draft, constraint=constraint
    )
    raw = llm.complete(
        model=model,
        system=system,
        messages=[LLMMessage(role="user", content=user)],
        max_tokens=1024,
        temperature=temperature,
    )
    return unwrap(raw)
```

- [ ] **Step 4: Run test — expect pass**

Run: `uv run pytest tests/generation/test_revoice.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(generation): revoice endpoint preserving structure, refining voice"
```

---

## Task 14: Pipeline `revoice` method

**Files:**
- Modify: `src/writer_profile/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_pipeline.py`:

```python
def test_pipeline_revoice_preserves_paragraph_count(tmp_path, embedder):
    from pathlib import Path

    store = ExemplarStore(path=str(tmp_path / "c3"), embedder=embedder, collection="rv")
    profiles = VoiceProfileStore(root=tmp_path / "profiles")
    profiles.save(_profile())
    hooks = HookLibrary.load(Path("data/hooks.jsonl"))

    llm = StubLLMClient(responses=[
        "refined para one\n\nrefined para two\n\nrefined para three",
    ])
    pipe = GenerationPipeline(
        store=store, profiles=profiles, hooks=hooks, llm=llm,
        writing_model="claude-sonnet-4-6",
    )

    edited = "rough para one\n\nrough para two\n\nrough para three"
    out = pipe.revoice(author="ali", platform=Platform.TWITTER, edited_draft=edited)

    assert out.text.count("\n\n") == edited.count("\n\n")
    assert out.author == "ali"
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/test_pipeline.py::test_pipeline_revoice_preserves_paragraph_count -q`
Expected: FAIL — method missing.

- [ ] **Step 3: Add `revoice` method to `GenerationPipeline`**

Edit `src/writer_profile/pipeline.py`, add to the class:

```python
    def revoice(
        self,
        *,
        author: str,
        platform: Platform,
        edited_draft: str,
    ) -> PostDraft:
        from writer_profile.generation.revoice import revoice as revoice_fn

        profile = self._profile(author, platform)
        constraint = constraint_for(profile)

        out = revoice_fn(
            profile=profile,
            edited_draft=edited_draft,
            constraint=constraint,
            llm=self._llm,
            model=self._writing_model,
        )

        final = constraint.validate(out)
        return PostDraft(
            text=out,
            author=author,
            platform=platform,
            idea=Idea(topic="(revoice)", angle=""),
            exemplars_used=[],
            refine_history=[],
            validation_ok=bool(final),
            validation_issues=list(final.issues),
        )
```

- [ ] **Step 4: Run test — expect pass**

Run: `uv run pytest tests/test_pipeline.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(pipeline): revoice method applying voice to edited drafts"
```

---

## Task 15: LLM-as-judge

**Files:**
- Create: `src/writer_profile/eval/__init__.py` (empty)
- Create: `src/writer_profile/eval/judge.py`
- Create: `tests/eval/__init__.py` (empty)
- Create: `tests/eval/test_judge.py`

- [ ] **Step 1: Write failing test**

Create `tests/eval/__init__.py` (empty).

Create `tests/eval/test_judge.py`:

```python
import json
from datetime import datetime, UTC

from writer_profile.corpus.models import Platform, Post
from writer_profile.eval.judge import JudgeScore, score_post
from writer_profile.llm import StubLLMClient


def _ref(text: str) -> Post:
    return Post(
        id=text[:5], author="ali", platform=Platform.TWITTER,
        text=text, created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def test_score_post_returns_structured_score():
    references = [_ref("open source wins"), _ref("spark ships vectorized exec today")]

    judge_json = json.dumps({
        "voice_fidelity": 8,
        "voice_reasoning": "strong cadence match, word choice aligns",
        "naturalness": 9,
        "naturalness_reasoning": "sounds human",
        "ai_tics": [],
    })
    llm = StubLLMClient(responses=[judge_json])

    score = score_post(
        author="ali",
        platform=Platform.TWITTER,
        candidate="open source wins. it always has.",
        references=references,
        llm=llm,
        model="claude-sonnet-4-6",
    )

    assert isinstance(score, JudgeScore)
    assert score.voice_fidelity == 8
    assert score.naturalness == 9
    assert len(score.ai_tics) == 0
    assert len(llm.calls) == 1
    # reference posts must appear in the judge prompt
    assert "open source wins" in llm.calls[0].system


def test_score_post_handles_json_fenced():
    references = [_ref("hi")]
    wrapped = "```json\n" + json.dumps({
        "voice_fidelity": 5, "voice_reasoning": "mediocre",
        "naturalness": 6, "naturalness_reasoning": "ok",
        "ai_tics": ["repetitive 'moreover'"],
    }) + "\n```"
    llm = StubLLMClient(responses=[wrapped])

    score = score_post(
        author="ali", platform=Platform.TWITTER,
        candidate="draft", references=references,
        llm=llm, model="claude-sonnet-4-6",
    )
    assert score.voice_fidelity == 5
    assert "moreover" in score.ai_tics[0]
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/eval/test_judge.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement `src/writer_profile/eval/judge.py`**

Create `src/writer_profile/eval/__init__.py` (empty).

Create `src/writer_profile/eval/judge.py`:

```python
from __future__ import annotations

import json
import re

from pydantic import BaseModel

from writer_profile.corpus.models import Platform, Post
from writer_profile.llm import LLMClient, LLMMessage

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)


class JudgeScore(BaseModel):
    voice_fidelity: int      # 1-10
    voice_reasoning: str
    naturalness: int         # 1-10
    naturalness_reasoning: str
    ai_tics: list[str]


def _strip_fence(raw: str) -> str:
    m = _FENCE_RE.search(raw)
    return m.group(1) if m else raw.strip()


_SYSTEM = """You are an expert judge of voice fidelity for social media posts.

You are given:
- an AUTHOR whose voice we are attempting to reproduce
- REFERENCE posts from that author on {platform}
- ONE CANDIDATE post allegedly in that author's voice

Score two axes on a 1-10 integer scale:
- voice_fidelity: does the candidate sound like the same writer as the references? 10 = indistinguishable, 1 = obviously a different person.
- naturalness: does the candidate read like a real human? 10 = fully natural, 1 = obvious AI output.

Also flag "ai_tics": specific words, phrases, or structural moves in the candidate that read as AI-generated (e.g. "Furthermore,", em-dash overuse, balanced three-part lists, empty intensifiers).

REFERENCE POSTS (author's real {platform} output):
{references_block}

Return ONLY a JSON object:
{{"voice_fidelity": int, "voice_reasoning": str, "naturalness": int, "naturalness_reasoning": str, "ai_tics": [str]}}

No prose. No explanation. Just the JSON."""


def score_post(
    *,
    author: str,
    platform: Platform,
    candidate: str,
    references: list[Post],
    llm: LLMClient,
    model: str,
) -> JudgeScore:
    refs = "\n\n---\n\n".join(p.text for p in references)
    system = _SYSTEM.format(platform=platform.value, references_block=refs)

    raw = llm.complete(
        model=model,
        system=system,
        messages=[LLMMessage(role="user", content=f"CANDIDATE POST by '{author}':\n\n{candidate}")],
        max_tokens=512,
        temperature=0.0,
    )
    data = json.loads(_strip_fence(raw))
    return JudgeScore.model_validate(data)
```

- [ ] **Step 4: Run test — expect pass**

Run: `uv run pytest tests/eval/test_judge.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(eval): LLM-as-judge scoring voice fidelity and naturalness"
```

---

## Task 16: Sample generator for manual scoring

**Files:**
- Create: `src/writer_profile/eval/samples.py`
- Create: `tests/eval/test_samples.py`

Generates N sample posts per (author, platform) across topic archetypes, writes them to disk as a markdown rubric sheet.

- [ ] **Step 1: Write failing test**

Create `tests/eval/test_samples.py`:

```python
from pathlib import Path

from writer_profile.corpus.models import Platform
from writer_profile.eval.samples import ARCHETYPE_IDEAS, write_samples_sheet


def test_archetypes_cover_five_topic_types():
    types = {idea.topic for idea in ARCHETYPE_IDEAS}
    assert len(ARCHETYPE_IDEAS) == 5
    assert len(types) == 5


def test_write_samples_sheet_produces_markdown(tmp_path: Path):
    samples = [
        ("product launch: new feature", "Shipping X today. it's fast."),
        ("acquisition", "welcome to the family, team X."),
    ]
    path = write_samples_sheet(
        root=tmp_path,
        author="ali",
        platform=Platform.TWITTER,
        samples=samples,
    )
    assert path.exists()
    content = path.read_text()
    assert "# ali — twitter" in content
    assert "product launch: new feature" in content
    assert "Shipping X today" in content
    assert "Voice accuracy (1-5):" in content
    assert "Post quality (1-5):" in content
    assert "Naturalness (1-5):" in content
```

- [ ] **Step 2: Run test — expect fail**

Run: `uv run pytest tests/eval/test_samples.py -q`
Expected: FAIL.

- [ ] **Step 3: Implement `src/writer_profile/eval/samples.py`**

```python
from __future__ import annotations

from pathlib import Path

from writer_profile.corpus.models import Idea, Platform

ARCHETYPE_IDEAS: list[Idea] = [
    Idea(
        topic="product launch: new feature",
        angle="a specific capability is shipping today and it solves a long-standing pain",
    ),
    Idea(
        topic="acquisition",
        angle="announcing an acquisition that validates a strategic thesis",
    ),
    Idea(
        topic="earnings / milestone",
        angle="crossing a meaningful number, with context on how we got here",
    ),
    Idea(
        topic="personal reflection",
        angle="a lesson from this week's work, with a generalizable point",
    ),
    Idea(
        topic="industry commentary",
        angle="a provocative take on where the field is heading, based on observation",
    ),
]


def write_samples_sheet(
    *,
    root: str | Path,
    author: str,
    platform: Platform,
    samples: list[tuple[str, str]],
) -> Path:
    """Write a markdown rubric sheet with one section per sample."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{author}__{platform.value}.md"

    lines: list[str] = [f"# {author} — {platform.value}", ""]
    for i, (idea_label, post) in enumerate(samples, start=1):
        lines.append(f"## Sample {i}: {idea_label}")
        lines.append("")
        lines.append("```")
        lines.append(post)
        lines.append("```")
        lines.append("")
        lines.append("- Voice accuracy (1-5): ")
        lines.append("- Post quality (1-5): ")
        lines.append("- Naturalness (1-5): ")
        lines.append("- Notes:")
        lines.append("")

    path.write_text("\n".join(lines))
    return path
```

- [ ] **Step 4: Run test — expect pass**

Run: `uv run pytest tests/eval/test_samples.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(eval): archetype-based sample generator writes markdown rubric sheets"
```

---

## Task 17: CLI — `profile build` / `profile show`

**Files:**
- Modify: `src/writer_profile/cli.py`
- Modify: `src/writer_profile/config.py`

- [ ] **Step 1: Extend `Settings`**

Edit `src/writer_profile/config.py`:

```python
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
    profiles_path: str = "./profiles"
    hooks_path: str = "./data/hooks.jsonl"
    writing_model: str = "claude-sonnet-4-6"
    classifier_model: str = "claude-haiku-4-5-20251001"
    judge_model: str = "claude-sonnet-4-6"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    refine_max_iterations: int = 2
    retrieval_k: int = 5
    hook_suggestion_k: int = 5
```

- [ ] **Step 2: Add `profile` subcommands to CLI**

Edit `src/writer_profile/cli.py` — replace entirely:

```python
from __future__ import annotations

import json
from pathlib import Path

import typer

from writer_profile.config import Settings
from writer_profile.corpus.ingest import ingest_file
from writer_profile.corpus.loader import load_posts_jsonl
from writer_profile.corpus.models import Idea, Platform
from writer_profile.eval.samples import ARCHETYPE_IDEAS, write_samples_sheet
from writer_profile.llm import AnthropicClient
from writer_profile.pipeline import GenerationPipeline
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore
from writer_profile.virality.hooks import HookLibrary
from writer_profile.voice.extractor import build_voice_profile
from writer_profile.voice.store import VoiceProfileStore

app = typer.Typer(help="CEO Voice Agent — style-aware post generator for X and LinkedIn.")
profile_app = typer.Typer(help="Build and inspect voice profiles.")
app.add_typer(profile_app, name="profile")


def _pipeline(settings: Settings) -> GenerationPipeline:
    embedder = Embedder(model_name=settings.embedding_model)
    store = ExemplarStore(path=settings.chroma_path, embedder=embedder)
    profiles = VoiceProfileStore(root=settings.profiles_path)
    hooks = HookLibrary.load(settings.hooks_path)
    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    return GenerationPipeline(
        store=store,
        profiles=profiles,
        hooks=hooks,
        llm=llm,
        writing_model=settings.writing_model,
        retrieval_k=settings.retrieval_k,
        refine_max_iterations=settings.refine_max_iterations,
        hook_suggestion_k=settings.hook_suggestion_k,
    )


@app.command()
def ingest(
    path: Path = typer.Argument(..., exists=True, readable=True, help="JSONL of posts"),
    author: str = typer.Option(..., help="Canonical author id (e.g. ali_ghodsi)"),
) -> None:
    """Ingest a JSONL corpus of past posts into the exemplar store."""
    settings = Settings()
    embedder = Embedder(model_name=settings.embedding_model)
    store = ExemplarStore(path=settings.chroma_path, embedder=embedder)
    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    count = ingest_file(
        path=path, store=store, llm=llm,
        classifier_model=settings.classifier_model,
        author=author,
    )
    typer.echo(f"ingested {count} posts for {author} into {settings.chroma_path}")


@profile_app.command("build")
def profile_build(
    author: str = typer.Option(..., help="Canonical author id"),
    platform: Platform = typer.Option(..., case_sensitive=False),
    source: Path = typer.Option(..., exists=True, readable=True,
                                help="JSONL of posts for this author+platform"),
) -> None:
    """Build a VoiceProfile from a JSONL of posts."""
    settings = Settings()
    posts = [p for p in load_posts_jsonl(source) if p.platform is platform and p.author == author]
    if not posts:
        typer.echo(f"error: no posts matched author={author} platform={platform.value}", err=True)
        raise typer.Exit(2)

    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    profile = build_voice_profile(
        author=author, platform=platform, posts=posts,
        llm=llm, model=settings.writing_model,
    )
    store = VoiceProfileStore(root=settings.profiles_path)
    path = store.save(profile)
    typer.echo(f"profile saved: {path} (based on {len(posts)} posts)")


@profile_app.command("show")
def profile_show(
    author: str = typer.Option(...),
    platform: Platform = typer.Option(..., case_sensitive=False),
) -> None:
    """Print a saved VoiceProfile as JSON."""
    settings = Settings()
    store = VoiceProfileStore(root=settings.profiles_path)
    profile = store.load(author=author, platform=platform)
    typer.echo(profile.model_dump_json(indent=2))


@profile_app.command("list")
def profile_list() -> None:
    """List all saved profiles."""
    settings = Settings()
    store = VoiceProfileStore(root=settings.profiles_path)
    entries = store.list_profiles()
    for author, platform in sorted(entries):
        typer.echo(f"{author}\t{platform.value}")


@app.command()
def generate(
    author: str = typer.Option(...),
    platform: Platform = typer.Option(..., case_sensitive=False),
    topic: str = typer.Option(..., help="Topic / subject of the post"),
    angle: str = typer.Option("", help="Narrative direction / angle"),
    virality: float = typer.Option(0.15, min=0.0, max=1.0,
                                   help="Strength of virality hook injection (0-1)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip LLM calls, echo config."),
) -> None:
    """Generate a post."""
    settings = Settings()

    if dry_run:
        typer.echo(json.dumps({
            "author": author, "platform": platform.value,
            "topic": topic, "angle": angle, "virality": virality,
            "writing_model": settings.writing_model, "dry_run": True,
        }))
        raise typer.Exit(0)

    pipe = _pipeline(settings)
    draft = pipe.generate(
        author=author, platform=platform,
        idea=Idea(topic=topic, angle=angle),
        virality_strength=virality,
    )
    typer.echo(draft.text)
    if not draft.validation_ok:
        typer.echo(f"[warning] validator issues: {draft.validation_issues}", err=True)


@app.command()
def revoice(
    author: str = typer.Option(...),
    platform: Platform = typer.Option(..., case_sensitive=False),
    draft_file: Path = typer.Option(..., exists=True, readable=True,
                                    help="Plain text file containing the edited draft"),
) -> None:
    """Re-voice an edited draft."""
    settings = Settings()
    pipe = _pipeline(settings)
    edited = draft_file.read_text()
    out = pipe.revoice(author=author, platform=platform, edited_draft=edited)
    typer.echo(out.text)
    if not out.validation_ok:
        typer.echo(f"[warning] validator issues: {out.validation_issues}", err=True)


@app.command()
def samples(
    author: str = typer.Option(...),
    platform: Platform = typer.Option(..., case_sensitive=False),
    out_dir: Path = typer.Option(Path("./eval"), help="Output directory for sheets"),
    virality: float = typer.Option(0.15, min=0.0, max=1.0),
) -> None:
    """Generate one post per topic archetype for manual scoring."""
    settings = Settings()
    pipe = _pipeline(settings)
    results: list[tuple[str, str]] = []
    for idea in ARCHETYPE_IDEAS:
        d = pipe.generate(author=author, platform=platform, idea=idea,
                          virality_strength=virality)
        results.append((idea.topic, d.text))
    path = write_samples_sheet(root=out_dir, author=author, platform=platform, samples=results)
    typer.echo(f"wrote rubric sheet: {path}")


@app.command()
def evaluate(
    author: str = typer.Option(...),
    platform: Platform = typer.Option(..., case_sensitive=False),
    candidates_file: Path = typer.Option(..., exists=True, readable=True,
                                         help="JSONL with {candidate: str} per line"),
    references_file: Path = typer.Option(..., exists=True, readable=True,
                                         help="JSONL of real Posts by the author"),
    out_file: Path = typer.Option(Path("./eval/scores.jsonl")),
) -> None:
    """Run LLM-as-judge over candidate posts against reference corpus."""
    import json as _json

    settings = Settings()
    references = load_posts_jsonl(references_file)
    references = [p for p in references if p.author == author and p.platform is platform][:20]
    if not references:
        typer.echo("error: no reference posts matched author+platform", err=True)
        raise typer.Exit(2)

    from writer_profile.eval.judge import score_post

    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with candidates_file.open("r", encoding="utf-8") as fin, \
         out_file.open("w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            cand = _json.loads(line)["candidate"]
            score = score_post(
                author=author, platform=platform, candidate=cand,
                references=references, llm=llm, model=settings.judge_model,
            )
            fout.write(_json.dumps({
                "candidate": cand,
                "voice_fidelity": score.voice_fidelity,
                "voice_reasoning": score.voice_reasoning,
                "naturalness": score.naturalness,
                "naturalness_reasoning": score.naturalness_reasoning,
                "ai_tics": score.ai_tics,
            }) + "\n")
    typer.echo(f"wrote scores: {out_file}")


if __name__ == "__main__":
    app()
```

- [ ] **Step 3: Update `ingest_file` to accept `author`**

Edit `src/writer_profile/corpus/ingest.py`:

```python
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
    author: str | None = None,
) -> int:
    posts = load_posts_jsonl(path)
    if author:
        # override author on all posts (useful when JSONL doesn't carry it)
        posts = [p.model_copy(update={"author": author}) for p in posts]
    annotated: list[AnnotatedPost] = []
    for post in posts:
        meta = extract_metadata(post, llm=llm, model=classifier_model)
        annotated.append(AnnotatedPost(post=post, metadata=meta))
    store.add_many(annotated)
    return len(annotated)
```

- [ ] **Step 4: Update CLI test**

Edit `tests/test_cli.py` to match the new CLI shape. Replace contents:

```python
import json
from datetime import datetime, UTC

import pytest
from typer.testing import CliRunner

from writer_profile.cli import app
from writer_profile.corpus.models import Platform, Post


@pytest.fixture
def sample_jsonl(tmp_path):
    p = tmp_path / "posts.jsonl"
    post = Post(
        id="p1", author="ali", platform=Platform.TWITTER,
        text="ai evaluation is the new bottleneck",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    p.write_text(post.model_dump_json())
    return p


def test_cli_help_lists_commands():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "generate" in result.stdout
    assert "revoice" in result.stdout
    assert "profile" in result.stdout
    assert "samples" in result.stdout
    assert "evaluate" in result.stdout


def test_cli_generate_dry_run(tmp_path, sample_jsonl, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("WRITER_PROFILE_CHROMA_PATH", str(tmp_path / "c"))
    monkeypatch.setenv("WRITER_PROFILE_PROFILES_PATH", str(tmp_path / "profiles"))

    runner = CliRunner()
    result = runner.invoke(app, [
        "generate",
        "--author", "ali",
        "--platform", "twitter",
        "--topic", "ai evaluation",
        "--angle", "generation is easy, eval is hard",
        "--dry-run",
    ])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["author"] == "ali"
    assert payload["platform"] == "twitter"
    assert payload["topic"] == "ai evaluation"
    assert payload["dry_run"] is True
```

- [ ] **Step 5: Run full suite — expect pass**

Run: `uv run pytest -q`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(cli): profile/generate/revoice/samples/evaluate commands"
```

---

## Task 18: Streamlit UI

**Files:**
- Create: `app.py`
- Modify: `pyproject.toml` (add streamlit dep)

- [ ] **Step 1: Add streamlit dependency**

Edit `pyproject.toml` — add `"streamlit>=1.32.0"` to `dependencies`:

```toml
dependencies = [
    "anthropic>=0.40.0",
    "chromadb>=0.5.0",
    "sentence-transformers>=3.0.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.5.0",
    "typer>=0.12.0",
    "python-dotenv>=1.0.0",
    "numpy>=2.0.0",
    "streamlit>=1.32.0",
]
```

Run: `uv sync` (syncs the lockfile).

- [ ] **Step 2: Write `app.py`**

Create `app.py` at repo root:

```python
from __future__ import annotations

import streamlit as st

from writer_profile.config import Settings
from writer_profile.corpus.models import Idea, Platform
from writer_profile.llm import AnthropicClient
from writer_profile.pipeline import GenerationPipeline
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore
from writer_profile.virality.hooks import HookLibrary
from writer_profile.voice.store import VoiceProfileStore


@st.cache_resource
def get_pipeline() -> GenerationPipeline:
    settings = Settings()
    embedder = Embedder(model_name=settings.embedding_model)
    store = ExemplarStore(path=settings.chroma_path, embedder=embedder)
    profiles = VoiceProfileStore(root=settings.profiles_path)
    hooks = HookLibrary.load(settings.hooks_path)
    llm = AnthropicClient(api_key=settings.anthropic_api_key)
    return GenerationPipeline(
        store=store, profiles=profiles, hooks=hooks, llm=llm,
        writing_model=settings.writing_model,
        retrieval_k=settings.retrieval_k,
        refine_max_iterations=settings.refine_max_iterations,
        hook_suggestion_k=settings.hook_suggestion_k,
    )


def main() -> None:
    st.set_page_config(page_title="CEO Voice Agent", layout="wide")
    st.title("CEO Voice Agent")

    pipe = get_pipeline()
    profiles = VoiceProfileStore(root=Settings().profiles_path)
    available = profiles.list_profiles()
    if not available:
        st.warning("No voice profiles found. Run `writer profile build` first.")
        st.stop()

    authors = sorted({a for a, _ in available})
    author = st.selectbox("CEO", authors)
    platforms_for_author = [p for a, p in available if a == author]
    platform_str = st.selectbox(
        "Platform",
        [p.value for p in platforms_for_author],
    )
    platform = Platform(platform_str)

    topic = st.text_input("Topic", placeholder="databricks acquires tabular")
    angle = st.text_area(
        "Angle / narrative direction",
        height=100,
        placeholder="this validates the open-source approach to data infra",
    )
    virality = st.slider("Virality strength", 0.0, 1.0, 0.15, 0.05)

    if "draft" not in st.session_state:
        st.session_state.draft = ""

    col_gen, col_rev = st.columns(2)

    with col_gen:
        if st.button("Generate", type="primary", disabled=not topic):
            with st.spinner("Generating..."):
                out = pipe.generate(
                    author=author, platform=platform,
                    idea=Idea(topic=topic, angle=angle),
                    virality_strength=virality,
                )
            st.session_state.draft = out.text
            if not out.validation_ok:
                st.warning(f"Validator issues: {out.validation_issues}")

    edited = st.text_area("Draft (edit freely)", value=st.session_state.draft, height=300)

    with col_rev:
        if st.button("Re-voice edits", disabled=not edited.strip()):
            with st.spinner("Revoicing..."):
                out = pipe.revoice(author=author, platform=platform, edited_draft=edited)
            st.session_state.draft = out.text
            st.rerun()

    st.caption("Tip: edit the draft above, then click 'Re-voice edits' to re-apply the author's voice while keeping your structure.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Smoke test UI loads**

Run: `uv run streamlit run app.py --server.headless true --server.port 8765 &`
Wait 3 seconds, then: `curl -s http://localhost:8765/ | head -20`
Expected: HTML containing `<title>` tag.
Kill: `pkill -f "streamlit run app.py"`

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(ui): minimal streamlit ui for generate + revoice"
```

---

## Task 19: Architecture doc + live smoke test

**Files:**
- Create: `docs/architecture.md`

- [ ] **Step 1: Write `docs/architecture.md`**

Create `docs/architecture.md`:

````markdown
# CEO Voice Agent — Architecture

## Overview

Retrieval-augmented generation with a hybrid statistical/LLM voice profile, author-derived platform constraints, a dialable virality layer, and a Self-Refine loop. Multi-tenant via an `author` field on every `Post`.

## Modules

| Module | Responsibility |
|---|---|
| `corpus` | Post / Idea / metadata pydantic models, JSONL loader, Haiku metadata extractor, ingest helper |
| `retrieval` | Sentence-transformer embedder + Chroma persistent store with `(author, platform, tone)` filtering |
| `voice` | `VoiceStats` (deterministic) + LLM synthesis extractor + `VoiceProfile` schema + JSON file store |
| `platforms` | `Constraint` protocol, Twitter + LinkedIn constraints, per-author constraint derivation |
| `virality` | `HookLibrary` with 40 seed hook patterns, dialable injection strength |
| `generation` | Generator (few-shot + profile + hooks), Self-Refine loop, thread splitter, revoice |
| `eval` | LLM-as-judge, archetype sample generator |
| `pipeline` | Composition layer: `generate()` and `revoice()` endpoints |
| `cli` | Typer commands: `ingest`, `profile build/show/list`, `generate`, `revoice`, `samples`, `evaluate` |
| `app.py` | Streamlit UI wrapping the pipeline |

## Voice Profile Engine

Hybrid approach — stats feed LLM synthesis:
1. `compute_stats(posts)` produces a deterministic `VoiceStats` fingerprint (sentence-length percentiles, emoji/hashtag/question/URL/mention rates, top-k openers/closers, bigrams/trigrams, thread rate).
2. `build_voice_profile` passes the stats JSON + a sample of the longest posts to Sonnet with a schema-constrained prompt, which returns a JSON object covering lexical/structural/rhetorical/tonal dimensions.
3. The final `VoiceProfile` is the union: deterministic stats + LLM synthesis + canonical examples.
4. Stored as `profiles/<author>__<platform>.json`. Updatable by re-running `profile build`.

Rationale: pure stats don't translate to prompt behavior well; pure LLM synthesis hallucinates traits that the numbers contradict. Grounding the synthesis in the stats block keeps the LLM honest.

## Constraint derivation

`constraint_for(profile)` reads the profile's stats and builds a `Constraint`:
- Hashtags allowed only if `hashtag_rate >= 5%`.
- No hardcoded case requirement — the voice profile drives case behavior via prompt examples.
- `max_hashtags` scaled from author's `avg_hashtags_per_post`.

This replaces the original project's hardcoded personal-style rules.

## Virality layer

Hand-curated 40-entry `hooks.jsonl` instead of a full clustering pipeline. Each entry has `platform`, `pattern_type`, `template`. `suggest(platform, k)` returns `k` hooks spanning distinct pattern types. `render_injection(hooks, virality_strength)` emits one of three prompt bands based on strength (off / subtle / strong-preference).

Scope decision: spec's "cluster top-100 posts" is a multi-week subproject; a hand-curated library gives the dialable-influence property the spec explicitly asks for at <1% of the build cost.

## Re-voicing

Reuses generation pipeline infrastructure (LLM client, constraint, profile). Dedicated `build_revoice_prompt` enforces structural preservation: explicit rules to preserve paragraph count, relative order of noun phrases, and structural intent. The refine loop is not used for revoicing; one LLM call with a tight prompt is enough because the human provided the structure.

## Evaluation

- **LLM-as-judge**: Sonnet scores each candidate on voice_fidelity (1–10) + naturalness (1–10) with written reasoning + flagged AI tics. Reference corpus = up to 20 real posts by the author.
- **Manual rubric**: `samples` command generates 5 posts per platform across archetypes (product launch, acquisition, earnings, personal reflection, industry commentary) and writes a markdown sheet with per-post scoring blanks.

## Onboarding a new CEO

1. Drop JSONL of their posts at `data/posts/<author>.jsonl`.
2. `writer ingest data/posts/<author>.jsonl --author <author>`
3. `writer profile build --author <author> --platform twitter --source data/posts/<author>.jsonl`
4. `writer profile build --author <author> --platform linkedin --source data/posts/<author>.jsonl`
5. Generate via CLI or UI.

No code changes required. That's the spec's constraint met.

## What worked

- Reusing the existing refine loop (renamed conceptually but structurally identical) for critic-driven revision.
- Grounding the LLM voice extractor in deterministic stats eliminated hallucinated traits in early tests.
- Per-author `Constraint` derivation cleanly killed the original hardcoded personal-style rules.

## What didn't

- Chroma's `where` clause API is awkward for `$and` over 3 fields; we flatten to single-clause dicts when only one filter is active.
- Pydantic BaseModel + dataclass mixing forced a conversion of `VoiceStats` to BaseModel (dataclass stats wouldn't JSON-roundtrip through `VoiceProfile`).

## Scaling to more CEOs

- Per-author Chroma collections if cross-author retrieval noise becomes an issue; currently one collection with `author` filter is fine at O(10^3) posts per author.
- Profile refresh is idempotent: re-running `profile build` overwrites the JSON. Incremental refresh (append new posts) would require storing the post-ids-seen set.

## Known limitations (V1)

- No thread generation via pipeline yet — `Thread` + `split_thread` exist, but `GenerationPipeline.generate` only returns single posts. Thread generation is one prompt template + a post-split validation pass away; deferred.
- No persona-diverse critics; single-critic Self-Refine has the diminishing-returns pattern noted in the research.
- Evaluation is LLM-judge only in V1 code; manual scoring uses the sheet output.
````

- [ ] **Step 2: Commit docs**

```bash
git add docs/architecture.md
git commit -m "docs: architecture and scaling notes"
```

- [ ] **Step 3: Live smoke test (requires ANTHROPIC_API_KEY)**

Only runs locally:

```bash
export ANTHROPIC_API_KEY=sk-...
# (assumes data/posts/ali_ghodsi.jsonl and data/posts/matei_zaharia.jsonl exist)
uv run writer ingest data/posts/ali_ghodsi.jsonl --author ali_ghodsi
uv run writer profile build --author ali_ghodsi --platform linkedin --source data/posts/ali_ghodsi.jsonl
uv run writer generate --author ali_ghodsi --platform linkedin \
    --topic "databricks acquires tabular" \
    --angle "open source wins when the best technology is open"
```

Expected: a plausible LinkedIn post, 150–300 words, in Ali's voice.

- [ ] **Step 4: Run full test suite + lint**

```bash
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
```

Expected: all green.

- [ ] **Step 5: Commit any lint/format fixes**

```bash
git add -A
git commit -m "chore: post-integration lint and format pass" || echo "nothing to commit"
```

---

## Self-review checklist (post-plan)

- **Spec coverage (CEO Voice Agent spec deliverables)**:
  - ✅ Data pipeline ingesting JSONL (Task 17 ingest) — sourcing is out of scope per user, handled separately
  - ✅ Voice Profile Engine multi-dimensional, structured, updatable (Tasks 4-7)
  - ⚠️ Virality Structure Library: hand-curated 40-entry library (Task 9), not full top-100 clustering; scope reduction documented in architecture.md. Dialable property preserved.
  - ✅ Draft Generator idea + CEO + platform (Tasks 10-11, 17)
  - ✅ Re-voicing endpoint (Tasks 13-14, 17)
  - ⚠️ Evaluation for 3 CEOs: framework built (Tasks 15-16); running it for 3 CEOs is execution, not plan. Smoke test task covers 1.
  - ✅ Technical documentation (Task 19)
  - ✅ Minimal front-end UI (Task 18)
  - ⚠️ X thread output: `Thread` + `split_thread` built (Task 12) but not wired into the pipeline's `generate()`. Documented as V1 limitation.
- **Placeholder scan**: no TODOs or vague "handle edge cases" steps.
- **Type consistency**: `VoiceProfile`, `Idea`, `Hook`, `JudgeScore` signatures match across all tasks that reference them. `ingest_file(author=...)` signature matches Task 17 call.
