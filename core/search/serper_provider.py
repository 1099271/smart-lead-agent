"""Serper.dev Search API 提供者"""

import uuid
import httpx
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from core.search.base import BaseSearchProvider
from core.schemas import SearchResult
from config import settings
from logs import logger


class SerperSearchProvider(BaseSearchProvider):
    """
    Serper.dev Search API 提供者实现。
    支持单个查询和批量查询，批量查询时可以将多个查询打包成一个请求发送。
    """

    def __init__(
        self, api_key: Optional[str] = None, db: Optional[AsyncSession] = None
    ):
        """
        初始化 Serper 搜索提供者。

        Args:
            api_key: Serper API Key，如果为 None 则使用配置中的 SERPER_API_KEY
            db: 可选的数据库会话，用于记录请求和响应数据
        """
        self.api_key = api_key or settings.SERPER_API_KEY
        self.base_url = "https://google.serper.dev/search"
        self.timeout = 30.0
        self.db = db

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
        self, queries: List[Dict[str, Any]], db: Optional[AsyncSession] = None
    ) -> Dict[str, List[SearchResult]]:
        """
        批量执行多个搜索查询。
        Serper API 支持一次请求发送多个查询，这样可以减少网络开销。

        Args:
            queries: 查询参数字典列表，每个字典包含查询相关的参数
                   例如：[{"q": "query1", "gl": "vn"}, {"q": "query2", "hl": "vi"}]
            db: 可选的数据库会话，用于记录请求和响应数据

        Returns:
            Dict[str, List[SearchResult]]: 查询到搜索结果的映射
            格式：{"query1": [SearchResult, ...], "query2": [SearchResult, ...]}
            其中 key 是查询字符串（q 参数的值）
        """
        if not queries:
            return {}

        # 优先使用传入的 db，否则使用实例的 db
        db_session = db or self.db

        result_map: Dict[str, List[SearchResult]] = {}

        # 生成 traceid（仅当有 db 会话时）
        trace_id = None
        if db_session:
            trace_id = str(uuid.uuid4())

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                }

                # 根据 Serper API 文档：
                # - 单个查询：发送单个对象，返回单个对象（包含 searchParameters、organic、credits）
                # - 批量查询：发送对象数组，返回对象数组
                # httpx 的 json 参数会自动序列化 Python 对象（dict/list），无需手动 json.dumps()
                if len(queries) == 1:
                    # 单个查询：发送单个字典对象
                    response = await client.post(
                        self.base_url,
                        headers=headers,
                        json=queries[0],  # httpx 会自动序列化为 JSON
                    )
                else:
                    # 批量查询：发送列表（数组）
                    response = await client.post(
                        self.base_url,
                        headers=headers,
                        json=queries,  # httpx 会自动序列化为 JSON 数组
                    )

                response.raise_for_status()
                response_data = response.json()

                # 记录响应数据到数据库（如果有 db 会话）
                if db_session and trace_id:
                    try:
                        from database.repository import Repository

                        repository = Repository(db_session)

                        # 处理响应：根据返回格式判断是数组还是单个对象
                        if isinstance(response_data, list):
                            # 批量查询返回数组，每个元素对应一个查询的结果
                            # 每个元素格式：{"searchParameters": {...}, "organic": [...], "credits": 1}
                            # 注意：一个 HTTP 请求对应一个 traceid，但可以为每个查询结果创建独立的响应记录
                            for idx, query_result in enumerate(response_data):
                                # 为每个查询结果生成独立的 traceid（因为它们对应不同的查询）
                                current_trace_id = (
                                    str(uuid.uuid4()) if idx > 0 else trace_id
                                )

                                # 记录响应参数
                                await repository.create_serper_response(
                                    current_trace_id, query_result, auto_commit=False
                                )

                                # 记录搜索结果
                                organic_results = query_result.get("organic", [])
                                if organic_results:
                                    await repository.create_serper_organic_results(
                                        current_trace_id,
                                        organic_results,
                                        auto_commit=False,
                                    )
                        else:
                            # 单个查询返回对象，包含 searchParameters、organic、credits 等字段
                            # 格式：{"searchParameters": {...}, "organic": [...], "credits": 1}
                            # 记录响应参数
                            await repository.create_serper_response(
                                trace_id, response_data, auto_commit=False
                            )

                            # 记录搜索结果
                            organic_results = response_data.get("organic", [])
                            if organic_results:
                                await repository.create_serper_organic_results(
                                    trace_id, organic_results, auto_commit=False
                                )
                    except Exception as e:
                        # 记录失败不影响主流程
                        logger.error(
                            f"记录 Serper API 响应数据失败: {e}", exc_info=True
                        )

                # 处理响应：根据返回格式判断是数组还是单个对象
                if isinstance(response_data, list):
                    # 批量查询返回数组，每个元素对应一个查询的结果
                    # 每个元素格式：{"searchParameters": {...}, "organic": [...], "credits": 1}
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
                    # 单个查询返回对象，包含 searchParameters、organic、credits 等字段
                    # 格式：{"searchParameters": {...}, "organic": [...], "credits": 1}
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
