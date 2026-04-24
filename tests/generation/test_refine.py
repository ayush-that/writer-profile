from writer_profile.corpus.models import Platform
from writer_profile.generation.refine import MultiRefineResult, refine, refine_multi
from writer_profile.llm import StubLLMClient
from writer_profile.platforms.twitter import TwitterConstraint


def test_refine_short_circuits_on_ok_critique_and_valid_draft():
    initial = "the bottleneck in ai moved from generation to evaluation"
    llm = StubLLMClient(responses=["OK"])
    result = refine(
        draft=initial,
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
        llm=llm,
        model="claude-sonnet-4-6",
        max_iterations=2,
    )
    assert result.final_draft == initial
    assert result.iterations == 1
    assert len(llm.calls) == 1


def test_refine_retries_when_validator_fails():
    bad = "This Has Uppercase"
    llm = StubLLMClient(
        responses=[
            "uppercase is banned",
            "this has uppercase fixed",
        ]
    )
    result = refine(
        draft=bad,
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
        llm=llm,
        model="claude-sonnet-4-6",
        max_iterations=2,
    )
    assert result.final_draft == "this has uppercase fixed"
    assert result.iterations == 2
    assert len(llm.calls) == 2


def test_refine_retries_when_critic_non_ok_even_if_validator_passes():
    initial = "the bottleneck in ai moved from generation to evaluation"
    llm = StubLLMClient(
        responses=[
            "- hook is weak, sharpen it",
            "evaluation is the new bottleneck in ai",
            "OK",
        ]
    )
    result = refine(
        draft=initial,
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
        llm=llm,
        model="claude-sonnet-4-6",
        max_iterations=3,
    )
    assert result.final_draft == "evaluation is the new bottleneck in ai"
    assert result.iterations == 3


def test_refine_caps_at_max_iterations():
    llm = StubLLMClient(
        responses=[
            "- weak hook",
            "new draft 1",
            "- still weak",
            "new draft 2",
        ]
    )
    result = refine(
        draft="starting draft",
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
        llm=llm,
        model="claude-sonnet-4-6",
        max_iterations=2,
    )
    assert result.iterations == 2
    assert result.final_draft == "new draft 1"


def test_refine_short_circuits_on_ok_with_punctuation():
    initial = "the bottleneck in ai moved from generation to evaluation"
    llm = StubLLMClient(responses=["OK."])
    result = refine(
        draft=initial,
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(require_lowercase=True, allow_hashtags=False),
        llm=llm,
        model="claude-sonnet-4-6",
        max_iterations=3,
    )
    assert result.iterations == 1
    assert len(llm.calls) == 1


def test_refine_short_circuits_on_lowercase_ok():
    initial = "the bottleneck in ai moved from generation to evaluation"
    llm = StubLLMClient(responses=["ok, looks strong to me"])
    result = refine(
        draft=initial,
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(require_lowercase=True, allow_hashtags=False),
        llm=llm,
        model="claude-sonnet-4-6",
        max_iterations=3,
    )
    assert result.iterations == 1


def test_refine_multi_returns_result():
    llm = StubLLMClient(responses=["OK", "OK", "OK"])
    result = refine_multi(
        draft="Test draft here",
        platform=Platform.TWITTER,
        constraint=TwitterConstraint(),
        author="ali",
        llm=llm,
        model="test",
        max_iterations=2,
    )
    assert isinstance(result, MultiRefineResult)
    assert result.final_draft == "Test draft here"
    assert result.all_critics_ok is True
