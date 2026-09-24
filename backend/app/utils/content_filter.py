from __future__ import annotations

import os
from typing import Iterable

_DEFAULT_WORDS: tuple[str, ...] = (
    "赌博", "色情", "暴力", "毒品", "恐怖", "分裂", "迷信", "诈骗",
    "六合彩", "时时彩", "赌球", "博彩",
)


class ContentFilter:
    def __init__(self, words: Iterable[str] | None = None, file_path: str | None = None) -> None:
        if words:
            self.words: list[str] = [w.strip() for w in words if w and w.strip()]
        else:
            self.words = list(_DEFAULT_WORDS)
        if file_path and os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                extra = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            self.words.extend(extra)
        self.words = list({w for w in self.words if w})

    def find_all(self, text: str) -> list[str]:
        if not text:
            return []
        return [w for w in self.words if w in text]

    def is_safe(self, text: str) -> bool:
        return len(self.find_all(text)) == 0
