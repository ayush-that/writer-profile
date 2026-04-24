from writer_profile.corpus.models import Idea, Platform
from writer_profile.generation.prompts import (
    build_critic_prompt,
    build_generator_prompt,
    build_refine_prompt,
)
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.virality.hooks import Hook
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
        author="ali_ghodsi",
        platform=Platform.TWITTER,
        stats=VoiceStats(
            post_count=50,
            avg_words_per_sentence=10.0,
            sentence_length_p25_p50_p75=(5.0, 9.0, 16.0),
            length_chars_p25_p50_p75=(80.0, 150.0, 230.0),
            emoji_rate=0.0,
            hashtag_rate=0.05,
            avg_hashtags_per_post=0.2,
            url_rate=0.1,
            question_rate=0.1,
            mention_rate=0.2,
            line_break_rate=0.0,
            top_openers=["open source is", "today we ship"],
            top_closers=["let's go", "always has"],
            top_bigrams=[("open source", 15)],
            top_trigrams=[],
            thread_rate=0.05,
        ),
        lexical=LexicalProfile(
            recurring_phrases=["open source"],
            word_preferences={"team": 1},
            jargon_level="medium",
            notes="conviction language",
        ),
        structural=StructuralProfile(
            typical_opener_patterns=["declarative one-liner"],
            typical_closer_patterns=["brief forward-looking line"],
            paragraph_shape="1-3 sentences",
            list_usage="rarely",
            question_usage="rarely",
        ),
        rhetorical=RhetoricalProfile(
            uses_analogies=False,
            uses_personal_anecdotes=True,
            uses_data_points=True,
            attribution_style="credits team",
            name_drop_rate="moderate",
        ),
        tonal=TonalProfile(
            warmth="warm",
            humor="dry",
            conviction="high",
            disclosure="moderate",
            vulnerability="rare",
        ),
        examples=["open source wins. it always has.", "today we ship spark 4."],
    )


def test_build_generator_prompt_injects_profile_and_hooks_and_idea():
    profile = _profile()
    idea = Idea(
        topic="databricks acquires tabular",
        angle="validates open-source approach to data",
        constraints=["mention spark + iceberg teams"],
    )
    hooks = [
        Hook(
            id="h1",
            platform=Platform.TWITTER,
            pattern_type="hot_take",
            template="Unpopular opinion: {claim}.",
        )
    ]

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


def test_critic_prompt_includes_draft_and_rules():
    sys_, user = build_critic_prompt(
        draft="some draft",
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
    )
    assert "some draft" in user
    assert "280" in sys_ or "twitter" in sys_.lower()


def test_refine_prompt_includes_feedback_and_validator_issues():
    _, user = build_refine_prompt(
        draft="some draft",
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
        critic_feedback="too generic, no surprise",
        validator_issues=["too long"],
    )
    assert "too generic" in user
    assert "too long" in user
