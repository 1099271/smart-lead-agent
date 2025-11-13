"""Compose and Send CLI 命令 - 撰写邮件并发送"""

import asyncio
import logging
import sys
from typing import Optional

import click
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import AsyncSessionLocal
from database.repository import Repository
from writer.service import WriterService
from mail_manager.service import MailManagerService
from schemas.mail_manager import SendEmailRequest

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@click.command(name="compose-and-send")
@click.option(
    "--company-id",
    type=int,
    help="公司ID（为该公司所有联系人生成并发送邮件）",
)
@click.option(
    "--contact-id",
    type=int,
    help="联系人ID（为指定联系人生成并发送邮件）",
)
def compose_and_send(
    company_id: Optional[int],
    contact_id: Optional[int],
):
    """
    为指定公司或指定联系人撰写邮件内容并发送

    示例:
        # 为指定公司的所有联系人生成并发送邮件
        smart-lead compose-and-send --company-id 1

        # 为指定联系人生成并发送邮件
        smart-lead compose-and-send --contact-id 123
    """
    # 验证参数
    if not company_id and not contact_id:
        logger.error("必须提供 --company-id 或 --contact-id 之一")
        click.echo(
            "错误: 必须提供 --company-id 或 --contact-id 之一",
            err=True,
        )
        sys.exit(1)

    if company_id and contact_id:
        logger.error("不能同时提供 --company-id 和 --contact-id")
        click.echo(
            "错误: 不能同时提供 --company-id 和 --contact-id",
            err=True,
        )
        sys.exit(1)

    try:
        logger.info("=" * 60)
        logger.info("Compose and Send - 撰写邮件并发送")
        logger.info("=" * 60)
        if company_id:
            logger.info(f"公司 ID: {company_id}")
        if contact_id:
            logger.info(f"联系人 ID: {contact_id}")
        logger.info("")

        # 运行异步任务
        result = asyncio.run(
            _run_compose_and_send(
                company_id=company_id,
                contact_id=contact_id,
            )
        )

        # 输出结果
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ 完成！")
        logger.info("=" * 60)
        logger.info(f"生成邮件数量: {result['generated_count']}")
        logger.info(f"发送成功数量: {result['sent_success_count']}")
        logger.info(f"发送失败数量: {result['sent_failed_count']}")

        if result["results"]:
            logger.info("")
            logger.info("发送结果详情:")
            logger.info("-" * 60)
            for i, email_result in enumerate(result["results"], 1):
                status_icon = "✓" if email_result["success"] else "✗"
                logger.info(
                    f"{i}. {status_icon} 联系人: {email_result['contact_name'] or '未知'}"
                )
                logger.info(f"   邮箱: {email_result['contact_email']}")
                logger.info(f"   主题: {email_result['subject'] or '未知'}")
                logger.info(f"   邮件ID: {email_result['email_id']}")
                logger.info(f"   状态: {email_result['status']}")
                if email_result.get("gmail_message_id"):
                    logger.info(f"   Gmail消息ID: {email_result['gmail_message_id']}")
                if email_result.get("error"):
                    logger.error(f"   错误: {email_result['error']}")
                logger.info("")

        logger.info("=" * 60)
        return 0 if result["sent_failed_count"] == 0 else 1

    except KeyboardInterrupt:
        logger.error("\n用户中断操作")
        return 130
    except ValueError as e:
        logger.error(f"业务逻辑错误: {e}")
        click.echo(f"错误: {e}", err=True)
        return 1
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        click.echo(f"错误: {e}", err=True)
        return 1


async def _run_compose_and_send(
    company_id: Optional[int],
    contact_id: Optional[int],
):
    """执行撰写并发送邮件异步任务"""
    async with AsyncSessionLocal() as session:
        try:
            writer_service = WriterService()
            mail_service = MailManagerService()
            repository = Repository(session)

            results = []
            generated_count = 0
            sent_success_count = 0
            sent_failed_count = 0

            # 情况1: 指定联系人
            if contact_id:
                logger.info(f"为联系人 {contact_id} 生成并发送邮件...")

                # 查询联系人
                contact = await repository.get_contact_by_id(contact_id)
                if not contact:
                    raise ValueError(f"联系人不存在: {contact_id}")

                if not contact.email:
                    raise ValueError(f"联系人 {contact_id} 没有邮箱地址")

                # 查询公司
                company = await repository.get_company_by_id(contact.company_id)
                if not company:
                    raise ValueError(f"联系人 {contact_id} 的公司不存在")

                # 生成邮件
                email_content = await writer_service._generate_email_for_contact(
                    company, contact
                )
                if not email_content:
                    raise ValueError(f"为联系人 {contact_id} 生成邮件失败")

                generated_count += 1

                # 发送邮件
                send_request = SendEmailRequest(
                    to_email=email_content.contact_email,
                    to_name=email_content.contact_name,
                    subject=email_content.subject,
                    html_content=email_content.html_content,
                    contact_id=email_content.contact_id,
                    company_id=company.id,
                )

                send_result = await mail_service.send_email(send_request, session)
                await session.commit()

                results.append(
                    {
                        "success": send_result.success,
                        "contact_id": contact.id,
                        "contact_name": contact.full_name,
                        "contact_email": contact.email,
                        "subject": email_content.subject,
                        "email_id": send_result.email_id,
                        "status": send_result.status,
                        "gmail_message_id": send_result.gmail_message_id,
                        "error": send_result.error,
                    }
                )

                if send_result.success:
                    sent_success_count += 1
                    logger.info(
                        f"✓ 邮件发送成功: {contact.email} (联系人 {contact.id})"
                    )
                else:
                    sent_failed_count += 1
                    logger.warning(
                        f"✗ 邮件发送失败: {contact.email} (联系人 {contact.id}): "
                        f"{send_result.error}"
                    )

            # 情况2: 指定公司
            elif company_id:
                logger.info(
                    f"为公司 {company_id} 的所有联系人（email不为空）生成并发送邮件..."
                )

                # 生成邮件（只发送 email 不为空的联系人）
                generate_result = await writer_service.generate_emails(
                    company_id=company_id,
                    company_name=None,
                    db=session,
                )

                generated_count = len(generate_result["emails"])
                logger.info(f"成功生成 {generated_count} 封邮件，开始发送...")

                if not generate_result["emails"]:
                    logger.warning("没有生成任何邮件")
                    return {
                        "generated_count": 0,
                        "sent_success_count": 0,
                        "sent_failed_count": 0,
                        "results": [],
                    }

                # 批量发送邮件（每个邮件独立提交，确保可靠性）
                for email_content in generate_result["emails"]:
                    send_request = SendEmailRequest(
                        to_email=email_content.contact_email,
                        to_name=email_content.contact_name,
                        subject=email_content.subject,
                        html_content=email_content.html_content,
                        contact_id=email_content.contact_id,
                        company_id=generate_result["company_id"],
                    )

                    try:
                        send_result = await mail_service.send_email(
                            send_request, session
                        )
                        # 每个邮件发送后立即提交，确保已发送的邮件不会丢失
                        await session.commit()

                        results.append(
                            {
                                "success": send_result.success,
                                "contact_id": email_content.contact_id,
                                "contact_name": email_content.contact_name,
                                "contact_email": email_content.contact_email,
                                "subject": email_content.subject,
                                "email_id": send_result.email_id,
                                "status": send_result.status,
                                "gmail_message_id": send_result.gmail_message_id,
                                "error": send_result.error,
                            }
                        )

                        if send_result.success:
                            sent_success_count += 1
                            logger.info(
                                f"✓ 邮件发送成功: {email_content.contact_email} "
                                f"(联系人 {email_content.contact_id})"
                            )
                        else:
                            sent_failed_count += 1
                            logger.warning(
                                f"✗ 邮件发送失败: {email_content.contact_email} "
                                f"(联系人 {email_content.contact_id}): {send_result.error}"
                            )

                    except Exception as e:
                        # 发送异常时回滚当前事务
                        await session.rollback()
                        logger.error(
                            f"发送邮件异常 (联系人 {email_content.contact_id}): {e}",
                            exc_info=True,
                        )
                        sent_failed_count += 1
                        results.append(
                            {
                                "success": False,
                                "contact_id": email_content.contact_id,
                                "contact_name": email_content.contact_name,
                                "contact_email": email_content.contact_email,
                                "subject": email_content.subject,
                                "email_id": 0,
                                "status": "failed",
                                "gmail_message_id": None,
                                "error": str(e),
                            }
                        )

            return {
                "generated_count": generated_count,
                "sent_success_count": sent_success_count,
                "sent_failed_count": sent_failed_count,
                "results": results,
            }

        except Exception as e:
            await session.rollback()
            logger.error(f"撰写并发送邮件流程失败: {e}", exc_info=True)
            raise
        finally:
            await session.close()
