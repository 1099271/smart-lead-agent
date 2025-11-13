"""Gmail API 邮件发送器实现"""

import asyncio
import base64
import json
import os
import sys

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential

from ..email_sender import EmailSender, EmailSendException
from ..oauth2_manager import get_oauth2_manager
from database.repository import Repository
from config import settings
from logs import logger

# Gmail API 所需的作用域
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GmailSender(EmailSender):
    """Gmail API 邮件发送器

    使用 OAuth 2.0 用户授权方式访问 Gmail API
    """

    def __init__(self):
        """
        初始化 Gmail 发送器

        使用 OAuth 2.0 用户授权，需要 credentials.json 文件
        Token 存储在数据库中，不再使用文件系统
        注意：凭据采用延迟初始化，在第一次使用时才获取
        """
        if not settings.GOOGLE_OAUTH2_CREDENTIALS_FILE:
            raise ValueError("GOOGLE_OAUTH2_CREDENTIALS_FILE 配置项未设置")

        # 延迟初始化：凭据和服务在第一次使用时才初始化
        self._credentials: Optional[Credentials] = None
        self._service = None
        self._initialized = False

        logger.info("Gmail 发送器实例已创建（延迟初始化，token 存储在数据库）")

    async def _ensure_initialized(self, db=None):
        """
        确保 Gmail 发送器已初始化（延迟初始化）

        如果尚未初始化，则获取凭据并构建服务

        Args:
            db: 数据库会话（可选，用于 OAuth 2.0 授权流程）
        """
        if self._initialized:
            return

        try:
            # 获取或刷新 OAuth 2.0 凭据
            self._credentials = await self._get_credentials_async(db=db)

            # 构建 Gmail API 服务
            self._service = build("gmail", "v1", credentials=self._credentials)

            self._initialized = True
            logger.info("Gmail 发送器初始化成功（OAuth 2.0 用户授权）")
        except Exception as e:
            logger.error(f"Gmail 发送器初始化失败: {e}")
            raise EmailSendException(f"Gmail 发送器初始化失败: {str(e)}", e)

    @property
    def credentials(self) -> Credentials:
        """获取凭据（同步访问，用于兼容性）"""
        if not self._initialized:
            raise RuntimeError("Gmail 发送器尚未初始化，请先调用 _ensure_initialized()")
        return self._credentials

    @property
    def service(self):
        """获取 Gmail API 服务（同步访问，用于兼容性）"""
        if not self._initialized:
            raise RuntimeError("Gmail 发送器尚未初始化，请先调用 _ensure_initialized()")
        return self._service

    async def _get_credentials_async(self, db=None) -> Credentials:
        """
        获取或刷新 OAuth 2.0 凭据（异步版本）

        Args:
            db: 数据库会话（必需，用于从数据库读取 token）

        Returns:
            Credentials: OAuth 2.0 凭据对象

        Raises:
            EmailSendException: 如果无法获取凭据
        """
        if not db:
            raise ValueError("需要提供数据库会话以从数据库读取 token")

        creds = None

        # 从数据库读取已保存的 token
        try:
            repository = Repository(db)
            token_json = await repository.get_oauth2_token(provider="gmail")
            if token_json:
                # 从 JSON 字符串创建凭据对象
                token_dict = json.loads(token_json)
                creds = Credentials.from_authorized_user_info(token_dict, SCOPES)
                logger.debug("已从数据库加载保存的 OAuth 2.0 凭据")
        except Exception as e:
            logger.warning(f"从数据库加载保存的凭据失败: {e}，将重新授权")

        # 如果凭据不存在或已过期，进行刷新或重新授权
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # 尝试刷新过期的凭据
                try:
                    logger.info("刷新过期的 OAuth 2.0 凭据")
                    # 刷新操作需要在同步上下文中执行
                    await asyncio.to_thread(creds.refresh, Request())
                    logger.info("凭据刷新成功")
                    # 刷新后立即保存到数据库
                    if db:
                        repository = Repository(db)
                        token_json = creds.to_json()
                        await repository.save_oauth2_token(
                            token_json=token_json, provider="gmail"
                        )
                        logger.debug("已保存刷新后的凭据到数据库")
                except Exception as e:
                    logger.warning(f"凭据刷新失败: {e}，需要重新授权")
                    creds = None

            if not creds:
                # 需要重新授权
                if not os.path.exists(settings.GOOGLE_OAUTH2_CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"OAuth 2.0 凭据文件不存在: {settings.GOOGLE_OAUTH2_CREDENTIALS_FILE}"
                    )

                logger.info("启动 OAuth 2.0 授权流程（使用 FastAPI 回调）")
                await self._authorize_with_fastapi_callback()

            # 保存凭据到数据库供下次使用
            try:
                if not db:
                    raise ValueError("需要提供数据库会话以保存 token 到数据库")

                repository = Repository(db)
                token_json = creds.to_json()
                await repository.save_oauth2_token(
                    token_json=token_json, provider="gmail"
                )
                logger.info("✓ OAuth 2.0 凭据已成功保存到数据库")
            except Exception as e:
                logger.error(f"保存凭据到数据库失败: {e}", exc_info=True)
                # 保存失败不应该阻止流程，但应该记录详细错误
                raise EmailSendException(
                    f"保存 OAuth 2.0 凭据到数据库失败: {str(e)}", e
                )

        return creds

    async def _authorize_with_fastapi_callback(self):
        """
        使用 FastAPI 回调端点进行 OAuth 2.0 授权

        Returns:
            Credentials: OAuth 2.0 凭据对象

        Raises:
            EmailSendException: 如果授权失败
        """
        # 构建回调 URL
        redirect_uri = f"{settings.API_BASE_URL}/mail_manager/oauth2/callback"
        logger.info(f"使用回调 URL: {redirect_uri}")

        # 创建 OAuth 2.0 流程
        flow = InstalledAppFlow.from_client_secrets_file(
            settings.GOOGLE_OAUTH2_CREDENTIALS_FILE, SCOPES
        )
        flow.redirect_uri = redirect_uri

        # 生成授权 URL
        authorization_url, state = flow.authorization_url(
            access_type="offline",  # 获取 refresh_token
            include_granted_scopes="true",
            prompt="consent",  # 强制显示同意页面，确保获取 refresh_token
        )

        logger.info(f"授权 URL: {authorization_url}")
        logger.info("请手动在浏览器中打开上述 URL 并完成授权")

        sys.exit(0)

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
        # 确保已初始化（传入数据库会话用于 OAuth 2.0 授权）
        # 注意：send_email 方法没有 db 参数，所以这里无法传入
        # 如果初始化时需要授权，会在 _ensure_initialized 中抛出异常
        await self._ensure_initialized()

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
                    self._service.users()
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
