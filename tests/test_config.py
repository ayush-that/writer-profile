import pytest
from pydantic import ValidationError

from writer_profile.config import Settings


def test_settings_reads_defaults(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("EXA_API_KEY", "exa-test")
    s = Settings()
    assert s.anthropic_api_key.get_secret_value() == "sk-test"
    assert s.gemini_api_key.get_secret_value() == "gemini-test"
    assert s.writing_model.startswith("claude-sonnet")
    assert s.classifier_model.startswith("claude-haiku")
    assert s.embedding_model == "gemini-embedding-2"
    assert s.chroma_path.endswith(".chroma")


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("EXA_API_KEY", "exa-test")
    monkeypatch.setenv("WRITER_PROFILE_WRITING_MODEL", "claude-opus-4-7")
    s = Settings()
    assert s.writing_model == "claude-opus-4-7"


def test_settings_v2_defaults(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("EXA_API_KEY", "exa-test")
    s = Settings()
    assert s.use_multi_critic is True
    assert s.use_diverse_sampling is True
    assert s.embedding_dimensions == 768


def test_settings_requires_exa_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    with pytest.raises(ValidationError, match="EXA_API_KEY"):
        Settings()


def test_settings_loads_exa_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("EXA_API_KEY", "exa-test")
    s = Settings()
    assert s.exa_api_key.get_secret_value() == "exa-test"
