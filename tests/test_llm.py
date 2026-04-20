from writer_profile.llm import LLMMessage, StubLLMClient


def test_stub_returns_scripted_responses():
    client = StubLLMClient(responses=["first", "second"])
    r1 = client.complete(
        model="claude-sonnet-4-6",
        system="sys",
        messages=[LLMMessage(role="user", content="hi")],
    )
    r2 = client.complete(
        model="claude-sonnet-4-6",
        system="sys",
        messages=[LLMMessage(role="user", content="again")],
    )
    assert r1 == "first"
    assert r2 == "second"
    assert len(client.calls) == 2
    assert client.calls[0].system == "sys"
    assert client.calls[0].messages[0].content == "hi"


def test_stub_raises_when_exhausted():
    client = StubLLMClient(responses=["only"])
    client.complete(model="m", system="s", messages=[LLMMessage(role="user", content="x")])
    try:
        client.complete(model="m", system="s", messages=[LLMMessage(role="user", content="y")])
    except IndexError:
        return
    raise AssertionError("expected IndexError")
