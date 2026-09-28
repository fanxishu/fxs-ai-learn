from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
_CN_HINTS = ("中国", "国内", "中文", "微信", "小程序", "大陆", "北京", "上海", "广州", "深圳")
_GLOBAL_HINTS = (
    "global",
    "international",
    "overseas",
    "english",
    "official",
    "github",
    "美国",
    "日本",
    "欧洲",
    "海外",
)
_COMPLEX_HINTS = (
    "架构",
    "原理",
    "最佳实践",
    "设计",
    "对比",
    "实践",
    "engineering",
    "harness",
    "protocol",
    "runtime",
    "最新",
    "争议",
)
_CN_DOMAINS = ["juejin.cn", "cloud.tencent.com", "zhihu.com", "aliyun.com", "cnblogs.com"]
_GLOBAL_DOMAINS = ["github.com", "stackoverflow.com", "docs.langchain.com", "wikipedia.org"]

# Tavily country 仅支持实例化时设置；城市级范围通过 query 改写补充。
_REGION_COUNTRY = {
    "cn": "china",
    "global": "united states",
}


@dataclass
class SearchQueryProfile:
    original_input: str
    urls: list[str] = field(default_factory=list)
    rewritten_query: str = ""
    preferred_domains: list[str] = field(default_factory=list)
    excluded_domains: list[str] = field(default_factory=list)
    is_complex: bool = False
    region_hint: str = "neutral"
    country: str | None = None
    suggested_max_results: int = 3


class WebSearchContextService:
    @classmethod
    async def generate_context(cls, user_input: str) -> str:
        if not settings.ENABLE_WEB_SEARCH:
            return ""
        if not settings.TAVILY_API_KEY:
            logger.info("Web search skipped: TAVILY_API_KEY not configured")
            return ""

        profile = cls._build_query_profile(user_input)
        try:
            tools = cls._build_tools(profile)
            timeout_seconds = max(5, min(settings.QUIZ_TASK_TIMEOUT_SECONDS - 5, 45))
            summary = await asyncio.wait_for(
                cls._invoke_agent(profile, tools),
                timeout=timeout_seconds,
            )
            return cls._clip_context(summary)
        except asyncio.TimeoutError:
            logger.warning("Web search context generation timed out")
            return ""
        except Exception as exc:  # noqa: BLE001
            logger.warning("Web search context generation failed: %s", exc)
            return ""

    @staticmethod
    def _extract_urls(user_input: str) -> list[str]:
        return list(dict.fromkeys(_URL_RE.findall(user_input or "")))

    @classmethod
    def _build_query_profile(cls, user_input: str) -> SearchQueryProfile:
        raw = (user_input or "").strip()
        lowered = raw.lower()
        urls = cls._extract_urls(raw)
        is_complex = len(raw) >= 32 or any(token in lowered for token in _COMPLEX_HINTS)
        region_hint = "neutral"
        preferred_domains: list[str] = []
        rewritten_query = raw

        if any(token in raw for token in _CN_HINTS):
            region_hint = "cn"
            preferred_domains = list(_CN_DOMAINS)
            rewritten_query = f"{raw} 中国 国内"
        elif any(token in lowered for token in _GLOBAL_HINTS) or any(
            token in raw for token in ("美国", "日本", "欧洲", "海外")
        ):
            region_hint = "global"
            preferred_domains = list(_GLOBAL_DOMAINS)
            rewritten_query = f"{raw} global official documentation"

        suggested_max_results = (
            max(settings.TAVILY_SEARCH_MAX_RESULTS, 5)
            if is_complex
            else min(settings.TAVILY_SEARCH_MAX_RESULTS, 3)
        )

        return SearchQueryProfile(
            original_input=raw,
            urls=urls,
            rewritten_query=rewritten_query,
            preferred_domains=preferred_domains,
            excluded_domains=[],
            is_complex=is_complex,
            region_hint=region_hint,
            country=_REGION_COUNTRY.get(region_hint),
            suggested_max_results=suggested_max_results,
        )

    @staticmethod
    def _build_tools(profile: SearchQueryProfile | None = None):
        from langchain_tavily import TavilyExtract, TavilySearch

        os.environ["TAVILY_API_KEY"] = settings.TAVILY_API_KEY or ""
        country = profile.country if profile else None
        summary_max = min(settings.TAVILY_SEARCH_MAX_RESULTS, 3)
        deep_max = max(settings.TAVILY_SEARCH_MAX_RESULTS, 5)
        if profile is not None:
            if profile.is_complex:
                deep_max = max(deep_max, profile.suggested_max_results)
            else:
                summary_max = min(summary_max, profile.suggested_max_results)

        # include_answer / include_raw_content 不能在 invocation 时动态改，
        # 因此用两个 TavilySearch 实例分别承担摘要搜索与深度搜索。
        # country 同样只能在实例化时设置，按本次输入地域倾向注入。
        summary_kwargs = {
            "name": "tavily_search_summary",
            "include_answer": "basic",
            "include_raw_content": False,
            "max_results": summary_max,
            "topic": "general",
        }
        deep_kwargs = {
            "name": "tavily_search_deep",
            "include_answer": "advanced",
            "include_raw_content": "markdown",
            "max_results": deep_max,
            "topic": "general",
        }
        if country:
            summary_kwargs["country"] = country
            deep_kwargs["country"] = country

        summary_tool = TavilySearch(**summary_kwargs)
        deep_tool = TavilySearch(**deep_kwargs)
        extract_tool = TavilyExtract(
            name="tavily_extract_basic",
            extract_depth="basic",
            include_images=False,
        )
        return [summary_tool, deep_tool, extract_tool]

    @classmethod
    async def _invoke_agent(cls, profile: SearchQueryProfile, tools) -> str:
        from langchain.agents import create_agent
        from langchain_openai import ChatOpenAI

        system_prompt = (
            "你是出题前的资料检索助手。你的任务不是出题，而是先为后续出题整理可信、最新的知识摘要。\n"
            "系统已为你绑定以下 LangChain 官方 Tavily 工具，请自主决定何时调用、调用几次、如何设置可动态参数：\n"
            "1. tavily_search_summary：关键词/主题的轻量搜索，适合简单常识；结果偏摘要，结果条数较少。\n"
            "2. tavily_search_deep：关键词/主题的深度搜索，适合复杂、新兴、易歧义主题；"
            "结果会包含更完整正文（raw content），结果条数更多。\n"
            "3. tavily_extract_basic：当输入是网址或包含 URL 时优先使用，提取整页正文；"
            "可动态设置 extract_depth（basic/advanced）。\n"
            "调用搜索工具时可动态设置：search_depth、time_range、include_domains、exclude_domains、topic。\n"
            "策略要求：\n"
            "- 有 URL：优先 tavily_extract_basic，必要时再用搜索补充。\n"
            "- 无 URL：用搜索工具；简单主题用 summary，复杂/最新主题用 deep。\n"
            "- 兼顾国内外：按地域倾向改写 query，并设置 include_domains；"
            "城市级意图写进 query（如“北京 政策”），不要幻想不存在的 city 参数。\n"
            "- 控制调用次数，优先一次高质量检索。\n"
            "最终只输出一段中文知识摘要，包含：主题定义、关键概念、适合出题的事实点。不要输出 JSON。"
        )
        model = ChatOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            model=settings.DEEPSEEK_MODEL,
            temperature=0.2,
            timeout=settings.DEEPSEEK_TIMEOUT,
            max_retries=settings.DEEPSEEK_MAX_RETRIES,
        )
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
        )
        user_prompt = cls._build_agent_user_prompt(profile)
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": user_prompt}]}
        )
        return cls._extract_text(result)

    @staticmethod
    def _build_agent_user_prompt(profile: SearchQueryProfile) -> str:
        urls = "\n".join(f"- {url}" for url in profile.urls) or "无"
        preferred_domains = ", ".join(profile.preferred_domains) or "无"
        complexity = "complex" if profile.is_complex else "simple"
        mode = "url_extract" if profile.urls else "keyword_search"
        country = profile.country or "未指定（全球）"
        return (
            f"原始输入：{profile.original_input}\n"
            f"知识获取模式：{mode}\n"
            f"建议检索 query：{profile.rewritten_query}\n"
            f"检测到的 URL：\n{urls}\n"
            f"复杂度：{complexity}\n"
            f"地域倾向：{profile.region_hint}\n"
            f"已按地域预置的 country 增强：{country}\n"
            f"建议结果条数：{profile.suggested_max_results}\n"
            f"优选域名：{preferred_domains}\n"
            "请根据这些信息自主决定调用哪些工具，以及是否设置 include_domains、exclude_domains、"
            "search_depth、time_range、extract_depth 等参数。"
            "若输入含城市名，请把城市写入搜索 query。"
        )

    @staticmethod
    def _extract_text(result) -> str:
        if isinstance(result, str):
            return result.strip()
        if isinstance(result, dict):
            if isinstance(result.get("output"), str):
                return result["output"].strip()
            messages = result.get("messages") or []
            for message in reversed(messages):
                content = getattr(message, "content", None)
                if content is None and isinstance(message, dict):
                    content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
                if isinstance(content, list) and content:
                    try:
                        joined = " ".join(
                            item.get("text", "")
                            for item in content
                            if isinstance(item, dict) and item.get("text")
                        ).strip()
                        if joined:
                            return joined
                    except Exception:
                        continue
        try:
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            return ""

    @staticmethod
    def _clip_context(summary: str) -> str:
        if not isinstance(summary, str):
            return ""
        cleaned = summary.strip()
        if not cleaned:
            return ""
        max_chars = max(200, int(settings.WEB_SEARCH_CONTEXT_MAX_CHARS))
        return cleaned[:max_chars]
