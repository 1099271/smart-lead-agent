"""基础响应模型"""
from pydantic import BaseModel
from typing import Optional


class BaseResponse(BaseModel):
    """API 基础响应模型"""

    success: bool
    message: str
    error: Optional[str] = None

