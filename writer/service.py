"""Writer 业务逻辑服务"""

import json
import re
import asyncio
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from llm import get_llm
from database.repository import Repository
from database.models import Company, Contact
from schemas.writer import GeneratedEmail
from prompts.writer.W_VN_PROMPT import W_VN_PROMPT
from logs import logger, log_llm_request, log_llm_response


class WriterService:
    """Writer 服务类，负责生成营销邮件（异步版本）"""

    def __init__(self):
        # 使用统一的 LLM 工厂函数
        self.llm = get_llm()

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        从文本中提取 JSON 内容，处理被 markdown 代码块包裹的情况
        复用 FindKP 的逻辑

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

        # 策略2: 查找 JSON 对象 {}
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
                            return candidate
                        except json.JSONDecodeError:
                            pass
                        break

        # 策略3: 尝试直接解析整个文本
        cleaned_text = text.strip()
        if cleaned_text:
            try:
                json.loads(cleaned_text)
                return cleaned_text
            except json.JSONDecodeError:
                pass

        return None

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

        注意：W_VN_PROMPT 模板已经包含了 JSON 格式要求，无需重复添加
        """
        prompt = W_VN_PROMPT.format(
            company_en_name=company.name or "",
            company_local_name=company.local_name or "",
            industry=company.industry or "",
            positioning=company.positioning or "",
            brief=company.brief or "",
            full_name=contact.full_name or "",
            role=contact.role or "",
        )

        return prompt

    def _parse_email_response(
        self, content: str, contact: Contact
    ) -> Optional[GeneratedEmail]:
        """
        解析 LLM 响应，提取邮件内容

        Args:
            content: LLM 返回的内容
            contact: 联系人对象

        Returns:
            GeneratedEmail 对象，如果解析失败则返回 None
        """
        try:
            # 提取 JSON
            json_str = self._extract_json_from_text(content)
            if not json_str:
                logger.warning(f"无法从 LLM 响应中提取 JSON: {content[:200]}")
                return None

            # 解析 JSON
            email_data = json.loads(json_str)

            subject = email_data.get("subject", "")
            content_en = email_data.get("content_en", "")
            content_vn = email_data.get("content_vn", "")

            # 组合完整内容（英文 + 越南语）
            full_content = ""
            if content_en:
                full_content += content_en
            if content_vn:
                if full_content:
                    full_content += "\n\n---\n\n"
                full_content += content_vn

            return GeneratedEmail(
                contact_id=contact.id,
                contact_name=contact.full_name,
                contact_email=contact.email,
                contact_role=contact.role,
                subject=subject,
                content_en=content_en,
                content_vn=content_vn,
                full_content=full_content,
            )

        except json.JSONDecodeError as e:
            logger.error(f"解析邮件 JSON 失败: {e}")
            logger.debug(f"原始响应内容: {content[:500]}")
            return None
        except Exception as e:
            logger.error(f"解析邮件响应失败: {e}", exc_info=True)
            return None

    async def _generate_email_for_contact(
        self, company: Company, contact: Contact
    ) -> Optional[GeneratedEmail]:
        """
        为单个联系人生成邮件

        Args:
            company: 公司对象
            contact: 联系人对象

        Returns:
            GeneratedEmail 对象，如果生成失败则返回 None
        """
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
        contacts = await repository.get_contacts_by_company(company.id)
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
