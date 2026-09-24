from __future__ import annotations

import re
import html


def strip_html_tags(text: str) -> str:
    clean = re.compile(r"<[^>]+>")
    return clean.sub(" ", text or "")


def clean_user_input(text: str, max_len: int = 500) -> str:
    if text is None:
        return ""
    raw = html.unescape(str(text))
    raw = strip_html_tags(raw)
    raw = raw.replace("\u3000", " ")
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = raw.strip()
    if len(raw) > max_len:
        raw = raw[:max_len].rstrip()
    return raw
