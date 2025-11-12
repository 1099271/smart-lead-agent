"""Writer 模块的数据模型"""

from pydantic import BaseModel, model_validator
from typing import Optional, List
from .base import BaseResponse


class GenerateEmailRequest(BaseModel):
    """生成邮件请求模型"""

    company_id: Optional[int] = None
    company_name: Optional[str] = None

    @model_validator(mode="after")
    def validate_at_least_one(self):
        """验证至少提供一个参数"""
        if not self.company_id and not self.company_name:
            raise ValueError("必须提供 company_id 或 company_name 之一")
        return self


class GeneratedEmail(BaseModel):
    """生成的邮件模型"""

    contact_id: int
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_role: Optional[str] = None
    subject: str  # 邮件主题
    content_en: str  # 英文邮件正文
    content_vn: str  # 越南语邮件正文
    full_content: str  # 完整双语内容（英文 + 越南语）


class GenerateEmailResponse(BaseResponse):
    """生成邮件响应模型"""

    company_id: int
    company_name: str
    emails: List[GeneratedEmail] = []
