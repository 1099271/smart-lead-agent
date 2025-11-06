"""FindKP API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db
from schemas.contact import CompanyQuery, FindKPResponse
from .service import FindKPService
from logs import logger

# 创建路由
router = APIRouter(prefix="/findkp", tags=["FindKP"])

# 创建服务实例
service = FindKPService()


@router.post("/search", response_model=FindKPResponse)
async def find_kp(request: CompanyQuery, db: AsyncSession = Depends(get_db)):
    """
    搜索公司的关键联系人(KP)

    Args:
        request: 包含公司名称的请求
        db: 异步数据库会话

    Returns:
        FindKPResponse: 包含公司信息和联系人列表

    Raises:
        HTTPException: 当搜索失败时抛出 500 错误
    """
    try:
        logger.info(
            f"收到 FindKP 请求: {request.company_name_en}|{request.company_name_local}"
            + (f" ({request.country})" if request.country else "")
        )
        result = await service.find_kps(
            request.company_name_en, request.company_name_local, request.country, db
        )
        return FindKPResponse(
            success=True,
            company_id=result["company_id"],
            company_domain=result["company_domain"],
            contacts=result["contacts"],
            message=f"成功找到 {len(result['contacts'])} 个联系人",
        )
    except Exception as e:
        logger.error(f"FindKP 请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "module": "FindKP"}
