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

    async def _search_contacts_parallel(
        self,
        company_name_en: str,
        company_name_local: str,
        country: Optional[str],
        department: str,
        country_context: str,
    ) -> Dict[str, List]:
        """
        并行搜索联系人（采购或销售）

        Args:
            company_name_en: 公司英文名称
            company_name_local: 公司本地名称
            country: 国家名称（可选）
            department: 部门名称（"采购" 或 "销售"）
            country_context: 国家上下文字符串

        Returns:
            包含 contacts 和 results 的字典
        """
        logger.info(
            f"搜索{department}部门 KP: {company_name_en}"
            + (f" ({country})" if country else "")
        )

        # 生成查询
        queries = self.search_strategy.generate_contact_queries(
            company_name_en, company_name_local, country, department
        )

        # 并行执行多工具搜索
        results_map = await self._search_with_multiple_providers(queries)

        # 聚合结果
        aggregated_results = self.result_aggregator.aggregate(results_map)

        # 转换为字典格式
        results = [
            {"title": r.title, "link": str(r.link), "snippet": r.snippet}
            for r in aggregated_results
        ]

        # LLM 提取联系人
        contacts = await self.extract_with_llm(
            EXTRACT_CONTACTS_PROMPT.format(
                department=department,
                country_context=country_context,
                search_results=json.dumps(results, ensure_ascii=False),
            )
        )

        # 确保返回的是列表
        if not isinstance(contacts, list):
            contacts = []

        logger.info(f"找到 {len(contacts)} 个{department}部门联系人")

        return {"contacts": contacts, "results": results}

    async def find_kps(
        self,
        company_name_en: str,
        company_name_local: str,
        country: Optional[str],
        db: AsyncSession,
    ) -> Dict:
        """
        主流程: 查找公司的 KP 联系人（异步版本）

        Args:
            company_name_en: 公司名称英文
            company_name_local: 公司名称本地
            country: 国家名称（可选）
            db: 异步数据库会话

        Returns:
            包含公司信息和联系人列表的字典
        """
        repo = Repository(db)

        try:
            # 1. 生成搜索查询
            logger.info(
                f"开始搜索公司信息: {company_name_local}"
                + (f" ({country})" if country else "")
            )
            company_queries = self.search_strategy.generate_company_queries(
                company_name_en, company_name_local, country
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
            company = await repo.get_or_create_company(company_name_en)
            company.domain = company_info.get("domain")
            company.industry = company_info.get("industry")
            company.positioning = company_info.get("positioning")
            company.brief = company_info.get("brief")
            company.status = CompanyStatus.processing
            await db.commit()
            await db.refresh(company)
            logger.info(f"公司记录已创建/更新: {company.name}")

            # 6. 并行搜索采购和销售部门 KP
            logger.info(
                f"并行搜索采购和销售部门 KP: {company_name_en}"
                + (f" ({country})" if country else "")
            )

            # 并行执行采购和销售搜索
            procurement_task = self._search_contacts_parallel(
                company_name_en, company_name_local, country, "采购", country_context
            )
            sales_task = self._search_contacts_parallel(
                company_name_en, company_name_local, country, "销售", country_context
            )

            procurement_result, sales_result = await asyncio.gather(
                procurement_task, sales_task, return_exceptions=True
            )

            # 处理异常情况
            if isinstance(procurement_result, Exception):
                logger.error(f"采购部门搜索失败: {procurement_result}")
                procurement_result = {"contacts": [], "results": []}
            if isinstance(sales_result, Exception):
                logger.error(f"销售部门搜索失败: {sales_result}")
                sales_result = {"contacts": [], "results": []}

            procurement_contacts = procurement_result.get("contacts", [])
            procurement_results = procurement_result.get("results", [])
            sales_contacts = sales_result.get("contacts", [])
            sales_results = sales_result.get("results", [])

            # 确保返回的是列表
            if not isinstance(procurement_contacts, list):
                procurement_contacts = []
            if not isinstance(sales_contacts, list):
                sales_contacts = []

            # 8. 批量保存联系人
            all_contacts = []
            contacts_to_save = []

            # 准备联系人数据
            for contact_data in procurement_contacts:
                try:
                    contact_data["department"] = "采购"
                    if not contact_data.get("source") and procurement_results:
                        contact_data["source"] = procurement_results[0].get(
                            "link", "N/A"
                        )
                    elif not contact_data.get("source"):
                        contact_data["source"] = "N/A"
                    contacts_to_save.append(contact_data)
                except Exception as e:
                    logger.error(f"准备采购联系人数据失败: {e}, 数据: {contact_data}")
                    continue

            for contact_data in sales_contacts:
                try:
                    contact_data["department"] = "销售"
                    if not contact_data.get("source") and sales_results:
                        contact_data["source"] = sales_results[0].get("link", "N/A")
                    elif not contact_data.get("source"):
                        contact_data["source"] = "N/A"
                    contacts_to_save.append(contact_data)
                except Exception as e:
                    logger.error(f"准备销售联系人数据失败: {e}, 数据: {contact_data}")
                    continue

            # 批量保存
            if contacts_to_save:
                logger.info(f"批量保存 {len(contacts_to_save)} 个联系人...")
                try:
                    # 转换为 KPInfo 对象列表
                    kp_info_list = [
                        KPInfo(**contact_data) for contact_data in contacts_to_save
                    ]
                    # 批量保存
                    saved_contacts = await repo.create_contacts_batch(
                        kp_info_list, company.id
                    )
                    all_contacts = kp_info_list
                    logger.info(f"成功保存 {len(saved_contacts)} 个联系人")
                except Exception as e:
                    logger.error(f"批量保存联系人失败: {e}", exc_info=True)
                    # 降级为单个保存
                    logger.info("降级为单个保存模式...")
                    for contact_data in contacts_to_save:
                        try:
                            kp_info = KPInfo(**contact_data)
                            contact = await repo.create_contact(kp_info, company.id)
                            all_contacts.append(kp_info)
                            logger.debug(f"联系人已保存: {contact.email}")
                        except Exception as e2:
                            logger.error(f"保存联系人失败: {e2}, 数据: {contact_data}")
                            continue

            # 9. 更新公司状态
            company.status = CompanyStatus.completed
            await db.commit()
            logger.info(
                f"FindKP 流程完成: {company_name_en}, 找到 {len(all_contacts)} 个联系人"
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
                company = await repo.get_or_create_company(company_name_en)
                company.status = CompanyStatus.failed
                await db.commit()
            except Exception:
                pass
            raise
