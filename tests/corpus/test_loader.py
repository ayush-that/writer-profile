from writer_profile.corpus.loader import load_posts_jsonl
from writer_profile.corpus.models import Platform


def test_load_posts_jsonl_reads_fixture(fixtures_dir):
    posts = load_posts_jsonl(fixtures_dir / "sample_posts.jsonl")
    assert len(posts) == 3
    assert posts[0].id == "t1"
    assert posts[0].platform is Platform.TWITTER
    assert posts[2].platform is Platform.LINKEDIN
    assert "Three things" in posts[2].text


def test_load_posts_jsonl_skips_blank_lines(tmp_path):
    f = tmp_path / "p.jsonl"
    f.write_text(
        '{"id":"a","author":"ali","platform":"twitter","text":"hi","created_at":"2025-01-01T00:00:00Z"}\n'
        "\n"
        '{"id":"b","author":"ali","platform":"twitter","text":"ho","created_at":"2025-01-02T00:00:00Z"}\n'
    )
    posts = load_posts_jsonl(f)
    assert [p.id for p in posts] == ["a", "b"]
