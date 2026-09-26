from __future__ import annotations

import os
from typing import Iterable, Optional


_DEFAULT_WORDS: tuple[str, ...] = (
    "赌博", "色情", "暴力", "毒品", "恐怖", "分裂", "迷信", "诈骗",
    "六合彩", "时时彩", "赌球", "博彩", "黄网", "裸聊", "成人影片",
    "冰毒", "海洛因", "大麻", "摇头丸", "白粉",
    "砍人", "枪杀", "恐怖袭击", "人肉炸弹",
    "台独", "藏独", "疆独", "港独",
    "传销", "非法集资", "套路贷", "高利贷",
    "加微信", "加vx", "加QQ", "加qq", "联系方式", "私聊我",
    "fuck", "shit", "bitch", "傻逼", "操你", "白痴", "笨蛋", "弱智",
)


class _DFANode:
    __slots__ = ("children", "is_end")

    def __init__(self) -> None:
        self.children: dict[str, "_DFANode"] = {}
        self.is_end: bool = False


class DFASensitiveWordFilter:
    """
    方案文档 §15.3 敏感词三层过滤链 — 第二层 后端 DFA 扫描。
    构造 O(sum(len(word)))，单文本扫描 O(len(text))。
    """

    def __init__(
        self,
        words: Iterable[str] | None = None,
        file_path: str | None = None,
    ) -> None:
        self._root = _DFANode()
        words_list: list[str] = []
        if words:
            words_list.extend(w.strip() for w in words if w and w.strip())
        else:
            words_list.extend(_DEFAULT_WORDS)
        if file_path and os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                extra = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]
            words_list.extend(extra)
        # 去重 & 去空
        seen: set[str] = set()
        self.words: list[str] = []
        for w in words_list:
            if not w or w in seen:
                continue
            seen.add(w)
            self.words.append(w)
            self._add_word(w)

    # ------------------------------------------------------------------
    # DFA 构建
    # ------------------------------------------------------------------
    def _add_word(self, word: str) -> None:
        node = self._root
        for ch in word:
            nxt = node.children.get(ch)
            if nxt is None:
                nxt = _DFANode()
                node.children[ch] = nxt
            node = nxt
        node.is_end = True

    # ------------------------------------------------------------------
    # 扫描接口
    # ------------------------------------------------------------------
    def find_all(self, text: str) -> list[str]:
        """扫描 text 中命中的所有敏感词（去重保序）。"""
        if not text:
            return []
        hits: list[str] = []
        seen_hit: set[str] = set()
        n = len(text)
        i = 0
        while i < n:
            node = self._root
            j = i
            matched_end: Optional[int] = None
            matched_word_len = 0
            while j < n:
                ch = text[j]
                nxt = node.children.get(ch)
                if nxt is None:
                    break
                node = nxt
                if node.is_end:
                    matched_end = j
                    matched_word_len = matched_end - i + 1
                j += 1
            if matched_end is not None:
                word = text[i : i + matched_word_len]
                if word not in seen_hit:
                    seen_hit.add(word)
                    hits.append(word)
                i += matched_word_len
            else:
                i += 1
        return hits

    def is_safe(self, text: str) -> bool:
        return len(self.find_all(text)) == 0

    def censor(self, text: str, mask: str = "*") -> str:
        """将命中敏感词替换为等长 mask 字符（用于 UI 展示，不用于后端逻辑）。"""
        if not text:
            return text or ""
        hits = self.find_all(text)
        if not hits:
            return text
        # 按长度倒序，避免短词先替换破坏长词
        hits_sorted = sorted(hits, key=len, reverse=True)
        out = text
        for w in hits_sorted:
            out = out.replace(w, mask * len(w))
        return out


# 兼容旧类名（方案文档中仍叫 ContentFilter，避免破坏已有 import）
ContentFilter = DFASensitiveWordFilter
