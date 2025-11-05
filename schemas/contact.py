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
