"""邮件发送器工厂函数"""

from typing import Optional

from ..email_sender import EmailSender
from .gmail_sender import GmailSender
from config import settings
from logs import logger


def create_email_sender(sender_type: Optional[str] = None) -> EmailSender:
    """
    创建邮件发送器实例

    Args:
        sender_type: 发送器类型（gmail/smtp），如果为 None 则从配置读取

    Returns:
        EmailSender 实例

    Raises:
        ValueError: 不支持的发送器类型
    """
    if sender_type is None:
        sender_type = settings.EMAIL_SENDER_TYPE

    sender_type = sender_type.lower()

    if sender_type == "gmail":
        logger.info("创建 Gmail 发送器实例")
        return GmailSender()
    elif sender_type == "smtp":
        # 未来实现 SMTP 发送器
        raise NotImplementedError("SMTP 发送器尚未实现")
    else:
        raise ValueError(f"不支持的邮件发送器类型: {sender_type}")

