import logging
import json
from openai import OpenAI

from core.schemas import ContactInfo, GeneratedEmail

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GenerationModule:
    """
    生成模块，负责根据提取的联系人信息生成个性化的开发信。
    """

    def __init__(self, client: OpenAI):
        """
        初始化生成模块。

        Args:
            client: 一个 OpenAI 客户端实例。
        """
        self.client = client

    def _get_email_generation_prompt(
        self, contact: ContactInfo, company_name: str
    ) -> str:
        """生成用于邮件撰写的提示。"""
        role_info = f"，职位是 {contact.role}" if contact.role else ""
        linkedin_info = (
            f"，其LinkedIn个人资料为 {contact.linkedin_url}"
            if contact.linkedin_url
            else ""
        )

        return f"""
        任务：为 {company_name} 公司的联系人 {contact.full_name or '采购负责人'}{role_info}{linkedin_info} 撰写一封专业的开发信（Cold Email）。

        收件人信息：
        - 姓名：{contact.full_name or '待确认'}
        - 公司：{company_name}
        - 职位：{contact.role or '待确认'}

        邮件要求：
        1. 主题行（Subject）：简洁、吸引人，能够激发收件人打开邮件的兴趣。长度不超过50个字符。
        2. 正文（Body）：
           - 开头要有礼貌的问候，使用收件人的姓名（如果知道）。
           - 简要介绍你自己或你的公司。
           - 说明你联系他们的原因，要与他们的职位和公司相关。
           - 明确说明你能为他们提供的价值或解决方案。
           - 包含一个清晰的行动号召（Call to Action）。
           - 保持专业但友好的语调。
           - 长度应在150-250字之间。
           - 使用简洁的段落，每段不超过3-4句话。

        输出格式：
        请以JSON格式返回结果，包含两个键：
        - "subject": 邮件主题
        - "body": 邮件正文（纯文本，不需要HTML标记）

        示例格式：
        {{
          "subject": "您的邮件主题",
          "body": "您的邮件正文内容..."
        }}
        """

    def generate_cold_email(
        self, contact: ContactInfo, company_name: str
    ) -> GeneratedEmail:
        """
        根据联系人信息和公司名，生成一封个性化的开发信。

        Args:
            contact: 联系人的结构化信息。
            company_name: 目标公司的名称。

        Returns:
            一个 GeneratedEmail 对象，包含邮件的主题和正文。
        """
        prompt = self._get_email_generation_prompt(contact, company_name)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # 稍微提高温度，以产生更有创造性的内容
                response_format={"type": "json_object"},
            )

            response_content = response.choices[0].message.content
            if not response_content:
                logger.error("LLM returned an empty response.")
                raise ValueError("Empty response from LLM")

            email_data = json.loads(response_content)

            # 验证并创建 GeneratedEmail 对象
            generated_email = GeneratedEmail(
                subject=email_data.get("subject", ""),
                body=email_data.get("body", ""),
            )

            logger.info(
                f"Successfully generated email with subject: {generated_email.subject}"
            )
            return generated_email

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during email generation: {e}")
            raise
