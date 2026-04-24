from writer_profile.corpus.models import Platform
from writer_profile.generation.critics import (
    CRITICS,
    CriticFeedback,
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
