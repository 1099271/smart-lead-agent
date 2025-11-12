"""Writer API 路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db
from schemas.writer import (
    GenerateEmailRequest,
    GenerateEmailResponse,
)
from .service import WriterService
from logs import logger

# 创建路由
router = APIRouter(prefix="/writer", tags=["Writer"])


@router.post("/generate", response_model=GenerateEmailResponse)
async def generate_emails(
    request: GenerateEmailRequest, db: AsyncSession = Depends(get_db)
):
    """
    根据公司信息生成营销邮件

    Args:
        request: 包含公司ID或公司名称的请求，可指定 LLM 模型类型
        db: 异步数据库会话

    Returns:
        GenerateEmailResponse: 包含公司信息和生成的邮件列表

    Raises:
        HTTPException: 当公司不存在时抛出 404 错误，其他错误抛出 500
    """
    try:
        logger.info(
            f"收到 Writer 请求: company_id={request.company_id}, "
            f"company_name={request.company_name}, "
            f"llm_model={request.llm_model}"
        )

        # 创建服务实例（如果指定了 LLM 模型，在初始化时传入）
        service = WriterService(llm_model=request.llm_model)

        result = await service.generate_emails(
            company_id=request.company_id,
            company_name=request.company_name,
            db=db,
            llm_model=request.llm_model,
        )

        return GenerateEmailResponse(
            success=True,
            company_id=result["company_id"],
            company_name=result["company_name"],
            emails=result["emails"],
            message=f"成功生成 {len(result['emails'])} 封邮件",
        )

    except ValueError as e:
        # 公司不存在或其他业务逻辑错误
        logger.warning(f"Writer 请求失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Writer 请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"生成邮件失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "module": "Writer"}
