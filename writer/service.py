"""Writer 业务逻辑服务"""

import re
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from llm import get_llm
from database.repository import Repository
from database.models import Company, Contact
from schemas.writer import EmailContent, GeneratedEmail as WriterGeneratedEmail
from prompts.writer.WRITER_V3 import BRIEF_PROMPT
from config import settings, get_language_config
from logs import logger, log_llm_request, log_llm_response


class WriterService:
    """Writer 服务类，负责生成营销邮件（异步版本）"""

    def __init__(self):
        """
        初始化 Writer 服务
        """
        # 使用统一的 LLM 工厂函数，支持指定模型类型
        self.llm = get_llm()

    def _separate_stages(self, content: str) -> tuple[str, str]:
        """
        分离 Stage A (YAML) 和 Stage B (HTML)

        Args:
            content: LLM 返回的完整内容

        Returns:
            (yaml_part, html_part) 元组
        """
        html_start = content.find("<!DOCTYPE html>")
        if html_start == -1:
            html_start = content.find("<html>")

        if html_start != -1:
            yaml_part = content[:html_start].strip()
            html_part = content[html_start:].strip()
            return yaml_part, html_part
        return "", content

    def _extract_subject_from_html(self, html: str) -> str:
        """
        从 HTML 中提取越南语主题行

        Args:
            html: HTML 内容

        Returns:
            提取的主题行，如果未找到则返回空字符串
        """
        # 查找越南语主题行：<p style="font-weight: bold; color: #0056b3;">Chủ đề: [VI Subject]</p>
        pattern = r"<p[^>]*>Chủ đề:\s*([^<]+)</p>"
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def _deduplicate_contacts(self, contacts: List[Contact]) -> List[Contact]:
        """
        按邮箱去重，保留置信度最高的联系人

        Args:
            contacts: 联系人列表

        Returns:
            去重后的联系人列表（只包含有邮箱的联系人）
        """
        email_map: Dict[str, Contact] = {}

        for contact in contacts:
            if not contact.email:
                continue

            email_lower = contact.email.lower()
            if email_lower not in email_map:
                email_map[email_lower] = contact
            else:
                # 比较置信度，保留更高的
                existing = email_map[email_lower]
                existing_score = existing.confidence_score or 0.0
                current_score = contact.confidence_score or 0.0

                if current_score > existing_score:
                    email_map[email_lower] = contact
                elif current_score == existing_score:
                    # 置信度相同，保留最新的
                    if contact.created_at and existing.created_at:
                        if contact.created_at > existing.created_at:
                            email_map[email_lower] = contact

        return list(email_map.values())

    def _format_prompt(self, company: Company, contact: Contact) -> str:
        """
        格式化 Prompt 模板

        Args:
            company: 公司对象
            contact: 联系人对象

        Returns:
            格式化后的 Prompt 字符串
        """
        # 判断是否有截图
        has_screenshot_customs_result = (
            "true" if settings.IMAGE_URL_CUSTOMS_RESULT else "false"
        )
        has_screenshot_filters = "true" if settings.IMAGE_URL_FILTERS else "false"

        # 从 company.country 获取本地化配置
        country_name = company.country
        language_config = get_language_config(country_name)
        target_language_name = language_config["language_name"]
        target_language_code = language_config["language_code"]

        prompt = BRIEF_PROMPT.format(
            # 公司信息
            company_en_name=company.name or "",
            company_local_name=company.local_name or "",
            industry_cn=company.industry or "",
            positioning_cn=company.positioning or "",
            brief_cn=company.brief or "",
            # 联系人信息
            full_name=contact.full_name or "",
            role_en=contact.role or "",
            department_cn=contact.department or "",
            email=contact.email or "",
            # 本地化上下文（从 company.country 动态获取）
            target_country_name=country_name,
            target_language_name=target_language_name,
            target_language_code=target_language_code,
            # 资产信息
            has_screenshot_customs_result=has_screenshot_customs_result,
            has_screenshot_filters=has_screenshot_filters,
            image_url_customs_result=settings.IMAGE_URL_CUSTOMS_RESULT or "",
            image_url_filters=settings.IMAGE_URL_FILTERS or "",
            # 产品信息
            trial_url=settings.TRIAL_URL,
            # 发送者信息
            sender_name=settings.SENDER_NAME or "",
            sender_title_en=settings.SENDER_TITLE_EN or "",
            sender_company=settings.SENDER_COMPANY or "",
            sender_email=settings.SENDER_EMAIL or "",
            # 其他
            whatsapp_number=settings.WHATSAPP_NUMBER or "",
        )

        return prompt

    def _parse_email_response(
        self, content: str, contact: Contact
    ) -> Optional[EmailContent]:
        """
        解析 LLM 响应，提取邮件内容（处理两阶段输出：YAML + HTML）

        Args:
            content: LLM 返回的内容（包含 Stage A YAML 和 Stage B HTML）
            contact: 联系人对象

        Returns:
            EmailContent 对象，如果解析失败则返回 None
        """
        try:
            # 分离 Stage A (YAML) 和 Stage B (HTML)
            yaml_part, html_part = self._separate_stages(content)

            if not html_part:
                logger.warning(f"无法从 LLM 响应中提取 HTML 内容: {content[:200]}")
                return None

            # 从 HTML 中提取主题行（越南语）
            subject = self._extract_subject_from_html(html_part)

            if not subject:
                logger.warning(f"无法从 HTML 中提取主题行: {html_part[:200]}")

            # 提取完整 HTML 内容（从 <!DOCTYPE html> 或 <html> 开始到 </html> 结束）
            html_start = html_part.find("<!DOCTYPE html>")
            if html_start == -1:
                html_start = html_part.find("<html>")

            html_end = html_part.rfind("</html>")
            if html_start != -1 and html_end != -1:
                html_content = html_part[html_start : html_end + 7]  # +7 包含 </html>
            else:
                # 如果没有找到完整的 HTML 标签，使用整个 html_part
                html_content = html_part

            # 返回新的 EmailContent 格式
            return EmailContent(
                contact_id=contact.id,
                contact_name=contact.full_name,
                contact_email=contact.email or "",  # 确保不为 None
                contact_role=contact.role,
                subject=subject,
                html_content=html_content,
            )

        except Exception as e:
            logger.error(f"解析邮件响应失败: {e}", exc_info=True)
            logger.debug(f"原始响应内容: {content[:500]}")
            return None

    async def _generate_email_for_contact(
        self, company: Company, contact: Contact
    ) -> Optional[EmailContent]:
        """
        为单个联系人生成邮件

        Args:
            company: 公司对象
            contact: 联系人对象

        Returns:
            EmailContent 对象，如果生成失败则返回 None
        """
        # 确保联系人有邮箱
        if not contact.email:
            logger.warning(f"联系人 {contact.id} 没有邮箱地址，跳过生成")
            return None

        prompt = self._format_prompt(company, contact)

        try:
            messages = [{"role": "user", "content": prompt}]
            model_name = (
                self.llm.model_name
                if hasattr(self.llm, "model_name")
                else getattr(self.llm, "_model_name", "unknown")
            )

            # 记录 LLM 请求
            request_log_path = log_llm_request(
                messages=messages,
                model=model_name,
                task_type="generate_email",
            )

            # 调用 LLM
            response = await self.llm.ainvoke(messages)

            # 记录 LLM 响应
            if hasattr(response, "content"):
                log_llm_response(
                    response_content=response.content,
                    request_log_path=request_log_path,
                    model=model_name,
                    task_type="generate_email",
                )

                # 解析响应
                return self._parse_email_response(response.content, contact)
            else:
                logger.error("LLM 返回无效响应: response 缺少 content 属性")
                return None

        except Exception as e:
            logger.error(
                f"为联系人 {contact.id} ({contact.email}) 生成邮件失败: {e}",
                exc_info=True,
            )
            return None

    async def generate_emails(
        self,
        company_id: Optional[int] = None,
        company_name: Optional[str] = None,
        db: AsyncSession = None,
    ) -> Dict[str, Any]:
        """
        生成邮件主方法

        Args:
            company_id: 公司ID（可选）
            company_name: 公司名称（可选）
            db: 数据库会话

        Returns:
            包含公司信息和邮件列表的字典

        Raises:
            ValueError: 当公司不存在时
        """
        if not db:
            raise ValueError("数据库会话不能为空")

        repository = Repository(db)

        # 查询公司
        if company_id:
            company = await repository.get_company_by_id(company_id)
        elif company_name:
            company = await repository.get_company_by_name(company_name)
        else:
            raise ValueError("必须提供 company_id 或 company_name")

        if not company:
            raise ValueError(f"公司不存在: {company_id or company_name}")

        # 查询联系人
        contacts = await repository.get_all_contacts_with_email_by_company(company.id)
        logger.info(f"公司 {company.name} 共有 {len(contacts)} 个联系人")

        # 去重
        deduplicated_contacts = self._deduplicate_contacts(contacts)
        logger.info(
            f"去重后（按邮箱）共有 {len(deduplicated_contacts)} 个联系人（有邮箱）"
        )

        if not deduplicated_contacts:
            logger.warning(f"公司 {company.name} 没有有效的联系人（有邮箱）")
            return {
                "company_id": company.id,
                "company_name": company.name,
                "emails": [],
            }

        # 并发生成邮件
        tasks = [
            self._generate_email_for_contact(company, contact)
            for contact in deduplicated_contacts
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤有效结果
        emails = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"生成邮件时发生异常: {result}",
                    exc_info=True,
                )
            elif result is not None:
                emails.append(result)
            else:
                logger.warning(
                    f"联系人 {deduplicated_contacts[i].id} ({deduplicated_contacts[i].email}) 的邮件生成失败"
                )

        logger.info(
            f"成功为 {len(emails)}/{len(deduplicated_contacts)} 个联系人生成邮件"
        )

        return {
            "company_id": company.id,
            "company_name": company.name,
            "emails": emails,
        }

    async def generate_emails_for_all_contacts(
        self,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        为所有有邮箱的联系人生成邮件（按邮箱去重）

        Args:
            db: 数据库会话

        Returns:
            包含邮件列表的字典
        """
        if not db:
            raise ValueError("数据库会话不能为空")

        repository = Repository(db)

        # 查询所有有邮箱的联系人（去重）
        contacts = await repository.get_all_contacts_with_email()
        logger.info(f"找到 {len(contacts)} 个有邮箱的联系人（已去重）")

        if not contacts:
            logger.warning("没有找到有邮箱的联系人")
            return {
                "total_contacts": 0,
                "emails": [],
            }

        # 按公司分组，以便获取公司信息
        company_map: Dict[int, Company] = {}
        contact_company_map: Dict[int, int] = {}  # contact_id -> company_id

        for contact in contacts:
            if contact.company_id not in company_map:
                company = await repository.get_company_by_id(contact.company_id)
                if company:
                    company_map[contact.company_id] = company
            contact_company_map[contact.id] = contact.company_id

        # 并发生成邮件
        tasks = []
        for contact in contacts:
            company = company_map.get(contact.company_id)
            if company:
                tasks.append(self._generate_email_for_contact(company, contact))
            else:
                logger.warning(
                    f"联系人 {contact.id} 的公司 {contact.company_id} 不存在，跳过"
                )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤有效结果
        emails = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"生成邮件时发生异常: {result}",
                    exc_info=True,
                )
            elif result is not None:
                emails.append(result)
            else:
                logger.warning(
                    f"联系人 {contacts[i].id} ({contacts[i].email}) 的邮件生成失败"
                )

        logger.info(f"成功为 {len(emails)}/{len(contacts)} 个联系人生成邮件")

        return {
            "total_contacts": len(contacts),
            "emails": emails,
        }
