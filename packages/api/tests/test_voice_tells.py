from __future__ import annotations

from writer_api.services.voice_tells import (
    EM_DASH_THRESHOLD,
    EMOJI_THRESHOLD,
    VoiceTells,
    extract_tells,
    sanitize_output,
)


def test_extract_tells_zero_em_dash_forbidden():
    posts = ["hello world", "another clean post", "no special chars here"]
    tells = extract_tells(posts)
    assert tells.em_dash_rate == 0.0
    assert tells.em_dash_forbidden is True
    assert tells.sample_size == 3


def test_extract_tells_high_em_dash_rate_not_forbidden():
    posts = [
        "this — has em dash",
        "another — one",
        "third — post",
        "fourth — post",
        "clean post",
    ]
    tells = extract_tells(posts)
    assert tells.em_dash_rate == 0.8
    assert tells.em_dash_forbidden is False


def test_extract_tells_empty_list_forbids_both():
    tells = extract_tells([])
    assert tells.em_dash_forbidden is True
    assert tells.emoji_forbidden is True
    assert tells.sample_size == 0
    assert tells.em_dash_rate == 0.0
    assert tells.emoji_rate == 0.0


def test_extract_tells_skips_blank_posts():
    posts = ["", "   ", "real post"]
    tells = extract_tells(posts)
    assert tells.sample_size == 1


def test_extract_tells_emoji_detection():
    posts = ["nice 🚀 launch", "another 🎉 win", "plain post"]
    tells = extract_tells(posts)
    assert tells.emoji_rate > 0.5
    assert tells.emoji_forbidden is False


def test_extract_tells_double_hyphen_counts_as_em_dash():
    posts = ["foo -- bar", "clean", "clean too"]
    tells = extract_tells(posts)
    assert tells.em_dash_rate > 0.0


def test_extract_tells_threshold_boundary():
    posts = [f"clean post {i}" for i in range(100)]
    posts[0] = "this — has em dash"
    tells = extract_tells(posts)
    assert tells.em_dash_rate == 0.01
    assert tells.em_dash_rate < EM_DASH_THRESHOLD
    assert tells.em_dash_forbidden is True
    assert tells.emoji_rate < EMOJI_THRESHOLD


def _forbid_em() -> VoiceTells:
    return VoiceTells(
        em_dash_rate=0.0,
        emoji_rate=0.0,
        em_dash_forbidden=True,
        emoji_forbidden=False,
        sample_size=10,
    )


def _forbid_emoji() -> VoiceTells:
    return VoiceTells(
        em_dash_rate=0.0,
        emoji_rate=0.0,
        em_dash_forbidden=False,
        emoji_forbidden=True,
        sample_size=10,
    )


def _forbid_neither() -> VoiceTells:
    return VoiceTells(
        em_dash_rate=0.5,
        emoji_rate=0.5,
        em_dash_forbidden=False,
        emoji_forbidden=False,
        sample_size=10,
    )


def test_sanitize_em_dash_replaced_with_comma():
    assert sanitize_output("hello — world", _forbid_em()) == "hello, world"


def test_sanitize_en_dash_replaced():
    assert sanitize_output("hello – world", _forbid_em()) == "hello, world"


def test_sanitize_double_hyphen_replaced():
    assert sanitize_output("hello -- world", _forbid_em()) == "hello, world"


def test_sanitize_emoji_removed_no_double_space():
    assert sanitize_output("nice 🚀 launch", _forbid_emoji()) == "nice launch"


def test_sanitize_noop_when_nothing_forbidden():
    text = "hello — world 🚀 great"
    assert sanitize_output(text, _forbid_neither()) == text


def test_sanitize_preserves_urls_with_double_hyphen():
    text = "check https://example.com/path--with-dashes for info"
    out = sanitize_output(text, _forbid_em())
    assert "https://example.com/path--with-dashes" in out


def test_sanitize_handles_empty_string():
    assert sanitize_output("", _forbid_em()) == ""


def test_sanitize_collapses_multiple_commas():
    out = sanitize_output("a — b — c", _forbid_em())
    assert ",," not in out
    assert out == "a, b, c"


def test_sanitize_both_forbidden():
    tells = VoiceTells(
        em_dash_rate=0.0,
        emoji_rate=0.0,
        em_dash_forbidden=True,
        emoji_forbidden=True,
        sample_size=10,
    )
    assert sanitize_output("yes — totally 🚀 win", tells) == "yes, totally win"
