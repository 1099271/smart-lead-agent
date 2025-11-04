"""Google Custom Search API 提供者"""

import httpx
import logging
import asyncio
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from core.search.base import BaseSearchProvider
from core.schemas import SearchResult
from config import settings

logger = logging.getLogger(__name__)


class GoogleSearchProvider(BaseSearchProvider):
    """
    Google Custom Search API 提供者实现。
    支持单个查询和批量查询，批量查询时并发执行多个单个查询。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cx: Optional[str] = None,
    ):
        """
        初始化 Google 搜索提供者。

        Args:
            api_key: Google Custom Search API Key，如果为 None 则使用配置中的 GOOGLE_SEARCH_API_KEY
            cx: Google Custom Search Engine ID，如果为 None 则使用配置中的 GOOGLE_SEARCH_CX
        """
        self.api_key = api_key or settings.GOOGLE_SEARCH_API_KEY
        self.cx = cx or settings.GOOGLE_SEARCH_CX
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.timeout = 30.0

        if not self.api_key:
            logger.warning("Google Search API Key 未配置")
        if not self.cx:
            logger.warning("Google Search CX (搜索引擎 ID) 未配置")

    async def search(
        self,
        query: str,
        num: int = 10,
        start: int = 1,
        **kwargs,
    ) -> List[SearchResult]:
        """
        执行单个搜索查询。

        Args:
            query: 搜索查询字符串
            num: 返回结果数量，默认 10，最大 10
            start: 起始索引，默认 1
            **kwargs: 其他参数

        Returns:
            List[SearchResult]: 搜索结果列表
        """
        if not self.api_key or not self.cx:
            logger.error("Google Search API Key 或 CX 未配置，无法执行搜索")
            return []

        params = {
            "q": query,
            "key": self.api_key,
            "cx": self.cx,
            "num": min(num, 10),  # Google API 限制最多 10 条
            "start": start,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}?{urlencode(params)}"
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                items = data.get("items", [])
                results = [
                    SearchResult(
                        title=item.get("title", ""),
                        link=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                    )
                    for item in items
                ]

                logger.info(
                    f"Google Search 查询完成: '{query}', 返回 {len(results)} 条结果"
                )
                return results

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Google Search API HTTP 错误: {e.response.status_code} - {e.response.text}"
            )
            return []
        except httpx.TimeoutException:
            logger.error(f"Google Search API 请求超时: {self.timeout}秒")
            return []
        except Exception as e:
            logger.error(f"Google Search API 调用失败: {e}", exc_info=True)
            return []

    async def search_batch(
        self, queries: List[Dict[str, Any]]
    ) -> Dict[str, List[SearchResult]]:
        """
        批量执行多个搜索查询。
        Google Search API 不支持批量查询，因此使用并发执行多个单个查询。

        Args:
            queries: 查询参数字典列表，每个字典包含查询相关的参数
                   例如：[{"q": "query1", "num": 10}, {"q": "query2", "num": 5}]

        Returns:
            Dict[str, List[SearchResult]]: 查询到搜索结果的映射
            格式：{"query1": [SearchResult, ...], "query2": [SearchResult, ...]}
            其中 key 是查询字符串（q 参数的值）
        """
        if not queries:
            return {}

        # 提取查询字符串和参数
        tasks = []
        query_keys = []

        for query_params in queries:
            query_key = query_params.get("q", "query")
            query_keys.append(query_key)

            # 创建单个查询任务
            task = self.search(
                query=query_key,
                num=query_params.get("num", 10),
                start=query_params.get("start", 1),
            )
            tasks.append(task)

        # 并发执行所有查询
        try:
            results_list = await asyncio.gather(*tasks, return_exceptions=True)

            # 构建结果映射
            result_map: Dict[str, List[SearchResult]] = {}
            for query_key, result in zip(query_keys, results_list):
                if isinstance(result, Exception):
                    logger.error(
                        f"Google Search 批量查询中查询 '{query_key}' 失败: {result}"
                    )
                    result_map[query_key] = []
                else:
                    result_map[query_key] = result

            logger.info(
                f"Google Search 批量搜索完成: {len(queries)} 个查询, "
                f"共返回 {sum(len(v) for v in result_map.values())} 条结果"
            )

            return result_map

        except Exception as e:
            logger.error(f"Google Search 批量查询失败: {e}", exc_info=True)
            # 返回空结果映射
            return {query_params.get("q", "query"): [] for query_params in queries}
