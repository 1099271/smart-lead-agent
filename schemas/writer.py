"""Writer 模块的数据模型"""

from pydantic import BaseModel, model_validator
from typing import Optional, List
from .base import BaseResponse


class GenerateEmailRequest(BaseModel):
    """生成邮件请求模型"""

    company_id: Optional[int] = None
    company_name: Optional[str] = None
    llm_model: Optional[str] = None  # 指定 LLM 模型类型

    @model_validator(mode="after")
    def validate_at_least_one(self):
        """验证至少提供一个参数"""
        if not self.company_id and not self.company_name:
            raise ValueError("必须提供 company_id 或 company_name 之一")
        return self


class EmailContent(BaseModel):
    """邮件内容数据结构（包含完整邮件信息）"""

    contact_id: int  # 联系人ID
    contact_name: Optional[str] = None  # 联系人姓名
    contact_email: str  # 收件地址（必需）
    contact_role: Optional[str] = None  # 联系人职位
    subject: str  # 邮件主题（从 HTML 中提取的越南语主题行）
    html_content: str  # 完整的 HTML 邮件内容


class GeneratedEmail(BaseModel):
    """生成的邮件模型（支持 HTML）- 兼容旧版本"""

    contact_id: int
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_role: Optional[str] = None
    subject: str  # 邮件主题（从 HTML 中提取的越南语主题行）
    html_content: str  # 完整的 HTML 邮件内容（直接用于邮件发送）


class GenerateEmailResponse(BaseResponse):
    """生成邮件响应模型"""

    company_id: int
    company_name: str
    emails: List[EmailContent] = []  # 使用新的 EmailContent 模型
