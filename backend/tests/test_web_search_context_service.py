import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.web_search_context_service import WebSearchContextService  # noqa: E402


def test_build_query_profile_detects_url_and_rewrites_region_query():
    profile = WebSearchContextService._build_query_profile(
        "请帮我理解国内 Harness Engineering，顺便参考 https://example.com/article"
    )
    assert profile.urls == ["https://example.com/article"]
    assert profile.region_hint == "cn"
    assert profile.country == "china"
    assert "中国" in profile.rewritten_query
    assert profile.preferred_domains


def test_build_query_profile_marks_complex_topic():
    profile = WebSearchContextService._build_query_profile(
        "Harness Engineering 架构原理、控制平面设计和最佳实践"
    )
    assert profile.is_complex is True
    assert profile.suggested_max_results >= 5


def test_build_query_profile_keyword_mode_has_no_urls():
    profile = WebSearchContextService._build_query_profile("Python 列表推导式基础用法")
    assert profile.urls == []
    assert "url_extract" not in WebSearchContextService._build_agent_user_prompt(profile)
    prompt = WebSearchContextService._build_agent_user_prompt(profile)
    assert "知识获取模式：keyword_search" in prompt


def test_build_query_profile_url_mode_enters_extract_path():
    profile = WebSearchContextService._build_query_profile(
        "请根据 https://docs.python.org/3/tutorial/ 出题"
    )
    assert profile.urls == ["https://docs.python.org/3/tutorial/"]
    prompt = WebSearchContextService._build_agent_user_prompt(profile)
    assert "知识获取模式：url_extract" in prompt
    assert "https://docs.python.org/3/tutorial/" in prompt


def test_build_tools_uses_two_search_instances_with_fixed_raw_content(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    profile = WebSearchContextService._build_query_profile("国内小程序开发实践")
    tools = WebSearchContextService._build_tools(profile)
    names = [tool.name for tool in tools]
    assert names == ["tavily_search_summary", "tavily_search_deep", "tavily_extract_basic"]
    assert tools[0].include_raw_content is False
    assert tools[1].include_raw_content == "markdown"
    assert tools[0].include_answer == "basic"
    assert tools[1].include_answer == "advanced"
    # country 只能实例化设置，复杂/国内主题应预置 china，而不是运行时改 include_raw_content
    assert tools[0].country == "china"
    assert tools[1].country == "china"
    assert tools[0].max_results <= tools[1].max_results


def test_build_tools_complex_topic_does_not_toggle_raw_content_at_runtime(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    complex_profile = WebSearchContextService._build_query_profile(
        "Harness Engineering 架构原理、控制平面设计和最佳实践"
    )
    simple_profile = WebSearchContextService._build_query_profile("什么是 Python")
    complex_tools = WebSearchContextService._build_tools(complex_profile)
    simple_tools = WebSearchContextService._build_tools(simple_profile)
    assert complex_tools[0].include_raw_content is False
    assert simple_tools[0].include_raw_content is False
    assert complex_tools[1].include_raw_content == "markdown"
    assert simple_tools[1].include_raw_content == "markdown"
    assert complex_tools[1].max_results >= simple_tools[0].max_results


def test_region_semantics_affect_query_or_domains():
    cn_profile = WebSearchContextService._build_query_profile("北京 小程序 备案政策解读")
    assert cn_profile.region_hint == "cn"
    assert cn_profile.country == "china"
    assert "中国" in cn_profile.rewritten_query or "北京" in cn_profile.rewritten_query
    assert any("juejin.cn" in d or "zhihu.com" in d for d in cn_profile.preferred_domains)

    global_profile = WebSearchContextService._build_query_profile(
        "LangChain official documentation overseas github"
    )
    assert global_profile.region_hint == "global"
    assert global_profile.country == "united states"
    assert "global" in global_profile.rewritten_query.lower()
    assert any("github.com" in d for d in global_profile.preferred_domains)


@pytest.mark.asyncio
async def test_generate_context_clips_agent_output():
    long_summary = "A" * 5000
    with (
        patch("app.services.web_search_context_service.settings.ENABLE_WEB_SEARCH", True),
        patch("app.services.web_search_context_service.settings.TAVILY_API_KEY", "tvly-test"),
        patch.object(WebSearchContextService, "_build_tools", return_value=[]),
        patch.object(WebSearchContextService, "_invoke_agent", new=AsyncMock(return_value=long_summary)),
    ):
        summary = await WebSearchContextService.generate_context("最新的 Harness Engineering")
    assert len(summary) == 4000


@pytest.mark.asyncio
async def test_generate_context_returns_empty_on_failure():
    with (
        patch("app.services.web_search_context_service.settings.ENABLE_WEB_SEARCH", True),
        patch("app.services.web_search_context_service.settings.TAVILY_API_KEY", "tvly-test"),
        patch.object(WebSearchContextService, "_build_tools", side_effect=RuntimeError("boom")),
    ):
        summary = await WebSearchContextService.generate_context("最新的 Harness Engineering")
    assert summary == ""


@pytest.mark.asyncio
async def test_generate_context_returns_empty_on_timeout():
    with (
        patch("app.services.web_search_context_service.settings.ENABLE_WEB_SEARCH", True),
        patch("app.services.web_search_context_service.settings.TAVILY_API_KEY", "tvly-test"),
        patch("app.services.web_search_context_service.settings.QUIZ_TASK_TIMEOUT_SECONDS", 6),
        patch.object(WebSearchContextService, "_build_tools", return_value=[]),
        patch(
            "app.services.web_search_context_service.asyncio.wait_for",
            new=AsyncMock(side_effect=asyncio.TimeoutError),
        ),
    ):
        summary = await WebSearchContextService.generate_context("最新的 Harness Engineering")
    assert summary == ""


@pytest.mark.asyncio
async def test_generate_context_keyword_and_url_enter_agent_with_matching_profile():
    captured = {}

    async def _fake_invoke(profile, tools):
        captured["profile"] = profile
        captured["tool_names"] = [getattr(t, "name", "") for t in tools]
        return "知识摘要"

    keyword_profile_tools = []
    url_profile_tools = []

    def _fake_build_tools(profile):
        tools = [
            type("T", (), {"name": "tavily_search_summary"})(),
            type("T", (), {"name": "tavily_search_deep"})(),
            type("T", (), {"name": "tavily_extract_basic"})(),
        ]
        if profile.urls:
            url_profile_tools.append(profile)
        else:
            keyword_profile_tools.append(profile)
        return tools

    with (
        patch("app.services.web_search_context_service.settings.ENABLE_WEB_SEARCH", True),
        patch("app.services.web_search_context_service.settings.TAVILY_API_KEY", "tvly-test"),
        patch.object(WebSearchContextService, "_build_tools", side_effect=_fake_build_tools),
        patch.object(
            WebSearchContextService,
            "_invoke_agent",
            new=AsyncMock(side_effect=_fake_invoke),
        ),
    ):
        kw = await WebSearchContextService.generate_context("Python 异步编程入门")
        url = await WebSearchContextService.generate_context("参考 https://example.com/a 出题")

    assert kw == "知识摘要"
    assert url == "知识摘要"
    assert keyword_profile_tools and not keyword_profile_tools[0].urls
    assert url_profile_tools and url_profile_tools[0].urls
    assert captured["tool_names"] == [
        "tavily_search_summary",
        "tavily_search_deep",
        "tavily_extract_basic",
    ]
