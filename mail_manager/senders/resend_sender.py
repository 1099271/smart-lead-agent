"""Resend API 邮件发送器实现"""

import asyncio
from typing import Optional
import resend
from tenacity import retry, stop_after_attempt, wait_exponential

from ..email_sender import EmailSender, EmailSendException
from config import settings
from logs import logger


class ResendSender(EmailSender):
    """Resend API 邮件发送器"""

    def __init__(self):
        """
        初始化 Resend 发送器

        使用 Resend API Key 进行认证
        """
        if not settings.RESEND_API_KEY:
            raise ValueError("RESEND_API_KEY 配置项未设置")

        try:
            # 设置 Resend API Key
            resend.api_key = settings.RESEND_API_KEY

            logger.info("Resend 发送器初始化成功")
        except Exception as e:
            logger.error(f"Resend 发送器初始化失败: {e}")
            raise EmailSendException(f"Resend 发送器初始化失败: {str(e)}", e)

    def _build_send_params(
        self,
        to_email: str,
        to_name: Optional[str],
        from_email: str,
        from_name: Optional[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> resend.Emails.SendParams:
        """
        构建 Resend 发送参数

        Args:
            to_email: 收件人邮箱
            to_name: 收件人姓名（可选）
            from_email: 发件人邮箱
            from_name: 发件人姓名（可选）
            subject: 邮件主题
            html_content: HTML 内容
            text_content: 纯文本内容（可选）

        Returns:
            Resend SendParams 字典
        """
        # 构建发件人格式: "Name <email@example.com>" 或 "email@example.com"
        if from_name:
            from_address = f'"{from_name}" <{from_email}>'
        else:
            from_address = from_email

        # 构建收件人格式
        if to_name:
            to_address = f'"{to_name}" <{to_email}>'
        else:
            to_address = to_email

        params: resend.Emails.SendParams = {
            "from": from_address,
            "to": [to_address],
            "subject": subject,
            "html": html_content,
        }

        # 如果提供了纯文本内容，添加到参数中
        if text_content:
            params["text"] = text_content

        return params

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def send_email(
        self,
        to_email: str,
        to_name: Optional[str],
        from_email: str,
        from_name: Optional[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> str:
        """
        发送邮件（异步）

        Args:
            to_email: 收件人邮箱
            to_name: 收件人姓名（可选）
            from_email: 发件人邮箱
            from_name: 发件人姓名（可选）
            subject: 邮件主题
            html_content: HTML 内容
            text_content: 纯文本内容（可选）

        Returns:
            message_id: Resend API 返回的消息ID

        Raises:
            EmailSendException: 发送失败时抛出
        """
        try:
            # 构建发送参数
            params = self._build_send_params(
                to_email=to_email,
                to_name=to_name,
                from_email=from_email,
                from_name=from_name,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )

            # 在后台线程中执行同步的 Resend API 调用
            def _send_sync():
                email = resend.Emails.send(params)
                # Resend API 返回的对象可能是字典或对象
                # 尝试多种方式获取 id
                if isinstance(email, dict):
                    message_id = email.get("id") or email.get("message_id")
                else:
                    # 如果是对象，尝试访问 id 属性
                    message_id = getattr(email, "id", None) or getattr(
                        email, "message_id", None
                    )

                if not message_id:
                    # 如果无法获取 id，使用对象的字符串表示
                    message_id = str(email)

                return message_id

            # 使用 asyncio.to_thread 将同步调用转换为异步
            message_id = await asyncio.to_thread(_send_sync)

            logger.info(f"邮件发送成功: {to_email}, message_id: {message_id}")
            return message_id

        except Exception as e:
            error_msg = f"Resend API 错误: {str(e)}"
            logger.error(f"邮件发送失败: {to_email}, {error_msg}")
            raise EmailSendException(error_msg, e)
