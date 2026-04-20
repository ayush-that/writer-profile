from writer_profile.platforms.linkedin import LinkedInConstraint


def test_accepts_short_lines_within_limit():
    c = LinkedInConstraint()
    post = (
        "Three things I changed this quarter:\n\n"
        "1. Stopped writing for search.\n"
        "2. Started writing for skimmers.\n"
        "3. Measured read-through only.\n\n"
        "Readership doubled."
    )
    r = c.validate(post)
    assert bool(r) is True, r.issues


def test_rejects_over_char_limit():
    c = LinkedInConstraint(max_chars=100)
    r = c.validate("x " * 200)
    assert bool(r) is False
    assert any("character" in i.lower() for i in r.issues)


def test_flags_lines_that_exceed_max_words_per_line():
    c = LinkedInConstraint(max_words_per_nonempty_line=9)
    long_line = " ".join(["word"] * 15)
    r = c.validate(long_line)
    assert bool(r) is False
    assert any("words per line" in i.lower() or "exceed" in i.lower() for i in r.issues)


def test_allows_long_post_if_lines_short():
    c = LinkedInConstraint()
    lines = ["a short punchy line." for _ in range(20)]
    r = c.validate("\n\n".join(lines))
    assert bool(r) is True, r.issues
