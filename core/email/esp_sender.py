import logging
from pydantic import EmailStr
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from core.schemas import GeneratedEmail, SendStatus
from core.email.base_sender import BaseEmailSender
from config import settings

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ESPEmailSender(BaseEmailSender):
    """
    使用邮件服务提供商（ESP）发送邮件的实现。
    当前实现使用 SendGrid API。

    优点：
    - 支持邮件跟踪（打开率、点击率、退信率）
    - 更好的送达率
    - 通过Webhook接收邮件事件
    """

    def __init__(self):
        """初始化ESP发送器，从配置中读取SendGrid API密钥。"""
        self.api_key = settings.SENDGRID_API_KEY
        self.sender_email = settings.ESP_SENDER_EMAIL

        if not self.api_key:
            raise ValueError(
                "SENDGRID_API_KEY is not set. "
                "Please provide a valid SendGrid API key in your .env file."
            )

        if not self.sender_email:
            raise ValueError(
                "ESP_SENDER_EMAIL is not set. "
                "Please provide a verified sender email address in your .env file."
            )

        self.client = SendGridAPIClient(self.api_key)

    def send(self, recipient_email: EmailStr, email_content: GeneratedEmail) -> SendStatus:
        """
        使用SendGrid API发送邮件。

        Args:
            recipient_email: 收件人的邮箱地址。
            email_content: 要发送的邮件内容。

        Returns:
            SendStatus: 发送结果，包含SendGrid返回的消息ID。
        """
        try:
            # 构建SendGrid邮件对象
            message = Mail(
                from_email=Email(self.sender_email),
                to_emails=To(recipient_email),
                subject=email_content.subject,
                plain_text_content=Content("text/plain", email_content.body),
            )

            # 发送邮件
            response = self.client.send(message)

            # SendGrid返回的状态码200-299表示成功
            if 200 <= response.status_code < 300:
                # 从响应头中提取消息ID（如果可用）
                message_id = None
                if hasattr(response, "headers") and "X-Message-Id" in response.headers:
                    message_id = response.headers["X-Message-Id"]

                logger.info(
                    f"Email sent successfully to {recipient_email} via SendGrid. "
                    f"Status: {response.status_code}, Message ID: {message_id}"
                )
                return SendStatus(
                    success=True,
                    message_id=message_id,
                    error=None,
                )
            else:
                error_msg = (
                    f"SendGrid API returned error status {response.status_code}. "
                    f"Response body: {response.body}"
                )
                logger.error(error_msg)
                return SendStatus(success=False, message_id=None, error=error_msg)

        except Exception as e:
            error_msg = f"Unexpected error occurred while sending email via SendGrid: {str(e)}"
            logger.error(error_msg)
            return SendStatus(success=False, message_id=None, error=error_msg)

