"""MailManager 业务逻辑服务"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request

from database.repository import Repository
from database.models import EmailStatus, EmailTrackingEventType
from schemas.mail_manager import (
    SendEmailRequest,
    SendEmailResponse,
    SendBatchEmailRequest,
    SendBatchEmailResponse,
    EmailStatusResponse,
    EmailListResponse,
    EmailTrackingEvent,
)
from writer.service import WriterService
from .email_sender import EmailSender, EmailSendException
from .senders.factory import create_email_sender
from .utils import (
    generate_tracking_id,
    generate_tracking_pixel_url,
    embed_tracking_pixel,
    generate_1x1_png,
)
from config import settings
from logs import logger


class MailManagerService:
    """MailManager 服务类，负责邮件发送和追踪"""

    def __init__(self):
        """初始化 MailManager 服务"""
        # 通过工厂函数创建邮件发送器
        self.email_sender: EmailSender = create_email_sender()
        self.writer_service = WriterService()

    async def send_email(
        self, request: SendEmailRequest, db: AsyncSession
    ) -> SendEmailResponse:
        """
        发送单封邮件

        Args:
            request: 发送邮件请求
            db: 数据库会话

        Returns:
            SendEmailResponse: 发送结果
        """
        repository = Repository(db)

        try:
            # 1. 获取邮件内容
            subject: str
            html_content: str
            text_content: Optional[str] = None
            contact_id: Optional[int] = None
            company_id: Optional[int] = None

            if request.subject and request.html_content:
                # 方式1: 直接提供邮件内容
                subject = request.subject
                html_content = request.html_content
                contact_id = request.contact_id
                company_id = request.company_id
            else:
                raise ValueError("必须提供邮件内容或 contact_id")

            # 2. 生成追踪ID和追踪像素
            tracking_id = generate_tracking_id()
            tracking_url = None

            if settings.TRACKING_ENABLED:
                tracking_url = generate_tracking_pixel_url(tracking_id)
                html_content = embed_tracking_pixel(html_content, tracking_url)

            # 3. 获取发件人信息
            from_email = request.from_email or settings.SENDER_EMAIL
            from_name = request.from_name or settings.SENDER_NAME

            if not from_email:
                raise ValueError("发件人邮箱未配置")

            # 4. 创建邮件记录（pending 状态）
            email_record = await repository.create_email_record(
                contact_id=contact_id,
                company_id=company_id,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                to_email=request.to_email,
                to_name=request.to_name,
                from_email=from_email,
                from_name=from_name,
                tracking_id=tracking_id,
                tracking_pixel_url=tracking_url,
                status=EmailStatus.pending,
            )

            # 5. 更新状态为 sending
            await repository.update_email_status(email_record.id, EmailStatus.sending)

            # 6. 调用邮件发送器发送
            try:
                message_id = await self.email_sender.send_email(
                    to_email=request.to_email,
                    to_name=request.to_name,
                    from_email=from_email,
                    from_name=from_name,
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                )

                # 7. 发送成功，更新状态
                sent_at = datetime.now()
                await repository.update_email_sent_info(
                    email_record.id, message_id, sent_at
                )

                logger.info(
                    f"邮件发送成功: email_id={email_record.id}, "
                    f"to={request.to_email}, message_id={message_id}"
                )

                return SendEmailResponse(
                    success=True,
                    message="邮件发送成功",
                    email_id=email_record.id,
                    tracking_id=tracking_id,
                    status="sent",
                    gmail_message_id=message_id,
                    sent_at=sent_at,
                )

            except EmailSendException as e:
                # 发送失败，更新状态
                error_msg = str(e)
                await repository.update_email_status(
                    email_record.id, EmailStatus.failed, error_message=error_msg
                )

                logger.error(
                    f"邮件发送失败: email_id={email_record.id}, "
                    f"to={request.to_email}, error={error_msg}"
                )

                return SendEmailResponse(
                    success=False,
                    message="邮件发送失败",
                    error=error_msg,
                    email_id=email_record.id,
                    tracking_id=tracking_id,
                    status="failed",
                )

        except Exception as e:
            logger.error(f"发送邮件时发生错误: {e}", exc_info=True)
            raise

    async def send_batch(
        self, request: SendBatchEmailRequest, db: AsyncSession
    ) -> SendBatchEmailResponse:
        """
        批量发送邮件

        Args:
            request: 批量发送请求
            db: 数据库会话

        Returns:
            SendBatchEmailResponse: 批量发送结果
        """
        # 检查每日发送上限
        if settings.EMAIL_DAILY_LIMIT > 0:
            repository = Repository(db)
            daily_count = await repository.get_daily_sent_count()
            if daily_count >= settings.EMAIL_DAILY_LIMIT:
                raise ValueError(
                    f"已达到每日发送上限: {daily_count}/{settings.EMAIL_DAILY_LIMIT}"
                )

        # 确定速率限制
        rate_limit = request.rate_limit or settings.EMAIL_SEND_RATE_LIMIT
        semaphore = asyncio.Semaphore(rate_limit)

        # 并发发送邮件
        async def send_with_semaphore(email_request: SendEmailRequest):
            async with semaphore:
                return await self.send_email(email_request, db)

        tasks = [send_with_semaphore(email_req) for email_req in request.emails]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        success_count = 0
        failed_count = 0
        response_results: List[SendEmailResponse] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_count += 1
                logger.error(f"批量发送第 {i+1} 封邮件失败: {result}")
                # 创建一个失败的响应
                response_results.append(
                    SendEmailResponse(
                        success=False,
                        message="发送失败",
                        error=str(result),
                        email_id=0,
                        tracking_id="",
                        status="failed",
                    )
                )
            else:
                if result.success:
                    success_count += 1
                else:
                    failed_count += 1
                response_results.append(result)

        return SendBatchEmailResponse(
            success=True,
            message=f"批量发送完成: 成功 {success_count}, 失败 {failed_count}",
            total=len(request.emails),
            success_count=success_count,
            failed=failed_count,
            results=response_results,
        )

    async def track_email_open(
        self, tracking_id: str, request: Request, db: AsyncSession
    ) -> bytes:
        """
        处理邮件打开追踪请求

        Args:
            tracking_id: 追踪ID
            request: FastAPI Request 对象
            db: 数据库会话

        Returns:
            1x1 透明 PNG 图片字节
        """
        repository = Repository(db)

        try:
            # 查找邮件
            email = await repository.get_email_by_tracking_id(tracking_id)

            if not email:
                logger.warning(f"追踪ID不存在: {tracking_id}")
                # 即使邮件不存在，也返回 PNG（避免暴露信息）
                return generate_1x1_png()

            # 获取请求信息
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            referer = request.headers.get("referer")

            # 创建追踪事件
            opened_at = datetime.now()
            await repository.create_tracking_event(
                email_id=email.id,
                event_type=EmailTrackingEventType.opened,
                ip_address=ip_address,
                user_agent=user_agent,
                referer=referer,
            )

            # 更新首次打开时间
            await repository.update_email_first_opened_at(email.id, opened_at)

            logger.debug(
                f"邮件打开追踪: email_id={email.id}, "
                f"tracking_id={tracking_id}, ip={ip_address}"
            )

        except Exception as e:
            # 追踪失败不影响响应，记录日志即可
            logger.error(f"追踪邮件打开时发生错误: {e}", exc_info=True)

        # 始终返回 PNG
        return generate_1x1_png()

    async def get_email_status(
        self, email_id: int, db: AsyncSession
    ) -> EmailStatusResponse:
        """
        查询邮件状态

        Args:
            email_id: 邮件ID
            db: 数据库会话

        Returns:
            EmailStatusResponse: 邮件状态信息
        """
        repository = Repository(db)

        email = await repository.get_email_by_id(email_id)
        if not email:
            raise ValueError(f"邮件不存在: {email_id}")

        # 查询追踪事件
        tracking_events = await repository.get_email_tracking_events(email_id)

        # 统计打开次数
        open_count = sum(
            1
            for event in tracking_events
            if event.event_type == EmailTrackingEventType.opened
        )

        # 转换为响应模型
        event_models = [
            EmailTrackingEvent(
                event_type=event.event_type.value,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                created_at=event.created_at,
            )
            for event in tracking_events
        ]

        return EmailStatusResponse(
            success=True,
            message="查询成功",
            email_id=email.id,
            status=email.status.value,
            to_email=email.to_email,
            subject=email.subject,
            sent_at=email.sent_at,
            first_opened_at=email.first_opened_at,
            open_count=open_count,
            tracking_events=event_models,
        )

    async def get_emails_list(
        self,
        status: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        db: AsyncSession = None,
    ) -> EmailListResponse:
        """
        查询邮件列表

        Args:
            status: 邮件状态（可选）
            limit: 每页数量
            offset: 偏移量
            db: 数据库会话

        Returns:
            EmailListResponse: 邮件列表
        """
        repository = Repository(db)

        # 转换状态字符串为枚举
        status_enum = None
        if status:
            try:
                status_enum = EmailStatus[status]
            except KeyError:
                raise ValueError(f"无效的邮件状态: {status}")

        # 查询邮件列表
        emails = await repository.get_emails_by_status(
            status=status_enum, limit=limit, offset=offset
        )

        # 转换为响应模型
        email_responses = []
        for email in emails:
            # 查询追踪事件
            tracking_events = await repository.get_email_tracking_events(email.id)
            open_count = sum(
                1
                for event in tracking_events
                if event.event_type == EmailTrackingEventType.opened
            )

            event_models = [
                EmailTrackingEvent(
                    event_type=event.event_type.value,
                    ip_address=event.ip_address,
                    user_agent=event.user_agent,
                    created_at=event.created_at,
                )
                for event in tracking_events
            ]

            email_responses.append(
                EmailStatusResponse(
                    success=True,
                    message="",
                    email_id=email.id,
                    status=email.status.value,
                    to_email=email.to_email,
                    subject=email.subject,
                    sent_at=email.sent_at,
                    first_opened_at=email.first_opened_at,
                    open_count=open_count,
                    tracking_events=event_models,
                )
            )

        return EmailListResponse(
            success=True,
            message="查询成功",
            emails=email_responses,
            total=len(email_responses),
            limit=limit,
            offset=offset,
        )
