import httpx
from typing import List
import logging

from config import settings
from core.schemas import SearchResult

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SearchModule:
    """
    搜索模块，负责与外部搜索服务（如 Serper.dev）交互。
    """

    def __init__(self, client: httpx.Client):
        """
        初始化搜索模块。

        Args:
            client: 一个 httpx.Client 实例，用于发出HTTP请求。
        """
        self.client = client
        self.api_key = settings.SERPER_API_KEY

    def search_for_company(
        self, company_name: str, search_queries: List[str]
    ) -> List[SearchResult]:
        """
        为指定公司执行一系列搜索查询。

        Args:
            company_name: 目标公司的名称。
            search_queries: 一个包含格式化字符串的列表，其中 `"{company_name}"` 将被替换为公司名称。

        Returns:
            一个 SearchResult 对象的列表，包含了所有查询的聚合结果。
        """
        all_results = []
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

        for query_template in search_queries:
            query = query_template.format(company_name=company_name)
            logger.info(f"Executing search query: {query}")

            try:
                response = self.client.post(
                    "https://google.serper.dev/search",
                    headers=headers,
                    json={"q": query},
                    timeout=10,
                )
                response.raise_for_status()  # 如果响应状态码不是 2xx，则引发异常

                search_data = response.json()

                if "organic" in search_data:
                    for item in search_data["organic"]:
                        all_results.append(
                            SearchResult(
                                title=item.get("title", ""),
                                link=item.get("link", ""),
                                snippet=item.get("snippet", ""),
                            )
                        )
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred while searching for '{query}': {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred for query '{query}': {e}")

        logger.info(f"Found {len(all_results)} results for company '{company_name}'.")
        return all_results
