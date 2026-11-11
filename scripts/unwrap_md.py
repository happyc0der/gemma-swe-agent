"""Unwrap hard-wrapped Markdown paragraphs for renderers that treat single newlines as line breaks (Kaggle Writeups).
Keeps headings, tables and blank lines; joins continuation lines into the paragraph or list item above."""
import re, sys
out = []
for line in open(sys.argv[1]).read().splitlines():
    s = line.strip()
    starts_block = (not s or s.startswith(("#", "|")) or re.match(r"^([-*]|\d+\.)\s", s))
    prev = out[-1] if out else ""
    prev_joinable = prev.strip() and not prev.lstrip().startswith(("#", "|"))
    if not starts_block and prev_joinable:
        out[-1] = prev.rstrip() + " " + s
    else:
        out.append(line.rstrip())
print("\n".join(out))
