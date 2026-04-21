from writer_profile.corpus.models import Platform
from writer_profile.generation.revoice import revoice
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
            post_count=10,
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


def test_revoice_produces_refined_output_via_llm():
    edited = (
        "Last week I met the Tabular team in person.\n\n"
        "Brilliant engineers. They built Iceberg from the ground up.\n\n"
        "Today, we're bringing them into the Databricks family."
    )
    llm = StubLLMClient(
        responses=[
            "Last week I sat down with the Tabular team.\n\n"
            "Brilliant engineers. They built iceberg.\n\n"
            "Today they join databricks. spark + iceberg under one roof. open source wins."
        ]
    )

    out = revoice(
        profile=_profile(),
        edited_draft=edited,
        constraint=TwitterConstraint(max_chars=1000),
        llm=llm,
        model="claude-sonnet-4-6",
    )

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
