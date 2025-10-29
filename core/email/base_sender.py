from abc import ABC, abstractmethod
from pydantic import EmailStr

from core.schemas import GeneratedEmail, SendStatus

class BaseEmailSender(ABC):
    """
    邮件发送器的抽象基类。
    所有具体的邮件发送实现（SMTP、ESP）都应该继承这个类。
    """

    @abstractmethod
    def send(self, recipient_email: EmailStr, email_content: GeneratedEmail) -> SendStatus:
        """
        发送邮件的抽象方法。

        Args:
            recipient_email: 收件人的邮箱地址。
            email_content: 要发送的邮件内容（包含主题和正文）。

        Returns:
            SendStatus: 发送结果，包含成功/失败状态、消息ID（如果成功）和错误信息（如果失败）。
        """
        pass

