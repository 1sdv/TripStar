"""You.com 联网搜索 / 深度研究服务封装

提供两个能力，作为地图数据（高德/Google）之外的"实时联网信息"补充:
  - search   → You.com Search API   (https://ydc-index.io/v1/search)
  - research → You.com Research API (https://api.you.com/v1/research)

设计要求（保证可在不安装 hello_agents / 不启动完整应用的情况下被单元测试）:
  - 只依赖 httpx，不依赖 config / hello_agents / 应用其它模块。
  - 任何异常路径都不抛出未捕获异常，只返回清晰的中文提示字符串。
  - 任何返回值都绝不包含 API Key 原文（即便发生异常）。
"""

from typing import Any, Dict, List, Optional, Tuple

import httpx


class YoucomService:
    """You.com 联网搜索 / 深度研究服务封装类"""

    SEARCH_URL = "https://ydc-index.io/v1/search"
    RESEARCH_URL = "https://api.you.com/v1/research"

    DEFAULT_COUNT = 5
    MAX_COUNT = 20
    DEFAULT_TIMEOUT = 15.0

    def __init__(self, api_key: str, timeout: float = DEFAULT_TIMEOUT):
        self.api_key = api_key or ""
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        """关闭 HTTP 客户端连接池。"""
        self._client.close()

    # ======================== 联网搜索 ========================

    def search(
        self,
        query: Any,
        count: Any = DEFAULT_COUNT,
        freshness: Optional[str] = None,
        country: Optional[str] = None,
    ) -> str:
        """You.com 实时联网搜索。

        Args:
            query: 搜索关键词
            count: 返回结果条数（默认 5，最大 20，非法值回退默认值）
            freshness: 时间范围过滤（可选，原样透传给 API）
            country: 国家/地区过滤（可选，原样透传给 API）

        Returns:
            供 Agent 阅读的编号结构化文本；出错或未配置 Key 时返回清晰提示，绝不抛出异常。
        """
        if not self.api_key:
            return "未配置 You.com API Key，无法使用联网搜索"

        q = self._normalize_query(query)
        if not q:
            return "搜索关键词不能为空"

        params: Dict[str, Any] = {
            "query": q,
            "count": self._normalize_count(count),
        }
        if freshness:
            params["freshness"] = freshness
        if country:
            params["country"] = country

        data, err = self._call(
            "GET",
            self.SEARCH_URL,
            "搜索",
            headers={"X-API-Key": self.api_key},
            params=params,
        )
        if err:
            return self._scrub(err)
        return self._scrub(self._format_search_result(data))

    # ======================== 深度研究 ========================

    def research(self, query: Any) -> str:
        """You.com 深度研究（复杂行程/多来源综合，附引用）。

        Args:
            query: 研究主题/问题

        Returns:
            研究结论 + 编号引用来源；出错或未配置 Key 时返回清晰提示，绝不抛出异常。
        """
        if not self.api_key:
            return "未配置 You.com API Key，无法使用深度研究"

        q = self._normalize_query(query)
        if not q:
            return "研究主题不能为空"

        body = {"input": q, "research_effort": "lite"}

        data, err = self._call(
            "POST",
            self.RESEARCH_URL,
            "深度研究",
            headers={"X-API-Key": self.api_key},
            json=body,
        )
        if err:
            return self._scrub(err)
        return self._scrub(self._format_research_result(data))

    # ======================== 内部工具 ========================

    def _call(
        self, method: str, url: str, label: str, **kwargs: Any
    ) -> Tuple[Optional[Any], Optional[str]]:
        """执行一次 HTTP 请求，返回 (data, error_message)，永不抛出异常。"""
        try:
            if method == "GET":
                resp = self._client.get(url, **kwargs)
            else:
                resp = self._client.post(url, **kwargs)
            resp.raise_for_status()
            data = resp.json()
            return data, None
        except httpx.TimeoutException:
            return None, f"You.com {label}请求超时，请稍后重试"
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if e.response is not None else 0
            return None, self._map_http_error(status_code, label)
        except httpx.RequestError as e:
            return None, f"You.com {label}网络请求失败: {type(e).__name__}"
        except ValueError:
            # 含 json.JSONDecodeError（响应体不是合法 JSON 或为空）
            return None, f"You.com {label}返回数据解析失败"
        except Exception as e:
            return None, f"You.com {label}调用异常: {type(e).__name__}"

    @staticmethod
    def _map_http_error(status_code: int, label: str) -> str:
        mapping = {
            401: "You.com API Key 无效或已过期",
            403: "You.com 请求被拒绝，请检查请求地址或权限",
            422: "You.com 请求参数有误",
            429: "You.com 请求过于频繁，请稍后重试",
        }
        if status_code in mapping:
            return f"You.com {label}失败: {mapping[status_code]} ({status_code})"
        if 500 <= status_code < 600:
            return f"You.com {label}失败: 服务暂时不可用 ({status_code})，请稍后重试"
        return f"You.com {label}失败: 返回错误状态码 {status_code}"

    @staticmethod
    def _normalize_query(query: Any) -> str:
        if query is None:
            return ""
        if not isinstance(query, str):
            try:
                query = str(query)
            except Exception:
                return ""
        return query.strip()

    @classmethod
    def _normalize_count(cls, count: Any) -> int:
        try:
            n = int(count)
        except (TypeError, ValueError):
            return cls.DEFAULT_COUNT
        if n <= 0:
            return cls.DEFAULT_COUNT
        if n > cls.MAX_COUNT:
            return cls.MAX_COUNT
        return n

    def _scrub(self, text: str) -> str:
        """兜底防护：确保返回文本中绝不出现 API Key 原文。"""
        if self.api_key and text and self.api_key in text:
            return text.replace(self.api_key, "[REDACTED]")
        return text

    @staticmethod
    def _format_item(idx: int, item: Any) -> str:
        if not isinstance(item, dict):
            return ""
        title = (item.get("title") or "").strip() if isinstance(item.get("title"), str) else ""
        url = (item.get("url") or "").strip() if isinstance(item.get("url"), str) else ""
        description = (
            (item.get("description") or "").strip()
            if isinstance(item.get("description"), str)
            else ""
        )
        raw_snippets = item.get("snippets")
        snippets: List[str] = raw_snippets if isinstance(raw_snippets, list) else []
        clean_snippets = [s.strip() for s in snippets if isinstance(s, str) and s.strip()]

        if not title and not url and not description and not clean_snippets:
            return ""

        lines = [f"{idx}. {title or '(无标题)'}"]
        if url:
            lines.append(f"   链接: {url}")
        if description:
            lines.append(f"   简介: {description}")
        for s in clean_snippets:
            lines.append(f"   摘要: {s}")
        return "\n".join(lines)

    @classmethod
    def _format_search_result(cls, data: Any) -> str:
        if not isinstance(data, dict):
            return "未找到相关信息"

        results = data.get("results")
        if not isinstance(results, dict):
            results = {}

        raw_web = results.get("web")
        web: List[Any] = raw_web if isinstance(raw_web, list) else []
        raw_news = results.get("news")
        news: List[Any] = raw_news if isinstance(raw_news, list) else []

        blocks: List[str] = []
        idx = 1
        for item in web:
            block = cls._format_item(idx, item)
            if block:
                blocks.append(block)
                idx += 1

        if news:
            news_blocks: List[str] = []
            for item in news:
                block = cls._format_item(idx, item)
                if block:
                    news_blocks.append(block)
                    idx += 1
            if news_blocks:
                blocks.append("相关资讯:")
                blocks.extend(news_blocks)

        if not blocks:
            return "未找到相关信息"
        return "\n".join(blocks)

    @staticmethod
    def _format_research_result(data: Any) -> str:
        if not isinstance(data, dict):
            return "未获取到研究结果"

        output = data.get("output")
        content = ""
        sources: List[Any] = []
        if isinstance(output, dict):
            raw_content = output.get("content")
            content = raw_content.strip() if isinstance(raw_content, str) else ""
            raw_sources = output.get("sources")
            sources = raw_sources if isinstance(raw_sources, list) else []

        lines: List[str] = [content if content else "未获取到研究内容"]

        valid_sources: List[Tuple[str, str]] = []
        for s in sources:
            if isinstance(s, dict):
                url = s.get("url") if isinstance(s.get("url"), str) else ""
                title = s.get("title") if isinstance(s.get("title"), str) else ""
                url = url.strip()
                title = title.strip()
                if url or title:
                    valid_sources.append((title, url))
            elif isinstance(s, str) and s.strip():
                valid_sources.append(("", s.strip()))

        if valid_sources:
            lines.append("")
            lines.append("参考来源:")
            for i, (title, url) in enumerate(valid_sources, start=1):
                if title and url:
                    lines.append(f"{i}. {title} - {url}")
                else:
                    lines.append(f"{i}. {title or url}")

        return "\n".join(lines)
