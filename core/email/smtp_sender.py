import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import EmailStr
from typing import Optional

from core.schemas import GeneratedEmail, SendStatus
from core.email.base_sender import BaseEmailSender
from config import settings

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SMTPEmailSender(BaseEmailSender):
    """
    使用标准SMTP协议发送邮件的实现。
    注意：SMTP不支持邮件跟踪功能（打开率、点击率、退信率）。
    """

    def __init__(self):
        """初始化SMTP发送器，从配置中读取SMTP设置。"""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.sender_email = settings.SENDER_EMAIL

        if not all([self.smtp_host, self.smtp_port, self.smtp_user, self.smtp_password, self.sender_email]):
            raise ValueError(
                "SMTP configuration is incomplete. "
                "Please provide SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and SENDER_EMAIL."
            )

    def send(self, recipient_email: EmailStr, email_content: GeneratedEmail) -> SendStatus:
        """
        使用SMTP发送邮件。

        Args:
            recipient_email: 收件人的邮箱地址。
            email_content: 要发送的邮件内容。

        Returns:
            SendStatus: 发送结果。
        """
        try:
            # 创建邮件消息
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = recipient_email
            msg["Subject"] = email_content.subject

            # 添加邮件正文（支持 HTML 格式）
            # 检测是否为 HTML 内容
            if "<html>" in email_content.body or "<!DOCTYPE html>" in email_content.body:
                msg.attach(MIMEText(email_content.body, "html"))
            else:
                msg.attach(MIMEText(email_content.body, "plain"))

            # 连接SMTP服务器并发送邮件
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()  # 启用TLS加密
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {recipient_email}")
            return SendStatus(
                success=True,
                message_id=None,  # SMTP不提供消息ID
                error=None,
            )

        except smtplib.SMTPException as e:
            error_msg = f"SMTP error occurred: {str(e)}"
            logger.error(error_msg)
            return SendStatus(success=False, message_id=None, error=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error occurred: {str(e)}"
            logger.error(error_msg)
            return SendStatus(success=False, message_id=None, error=error_msg)

