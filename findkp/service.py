"""FindKP 业务逻辑服务"""

import json
import logging
import asyncio
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from llm import get_llm
from database.repository import Repository
from database.models import CompanyStatus
from schemas.contact import KPInfo
from core.search import SerperSearchProvider, GoogleSearchProvider
from .prompts import EXTRACT_COMPANY_INFO_PROMPT, EXTRACT_CONTACTS_PROMPT
from .search_strategy import SearchStrategy
from .result_aggregator import ResultAggregator

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FindKPService:
    """FindKP 服务类,负责搜索和提取公司 KP 信息（异步版本）"""

    def __init__(self):
        # 使用统一的 LLM 工厂函数（自动路由到 OpenRouter 或直接调用）
        self.llm = get_llm()
        # 初始化多个搜索提供者
        self.serper_provider = SerperSearchProvider()
        self.google_provider = GoogleSearchProvider()
        # 初始化搜索策略和结果聚合器
        self.search_strategy = SearchStrategy()
        self.result_aggregator = ResultAggregator()

    async def extract_with_llm(self, prompt: str) -> Dict:
        """
        使用 LLM 提取结构化信息（异步版本）

        Args:
            prompt: 提示词

        Returns:
            提取的结构化数据
        """
        try:
            # 使用 LangChain V1 的异步调用方式
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"LLM 返回的 JSON 解析失败: {e}")
            logger.debug(f"原始响应: {response.content}")
            return {}
        except Exception as e:
            logger.error(f"LLM 提取信息失败: {e}")
            return {}

    def _get_country_context(self, country: Optional[str]) -> str:
        """
        生成国家上下文信息，用于 Prompt

        Args:
            country: 国家名称

        Returns:
            国家上下文字符串
        """
        if country:
            return f"这是一家位于 {country} 的公司。"
        return ""

    async def _search_with_multiple_providers(
        self, queries: List[Dict[str, Any]]
    ) -> Dict[str, List]:
        """
        使用多个搜索工具并行搜索

        Args:
            queries: 查询参数字典列表

        Returns:
            查询到搜索结果的映射
        """
        # 并行执行多个搜索工具的批量搜索
        try:
            serper_task = self.serper_provider.search_batch(queries)
            google_task = self.google_provider.search_batch(queries)

            serper_results, google_results = await asyncio.gather(
                serper_task, google_task, return_exceptions=True
            )

            # 处理异常情况
            if isinstance(serper_results, Exception):
                logger.warning(f"Serper 搜索失败: {serper_results}")
                serper_results = {}
            if isinstance(google_results, Exception):
                logger.warning(f"Google 搜索失败: {google_results}")
                google_results = {}

            # 合并结果
            merged_results = {}
            all_query_keys = set(serper_results.keys()) | set(google_results.keys())

            for query_key in all_query_keys:
                serper_result = serper_results.get(query_key, [])
                google_result = google_results.get(query_key, [])
                # 合并两个工具的结果
                merged_results[query_key] = serper_result + google_result

            return merged_results

        except Exception as e:
            logger.error(f"并行搜索失败: {e}", exc_info=True)
            # 返回空结果
            return {query.get("q", "query"): [] for query in queries}

    async def find_kps(
        self, company_name: str, country: Optional[str], db: AsyncSession
    ) -> Dict:
        """
        主流程: 查找公司的 KP 联系人（异步版本）

        Args:
            company_name: 公司名称
            country: 国家名称（可选）
            db: 异步数据库会话

        Returns:
            包含公司信息和联系人列表的字典
        """
        repo = Repository(db)

        try:
            # 1. 生成搜索查询
            logger.info(
                f"开始搜索公司信息: {company_name}"
                + (f" ({country})" if country else "")
            )
            company_queries = self.search_strategy.generate_company_queries(
                company_name, country
            )

            # 2. 并行执行多工具搜索
            company_results_map = await self._search_with_multiple_providers(
                company_queries
            )

            # 3. 聚合结果
            aggregated_company_results = self.result_aggregator.aggregate(
                company_results_map
            )

            # 4. 转换为字典格式用于 LLM
            company_results = [
                {"title": r.title, "link": str(r.link), "snippet": r.snippet}
                for r in aggregated_company_results
            ]

            # 5. LLM 提取公司信息
            country_context = self._get_country_context(country)
            company_info = await self.extract_with_llm(
                EXTRACT_COMPANY_INFO_PROMPT.format(
                    country_context=country_context,
                    search_results=json.dumps(company_results, ensure_ascii=False),
                )
            )

            # 2. 创建或获取公司记录
            company = await repo.get_or_create_company(company_name)
            company.domain = company_info.get("domain")
            company.industry = company_info.get("industry")
            company.status = CompanyStatus.processing
            await db.commit()
            await db.refresh(company)
            logger.info(f"公司记录已创建/更新: {company.name}")

            # 6. 搜索采购部门 KP
            logger.info(
                f"搜索采购部门 KP: {company_name}"
                + (f" ({country})" if country else "")
            )
            procurement_queries = self.search_strategy.generate_contact_queries(
                company_name, country, "采购"
            )

            # 并行执行多工具搜索
            procurement_results_map = await self._search_with_multiple_providers(
                procurement_queries
            )

            # 聚合结果
            aggregated_procurement_results = self.result_aggregator.aggregate(
                procurement_results_map
            )

            # 转换为字典格式
            procurement_results = [
                {"title": r.title, "link": str(r.link), "snippet": r.snippet}
                for r in aggregated_procurement_results
            ]

            # LLM 提取采购联系人
            procurement_contacts = await self.extract_with_llm(
                EXTRACT_CONTACTS_PROMPT.format(
                    department="采购",
                    country_context=country_context,
                    search_results=json.dumps(procurement_results, ensure_ascii=False),
                )
            )

            # 确保返回的是列表
            if not isinstance(procurement_contacts, list):
                procurement_contacts = []

            # 7. 搜索销售部门 KP
            logger.info(
                f"搜索销售部门 KP: {company_name}"
                + (f" ({country})" if country else "")
            )
            sales_queries = self.search_strategy.generate_contact_queries(
                company_name, country, "销售"
            )

            # 并行执行多工具搜索
            sales_results_map = await self._search_with_multiple_providers(
                sales_queries
            )

            # 聚合结果
            aggregated_sales_results = self.result_aggregator.aggregate(
                sales_results_map
            )

            # 转换为字典格式
            sales_results = [
                {"title": r.title, "link": str(r.link), "snippet": r.snippet}
                for r in aggregated_sales_results
            ]

            # LLM 提取销售联系人
            sales_contacts = await self.extract_with_llm(
                EXTRACT_CONTACTS_PROMPT.format(
                    department="销售",
                    country_context=country_context,
                    search_results=json.dumps(sales_results, ensure_ascii=False),
                )
            )

            # 确保返回的是列表
            if not isinstance(sales_contacts, list):
                sales_contacts = []

            # 8. 保存联系人
            all_contacts = []
            for contact_data in procurement_contacts + sales_contacts:
                try:
                    # 添加部门信息
                    if contact_data in procurement_contacts:
                        contact_data["department"] = "采购"
                    else:
                        contact_data["department"] = "销售"

                    # 添加来源信息(使用第一个搜索结果的链接)
                    if not contact_data.get("source"):
                        if contact_data["department"] == "采购" and procurement_results:
                            contact_data["source"] = procurement_results[0].get(
                                "link", "N/A"
                            )
                        elif sales_results:
                            contact_data["source"] = sales_results[0].get("link", "N/A")
                        else:
                            contact_data["source"] = "N/A"

                    # 创建 KPInfo 对象并保存
                    kp_info = KPInfo(**contact_data)
                    contact = await repo.create_contact(kp_info, company.id)
                    all_contacts.append(kp_info)
                    logger.info(f"联系人已保存: {contact.email}")
                except Exception as e:
                    logger.error(f"保存联系人失败: {e}, 数据: {contact_data}")
                    continue

            # 9. 更新公司状态
            company.status = CompanyStatus.completed
            await db.commit()
            logger.info(
                f"FindKP 流程完成: {company_name}, 找到 {len(all_contacts)} 个联系人"
            )

            return {
                "company_id": company.id,
                "company_domain": company.domain,
                "contacts": all_contacts,
            }

        except Exception as e:
            logger.error(f"FindKP 流程失败: {e}", exc_info=True)
            # 更新公司状态为失败
            try:
                company = await repo.get_or_create_company(company_name)
                company.status = CompanyStatus.failed
                await db.commit()
            except Exception:
                pass
            raise
