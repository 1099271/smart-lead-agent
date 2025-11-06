"""联系人相关数据模型"""

from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional, List
from .base import BaseResponse


class CompanyQuery(BaseModel):
    """FindKP API 输入"""

    company_name_en: str
    company_name_local: str
    country: Optional[str] = None


class KPInfo(BaseModel):
    """单个 KP 信息"""

    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    department: Optional[str] = None  # "采购" or "销售"
    linkedin_url: Optional[HttpUrl] = None
    twitter_url: Optional[HttpUrl] = None
    source: str
    confidence_score: float = 0.0


class FindKPResponse(BaseResponse):
    """FindKP API 输出"""

    company_id: int
    company_domain: Optional[str] = None
    contacts: List[KPInfo] = []


# 结构化输出响应模型（用于 LangChain with_structured_output）
class ContactInfo(BaseModel):
    """单个联系人信息（用于 LLM 结构化输出）"""
    
    full_name: Optional[str] = None
    email: Optional[str] = None  # 使用 str 而不是 EmailStr，因为 LLM 可能返回无效邮箱
    role: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    confidence_score: float = 0.0


class ContactsResponse(BaseModel):
    """联系人列表响应（用于 LLM 结构化输出）"""
    
    contacts: List[ContactInfo] = []


class CompanyInfoResponse(BaseModel):
    """公司信息响应（用于 LLM 结构化输出）"""
    
    domain: Optional[str] = None
    industry: Optional[str] = None
    positioning: Optional[str] = None
    brief: Optional[str] = None
