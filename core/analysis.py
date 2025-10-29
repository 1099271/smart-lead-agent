import re
import json
import logging
from typing import List, Optional

from openai import OpenAI
from pydantic import ValidationError

from core.schemas import SearchResult, ContactInfo
from config import settings

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 一个基础的正则表达式，用于从文本中查找可能的电子邮件地址
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"


class AnalysisModule:
    """
    分析模块，负责从原始搜索结果中提取结构化的联系人信息。
    """

    def __init__(self, client: OpenAI):
        """
        初始化分析模块。

        Args:
            client: 一个 OpenAI 客户端实例。
        """
        self.client = client

    def _get_llm_extraction_prompt(self, context: str, company_name: str) -> str:
        """生成用于LLM信息提取的提示。"""
        return f"""
        任务：从以下提供的文本中，为 '{company_name}' 公司提取一名相关联系人的信息。
        目标角色：采购经理、采购负责人、供应链经理、运营总监或类似职位。

        文本内容:
        ---
        {context}
        ---

        提取要求：
        1. 找出最符合目标角色的一个人。
        2. 提取其全名、工作邮箱、LinkedIn个人资料URL（如果找到）。
        3. 结果必须以一个JSON对象的格式返回。
        4. JSON对象应包含以下键：'full_name', 'email', 'linkedin_url', 'role'。
        5. 如果找不到任何符合条件的联系人，请返回一个包含空字符串值的JSON对象，例如：
           {{"full_name": "", "email": "", "linkedin_url": "", "role": ""}}

        请直接输出JSON对象，不要包含任何额外的解释或标记。
        """

    def find_contact(
        self, search_results: List[SearchResult], company_name: str
    ) -> Optional[ContactInfo]:
        """
        分析搜索结果，尝试找到最相关的采购负责人联系信息。
        它首先尝试通过正则表达式快速查找，然后使用LLM进行更深入的分析。

        Args:
            search_results: 搜索结果列表。
            company_name: 目标公司名称。

        Returns:
            如果找到联系人，则返回 ContactInfo 对象，否则返回 None。
        """
        # 策略 1: 快速的正则表达式扫描
        for result in search_results:
            found_emails = re.findall(EMAIL_REGEX, result.snippet)
            for email in found_emails:
                # 简单验证，排除常见的非联系人邮箱
                if "contact" in email or "info" in email or "sales" in email:
                    continue
                logger.info(f"Regex found a potential email: {email} in {result.link}")
                # 即使找到邮箱，我们仍然希望LLM提供更丰富的信息
                break  # 暂时中断，进入LLM流程

        # 策略 2: 使用 LLM 进行深度提取
        context = "\n".join(
            [f"Source: {r.link}\nSnippet: {r.snippet}" for r in search_results]
        )
        if not context.strip():
            logger.warning("Search results were empty, skipping analysis.")
            return None

        prompt = self._get_llm_extraction_prompt(context, company_name)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
            )

            response_content = response.choices[0].message.content
            if not response_content:
                logger.warning("LLM returned an empty response.")
                return None

            contact_data = json.loads(response_content)

            # 验证从LLM获取的数据是否有效
            if not contact_data.get("email"):
                logger.info("LLM analysis did not yield a contact with an email.")
                return None

            # 找到一个随机的source URL作为来源
            # 在更复杂的实现中，可以尝试将提取的信息与源URL关联
            source_url = search_results[0].link if search_results else "N/A"

            # 使用 Pydantic 模型进行验证和数据转换
            return ContactInfo(**contact_data, source=source_url)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            logger.debug(f"Invalid JSON string: {response_content}")
            return None
        except ValidationError as e:
            logger.error(f"LLM response failed Pydantic validation: {e}")
            logger.debug(f"LLM data: {contact_data}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during LLM analysis: {e}")
            return None
