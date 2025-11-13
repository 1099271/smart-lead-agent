"""Writer 业务逻辑服务"""

import re
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from llm import get_llm
from database.repository import Repository
from database.models import Company, Contact
from schemas.writer import (
    EmailContent,
    GeneratedEmail as WriterGeneratedEmail,
    V4EmailFragment,
    V4EmailContent,
)
from prompts.writer.WRITER_V3 import BRIEF_PROMPT
from prompts.writer.WRITER_V4_LIGHT import V4_LIGHT_PROMPT
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
        从 HTML 中提取主题行（从 <title> 标签）

        Args:
            html: HTML 内容

        Returns:
            提取的主题行，如果未找到则返回空字符串
        """
        # 查找 <title> 标签内容：<title>...</title>
        # 支持 title 标签可能有属性，如 <title lang="vi">...</title>
        pattern = r"<title[^>]*>(.*?)</title>"
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            # 提取内容并清理 HTML 实体和空白字符
            title = match.group(1).strip()
            # 移除可能的 HTML 实体（如 &nbsp;）和多余空白
            title = re.sub(r"\s+", " ", title)
            return title
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
        generator_version: str = "v3",
    ) -> Dict[str, Any]:
        """
        生成邮件主方法

        Args:
            company_id: 公司ID（可选）
            company_name: 公司名称（可选）
            db: 数据库会话
            generator_version: 生成器版本
        Returns:
            包含公司信息和邮件列表的字典

        Raises:
            ValueError: 当公司不存在时
        """
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

        if generator_version == "v3":
            tasks = [
                self._generate_email_for_contact(company, contact)
                for contact in deduplicated_contacts
            ]
        elif generator_version == "v4":
            tasks = [
                self._generate_v4_fragment_for_contact(company, contact)
                for contact in deduplicated_contacts
            ]
        else:
            raise ValueError(f"无效的生成器版本: {generator_version}")

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
                if generator_version == "v3":
                    emails.append(result)
                elif generator_version == "v4":
                    html_content = self._assemble_html_email(
                        result, deduplicated_contacts[i]
                    )
                    # 创建 V4EmailContent
                    email_content = V4EmailContent(
                        contact_id=deduplicated_contacts[i].id,
                        contact_name=deduplicated_contacts[i].full_name,
                        contact_email=deduplicated_contacts[i].email or "",
                        contact_role=deduplicated_contacts[i].role,
                        subject=result.subject,
                        html_content=html_content,
                    )
                    emails.append(email_content)
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

    # ==================== V4 相关方法 ====================

    def _format_v4_prompt(self, company: Company, contact: Contact) -> str:
        """
        格式化 V4 Prompt 模板

        Args:
            company: 公司对象
            contact: 联系人对象

        Returns:
            格式化后的 Prompt 字符串
        """
        prompt = V4_LIGHT_PROMPT.format(
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
        )

        return prompt

    def _parse_v4_json_response(self, content: str) -> Optional[V4EmailFragment]:
        """
        解析 LLM 返回的 JSON 响应

        Args:
            content: LLM 返回的内容（JSON 字符串）

        Returns:
            V4EmailFragment 对象，如果解析失败则返回 None
        """
        try:
            # 尝试提取 JSON（可能包含 markdown 代码块）
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                logger.warning(f"无法从响应中找到 JSON: {content[:200]}")
                return None

            json_str = content[json_start:json_end]
            data = json.loads(json_str)

            # 使用 Pydantic 验证
            fragment = V4EmailFragment(**data)
            return fragment

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}", exc_info=True)
            logger.debug(f"原始响应内容: {content[:500]}")
            return None
        except Exception as e:
            logger.error(f"解析 V4 JSON 响应失败: {e}", exc_info=True)
            logger.debug(f"原始响应内容: {content[:500]}")
            return None

    async def _generate_v4_fragment_for_contact(
        self, company: Company, contact: Contact
    ) -> Optional[V4EmailFragment]:
        """
        为单个联系人生成 V4 JSON 片段

        Args:
            company: 公司对象
            contact: 联系人对象

        Returns:
            V4EmailFragment 对象，如果生成失败则返回 None
        """
        # 确保联系人有邮箱
        if not contact.email:
            logger.warning(f"联系人 {contact.id} 没有邮箱地址，跳过生成")
            return None

        prompt = self._format_v4_prompt(company, contact)

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
                task_type="generate_v4_email",
            )

            # 调用 LLM
            response = await self.llm.ainvoke(messages)

            # 记录 LLM 响应
            if hasattr(response, "content"):
                log_llm_response(
                    response_content=response.content,
                    request_log_path=request_log_path,
                    model=model_name,
                    task_type="generate_v4_email",
                )

                # 解析 JSON 响应
                return self._parse_v4_json_response(response.content)
            else:
                logger.error("LLM 返回无效响应: response 缺少 content 属性")
                return None

        except Exception as e:
            logger.error(
                f"为联系人 {contact.id} ({contact.email}) 生成 V4 片段失败: {e}",
                exc_info=True,
            )
            return None

    def _assemble_html_email(self, fragment: V4EmailFragment, contact: Contact) -> str:
        """
        组装完整的 HTML 邮件（JSON 片段 + 固定片段）

        Args:
            fragment: V4EmailFragment 对象（包含 subject 和 email_body_html）
            contact: 联系人对象

        Returns:
            完整的 HTML 邮件字符串
        """
        # HTML 头部和样式（参考 V3 的样式）
        html_head = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; color: #333; }}
        .container {{ background-color: #ffffff; margin: 0 auto; padding: 20px 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 600px; }}
        p {{ line-height: 1.6; margin-bottom: 10px; }}
        h3 {{ color: #0056b3; margin-top: 20px; margin-bottom: 15px; }}
        h4 {{ color: #004a99; margin-top: 15px; margin-bottom: 10px; }}
        .problem {{ margin-bottom: 20px; padding: 15px; background-color: #f9f9f9; border-left: 3px solid #ff6b6b; }}
        .value-proposition {{ margin-bottom: 20px; padding: 15px; background-color: #f0f8ff; border-left: 3px solid #4dabf7; }}
        .image-container {{ text-align: center; margin: 20px 0; }}
        .image-container img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; display: block; margin: 10px auto; }}
        .image-container p {{ font-size: 0.9em; color: #555; margin: 5px 0; }}
        .signature-block {{ margin-top: 20px; font-size: 0.9em; line-height: 1.4; color: #333; }}
        .signature-block .sender-name {{ font-weight: bold; color: #000; }}
        ul {{ margin: 15px 0; padding-left: 20px; }}
        li {{ margin-bottom: 8px; }}
        a {{ color: #007bff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
""".format(
            subject=fragment.subject
        )

        # JSON 返回的 HTML 片段
        email_body = fragment.email_body_html

        # 固定片段一：截图展示
        screenshot_section = f"""
        <div class="image-container">
            <p style="font-size: 0.9em; color: #555;">Smart Filters Screenshot</p>
            <img src="{settings.IMAGE_URL_FILTERS or ''}" alt="Smart Filters Screenshot">
            <p style="font-size: 0.9em; color: #555;">Customs Results Screenshot</p>
            <img src="{settings.IMAGE_URL_CUSTOMS_RESULT or ''}" alt="Customs Results Screenshot">
        </div>
"""

        # 固定片段二：联系方式和结尾
        contact_section = f"""
        <p>We'd love to help you explore these solutions. Feel free to reach out:</p>
        <ul>
            <li>Free Trial: <a href="{settings.TRIAL_URL or ''}">{settings.TRIAL_URL or ''}</a></li>
            <li>WhatsApp: {settings.WHATSAPP_NUMBER or ''}</li>
            <li>Email: <a href="mailto:{settings.SENDER_EMAIL or ''}">{settings.SENDER_EMAIL or ''}</a></li>
        </ul>
        <p>Best regards,</p>
        <div class="signature-block">
            <span class="sender-name">{settings.SENDER_NAME or ''}</span><br>
            {settings.SENDER_COMPANY or ''}
        </div>
    </div>
</body>
</html>
"""

        # 组装完整 HTML
        full_html = html_head + email_body + screenshot_section + contact_section

        return full_html
