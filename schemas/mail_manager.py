"""MailManager 模块的数据模型"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional, List

from .base import BaseResponse


class SendEmailRequest(BaseModel):
    """发送邮件请求模型"""

    # 收件人信息
    to_email: EmailStr
    to_name: Optional[str] = None

    # 邮件内容（方式1: 直接提供）
    subject: Optional[str] = None
    html_content: Optional[str] = None

    # 关联信息（方式2: 从 Writer 模块获取）
    contact_id: Optional[int] = None
    company_id: Optional[int] = None

    # 发件人信息（可选，默认使用配置）
    from_email: Optional[str] = None
    from_name: Optional[str] = None

    @model_validator(mode="after")
    def validate_at_least_one(self):
        """验证至少提供邮件内容或 contact_id 之一"""
        has_content = self.subject and self.html_content
        has_contact = self.contact_id is not None

        if not has_content and not has_contact:
            raise ValueError("必须提供邮件内容（subject + html_content）或 contact_id 之一")
        return self


class SendBatchEmailRequest(BaseModel):
    """批量发送邮件请求模型"""

    emails: List[SendEmailRequest]
    rate_limit: Optional[int] = None  # 覆盖全局配置


class SendEmailResponse(BaseResponse):
    """发送邮件响应模型"""

    email_id: int
    tracking_id: str
    status: str
    gmail_message_id: Optional[str] = None
    sent_at: Optional[datetime] = None


class SendBatchEmailResponse(BaseResponse):
    """批量发送邮件响应模型"""

    total: int
    success_count: int
    failed: int
    results: List[SendEmailResponse]


class EmailTrackingEvent(BaseModel):
    """邮件追踪事件模型"""

    event_type: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


class EmailStatusResponse(BaseResponse):
    """邮件状态响应模型"""

    email_id: int
    status: str
    to_email: str
    subject: str
    sent_at: Optional[datetime] = None
    first_opened_at: Optional[datetime] = None
    open_count: int
    tracking_events: List[EmailTrackingEvent] = []


class EmailListResponse(BaseResponse):
    """邮件列表响应模型"""

    emails: List[EmailStatusResponse] = []
    total: int
    limit: int
    offset: int

