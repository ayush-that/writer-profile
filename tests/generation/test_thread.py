from writer_profile.generation.thread import Thread, split_thread, validate_thread
from writer_profile.platforms.twitter import TwitterConstraint


def test_split_thread_basic():
    raw = (
        "1/ the bottleneck in ai moved from generation to evaluation.\n\n---\n\n"
        "2/ eval is hard because you can't unit-test taste.\n\n---\n\n"
        "3/ we're building eval tooling first, model work second."
    )
    thread = split_thread(raw)
    assert isinstance(thread, Thread)
    assert len(thread.posts) == 3
    assert thread.posts[0].startswith("the bottleneck")
    assert not thread.posts[1].startswith("2/")


def test_split_thread_single_post_returns_single_element_thread():
    raw = "just a single thought no threading"
    thread = split_thread(raw)
    assert len(thread.posts) == 1


def test_validate_thread_reports_per_post_violations():
    c = TwitterConstraint(max_chars=20)
    thread = Thread(posts=["short one", "this one is way way way too long to fit"])
    result = validate_thread(thread, c)
    assert not bool(result)
    assert any("post 2" in i for i in result.issues)


def test_validate_thread_caps_at_5_posts():
    c = TwitterConstraint()
    thread = Thread(posts=["a", "b", "c", "d", "e", "f"])
    result = validate_thread(thread, c, max_posts=5)
    assert not bool(result)
    assert any("thread exceeds 5 posts" in i for i in result.issues)
