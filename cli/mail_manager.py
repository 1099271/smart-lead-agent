"""MailManager CLI 命令"""

import asyncio
import logging
import sys
from typing import Optional

import click
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import AsyncSessionLocal
from mail_manager.service import MailManagerService
from schemas.mail_manager import SendEmailRequest, SendBatchEmailRequest

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool):
    """设置日志级别"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("启用详细日志模式")
    else:
        logging.getLogger().setLevel(logging.INFO)


@click.group(name="mail")
def mail_group():
    """MailManager 命令组 - 邮件发送和追踪"""
    pass


@mail_group.command(name="send")
@click.option(
    "--to-email",
    type=str,
    required=True,
    help="收件人邮箱",
)
@click.option(
    "--to-name",
    type=str,
    help="收件人姓名",
)
@click.option(
    "--subject",
    type=str,
    help="邮件主题（如果提供邮件内容）",
)
@click.option(
    "--html-content",
    type=str,
    help="HTML 邮件内容（如果提供邮件内容）",
)
@click.option(
    "--contact-id",
    type=int,
    help="联系人ID（从 Writer 模块获取邮件内容）",
)
@click.option(
    "--from-email",
    type=str,
    help="发件人邮箱（可选，默认使用配置）",
)
@click.option(
    "--from-name",
    type=str,
    help="发件人姓名（可选，默认使用配置）",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="显示详细日志输出",
    default=False,
)
def send(
    to_email: str,
    to_name: Optional[str],
    subject: Optional[str],
    html_content: Optional[str],
    contact_id: Optional[int],
    from_email: Optional[str],
    from_name: Optional[str],
    verbose: bool,
):
    """
    发送单封邮件

    示例:
        # 直接提供邮件内容
        smart-lead mail send --to-email "test@example.com" --subject "测试邮件" --html-content "<html>...</html>"

        # 从 Writer 模块获取邮件内容
        smart-lead mail send --to-email "test@example.com" --contact-id 123
    """
    setup_logging(verbose)

    # 验证参数
    has_content = subject and html_content
    has_contact = contact_id is not None

    if not has_content and not has_contact:
        logger.error(
            "必须提供邮件内容（--subject + --html-content）或 --contact-id 之一"
        )
        click.echo(
            "错误: 必须提供邮件内容（--subject + --html-content）或 --contact-id 之一",
            err=True,
        )
        sys.exit(1)

    try:
        logger.info("=" * 60)
        logger.info("MailManager - 发送邮件")
        logger.info("=" * 60)
        logger.info(f"收件人: {to_email}")
        if to_name:
            logger.info(f"收件人姓名: {to_name}")
        if contact_id:
            logger.info(f"联系人ID: {contact_id}")
        if subject:
            logger.info(f"邮件主题: {subject}")
        logger.info("")

        # 构建请求
        request = SendEmailRequest(
            to_email=to_email,
            to_name=to_name,
            subject=subject,
            html_content=html_content,
            contact_id=contact_id,
            from_email=from_email,
            from_name=from_name,
        )

        # 运行异步任务
        result = asyncio.run(_run_send(request))

        # 输出结果
        logger.info("")
        logger.info("=" * 60)
        if result.success:
            logger.info("✓ 邮件发送成功！")
        else:
            logger.info("✗ 邮件发送失败")
        logger.info("=" * 60)
        logger.info(f"邮件ID: {result.email_id}")
        logger.info(f"追踪ID: {result.tracking_id}")
        logger.info(f"状态: {result.status}")
        if result.gmail_message_id:
            logger.info(f"Mail消息ID: {result.gmail_message_id}")
        if result.sent_at:
            logger.info(f"发送时间: {result.sent_at}")
        if result.error:
            logger.error(f"错误信息: {result.error}")

        logger.info("=" * 60)
        return 0 if result.success else 1

    except KeyboardInterrupt:
        logger.error("\n用户中断操作")
        return 130
    except ValueError as e:
        logger.error(f"业务逻辑错误: {e}")
        click.echo(f"错误: {e}", err=True)
        return 1
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=verbose)
        click.echo(f"错误: {e}", err=True)
        return 1


async def _run_send(request: SendEmailRequest):
    """执行发送邮件异步任务"""
    async with AsyncSessionLocal() as session:
        try:
            service = MailManagerService()
            result = await service.send_email(request, session)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            logger.error(f"发送邮件流程失败: {e}", exc_info=True)
            raise
        finally:
            await session.close()


@mail_group.command(name="status")
@click.option(
    "--email-id",
    type=int,
    required=True,
    help="邮件ID",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="显示详细日志输出",
    default=False,
)
def status(email_id: int, verbose: bool):
    """
    查询邮件状态

    示例:
        smart-lead mail status --email-id 1
    """
    setup_logging(verbose)

    try:
        logger.info("=" * 60)
        logger.info("MailManager - 查询邮件状态")
        logger.info("=" * 60)
        logger.info(f"邮件ID: {email_id}")
        logger.info("")

        # 运行异步任务
        result = asyncio.run(_run_status(email_id))

        # 输出结果
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ 查询成功！")
        logger.info("=" * 60)
        logger.info(f"邮件ID: {result.email_id}")
        logger.info(f"状态: {result.status}")
        logger.info(f"收件人: {result.to_email}")
        logger.info(f"主题: {result.subject}")
        if result.sent_at:
            logger.info(f"发送时间: {result.sent_at}")
        if result.first_opened_at:
            logger.info(f"首次打开时间: {result.first_opened_at}")
        logger.info(f"打开次数: {result.open_count}")

        if result.tracking_events:
            logger.info("")
            logger.info("追踪事件:")
            logger.info("-" * 60)
            for i, event in enumerate(result.tracking_events, 1):
                logger.info(f"{i}. 事件类型: {event.event_type}")
                logger.info(f"   时间: {event.created_at}")
                if event.ip_address:
                    logger.info(f"   IP地址: {event.ip_address}")
                if event.user_agent:
                    logger.info(f"   User-Agent: {event.user_agent[:50]}...")
                logger.info("")

        logger.info("=" * 60)
        return 0

    except KeyboardInterrupt:
        logger.error("\n用户中断操作")
        return 130
    except ValueError as e:
        logger.error(f"业务逻辑错误: {e}")
        click.echo(f"错误: {e}", err=True)
        return 1
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=verbose)
        click.echo(f"错误: {e}", err=True)
        return 1


async def _run_status(email_id: int):
    """执行查询邮件状态异步任务"""
    async with AsyncSessionLocal() as session:
        try:
            service = MailManagerService()
            result = await service.get_email_status(email_id, session)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            logger.error(f"查询邮件状态流程失败: {e}", exc_info=True)
            raise
        finally:
            await session.close()


@mail_group.command(name="list")
@click.option(
    "--status",
    type=click.Choice(["pending", "sending", "sent", "failed", "bounced"]),
    help="邮件状态筛选",
)
@click.option(
    "--limit",
    type=int,
    default=10,
    help="每页数量（默认10）",
)
@click.option(
    "--offset",
    type=int,
    default=0,
    help="偏移量（默认0）",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="显示详细日志输出",
    default=False,
)
def list_emails(status: Optional[str], limit: int, offset: int, verbose: bool):
    """
    查询邮件列表

    示例:
        smart-lead mail list
        smart-lead mail list --status sent --limit 20
    """
    setup_logging(verbose)

    try:
        logger.info("=" * 60)
        logger.info("MailManager - 查询邮件列表")
        logger.info("=" * 60)
        if status:
            logger.info(f"状态筛选: {status}")
        logger.info(f"每页数量: {limit}")
        logger.info(f"偏移量: {offset}")
        logger.info("")

        # 运行异步任务
        result = asyncio.run(_run_list(status, limit, offset))

        # 输出结果
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ 查询成功！")
        logger.info("=" * 60)
        logger.info(f"总数: {result.total}")
        logger.info(f"当前页: {len(result.emails)} 条")

        if result.emails:
            logger.info("")
            logger.info("邮件列表:")
            logger.info("-" * 60)
            for i, email in enumerate(result.emails, 1):
                logger.info(f"{i}. 邮件ID: {email.email_id}")
                logger.info(f"   状态: {email.status}")
                logger.info(f"   收件人: {email.to_email}")
                logger.info(f"   主题: {email.subject}")
                if email.sent_at:
                    logger.info(f"   发送时间: {email.sent_at}")
                if email.first_opened_at:
                    logger.info(f"   首次打开: {email.first_opened_at}")
                logger.info(f"   打开次数: {email.open_count}")
                logger.info("")

        logger.info("=" * 60)
        return 0

    except KeyboardInterrupt:
        logger.error("\n用户中断操作")
        return 130
    except ValueError as e:
        logger.error(f"业务逻辑错误: {e}")
        click.echo(f"错误: {e}", err=True)
        return 1
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=verbose)
        click.echo(f"错误: {e}", err=True)
        return 1


async def _run_list(status: Optional[str], limit: int, offset: int):
    """执行查询邮件列表异步任务"""
    async with AsyncSessionLocal() as session:
        try:
            service = MailManagerService()
            result = await service.get_emails_list(status, limit, offset, session)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            logger.error(f"查询邮件列表流程失败: {e}", exc_info=True)
            raise
        finally:
            await session.close()
