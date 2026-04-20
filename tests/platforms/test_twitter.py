from writer_profile.platforms.twitter import TwitterConstraint


def test_accepts_lowercase_no_hashtag_under_280():
    c = TwitterConstraint()
    r = c.validate("the bottleneck in ai agents moved from generation to evaluation")
    assert bool(r) is True


def test_rejects_over_280_chars():
    c = TwitterConstraint()
    r = c.validate("x" * 281)
    assert bool(r) is False
    assert any("280" in i for i in r.issues)


def test_rejects_hashtags():
    c = TwitterConstraint()
    r = c.validate("this has #ai which is not allowed")
    assert bool(r) is False
    assert any("hashtag" in i.lower() for i in r.issues)


def test_rejects_uppercase():
    c = TwitterConstraint()
    r = c.validate("This Has Uppercase Letters")
    assert bool(r) is False
    assert any("lowercase" in i.lower() for i in r.issues)


def test_allows_urls_up_to_limit():
    c = TwitterConstraint(max_urls=1)
    ok = c.validate("check this out https://example.com/x")
    bad = c.validate("two links https://a.example/1 and https://b.example/2")
    assert bool(ok) is True
    assert bool(bad) is False
