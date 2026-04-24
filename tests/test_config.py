from writer_profile.config import Settings


def test_settings_reads_defaults(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    s = Settings()
    assert s.anthropic_api_key.get_secret_value() == "sk-test"
    assert s.writing_model.startswith("claude-sonnet")
    assert s.classifier_model.startswith("claude-haiku")
    assert s.chroma_path.endswith(".chroma")


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("WRITER_PROFILE_WRITING_MODEL", "claude-opus-4-7")
    s = Settings()
    assert s.writing_model == "claude-opus-4-7"
