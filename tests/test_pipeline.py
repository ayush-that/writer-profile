from datetime import UTC, datetime

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
            author="ali",
            platform=Platform.TWITTER,
            text=text,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        ),
        metadata=PostMetadata(
            topics=["ai"], tone=Tone.OBSERVATIONAL, length_bucket="short", language="en"
        ),
    )


def test_pipeline_end_to_end_with_stub(tmp_path, embedder):
    store = ExemplarStore(path=str(tmp_path / "c"), embedder=embedder, collection="pipe")
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
    store = ExemplarStore(path=str(tmp_path / "c2"), embedder=embedder, collection="pipe2")
    llm = StubLLMClient(responses=[])
    pipe = GenerationPipeline(
        store=store,
        llm=llm,
        writing_model="claude-sonnet-4-6",
        constraints={Platform.TWITTER: TwitterConstraint()},
    )
    with pytest.raises(KeyError):
        pipe.generate(topic="x", platform=Platform.LINKEDIN)
