import json
from datetime import UTC, datetime

from writer_profile.corpus.models import Platform, Post
from writer_profile.eval.judge import JudgeScore, score_post
from writer_profile.llm import StubLLMClient


def _ref(text: str) -> Post:
    return Post(
        id=text[:5],
        author="ali",
        platform=Platform.TWITTER,
        text=text,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def test_score_post_returns_structured_score():
    references = [_ref("open source wins"), _ref("spark ships vectorized exec today")]

    judge_json = json.dumps(
        {
            "voice_fidelity": 8,
            "voice_reasoning": "strong cadence match, word choice aligns",
            "naturalness": 9,
            "naturalness_reasoning": "sounds human",
            "ai_tics": [],
        }
    )
    llm = StubLLMClient(responses=[judge_json])

    score = score_post(
        author="ali",
        platform=Platform.TWITTER,
        candidate="open source wins. it always has.",
        references=references,
        llm=llm,
        model="claude-sonnet-4-6",
    )

    assert isinstance(score, JudgeScore)
    assert score.voice_fidelity == 8
    assert score.naturalness == 9
    assert len(score.ai_tics) == 0
    assert len(llm.calls) == 1
    assert "open source wins" in llm.calls[0].system


def test_score_post_handles_json_fenced():
    references = [_ref("hi")]
    wrapped = (
        "```json\n"
        + json.dumps(
            {
                "voice_fidelity": 5,
                "voice_reasoning": "mediocre",
                "naturalness": 6,
                "naturalness_reasoning": "ok",
                "ai_tics": ["repetitive 'moreover'"],
            }
        )
        + "\n```"
    )
    llm = StubLLMClient(responses=[wrapped])

    score = score_post(
        author="ali",
        platform=Platform.TWITTER,
        candidate="draft",
        references=references,
        llm=llm,
        model="claude-sonnet-4-6",
    )
    assert score.voice_fidelity == 5
    assert "moreover" in score.ai_tics[0]
