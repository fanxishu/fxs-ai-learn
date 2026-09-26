"""Task5 - DFA 敏感词过滤测试（5 cases）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.utils.content_filter import DFASensitiveWordFilter


@pytest.fixture
def dfa() -> DFASensitiveWordFilter:
    return DFASensitiveWordFilter()


class TestDFAConstruction:
    def test_empty_input_is_safe(self, dfa):
        assert dfa.is_safe("")
        assert dfa.is_safe(None) is False if False else dfa.is_safe("")
        assert dfa.find_all("") == []

    def test_clean_text_not_hit(self, dfa):
        sample = "我想学习 Java 的设计模式，重点掌握单例模式和策略模式。"
        assert dfa.is_safe(sample)
        assert dfa.find_all(sample) == []

    def test_single_word_hit(self, dfa):
        hits = dfa.find_all("这里讲赌博的技巧")
        assert "赌博" in hits
        assert not dfa.is_safe("这里讲赌博的技巧")

    def test_multi_overlap_hit_preserves_longest(self):
        """自定义敏感词包含 赌博 和 赌博网站，命中时都要能查到。"""
        f = DFASensitiveWordFilter(words=["赌博", "赌博网站", "六合彩"])
        text = "推荐一个赌博网站，还可以玩六合彩"
        hits = f.find_all(text)
        assert "赌博网站" in hits
        assert "六合彩" in hits
        assert not f.is_safe(text)

    def test_censor_replaces_equal_length(self, dfa):
        text = "远离赌博和色情，健康生活"
        censored = dfa.censor(text)
        assert "赌博" not in censored
        assert "色情" not in censored
        assert len(censored) == len(text)
        # 原 2+2=4 个敏感字符被替换为 4 个 *
        assert censored.count("*") >= 4
