"""3-tier resilient replacement engine (adk-eval-core `apply_replacement`, README 6.2)."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ReplaceResult:
    ok: bool
    content: str
    occurrences: int
    strategy: str
    error: str = ""


def _count_exact(text: str, needle: str) -> int:
    return text.count(needle)


def _flexible_pattern(old: str) -> re.Pattern:
    """Line-by-line match ignoring leading/trailing whitespace per line."""
    lines = [ln.strip() for ln in old.strip("\n").splitlines()]
    parts = [r"[ \t]*" + re.escape(ln) + r"[ \t]*" if ln else r"[ \t]*" for ln in lines]
    return re.compile("\n".join(parts), flags=re.M)


def _regex_pattern(old: str) -> re.Pattern:
    """Tokenize around code delimiters and join with flexible whitespace."""
    tokens = [t for t in re.split(r"(\(|\)|:|\[|\]|\{|\}|>|=|<|\s+)", old) if t and not t.isspace()]
    return re.compile(r"\s*".join(re.escape(t) for t in tokens))


def _reindent(new: str, baseline_indent: str) -> str:
    """Re-indent `new` so its first non-empty line carries `baseline_indent`, preserving relative indents."""
    lines = new.strip("\n").splitlines()
    nonempty = [ln for ln in lines if ln.strip()]
    if not nonempty:
        return new
    common = min(len(ln) - len(ln.lstrip()) for ln in nonempty)
    out = []
    for ln in lines:
        out.append((baseline_indent + ln[common:]) if ln.strip() else "")
    return "\n".join(out)


def apply_replacement(content: str, old: str, new: str, allow_multiple: bool = False) -> ReplaceResult:
    content = content.replace("\r\n", "\n")
    old_n = old.replace("\r\n", "\n")
    new_n = new.replace("\r\n", "\n")
    if old_n == "":
        return ReplaceResult(False, content, 0, "none", "old_string must not be empty")

    # Tier 1: exact
    n = _count_exact(content, old_n)
    if n == 1 or (n > 1 and allow_multiple):
        return ReplaceResult(True, content.replace(old_n, new_n), n, "exact")
    if n > 1:
        return ReplaceResult(False, content, n, "exact", f"old_string matched {n} times; pass allow_multiple=True to replace all")

    # Tier 2: flexible (whitespace-insensitive per line, re-indented replacement)
    pat = _flexible_pattern(old_n)
    matches = list(pat.finditer(content))
    if len(matches) == 1 or (len(matches) > 1 and allow_multiple):
        out = content
        for m in reversed(matches):
            first_line = content[m.start():].split("\n", 1)[0]
            indent = first_line[: len(first_line) - len(first_line.lstrip())]
            out = out[: m.start()] + _reindent(new_n, indent) + out[m.end():]
        return ReplaceResult(True, out, len(matches), "flexible")
    if len(matches) > 1:
        return ReplaceResult(False, content, len(matches), "flexible", f"old_string matched {len(matches)} times (flexible); pass allow_multiple=True")

    # Tier 3: regex tokenized
    try:
        pat = _regex_pattern(old_n)
        matches = list(pat.finditer(content))
    except re.error:
        matches = []
    if len(matches) == 1 or (len(matches) > 1 and allow_multiple):
        out = content
        for m in reversed(matches):
            out = out[: m.start()] + new_n + out[m.end():]
        return ReplaceResult(True, out, len(matches), "regex")
    if len(matches) > 1:
        return ReplaceResult(False, content, len(matches), "regex", f"old_string matched {len(matches)} times (regex); pass allow_multiple=True")
    return ReplaceResult(False, content, 0, "none", "old_string not found in file")
