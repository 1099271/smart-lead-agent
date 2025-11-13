"""MailManager API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db
from schemas.mail_manager import (
    SendEmailRequest,
    SendEmailResponse,
    SendBatchEmailRequest,
    SendBatchEmailResponse,
    EmailStatusResponse,
    EmailListResponse,
)
from .service import MailManagerService
from logs import logger

# 创建路由
router = APIRouter(prefix="/mail_manager", tags=["MailManager"])


@router.post("/send", response_model=SendEmailResponse)
async def send_email(
    request: SendEmailRequest, db: AsyncSession = Depends(get_db)
):
    """
    发送单封邮件

    Args:
        request: 发送邮件请求
        db: 数据库会话

    Returns:
        SendEmailResponse: 发送结果
    """
    try:
        service = MailManagerService()
        result = await service.send_email(request, db)
        return result
    except Exception as e:
        logger.error(f"发送邮件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"发送邮件失败: {str(e)}")


@router.post("/send_batch", response_model=SendBatchEmailResponse)
async def send_batch(
    request: SendBatchEmailRequest, db: AsyncSession = Depends(get_db)
):
    """
    批量发送邮件

    Args:
        request: 批量发送请求
        db: 数据库会话

    Returns:
        SendBatchEmailResponse: 批量发送结果
    """
    try:
        service = MailManagerService()
        result = await service.send_batch(request, db)
        return result
    except Exception as e:
        logger.error(f"批量发送邮件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量发送邮件失败: {str(e)}")


@router.get("/track/{tracking_id}")
async def track_email_open(
    tracking_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    追踪像素端点

    返回 1x1 透明 PNG 图片，并记录邮件打开事件

    Args:
        tracking_id: 追踪ID
        request: FastAPI Request 对象
        db: 数据库会话

    Returns:
        Response: 1x1 PNG 图片
    """
    try:
        service = MailManagerService()
        png_data = await service.track_email_open(tracking_id, request, db)
        return Response(content=png_data, media_type="image/png")
    except Exception as e:
        # 追踪失败不影响响应，返回 PNG
        logger.error(f"追踪邮件打开失败: {e}", exc_info=True)
        from .utils import generate_1x1_png

        return Response(content=generate_1x1_png(), media_type="image/png")


@router.get("/emails/{email_id}", response_model=EmailStatusResponse)
async def get_email_status(
    email_id: int, db: AsyncSession = Depends(get_db)
):
    """
    查询邮件状态

    Args:
        email_id: 邮件ID
        db: 数据库会话

    Returns:
        EmailStatusResponse: 邮件状态信息
    """
    try:
        service = MailManagerService()
        result = await service.get_email_status(email_id, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"查询邮件状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询邮件状态失败: {str(e)}")


@router.get("/emails", response_model=EmailListResponse)
async def get_emails_list(
    status: str = None,
    limit: int = 10,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    查询邮件列表

    Args:
        status: 邮件状态（可选：pending/sending/sent/failed/bounced）
        limit: 每页数量（默认 10）
        offset: 偏移量（默认 0）
        db: 数据库会话

    Returns:
        EmailListResponse: 邮件列表
    """
    try:
        service = MailManagerService()
        result = await service.get_emails_list(status, limit, offset, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"查询邮件列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询邮件列表失败: {str(e)}")

