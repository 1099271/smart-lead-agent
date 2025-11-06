"""FindKP 业务逻辑服务"""

import json
import re
import asyncio
from typing import List, Dict, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from llm import get_llm
from database.repository import Repository
from database.models import CompanyStatus, Company
from schemas.contact import KPInfo, ContactsResponse, CompanyInfoResponse
from core.search import SerperSearchProvider, GoogleSearchProvider
from .prompts import EXTRACT_COMPANY_INFO_PROMPT, EXTRACT_CONTACTS_PROMPT
from .search_strategy import SearchStrategy
from .email_search_strategy import EmailSearchStrategy
from .result_aggregator import ResultAggregator
from config import settings
from logs import logger, log_llm_request, log_llm_response


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
        self.email_search_strategy = EmailSearchStrategy()
        self.result_aggregator = ResultAggregator()

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        从文本中提取 JSON 内容，处理被 markdown 代码块包裹的情况

        使用多种策略：
        1. 提取 markdown 代码块中的内容
        2. 查找 JSON 对象或数组
        3. 验证提取的内容是否为有效 JSON

        Args:
            text: 可能包含 JSON 的文本

        Returns:
            提取出的 JSON 字符串，如果未找到则返回 None
        """
        if not text or not text.strip():
            return None

        # 策略1: 提取 markdown 代码块中的 JSON
        code_block_patterns = [
            r"```json\s*\n(.*?)\n```",  # ```json ... ```
            r"```\s*\n(.*?)\n```",  # ``` ... ```
        ]

        for pattern in code_block_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                cleaned = match.strip()
                if cleaned:
                    try:
                        # 验证是否是有效的 JSON
                        json.loads(cleaned)
                        return cleaned
                    except json.JSONDecodeError:
                        continue

        # 策略2: 查找 JSON 对象 {} 或数组 []
        # 使用括号匹配来找到完整的 JSON 结构
        candidates = []

        # 查找 JSON 对象
        start_idx = text.find("{")
        if start_idx != -1:
            depth = 0
            for i in range(start_idx, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start_idx : i + 1]
                        try:
                            json.loads(candidate)
                            candidates.append(candidate)
                        except json.JSONDecodeError:
                            pass
                        break

        # 查找 JSON 数组
        start_idx = text.find("[")
        if start_idx != -1:
            depth = 0
            for i in range(start_idx, len(text)):
                if text[i] == "[":
                    depth += 1
                elif text[i] == "]":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start_idx : i + 1]
                        try:
                            json.loads(candidate)
                            candidates.append(candidate)
                        except json.JSONDecodeError:
                            pass
                        break

        # 返回最长的有效 JSON（可能是最完整的）
        if candidates:
            return max(candidates, key=len)

        # 策略3: 如果都没找到，尝试直接解析整个文本
        # 这可能是一个纯 JSON 字符串
        cleaned_text = text.strip()
        if cleaned_text:
            try:
                json.loads(cleaned_text)
                return cleaned_text
            except json.JSONDecodeError:
                pass

        return None

    def _fix_common_json_issues(self, json_str: str) -> str:
        """
        修复常见的 JSON 格式问题

        Args:
            json_str: JSON 字符串

        Returns:
            修复后的 JSON 字符串
        """
        # 移除 BOM 标记
        json_str = json_str.lstrip("\ufeff")

        # 修复单引号为双引号（简单情况）
        json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
        json_str = re.sub(r":\s*'([^']*)'", r': "\1"', json_str)

        # 修复尾随逗号
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)

        # 移除注释（JSON 不支持注释）
        json_str = re.sub(r"//.*?\n", "\n", json_str)
        json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)

        return json_str.strip()

    def _parse_json_with_fallback(
        self, content: str, expected_type: type = dict
    ) -> Optional[Union[Dict, List]]:
        """
        解析 JSON，支持多种容错机制

        Args:
            content: 原始内容
            expected_type: 期望的类型（dict 或 list）

        Returns:
            解析后的 JSON 对象或列表，失败返回 None
        """
        if not content or not content.strip():
            logger.error("JSON 解析失败: 内容为空")
            return None

        # 步骤1: 提取 JSON 内容
        json_str = self._extract_json_from_text(content)
        if not json_str:
            logger.warning(f"无法从内容中提取 JSON，原始内容: {content[:200]}")
            json_str = content.strip()

        # 步骤2: 修复常见问题
        json_str = self._fix_common_json_issues(json_str)

        # 步骤3: 尝试解析
        attempts = [
            json_str,  # 原始修复后的字符串
            json_str.replace("\n", " ").replace("\r", ""),  # 移除换行
        ]

        for attempt in attempts:
            try:
                result = json.loads(attempt)
                # 验证类型
                if isinstance(result, expected_type):
                    return result
                elif isinstance(result, dict) and expected_type == list:
                    # 如果期望列表但得到字典，尝试提取数组
                    if "contacts" in result:
                        return result.get("contacts", [])
                    return []
                elif isinstance(result, list) and expected_type == dict:
                    # 如果期望字典但得到列表，返回包装后的字典
                    return {"contacts": result}
                else:
                    logger.warning(
                        f"JSON 类型不匹配: 期望 {expected_type.__name__}, "
                        f"实际 {type(result).__name__}"
                    )
                    return result
            except json.JSONDecodeError as e:
                continue

        # 所有尝试都失败
        logger.error(f"JSON 解析失败，已尝试多种方法")
        logger.debug(f"最终尝试的内容: {json_str[:500]}")
        return None

    async def extract_contacts_with_llm(self, prompt: str) -> Dict:
        """
        使用 LLM 提取联系人信息（结构化输出版本）

        使用 LangChain 的 with_structured_output 确保返回结构化数据，
        避免 JSON 解析失败的问题。

        Args:
            prompt: 提示词

        Returns:
            包含 contacts 列表的字典格式
        """
        try:
            # 记录 LLM 请求
            messages = [{"role": "user", "content": prompt}]
            model_name = (
                getattr(self.llm, "model_name", None)
                or getattr(self.llm, "model", None)
                or "unknown"
            )
            request_log_path = log_llm_request(
                messages=messages,
                model=model_name,
                task_type="extract_contacts",
            )

            # 使用结构化输出，直接返回 Pydantic 模型
            structured_llm = self.llm.with_structured_output(ContactsResponse)
            result = await structured_llm.ainvoke(messages)

            # 记录 LLM 响应
            if hasattr(result, "model_dump"):
                response_content = str(result.model_dump())
            elif hasattr(result, "contacts"):
                response_content = f"Extracted {len(result.contacts)} contacts"
            else:
                response_content = str(result)

            log_llm_response(
                response_content=response_content,
                request_log_path=request_log_path,
                model=model_name,
                task_type="extract_contacts",
            )

            # result 已经是 ContactsResponse 实例，直接转换
            if isinstance(result, ContactsResponse):
                # 转换为字典格式，保持向后兼容
                contacts_dict = []
                for contact in result.contacts:
                    contact_dict = contact.model_dump(exclude_none=True)
                    # 确保所有字段都存在
                    contacts_dict.append(
                        {
                            "full_name": contact_dict.get("full_name"),
                            "email": contact_dict.get("email"),
                            "role": contact_dict.get("role"),
                            "linkedin_url": contact_dict.get("linkedin_url"),
                            "twitter_url": contact_dict.get("twitter_url"),
                            "confidence_score": contact_dict.get(
                                "confidence_score", 0.0
                            ),
                        }
                    )

                logger.info(f"使用结构化输出成功提取 {len(contacts_dict)} 个联系人")
                return {"contacts": contacts_dict}
            else:
                logger.warning(f"LLM 返回了意外的类型: {type(result)}")
                return {"contacts": []}

        except Exception as e:
            logger.error(f"LLM 结构化输出提取联系人失败: {e}", exc_info=True)
            # 降级到旧的 JSON 解析方法
            logger.info("降级到旧的 JSON 解析方法")
            return await self.extract_with_llm(prompt)

    async def extract_company_info_with_llm(self, prompt: str) -> Dict:
        """
        使用 LLM 提取公司信息（结构化输出版本）

        使用 LangChain 的 with_structured_output 确保返回结构化数据，
        避免 JSON 解析失败的问题。

        Args:
            prompt: 提示词

        Returns:
            包含 domain, industry, positioning, brief 的字典格式
        """
        try:
            # 记录 LLM 请求
            messages = [{"role": "user", "content": prompt}]
            model_name = (
                getattr(self.llm, "model_name", None)
                or getattr(self.llm, "model", None)
                or "unknown"
            )
            request_log_path = log_llm_request(
                messages=messages,
                model=model_name,
                task_type="extract_company_info",
            )

            # 使用结构化输出，直接返回 Pydantic 模型
            structured_llm = self.llm.with_structured_output(CompanyInfoResponse)
            result = await structured_llm.ainvoke(messages)

            # 记录 LLM 响应
            if hasattr(result, "model_dump"):
                response_content = str(result.model_dump())
            else:
                response_content = str(result)

            log_llm_response(
                response_content=response_content,
                request_log_path=request_log_path,
                model=model_name,
                task_type="extract_company_info",
            )

            # result 已经是 CompanyInfoResponse 实例，直接转换
            if isinstance(result, CompanyInfoResponse):
                # 转换为字典格式，保持向后兼容
                company_dict = result.model_dump(exclude_none=True)
                logger.info("使用结构化输出成功提取公司信息")
                return company_dict
            else:
                logger.warning(f"LLM 返回了意外的类型: {type(result)}")
                return {}

        except Exception as e:
            logger.error(f"LLM 结构化输出提取公司信息失败: {e}", exc_info=True)
            # 降级到旧的 JSON 解析方法
            logger.info("降级到旧的 JSON 解析方法")
            return await self.extract_with_llm(prompt)

    async def extract_with_llm(self, prompt: str) -> Dict:
        """
        使用 LLM 提取结构化信息（异步版本）

        支持多种容错机制：
        1. 提取被 markdown 代码块包裹的 JSON
        2. 修复常见的 JSON 格式问题
        3. 处理数组和对象两种格式
        4. 详细的错误日志

        Args:
            prompt: 提示词

        Returns:
            提取的结构化数据（字典格式）
        """
        try:
            # 记录 LLM 请求
            messages = [{"role": "user", "content": prompt}]
            model_name = (
                getattr(self.llm, "model_name", None)
                or getattr(self.llm, "model", None)
                or "unknown"
            )
            request_log_path = log_llm_request(
                messages=messages,
                model=model_name,
                task_type="extract_with_llm",
            )

            # 使用 LangChain V1 的异步调用方式
            response = await self.llm.ainvoke(messages)

            # 检查响应是否有效
            if not response:
                logger.error("LLM 返回无效响应: response 为空")
                log_llm_response(
                    response_content="[ERROR] Empty response",
                    request_log_path=request_log_path,
                    model=model_name,
                    task_type="extract_with_llm",
                )
                return {}

            if not hasattr(response, "content"):
                logger.error("LLM 返回无效响应: response 缺少 content 属性")
                log_llm_response(
                    response_content="[ERROR] Missing content attribute",
                    request_log_path=request_log_path,
                    model=model_name,
                    task_type="extract_with_llm",
                )
                return {}

            content = response.content

            # 记录 LLM 响应
            log_llm_response(
                response_content=content,
                request_log_path=request_log_path,
                model=model_name,
                task_type="extract_with_llm",
            )

            # 检查内容是否为空
            if not content or not content.strip():
                logger.error("LLM 返回空内容")
                return {}

            # 使用容错解析方法
            result = self._parse_json_with_fallback(content, expected_type=dict)

            if result is None:
                logger.error(f"无法解析 LLM 返回的 JSON")
                logger.debug(f"原始响应内容: {content[:1000]}")
                return {}

            # 确保返回字典格式
            if isinstance(result, dict):
                return result
            elif isinstance(result, list):
                # 如果返回的是列表（可能是联系人列表），包装成字典
                logger.info("LLM 返回了列表格式，包装为字典")
                return {"contacts": result}
            else:
                logger.warning(f"LLM 返回了意外的类型: {type(result)}")
                return {}

        except Exception as e:
            logger.error(f"LLM 提取信息失败: {e}", exc_info=True)
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
        self, queries: List[Dict[str, Any]], db: Optional[AsyncSession] = None
    ) -> Dict[str, List]:
        """
        使用选择的搜索工具搜索（优先 Serper，失败则 Google）

        Args:
            queries: 查询参数字典列表
            db: 可选的数据库会话，用于记录 Serper API 请求和响应

        Returns:
            查询到搜索结果的映射
        """
        # 优先尝试 Serper（结构化数据返回、搜索质量高）
        if settings.SERPER_API_KEY:
            try:
                logger.debug("使用 Serper 进行搜索")
                serper_results = await self.serper_provider.search_batch(queries, db=db)

                # 检查结果是否有效（至少有一些结果）
                if isinstance(serper_results, dict) and serper_results:
                    # 检查是否有任何查询返回了结果
                    has_results = any(
                        results and len(results) > 0
                        for results in serper_results.values()
                    )
                    if has_results:
                        logger.info(
                            f"Serper 搜索成功，返回 {len(serper_results)} 个查询结果"
                        )
                        return serper_results
                    else:
                        logger.warning("Serper 返回空结果，切换到 Google")
                else:
                    logger.warning("Serper 返回无效结果，切换到 Google")
            except Exception as e:
                logger.warning(f"Serper 搜索失败: {e}，切换到 Google")
        else:
            logger.debug("Serper API Key 未配置，使用 Google")

        # 回退到 Google（官方 API，参数更多样化）
        if settings.GOOGLE_SEARCH_API_KEY and settings.GOOGLE_SEARCH_CX:
            try:
                logger.debug("使用 Google 进行搜索")
                google_results = await self.google_provider.search_batch(queries)

                if isinstance(google_results, dict) and google_results:
                    logger.info(
                        f"Google 搜索成功，返回 {len(google_results)} 个查询结果"
                    )
                    return google_results
                else:
                    logger.warning("Google 返回空结果")
            except Exception as e:
                logger.error(f"Google 搜索失败: {e}", exc_info=True)
        else:
            logger.warning("Google Search API Key 或 CX 未配置")

        # 如果两者都失败，返回空结果
        logger.error("所有搜索提供商都失败，返回空结果")
        return {query.get("q", "query"): [] for query in queries}

    async def _search_contacts_parallel(
        self,
        company_name_en: str,
        company_name_local: str,
        domain: Optional[str],
        country: Optional[str],
        department: str,
        country_context: str,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, List]:
        """
        搜索联系人（采购或销售），支持邮箱搜索策略

        Args:
            company_name_en: 公司英文名称
            company_name_local: 公司本地名称
            domain: 公司域名（可选）
            country: 国家名称（可选）
            department: 部门名称（"采购" 或 "销售"）
            country_context: 国家上下文字符串
            db: 可选的数据库会话

        Returns:
            包含 contacts 和 results 的字典
        """
        try:
            logger.info(
                f"搜索{department}部门 KP: {company_name_en}"
                + (f" ({country})" if country else "")
                + (f" [域名: {domain}]" if domain else "")
            )

            # 如果 domain 存在，使用邮箱搜索策略（阶段1-4）
            if domain:
                logger.info(f"使用邮箱搜索策略（域名: {domain}）")
                queries = self.email_search_strategy.generate_email_search_queries(
                    domain=domain,
                    company_name_en=company_name_en,
                    department=department,
                    country=country,
                )
            else:
                # 回退到原有的联系人搜索策略
                logger.info("使用原有联系人搜索策略（无域名）")
                queries = self.search_strategy.generate_contact_queries(
                    company_name_en, company_name_local, country, department
                )

            # 使用选择的搜索工具搜索（优先 Serper，失败则 Google）
            results_map = await self._search_with_multiple_providers(queries, db=db)

            # 聚合结果
            aggregated_results = self.result_aggregator.aggregate(results_map)

            # 转换为字典格式
            results = [
                {"title": r.title, "link": str(r.link), "snippet": r.snippet}
                for r in aggregated_results
            ]

            # LLM 提取联系人（使用结构化输出）
            contacts_result = await self.extract_contacts_with_llm(
                EXTRACT_CONTACTS_PROMPT.format(
                    department=department,
                    country_context=country_context,
                    search_results=json.dumps(results, ensure_ascii=False),
                )
            )

            # 处理 LLM 返回的联系人数据
            # 结构化输出保证返回格式为 {"contacts": [...]}
            contacts = contacts_result.get("contacts", [])

            # 确保 contacts 是列表，且每个元素都是字典
            if not isinstance(contacts, list):
                logger.warning(f"联系人数据不是列表格式: {type(contacts)}")
                contacts = []
            else:
                # 验证并过滤无效的联系人数据
                valid_contacts = []
                for idx, contact in enumerate(contacts):
                    if isinstance(contact, dict):
                        valid_contacts.append(contact)
                    else:
                        logger.warning(
                            f"跳过无效的联系人数据（索引 {idx}）: {type(contact)}"
                        )
                contacts = valid_contacts

            logger.info(f"找到 {len(contacts)} 个{department}部门联系人")

            return {"contacts": contacts, "results": results}

        except Exception as e:
            logger.error(f"搜索{department}部门联系人失败: {e}", exc_info=True)
            # 确保总是返回有效的字典
            return {"contacts": [], "results": []}

    async def _search_and_save_company_info(
        self,
        company_name_en: str,
        company_name_local: str,
        country: Optional[str],
        db: AsyncSession,
        repo: Repository,
    ) -> Company:
        """
        搜索并保存公司信息

        Args:
            company_name_en: 公司名称英文
            company_name_local: 公司名称本地
            country: 国家名称（可选）
            db: 异步数据库会话
            repo: Repository 实例

        Returns:
            Company 对象（已创建或更新的公司记录）
        """
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
            company_queries, db=db
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

        # 5. LLM 提取公司信息（使用结构化输出）
        country_context = self._get_country_context(country)
        company_info = await self.extract_company_info_with_llm(
            EXTRACT_COMPANY_INFO_PROMPT.format(
                country_context=country_context,
                search_results=json.dumps(company_results, ensure_ascii=False),
            )
        )

        # 6. 创建或获取公司记录
        company = await repo.get_or_create_company(company_name_en)
        company.domain = company_info.get("domain")
        company.industry = company_info.get("industry")
        company.positioning = company_info.get("positioning")
        company.brief = company_info.get("brief")
        company.status = CompanyStatus.processing
        await db.commit()
        await db.refresh(company)
        logger.info(f"公司记录已创建/更新: {company.name}")

        return company

    async def _search_and_save_contacts(
        self,
        company: Company,
        company_name_en: str,
        company_name_local: str,
        country: Optional[str],
        country_context: str,
        db: AsyncSession,
        repo: Repository,
    ) -> List[KPInfo]:
        """
        搜索并保存联系人（独立方法，可被复用）

        Args:
            company: 公司对象
            company_name_en: 公司名称英文
            company_name_local: 公司名称本地
            country: 国家名称（可选）
            country_context: 国家上下文信息
            db: 异步数据库会话
            repo: Repository 实例

        Returns:
            保存的联系人列表（KPInfo）
        """
        # 1. 并行搜索采购和销售部门 KP
        logger.info(
            f"并行搜索采购和销售部门 KP: {company_name_en}"
            + (f" ({country})" if country else "")
        )

        # 并行执行采购和销售搜索
        procurement_task = self._search_contacts_parallel(
            company_name_en,
            company_name_local,
            company.domain,
            country,
            "采购",
            country_context,
            db,
        )
        sales_task = self._search_contacts_parallel(
            company_name_en,
            company_name_local,
            company.domain,
            country,
            "销售",
            country_context,
            db,
        )

        procurement_result, sales_result = await asyncio.gather(
            procurement_task, sales_task, return_exceptions=True
        )

        # 处理异常情况和 None 值
        if isinstance(procurement_result, Exception):
            logger.error(f"采购部门搜索失败: {procurement_result}")
            procurement_result = {"contacts": [], "results": []}
        elif procurement_result is None:
            logger.error("采购部门搜索返回 None")
            procurement_result = {"contacts": [], "results": []}
        elif not isinstance(procurement_result, dict):
            logger.error(f"采购部门搜索返回无效类型: {type(procurement_result)}")
            procurement_result = {"contacts": [], "results": []}

        if isinstance(sales_result, Exception):
            logger.error(f"销售部门搜索失败: {sales_result}")
            sales_result = {"contacts": [], "results": []}
        elif sales_result is None:
            logger.error("销售部门搜索返回 None")
            sales_result = {"contacts": [], "results": []}
        elif not isinstance(sales_result, dict):
            logger.error(f"销售部门搜索返回无效类型: {type(sales_result)}")
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

        # 2. 准备联系人数据
        contacts_to_save = []

        for contact_data in procurement_contacts:
            try:
                contact_data["department"] = "采购"
                if not contact_data.get("source") and procurement_results:
                    contact_data["source"] = procurement_results[0].get("link", "N/A")
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

        # 3. 清理联系人数据：将空字符串转换为 None，并过滤无效数据
        def clean_contact_data(data: dict) -> dict:
            """清理联系人数据：将空字符串转换为 None"""
            cleaned = {}
            for key, value in data.items():
                if value == "":
                    cleaned[key] = None
                else:
                    cleaned[key] = value
            return cleaned

        # 清理数据
        cleaned_contacts = [
            clean_contact_data(contact_data) for contact_data in contacts_to_save
        ]

        # 过滤掉没有 email 的联系人（数据库要求 email 不能为空）
        valid_contacts = [
            contact_data
            for contact_data in cleaned_contacts
            if contact_data.get("email")  # 必须有 email
        ]

        if len(cleaned_contacts) > len(valid_contacts):
            logger.warning(
                f"过滤掉 {len(cleaned_contacts) - len(valid_contacts)} 个没有 email 的联系人"
            )

        # 4. 批量保存联系人
        all_contacts = []
        if valid_contacts:
            logger.info(f"批量保存 {len(valid_contacts)} 个联系人...")
            try:
                # 转换为 KPInfo 对象列表
                kp_info_list = [
                    KPInfo(**contact_data) for contact_data in valid_contacts
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
                for contact_data in valid_contacts:
                    try:
                        kp_info = KPInfo(**contact_data)
                        contact = await repo.create_contact(kp_info, company.id)
                        all_contacts.append(kp_info)
                        logger.debug(f"联系人已保存: {contact.email}")
                    except Exception as e2:
                        logger.error(f"保存联系人失败: {e2}, 数据: {contact_data}")
                        continue

        return all_contacts

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
            # 0. 检查缓存：如果公司已完成且联系人已存在，直接返回
            company = await repo.get_company_by_name(company_name_en)
            if company and company.status == CompanyStatus.completed:
                logger.info(f"公司 {company_name_en} 已完成，查询现有联系人...")
                existing_contacts = await repo.get_contacts_by_company(company.id)

                if existing_contacts:
                    logger.info(f"找到 {len(existing_contacts)} 个现有联系人，直接返回")
                    # 将 Contact 对象转换为 KPInfo
                    kp_info_list = [
                        KPInfo(
                            full_name=contact.full_name,
                            email=contact.email,
                            role=contact.role,
                            department=contact.department,
                            linkedin_url=(
                                contact.linkedin_url if contact.linkedin_url else None
                            ),
                            twitter_url=(
                                contact.twitter_url if contact.twitter_url else None
                            ),
                            source=contact.source or "N/A",
                            confidence_score=float(contact.confidence_score or 0.0),
                        )
                        for contact in existing_contacts
                    ]
                    return {
                        "company_id": company.id,
                        "company_domain": company.domain,
                        "contacts": kp_info_list,
                    }
                else:
                    # 公司已完成但联系人不存在，只搜索联系人，跳过公司信息搜索
                    logger.info(
                        f"公司 {company_name_en} 已完成，但未找到联系人，仅搜索联系人..."
                    )
                    country_context = self._get_country_context(country)

                    # 更新公司状态为处理中
                    company.status = CompanyStatus.processing
                    await db.commit()

                    # 直接搜索并保存联系人
                    all_contacts = await self._search_and_save_contacts(
                        company,
                        company_name_en,
                        company_name_local,
                        country,
                        country_context,
                        db,
                        repo,
                    )

                    # 更新公司状态为已完成
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
            company = await self._search_and_save_company_info(
                company_name_en,
                company_name_local,
                country,
                db,
                repo,
            )
            country_context = self._get_country_context(country)

            # 6. 搜索并保存联系人
            all_contacts = await self._search_and_save_contacts(
                company,
                company_name_en,
                company_name_local,
                country,
                country_context,
                db,
                repo,
            )

            # 更新公司状态
            company.status = CompanyStatus.completed
            await db.commit()
            logger.info(
                f"FindKP 流程完成: {company_name_en}, 找到 {len(all_contacts)} 个联系人"
            )
            logger.debug(f"公司状态已更新为: {company.status.value}")

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
