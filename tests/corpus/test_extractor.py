import json
from datetime import datetime, timezone

from writer_profile.corpus.extractor import extract_metadata
from writer_profile.corpus.models import Platform, Post, Tone
from writer_profile.llm import StubLLMClient


def _mk_post(text: str) -> Post:
    return Post(
        id="x",
        platform=Platform.TWITTER,
        text=text,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def test_extract_metadata_parses_json_response():
    payload = json.dumps(
        {
            "topics": ["ai", "evaluation"],
            "tone": "observational",
            "length_bucket": "short",
            "language": "en",
        }
    )
    llm = StubLLMClient(responses=[payload])
    meta = extract_metadata(
        _mk_post("the bottleneck in ai is evaluation"),
        llm=llm,
        model="claude-haiku-4-5-20251001",
    )
    assert meta.topics == ["ai", "evaluation"]
    assert meta.tone is Tone.OBSERVATIONAL
    assert meta.length_bucket == "short"
    assert llm.calls[0].model == "claude-haiku-4-5-20251001"


def test_extract_metadata_tolerates_fenced_json():
    payload = (
        "```json\n"
        '{"topics":["devrel"],"tone":"contrarian","length_bucket":"medium","language":"en"}\n'
        "```"
    )
    llm = StubLLMClient(responses=[payload])
    meta = extract_metadata(
        _mk_post("most devrel writing is wrong"),
        llm=llm,
        model="claude-haiku-4-5-20251001",
    )
    assert meta.tone is Tone.CONTRARIAN
