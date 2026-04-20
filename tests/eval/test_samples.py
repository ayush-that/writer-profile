from pathlib import Path

from writer_profile.corpus.models import Platform
from writer_profile.eval.samples import ARCHETYPE_IDEAS, write_samples_sheet


def test_archetypes_cover_five_topic_types():
    types = {idea.topic for idea in ARCHETYPE_IDEAS}
    assert len(ARCHETYPE_IDEAS) == 5
    assert len(types) == 5


def test_write_samples_sheet_produces_markdown(tmp_path: Path):
    samples = [
        ("product launch: new feature", "Shipping X today. it's fast."),
        ("acquisition", "welcome to the family, team X."),
    ]
    path = write_samples_sheet(
        root=tmp_path,
        author="ali",
        platform=Platform.TWITTER,
        samples=samples,
    )
    assert path.exists()
    content = path.read_text()
    assert "# ali — twitter" in content
    assert "product launch: new feature" in content
    assert "Shipping X today" in content
    assert "Voice accuracy (1-5):" in content
    assert "Post quality (1-5):" in content
    assert "Naturalness (1-5):" in content
