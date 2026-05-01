from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from writer_api.config import settings
from writer_api.services.embeddings import EmbeddingClient, get_embedding_client


def _install_fake_genai() -> None:
    # If the real google.genai is importable, use it (don't overwrite — the real
    # module has google.genai.types which other code paths depend on).
    if "google.genai" in sys.modules:
        return
    try:
        import google.genai  # noqa: F401
        return
    except ImportError:
        pass

    google_pkg = sys.modules.get("google") or types.ModuleType("google")
    genai_mod = types.ModuleType("google.genai")

    class Client:
        def __init__(self, *args, **kwargs):
            self.models = MagicMock()

    genai_mod.Client = Client
    google_pkg.genai = genai_mod

    sys.modules["google"] = google_pkg
    sys.modules["google.genai"] = genai_mod


def test_openai_embedding_returns_vectors() -> None:
    from pydantic import SecretStr

    fake_response = MagicMock()
    fake_response.data = [MagicMock(embedding=[0.1] * 1536)]

    fake_client = MagicMock()
    fake_client.embeddings.create.return_value = fake_response

    with patch.object(settings, "openai_api_key", SecretStr("fake-key")), patch(
        "openai.OpenAI", return_value=fake_client
    ):
        client = EmbeddingClient(provider="openai", model="text-embedding-3-small")
        result = client.embed(["hello"])

    assert isinstance(result, list)
    assert len(result) == 1
    assert len(result[0]) == 1536
    assert isinstance(result[0][0], float)
    assert client.dimension == 1536


def test_gemini_embedding_returns_vectors() -> None:
    from pydantic import SecretStr

    _install_fake_genai()

    fake_embedding = MagicMock()
    fake_embedding.values = [0.2] * 768
    fake_response = MagicMock()
    fake_response.embeddings = [fake_embedding]

    fake_client = MagicMock()
    fake_client.models.embed_content.return_value = fake_response

    with patch.object(settings, "gemini_api_key", SecretStr("fake-key")), patch(
        "google.genai.Client", return_value=fake_client
    ):
        client = EmbeddingClient(provider="gemini", model="text-embedding-004")
        result = client.embed(["hello"])

    assert isinstance(result, list)
    assert len(result) == 1
    assert len(result[0]) == 768
    assert isinstance(result[0][0], float)
    assert client.dimension == 768


def test_unknown_provider_raises() -> None:
    with pytest.raises(ValueError):
        EmbeddingClient(provider="not-a-provider")


def test_missing_openai_key_raises() -> None:
    with patch.object(settings, "openai_api_key", None), pytest.raises(ValueError):
        EmbeddingClient(provider="openai")


def test_missing_gemini_key_raises() -> None:
    with patch.object(settings, "gemini_api_key", None), pytest.raises(ValueError):
        EmbeddingClient(provider="gemini")


def test_get_embedding_client_uses_settings_default() -> None:
    from pydantic import SecretStr

    with patch.object(settings, "embedding_provider", "openai"), patch.object(
        settings, "openai_api_key", SecretStr("fake-key")
    ), patch("openai.OpenAI", return_value=MagicMock()):
        client = get_embedding_client()
        assert isinstance(client, EmbeddingClient)
        assert client.dimension == 1536
