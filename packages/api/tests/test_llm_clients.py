from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from writer_api.services.llm import (
    AnthropicClient,
    GeminiClient,
    LLMResponse,
    MistralClient,
    OpenAIClient,
    OpenRouterClient,
    get_llm_client,
)


def _install_fake_genai() -> None:
    # If the real google.genai is importable, use it (don't overwrite).
    if "google.genai" in sys.modules:
        return
    try:
        import google.genai  # noqa: F401
        return
    except ImportError:
        pass

    google_pkg = sys.modules.get("google") or types.ModuleType("google")
    genai_mod = types.ModuleType("google.genai")
    types_mod = types.ModuleType("google.genai.types")

    class GenerateContentConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    types_mod.GenerateContentConfig = GenerateContentConfig

    class Client:
        def __init__(self, *args, **kwargs):
            self.models = MagicMock()

    genai_mod.Client = Client
    genai_mod.types = types_mod
    google_pkg.genai = genai_mod

    sys.modules["google"] = google_pkg
    sys.modules["google.genai"] = genai_mod
    sys.modules["google.genai.types"] = types_mod


def _install_fake_mistral() -> None:
    if "mistralai" in sys.modules:
        return
    mod = types.ModuleType("mistralai")

    class Mistral:
        def __init__(self, *args, **kwargs):
            self.chat = MagicMock()

    mod.Mistral = Mistral
    sys.modules["mistralai"] = mod


def test_anthropic_client_returns_llm_response() -> None:
    fake_message = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = "hello world"
    fake_message.content = [block]
    fake_message.usage.input_tokens = 10
    fake_message.usage.output_tokens = 5

    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message

    with patch("anthropic.Anthropic", return_value=fake_client):
        client = AnthropicClient(api_key="fake-key", model="claude-test")
        result = client.complete(system="sys", user="usr")

    assert isinstance(result, LLMResponse)
    assert result.text == "hello world"
    assert result.model == "claude-test"
    assert result.input_tokens == 10
    assert result.output_tokens == 5


def test_openai_client_returns_llm_response() -> None:
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="openai text"))]
    fake_response.usage = MagicMock(prompt_tokens=12, completion_tokens=7)

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response

    with patch("openai.OpenAI", return_value=fake_client):
        client = OpenAIClient(api_key="fake-key", model="gpt-test")
        result = client.complete(system="sys", user="usr")

    assert isinstance(result, LLMResponse)
    assert result.text == "openai text"
    assert result.model == "gpt-test"
    assert result.input_tokens == 12
    assert result.output_tokens == 7


def test_gemini_client_returns_llm_response() -> None:
    _install_fake_genai()

    fake_response = MagicMock()
    fake_response.text = "gemini text"
    fake_response.usage_metadata = MagicMock(
        prompt_token_count=20, candidates_token_count=8
    )

    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("google.genai.Client", return_value=fake_client):
        client = GeminiClient(api_key="fake-key", model="gemini-test")
        result = client.complete(system="sys", user="usr")

    assert isinstance(result, LLMResponse)
    assert result.text == "gemini text"
    assert result.model == "gemini-test"
    assert result.input_tokens == 20
    assert result.output_tokens == 8


def test_openrouter_client_returns_llm_response() -> None:
    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="router text"))]
    fake_response.usage = MagicMock(prompt_tokens=3, completion_tokens=4)

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_response

    with patch("openai.OpenAI", return_value=fake_client) as openai_ctor:
        client = OpenRouterClient(api_key="fake-key", model="anthropic/claude-test")
        result = client.complete(system="sys", user="usr")

    assert openai_ctor.call_args.kwargs["base_url"] == "https://openrouter.ai/api/v1"
    assert isinstance(result, LLMResponse)
    assert result.text == "router text"
    assert result.model == "anthropic/claude-test"
    assert result.input_tokens == 3
    assert result.output_tokens == 4


def test_mistral_client_returns_llm_response() -> None:
    _install_fake_mistral()

    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content="mistral text"))]
    fake_response.usage = MagicMock(prompt_tokens=11, completion_tokens=6)

    fake_inner = MagicMock()
    fake_inner.chat.complete.return_value = fake_response

    with patch("mistralai.Mistral", return_value=fake_inner):
        client = MistralClient(api_key="fake-key", model="mistral-test")
        result = client.complete(system="sys", user="usr")

    assert isinstance(result, LLMResponse)
    assert result.text == "mistral text"
    assert result.model == "mistral-test"
    assert result.input_tokens == 11
    assert result.output_tokens == 6


def test_get_llm_client_dispatch() -> None:
    _install_fake_genai()
    _install_fake_mistral()

    with patch("anthropic.Anthropic", return_value=MagicMock()):
        assert isinstance(get_llm_client("anthropic", api_key="k"), AnthropicClient)
        assert isinstance(get_llm_client("claude", api_key="k"), AnthropicClient)

    with patch("openai.OpenAI", return_value=MagicMock()):
        assert isinstance(get_llm_client("openai", api_key="k"), OpenAIClient)
        assert isinstance(get_llm_client("openrouter", api_key="k"), OpenRouterClient)

    with patch("google.genai.Client", return_value=MagicMock()):
        assert isinstance(get_llm_client("gemini", api_key="k"), GeminiClient)

    with patch("mistralai.Mistral", return_value=MagicMock()):
        assert isinstance(get_llm_client("mistral", api_key="k"), MistralClient)

    with pytest.raises(ValueError):
        get_llm_client("nonexistent", api_key="k")
