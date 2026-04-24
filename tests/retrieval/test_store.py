from datetime import UTC, datetime
from pathlib import Path

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
            author="ali",
            platform=platform,
            text=text,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        ),
        metadata=PostMetadata(topics=topics, tone=tone, length_bucket="short", language="en"),
    )


def test_store_roundtrip_with_platform_filter(tmp_path, embedder):
    store = ExemplarStore(path=str(tmp_path / "chroma"), embedder=embedder, collection="roundtrip")
    store.add_many(
        [
            _ann(
                "a",
                Platform.TWITTER,
                "ai evaluation is the new bottleneck",
                Tone.OBSERVATIONAL,
                ["ai"],
            ),
            _ann(
                "b",
                Platform.TWITTER,
                "unrelated post about sourdough bread",
                Tone.STORY,
                ["cooking"],
            ),
            _ann(
                "c",
                Platform.LINKEDIN,
                "ai evaluation is the new bottleneck",
                Tone.OBSERVATIONAL,
                ["ai"],
            ),
        ]
    )
    hits = store.query(
        text="how do we evaluate ai agents",
        platform=Platform.TWITTER,
        k=2,
    )
    assert len(hits) == 2
    assert all(h.post.platform is Platform.TWITTER for h in hits)
    assert hits[0].post.id == "a"


def test_store_filters_by_author(tmp_path, embedder):
    def ann(pid: str, author: str, text: str) -> AnnotatedPost:
        return AnnotatedPost(
            post=Post(
                id=pid,
                author=author,
                platform=Platform.TWITTER,
                text=text,
                created_at=datetime(2025, 1, 1, tzinfo=UTC),
            ),
            metadata=PostMetadata(
                topics=["ai"],
                tone=Tone.OBSERVATIONAL,
                length_bucket="short",
                language="en",
            ),
        )

    store = ExemplarStore(path=str(tmp_path / "c"), embedder=embedder, collection="author_filter")
    store.add_many(
        [
            ann("a1", "ali", "iceberg is the future of open data"),
            ann("m1", "matei", "spark 4 is shipping vectorized execution"),
        ]
    )

    hits = store.query(text="open data formats", platform=Platform.TWITTER, author="ali", k=5)
    assert len(hits) == 1
    assert hits[0].post.author == "ali"


def test_query_empty_collection_returns_empty_list(tmp_path: Path):
    embedder = Embedder(model_name="sentence-transformers/all-MiniLM-L6-v2")
    store = ExemplarStore(path=str(tmp_path), embedder=embedder)
    hits = store.query(text="hello world", platform=Platform.TWITTER, author="nobody", k=5)
    assert hits == []


def test_query_diverse_spans_tones(tmp_path: Path, embedder):
    store = ExemplarStore(path=str(tmp_path / "diverse"), embedder=embedder, collection="diverse")
    store.add_many(
        [
            _ann(
                "t1",
                Platform.TWITTER,
                "first observational post about ai",
                Tone.OBSERVATIONAL,
                ["ai"],
            ),
            _ann(
                "t2", Platform.TWITTER, "second observational about ai", Tone.OBSERVATIONAL, ["ai"]
            ),
            _ann("t3", Platform.TWITTER, "story about building ai", Tone.STORY, ["ai"]),
            _ann("t4", Platform.TWITTER, "contrarian take on ai", Tone.CONTRARIAN, ["ai"]),
        ]
    )

    hits = store.query_diverse(
        text="artificial intelligence",
        platform=Platform.TWITTER,
        author="ali",
        k=3,
    )
    assert len(hits) == 3
    tones = {h.metadata.tone for h in hits}
    assert len(tones) >= 2


def test_store_persists_across_instances(tmp_path, embedder):
    path = str(tmp_path / "chroma")
    s1 = ExemplarStore(path=path, embedder=embedder, collection="persist")
    s1.add_many(
        [
            _ann("x", Platform.TWITTER, "stored post about ai", Tone.OBSERVATIONAL, ["ai"]),
        ]
    )
    s2 = ExemplarStore(path=path, embedder=embedder, collection="persist")
    hits = s2.query(text="ai", platform=Platform.TWITTER, k=1)
    assert len(hits) == 1
    assert hits[0].post.id == "x"
