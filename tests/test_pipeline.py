from datetime import UTC, datetime
from pathlib import Path

import pytest

from writer_profile.corpus.models import AnnotatedPost, Idea, Platform, Post, PostMetadata, Tone
from writer_profile.llm import StubLLMClient
from writer_profile.pipeline import GenerationPipeline, PostDraft
from writer_profile.retrieval.embedder import Embedder
from writer_profile.retrieval.store import ExemplarStore
from writer_profile.virality.hooks import HookLibrary
from writer_profile.voice.profile import (
    LexicalProfile,
    RhetoricalProfile,
    StructuralProfile,
    TonalProfile,
    VoiceProfile,
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
