from datetime import UTC, datetime

from writer_profile.corpus.models import Platform, Post, PostMetadata, Tone
from writer_profile.generation.generator import generate_draft
from writer_profile.llm import StubLLMClient
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.retrieval.store import ExemplarHit


def _hit(text: str) -> ExemplarHit:
    return ExemplarHit(
        post=Post(
            id="x",
            author="ali",
            platform=Platform.TWITTER,
            text=text,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
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
