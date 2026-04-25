import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from writer_profile.cli import app


def test_scrape_command_exists():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert "scrape" in result.stdout


def test_scrape_dry_run(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test")
    monkeypatch.setenv("EXA_API_KEY", "exa-test")

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "scrape",
            "Ali Ghodsi",
            "--linkedin-handle", "alighodsi",
            "--output-dir", str(tmp_path),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["author_name"] == "Ali Ghodsi"
    assert payload["linkedin_handle"] == "alighodsi"
    assert payload["dry_run"] is True
