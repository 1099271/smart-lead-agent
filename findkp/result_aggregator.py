"""结果聚合器

负责合并多个搜索工具的结果，进行去重和排序。
"""

import logging
from typing import List, Dict
from core.schemas import SearchResult

logger = logging.getLogger(__name__)


class ResultAggregator:
    """结果聚合器，用于合并和去重多个搜索工具的结果"""

    def aggregate(
        self, results_map: Dict[str, List[SearchResult]]
    ) -> List[SearchResult]:
        """
        聚合多个查询的结果

        Args:
            results_map: 查询到搜索结果的映射
                       格式：{"query1": [SearchResult, ...], "query2": [SearchResult, ...]}

        Returns:
            聚合后的搜索结果列表
        """
        all_results = []

        # 合并所有查询的结果
        for query_key, results in results_map.items():
            if results:
                all_results.extend(results)
                logger.debug(f"查询 '{query_key}' 返回 {len(results)} 条结果")

        logger.info(f"聚合前共有 {len(all_results)} 条结果")

        # 去重
        deduplicated_results = self.deduplicate(all_results)

        logger.info(f"去重后共有 {len(deduplicated_results)} 条结果")

        # 排序
        sorted_results = self.sort_by_relevance(deduplicated_results)

        return sorted_results

    def deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        对搜索结果进行去重

        去重策略：
        1. URL完全匹配去重
        2. 标题相似度去重（简单字符串匹配）

        Args:
            results: 搜索结果列表

        Returns:
            去重后的搜索结果列表
        """
        if not results:
            return []

        seen_urls = set()
        seen_titles = set()
        deduplicated = []

        for result in results:
            url = str(result.link).lower().rstrip("/")
            title_lower = result.title.lower()

            # URL完全匹配去重
            if url in seen_urls:
                logger.debug(f"跳过重复URL: {url}")
                continue

            # 标题相似度去重（简单判断：如果标题被另一个标题包含，认为是重复）
            is_duplicate_title = False
            for seen_title in seen_titles:
                if title_lower in seen_title or seen_title in title_lower:
                    # 找到对应的已存在结果
                    existing_result = next(
                        (r for r in deduplicated if r.title.lower() == seen_title),
                        None,
                    )
                    if existing_result:
                        # 找到了已存在的结果，比较snippet长度
                        if len(result.snippet) > len(existing_result.snippet):
                            # 替换为snippet更长的版本
                            deduplicated.remove(existing_result)
                            deduplicated.append(result)
                            seen_titles.remove(seen_title)
                            seen_titles.add(title_lower)
                            # 替换后不标记为重复，因为已经用新结果替换了旧结果
                        else:
                            # 保留已存在的结果（snippet更长或相等）
                            # 标记为重复，跳过当前结果
                            is_duplicate_title = True
                    else:
                        # 如果没找到对应的结果，说明数据不一致
                        # 记录警告，但不跳过（可能是真正的重复，也可能是不一致）
                        logger.warning(
                            f"检测到标题相似但未找到对应的已存在结果: "
                            f"seen_title='{seen_title}', current_title='{title_lower}'. "
                            f"跳过标题去重检查，继续处理URL去重。"
                        )
                        # 不设置 is_duplicate_title，继续处理
                    break  # 找到匹配的标题后，退出循环

            if is_duplicate_title:
                logger.debug(f"跳过重复标题: {result.title}")
                continue

            # 添加到结果列表
            seen_urls.add(url)
            seen_titles.add(title_lower)
            deduplicated.append(result)

        return deduplicated

    def sort_by_relevance(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        对搜索结果按相关性排序

        当前策略：保持原始顺序（Serper结果在前，Google结果在后）
        未来可以添加更复杂的排序逻辑（如关键词匹配度、snippet长度等）

        Args:
            results: 搜索结果列表

        Returns:
            排序后的搜索结果列表
        """
        # 当前实现：保持原始顺序
        # 可以后续优化：根据关键词匹配度、snippet质量等排序
        return results
