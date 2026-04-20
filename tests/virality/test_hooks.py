from pathlib import Path

from writer_profile.corpus.models import Platform
from writer_profile.virality.hooks import HookLibrary


def test_load_and_filter_by_platform():
    lib = HookLibrary.load(Path("data/hooks.jsonl"))
    assert len(lib.all()) >= 40
    x_hooks = lib.for_platform(Platform.TWITTER)
    li_hooks = lib.for_platform(Platform.LINKEDIN)
    assert len(x_hooks) > 0
    assert len(li_hooks) > 0
    assert all(h.platform is Platform.TWITTER for h in x_hooks)
    assert all(h.platform is Platform.LINKEDIN for h in li_hooks)


def test_suggest_returns_mix_of_pattern_types():
    lib = HookLibrary.load(Path("data/hooks.jsonl"))
    suggestions = lib.suggest(platform=Platform.TWITTER, k=5)
    assert len(suggestions) == 5
    # should span at least 3 distinct pattern types
    types = {h.pattern_type for h in suggestions}
    assert len(types) >= 3


def test_render_injection_block_respects_strength():
    lib = HookLibrary.load(Path("data/hooks.jsonl"))
    suggestions = lib.suggest(platform=Platform.TWITTER, k=3, seed=42)

    subtle = lib.render_injection(suggestions, virality_strength=0.15)
    aggressive = lib.render_injection(suggestions, virality_strength=1.0)
    off = lib.render_injection(suggestions, virality_strength=0.0)

    assert "optional" in subtle.lower() or "may" in subtle.lower()
    assert "prefer" in aggressive.lower() or "adopt" in aggressive.lower()
    assert off.strip() == "" or "ignore" in off.lower()
