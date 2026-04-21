from writer_profile.corpus.models import Platform
from writer_profile.platforms.author_derived import constraint_for
from writer_profile.platforms.linkedin import LinkedInConstraint
from writer_profile.platforms.twitter import TwitterConstraint
from writer_profile.voice.profile import (
    LexicalProfile,
    RhetoricalProfile,
    StructuralProfile,
    TonalProfile,
    VoiceProfile,
)
from writer_profile.voice.stats import VoiceStats


def _profile_with(hashtag_rate: float, platform: Platform) -> VoiceProfile:
    return VoiceProfile(
        author="x",
        platform=platform,
        stats=VoiceStats(
            post_count=100,
            avg_words_per_sentence=12.0,
            sentence_length_p25_p50_p75=(6.0, 11.0, 18.0),
            length_chars_p25_p50_p75=(80.0, 150.0, 220.0),
            emoji_rate=0.0,
            hashtag_rate=hashtag_rate,
            avg_hashtags_per_post=0.5,
            url_rate=0.1,
            question_rate=0.1,
            mention_rate=0.2,
            line_break_rate=0.1,
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
            conviction="low",
            disclosure="rare",
            vulnerability="rare",
        ),
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
