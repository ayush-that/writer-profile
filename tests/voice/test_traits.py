import pytest

from writer_profile.voice.traits import TraitVector


def test_trait_vector_defaults():
    tv = TraitVector()
    assert tv.warmth == 0.5
    assert tv.humor == 0.5
    assert tv.formality == 0.5
    assert tv.energy == 0.5
    assert tv.conviction == 0.5
    assert tv.disclosure == 0.5


def test_trait_vector_clamps_values():
    with pytest.raises(ValueError):
        TraitVector(warmth=1.5)
    with pytest.raises(ValueError):
        TraitVector(humor=-0.1)


def test_trait_vector_interpolation():
    tv1 = TraitVector(warmth=0.0, humor=0.0)
    tv2 = TraitVector(warmth=1.0, humor=1.0)
    blended = tv1.blend(tv2, alpha=0.5)
    assert blended.warmth == 0.5
    assert blended.humor == 0.5


def test_trait_vector_to_prompt_description():
    tv = TraitVector(warmth=0.9, humor=0.2, conviction=0.8)
    desc = tv.to_prompt_description()
    assert "warm" in desc.lower()
    assert "serious" in desc.lower() or "dry" in desc.lower()
    assert "confident" in desc.lower() or "assertive" in desc.lower()
