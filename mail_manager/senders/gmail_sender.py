"""Gmail API 邮件发送器实现"""

import asyncio
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential

from ..email_sender import EmailSender, EmailSendException
from config import settings
from logs import logger


class GmailSender(EmailSender):
    """Gmail API 邮件发送器"""

    def __init__(self):
        """
        初始化 Gmail 发送器

        使用 Service Account 认证，配置 Domain-wide Delegation
        """
        if not settings.GOOGLE_SERVICE_ACCOUNT_FILE:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_FILE 配置项未设置")

        if not settings.GOOGLE_WORKSPACE_USER_EMAIL:
            raise ValueError("GOOGLE_WORKSPACE_USER_EMAIL 配置项未设置")

        try:
            # 加载 Service Account 凭据
            self.credentials = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_SERVICE_ACCOUNT_FILE,
                scopes=["https://www.googleapis.com/auth/gmail.send"],
            )

            # 使用 Domain-wide Delegation
            self.delegated_credentials = self.credentials.with_subject(
                settings.GOOGLE_WORKSPACE_USER_EMAIL
            )

            # 构建 Gmail API 服务
            self.service = build("gmail", "v1", credentials=self.delegated_credentials)

            logger.info(
                f"Gmail 发送器初始化成功，用户: {settings.GOOGLE_WORKSPACE_USER_EMAIL}"
            )
        except Exception as e:
            logger.error(f"Gmail 发送器初始化失败: {e}")
            raise EmailSendException(f"Gmail 发送器初始化失败: {str(e)}", e)

    def _create_message(
        self,
        to_email: str,
        to_name: Optional[str],
        from_email: str,
        from_name: Optional[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> dict:
        """
        创建邮件消息

        Args:
            to_email: 收件人邮箱
            to_name: 收件人姓名（可选）
            from_email: 发件人邮箱
            from_name: 发件人姓名（可选）
            subject: 邮件主题
            html_content: HTML 内容
            text_content: 纯文本内容（可选）

        Returns:
            包含 raw 消息的字典
        """
        message = MIMEMultipart("alternative")
        message["to"] = f'"{to_name}" <{to_email}>' if to_name else to_email
        message["from"] = f'"{from_name}" <{from_email}>' if from_name else from_email
        message["subject"] = subject

        # 添加纯文本部分（如果提供）
        if text_content:
            text_part = MIMEText(text_content, "plain", "utf-8")
            message.attach(text_part)

        # 添加 HTML 部分
        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(html_part)

        # 编码为 base64url
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return {"raw": raw_message}

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
            message_id: Gmail API 返回的消息ID

        Raises:
            EmailSendException: 发送失败时抛出
        """
        try:
            # 构建邮件消息
            message = self._create_message(
                to_email=to_email,
                to_name=to_name,
                from_email=from_email,
                from_name=from_name,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )

            # 在后台线程中执行同步的 Gmail API 调用
            def _send_sync():
                result = (
                    self.service.users()
                    .messages()
                    .send(userId="me", body=message)
                    .execute()
                )
                return result.get("id")

            # 使用 asyncio.to_thread 将同步调用转换为异步
            message_id = await asyncio.to_thread(_send_sync)

            logger.info(f"邮件发送成功: {to_email}, message_id: {message_id}")
            return message_id

        except HttpError as e:
            error_msg = f"Gmail API 错误: {e.resp.status} - {e.content.decode()}"
            logger.error(f"邮件发送失败: {to_email}, {error_msg}")
            raise EmailSendException(error_msg, e)
        except Exception as e:
            error_msg = f"邮件发送失败: {str(e)}"
            logger.error(f"邮件发送失败: {to_email}, {error_msg}")
            raise EmailSendException(error_msg, e)

