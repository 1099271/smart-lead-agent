from pydantic import BaseModel, EmailStr, HttpUrl
from typing import List, Optional


class SearchResult(BaseModel):
    """单条搜索结果的结构"""

    title: str
    link: HttpUrl
    snippet: str


class ContactInfo(BaseModel):
    """从分析中提取出的结构化联系人信息"""

    full_name: Optional[str] = None
    email: EmailStr
    linkedin_url: Optional[HttpUrl] = None
    role: Optional[str] = None
    source: HttpUrl  # 信息来源URL


class GeneratedEmail(BaseModel):
    """生成的邮件内容"""

    subject: str
    body: str


class SendStatus(BaseModel):
    """邮件发送结果"""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
