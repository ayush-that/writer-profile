from datetime import UTC, datetime

import pytest

from writer_profile.corpus.extractor import extract_metadata, ExtractionError
from writer_profile.corpus.models import Platform, Post
from writer_profile.llm import LLMMessage


class MalformedJSONLLM:
    def complete(self, *, model: str, system: str, messages: list[LLMMessage], max_tokens: int, temperature: float) -> str:
        return "Here is the metadata: {broken json"


def test_extract_metadata_raises_on_malformed_json():
    post = Post(id="1", text="test", platform=Platform.TWITTER, created_at=datetime(2025, 1, 1, tzinfo=UTC), author="ali")
    llm = MalformedJSONLLM()
    with pytest.raises(ExtractionError) as exc:
        extract_metadata(post, llm=llm, model="test")
    assert "Failed to parse" in str(exc.value)
