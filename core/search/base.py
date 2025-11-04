"""搜索提供者抽象基类"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from core.schemas import SearchResult


class BaseSearchProvider(ABC):
    """
    搜索提供者的抽象基类。
    所有具体的搜索实现（Serper、Google等）都应该继承这个类。
    """

    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """
        执行单个搜索查询的抽象方法。

        Args:
            query: 搜索查询字符串
            **kwargs: 其他搜索参数（由具体实现决定）

        Returns:
            List[SearchResult]: 搜索结果列表
        """
        pass

    @abstractmethod
    async def search_batch(
        self, queries: List[Dict[str, Any]]
    ) -> Dict[str, List[SearchResult]]:
        """
        批量执行多个搜索查询的抽象方法。

        Args:
            queries: 查询参数字典列表，每个字典包含查询相关的参数
                   例如：[{"q": "query1"}, {"q": "query2"}]
                   返回字典的 key 可以是查询字符串或查询标识符

        Returns:
            Dict[str, List[SearchResult]]: 查询到搜索结果的映射
            格式：{"query1": [SearchResult, ...], "query2": [SearchResult, ...]}
        """
        pass
