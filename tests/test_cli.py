import json
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from writer_profile.cli import app
from writer_profile.corpus.models import Platform, Post


@pytest.fixture
def sample_jsonl(tmp_path):
    p = tmp_path / "posts.jsonl"
    post = Post(
        id="p1",
        author="ali",
        platform=Platform.TWITTER,
        text="ai evaluation is the new bottleneck",
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    p.write_text(post.model_dump_json())
    return p


def test_cli_help_lists_commands():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "generate" in result.stdout
    assert "revoice" in result.stdout
    assert "profile" in result.stdout
    assert "samples" in result.stdout
    assert "evaluate" in result.stdout


def test_cli_generate_dry_run(tmp_path, sample_jsonl, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("WRITER_PROFILE_CHROMA_PATH", str(tmp_path / "c"))
    monkeypatch.setenv("WRITER_PROFILE_PROFILES_PATH", str(tmp_path / "profiles"))

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "generate",
            "--author",
            "ali",
            "--platform",
            "twitter",
            "--topic",
            "ai evaluation",
            "--angle",
            "generation is easy, eval is hard",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["author"] == "ali"
    assert payload["platform"] == "twitter"
    assert payload["topic"] == "ai evaluation"
    assert payload["dry_run"] is True
