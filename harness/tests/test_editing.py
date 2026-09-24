from swelite.editing import apply_replacement


def test_exact():
    r = apply_replacement("a\nb\nc\n", "b", "B")
    assert r.ok and r.strategy == "exact" and r.content == "a\nB\nc\n"


def test_exact_multiple_rejected():
    r = apply_replacement("x\nx\n", "x", "y")
    assert not r.ok and r.occurrences == 2


def test_allow_multiple():
    r = apply_replacement("x\nx\n", "x", "y", allow_multiple=True)
    assert r.ok and r.content == "y\ny\n"


def test_flexible_reindents():
    src = "def f():\n    if a:\n        return 1\n"
    r = apply_replacement(src, "if a:\n    return 1", "if a:\n    return 2")
    assert r.ok and r.strategy == "flexible", r
    assert r.content == "def f():\n    if a:\n        return 2\n"


def test_regex_tokens():
    src = "foo( a,  b )\n"
    r = apply_replacement(src, "foo(a, b)", "bar(a, b)")
    assert r.ok and r.strategy == "regex", r
    assert r.content == "bar(a, b)\n"


def test_missing():
    r = apply_replacement("abc", "zzz", "y")
    assert not r.ok and r.occurrences == 0


def test_empty_old():
    assert not apply_replacement("abc", "", "y").ok


def test_crlf_normalised():
    r = apply_replacement("a\r\nb\r\n", "a\nb", "c")
    assert r.ok and r.content == "c\n"
