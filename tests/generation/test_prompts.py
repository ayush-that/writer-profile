from datetime import datetime, timezone

from writer_profile.corpus.models import Platform, Post, PostMetadata, Tone
from writer_profile.generation.prompts import (
    build_critic_prompt,
    build_generator_prompt,
    build_refine_prompt,
)
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.retrieval.store import ExemplarHit


def _hit(pid: str, text: str) -> ExemplarHit:
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
