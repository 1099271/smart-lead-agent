"""邮件发送器抽象基类"""

from abc import ABC, abstractmethod
from typing import Optional


class EmailSendException(Exception):
    """邮件发送异常"""

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception


class EmailSender(ABC):
    """邮件发送器抽象基类"""

    @abstractmethod
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
        发送邮件

        Args:
            to_email: 收件人邮箱
            to_name: 收件人姓名（可选）
            from_email: 发件人邮箱
            from_name: 发件人姓名（可选）
            subject: 邮件主题
            html_content: HTML 内容
            text_content: 纯文本内容（可选）

        Returns:
            message_id: 邮件消息ID或唯一标识符

        Raises:
            EmailSendException: 发送失败时抛出
        """
        pass

