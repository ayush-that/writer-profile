import pytest

from writer_profile.generation.critics import (
    CRITICS,
    CriticFeedback,
    _is_ok,
    parse_critic_response,
    synthesize_feedback,
)


def test_critics_list_has_three_critics():
    assert len(CRITICS) == 3
    names = [c["name"] for c in CRITICS]
    assert "voice_fidelity" in names
    assert "engagement" in names
    assert "platform_native" in names


def test_synthesize_feedback_returns_combined():
    feedbacks = [
        CriticFeedback(name="voice_fidelity", feedback="Tone is off", is_ok=False),
        CriticFeedback(name="engagement", feedback="OK", is_ok=True),
        CriticFeedback(name="platform_native", feedback="Too long", is_ok=False),
    ]
    combined = synthesize_feedback(feedbacks)
    assert "Tone is off" in combined
    assert "Too long" in combined


def test_synthesize_feedback_all_ok():
    feedbacks = [
        CriticFeedback(name="voice_fidelity", feedback="OK", is_ok=True),
        CriticFeedback(name="engagement", feedback="OK", is_ok=True),
        CriticFeedback(name="platform_native", feedback="OK", is_ok=True),
    ]
    combined = synthesize_feedback(feedbacks)
    assert combined == "OK"


@pytest.mark.parametrize(
    "feedback,expected",
    [
        ("OK", True),
        ("OK.", True),
        ("ok", True),
        ("Ok, looks good", True),
        ("- OK, no issues", True),
        ("* OK", True),
        ("", False),
        ("Not OK", False),
        ("The hook is weak", False),
        ("   ", False),
    ],
)
def test_is_ok_detection(feedback: str, expected: bool):
    assert _is_ok(feedback) == expected


def test_parse_critic_response_ok():
    result = parse_critic_response("voice_fidelity", "OK")
    assert result.name == "voice_fidelity"
    assert result.feedback == "OK"
    assert result.is_ok is True


def test_parse_critic_response_not_ok():
    result = parse_critic_response("engagement", "- Hook is weak\n- Add CTA")
    assert result.name == "engagement"
    assert "Hook is weak" in result.feedback
    assert result.is_ok is False
