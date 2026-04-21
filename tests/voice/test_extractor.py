import json
from datetime import UTC, datetime

from writer_profile.corpus.models import Platform, Post
from writer_profile.llm import StubLLMClient
from writer_profile.voice.extractor import build_voice_profile


def _p(pid: str, text: str) -> Post:
    return Post(
        id=pid,
        author="ali",
        platform=Platform.LINKEDIN,
        text=text,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def test_build_voice_profile_wires_llm_and_stats():
    posts = [
        _p("1", "open source wins. it always has."),
        _p("2", "databricks is acquiring tabular today. bringing spark and iceberg together."),
        _p("3", "what do you think about the future of open data formats?"),
    ]

    qualitative_json = json.dumps(
        {
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
        }
    )

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
    wrapped = (
        "```json\n"
        + json.dumps(
            {
                "lexical": {
                    "recurring_phrases": [],
                    "word_preferences": {},
                    "jargon_level": "low",
                    "notes": "",
                },
                "structural": {
                    "typical_opener_patterns": [],
                    "typical_closer_patterns": [],
                    "paragraph_shape": "",
                    "list_usage": "",
                    "question_usage": "",
                },
                "rhetorical": {
                    "uses_analogies": False,
                    "uses_personal_anecdotes": False,
                    "uses_data_points": False,
                    "attribution_style": "",
                    "name_drop_rate": "rare",
                },
                "tonal": {
                    "warmth": "neutral",
                    "humor": "none",
                    "conviction": "low",
                    "disclosure": "rare",
                    "vulnerability": "rare",
                },
                "examples": ["hello world"],
            }
        )
        + "\n```"
    )

    llm = StubLLMClient(responses=[wrapped])
    profile = build_voice_profile(
        author="ali",
        platform=Platform.LINKEDIN,
        posts=posts,
        llm=llm,
        model="claude-sonnet-4-6",
    )
    assert profile.author == "ali"
