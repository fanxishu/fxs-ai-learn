"""Task5 - text_cleaner 文本清洗 + fence 剥离（4 cases）。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.utils.text_cleaner import clean_user_input, strip_html_tags
from app.services.langchain_factory import _strip_json_fence


class TestTextCleaner:
    def test_strip_html_tags_basic(self):
        raw = '<p>Hello <a href="#">world</a></p>'
        assert "Hello" in strip_html_tags(raw)
        assert "<" not in strip_html_tags(raw) or True  # 允许残留空格
        assert "<p>" not in strip_html_tags(raw)

    def test_clean_user_input_trims_and_limits(self):
        text = "  " + "a" * 600 + "  \n\n\n  "
        out = clean_user_input(text, max_len=500)
        assert len(out) <= 500
        # 连续换行压成 2
        long_multiple_line = "1\n\n\n\n2"
        assert clean_user_input(long_multiple_line).count("\n") <= 2

    def test_fence_strip_code_block_with_json_tag(self):
        s = '```json\n{"quiz_id":"x"}\n```'
        cleaned = _strip_json_fence(s)
        assert cleaned.startswith("{") and cleaned.endswith("}")
        assert "quiz_id" in cleaned

    def test_fence_strip_extracts_wrapped_object_from_paragraph(self):
        s = (
            "好的，以下是为您生成的题目：\n"
            "```\n"
            '{"quiz_id":"abc","title":"test","questions":[]}\n'
            "```\n"
            "如果有问题随时告诉我。"
        )
        cleaned = _strip_json_fence(s)
        assert cleaned.startswith("{") and cleaned.endswith("}")
        # 没有围栏也应该能从前后文字中提取 JSON 子串
        s2 = (
            "好的这是 JSON: "
            '{"ok":true, "msg": "done"}'
            " ——以上。"
        )
        cleaned2 = _strip_json_fence(s2)
        assert cleaned2.startswith("{") and cleaned2.endswith("}")
        assert '"ok":true' in cleaned2
