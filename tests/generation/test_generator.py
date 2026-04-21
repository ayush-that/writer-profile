from writer_profile.corpus.models import Idea, Platform
from writer_profile.generation.generator import generate_draft
from writer_profile.llm import StubLLMClient
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.voice.profile import (
    LexicalProfile,
    RhetoricalProfile,
    StructuralProfile,
    TonalProfile,
    VoiceProfile,
)
from writer_profile.voice.stats import VoiceStats


def _profile() -> VoiceProfile:
    return VoiceProfile(
        author="ali",
        platform=Platform.TWITTER,
        stats=VoiceStats(
            post_count=20,
            avg_words_per_sentence=10.0,
            sentence_length_p25_p50_p75=(5.0, 9.0, 14.0),
            length_chars_p25_p50_p75=(70.0, 150.0, 220.0),
            emoji_rate=0.0,
            hashtag_rate=0.0,
            avg_hashtags_per_post=0.0,
            url_rate=0.1,
            question_rate=0.1,
            mention_rate=0.2,
            line_break_rate=0.0,
            top_openers=[],
            top_closers=[],
            top_bigrams=[],
            top_trigrams=[],
            thread_rate=0.0,
        ),
        lexical=LexicalProfile(
            recurring_phrases=[], word_preferences={}, jargon_level="low", notes=""
        ),
        structural=StructuralProfile(
            typical_opener_patterns=[],
            typical_closer_patterns=[],
            paragraph_shape="",
            list_usage="",
            question_usage="",
        ),
        rhetorical=RhetoricalProfile(
            uses_analogies=False,
            uses_personal_anecdotes=False,
            uses_data_points=False,
            attribution_style="",
            name_drop_rate="rare",
        ),
        tonal=TonalProfile(
            warmth="neutral",
            humor="none",
            conviction="medium",
            disclosure="rare",
            vulnerability="rare",
        ),
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
