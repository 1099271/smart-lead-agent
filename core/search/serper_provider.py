"""Serper.dev Search API 提供者"""

import httpx
import logging
from typing import List, Dict, Any, Optional
from core.search.base import BaseSearchProvider
from core.schemas import SearchResult
from config import settings

logger = logging.getLogger(__name__)


class SerperSearchProvider(BaseSearchProvider):
    """
    Serper.dev Search API 提供者实现。
    支持单个查询和批量查询，批量查询时可以将多个查询打包成一个请求发送。
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化 Serper 搜索提供者。

        Args:
            api_key: Serper API Key，如果为 None 则使用配置中的 SERPER_API_KEY
        """
        self.api_key = api_key or settings.SERPER_API_KEY
        self.base_url = "https://google.serper.dev/search"
        self.timeout = 30.0

    async def search(
        self,
        query: str,
        search_type: str = "search",
        location: Optional[str] = None,
        gl: Optional[str] = None,
        hl: Optional[str] = None,
        tbs: Optional[str] = None,
        autocorrect: bool = True,
        page: int = 1,
        **kwargs,
    ) -> List[SearchResult]:
        """
        执行单个搜索查询。

        Args:
            query: 搜索查询字符串
            search_type: 搜索类型，默认 "search"，可选 "image"、"videos" 等
            location: 具体位置，例如 "Vietnam"
            gl: 国家代码，例如 "vn" 表示越南
            hl: 语言代码，例如 "vi" 表示越南语
            tbs: 时间范围，例如 "qdr:d" 表示过去一天
            autocorrect: 是否自动更正，默认 True
            page: 页码，默认 1
            **kwargs: 其他参数

        Returns:
            List[SearchResult]: 搜索结果列表
        """
        query_params = {
            "q": query,
            "autocorrect": autocorrect,
            "page": page,
        }

        if search_type != "search":
            query_params["type"] = search_type
        if location:
            query_params["location"] = location
        if gl:
            query_params["gl"] = gl
        if hl:
            query_params["hl"] = hl
        if tbs:
            query_params["tbs"] = tbs

        # 使用批量接口，但只发送一个查询
        results = await self.search_batch([query_params])
        # 返回第一个查询的结果
        query_key = query_params.get("q", query)
        return results.get(query_key, [])

    async def search_batch(
        self, queries: List[Dict[str, Any]]
    ) -> Dict[str, List[SearchResult]]:
        """
        批量执行多个搜索查询。
        Serper API 支持一次请求发送多个查询，这样可以减少网络开销。

        Args:
            queries: 查询参数字典列表，每个字典包含查询相关的参数
                   例如：[{"q": "query1", "gl": "vn"}, {"q": "query2", "hl": "vi"}]

        Returns:
            Dict[str, List[SearchResult]]: 查询到搜索结果的映射
            格式：{"query1": [SearchResult, ...], "query2": [SearchResult, ...]}
            其中 key 是查询字符串（q 参数的值）
        """
        if not queries:
            return {}

        result_map: Dict[str, List[SearchResult]] = {}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=queries,  # Serper API 支持接收数组
                )
                response.raise_for_status()
                response_data = response.json()

                # 处理响应：Serper API 批量查询返回数组，每个元素对应一个查询的结果
                if isinstance(response_data, list):
                    for idx, query_result in enumerate(response_data):
                        query_key = queries[idx].get("q", f"query_{idx}")
                        organic_results = query_result.get("organic", [])
                        result_map[query_key] = [
                            SearchResult(
                                title=item.get("title", ""),
                                link=item.get("link", ""),
                                snippet=item.get("snippet", ""),
                            )
                            for item in organic_results
                        ]
                else:
                    # 如果返回的不是数组（单个查询的情况），处理单个结果
                    query_key = queries[0].get("q", "query")
                    organic_results = response_data.get("organic", [])
                    result_map[query_key] = [
                        SearchResult(
                            title=item.get("title", ""),
                            link=item.get("link", ""),
                            snippet=item.get("snippet", ""),
                        )
                        for item in organic_results
                    ]

                logger.info(
                    f"Serper 批量搜索完成: {len(queries)} 个查询, "
                    f"共返回 {sum(len(v) for v in result_map.values())} 条结果"
                )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Serper API HTTP 错误: {e.response.status_code} - {e.response.text}"
            )
            # 初始化所有查询的结果为空列表
            for query in queries:
                query_key = query.get("q", "query")
                result_map[query_key] = []
        except httpx.TimeoutException:
            logger.error(f"Serper API 请求超时: {self.timeout}秒")
            # 初始化所有查询的结果为空列表
            for query in queries:
                query_key = query.get("q", "query")
                result_map[query_key] = []
        except Exception as e:
            logger.error(f"Serper API 调用失败: {e}", exc_info=True)
            # 初始化所有查询的结果为空列表
            for query in queries:
                query_key = query.get("q", "query")
                result_map[query_key] = []

        return result_map
