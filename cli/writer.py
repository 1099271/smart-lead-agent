"""Writer CLI 命令"""

import asyncio
import logging
import sys
from typing import Optional

import click
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import AsyncSessionLocal
from writer.service import WriterService

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


@click.group(name="writer")
def writer_group():
    """Writer 命令组 - 生成营销邮件"""
    pass


@writer_group.command(name="generate")
@click.option(
    "--company-id",
    type=int,
    help="公司ID",
)
@click.option(
    "--company-name",
    type=str,
    help="公司名称",
)
@click.option(
    "--llm-model",
    type=str,
    help="指定 LLM 模型类型（如 gpt-4o, deepseek-chat）",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="显示详细日志输出",
    default=False,
)
def generate(
    company_id: Optional[int],
    company_name: Optional[str],
    llm_model: Optional[str],
    verbose: bool,
):
    """
    根据公司信息生成营销邮件

    示例:
        smart-lead writer generate --company-id 1
        smart-lead writer generate --company-name "Apple Inc."
        smart-lead writer generate --company-id 1 --llm-model "gpt-4o"
    """
    setup_logging(verbose)

    # 验证参数
    if not company_id and not company_name:
        logger.error("必须提供 --company-id 或 --company-name 之一")
        click.echo("错误: 必须提供 --company-id 或 --company-name 之一", err=True)
        sys.exit(1)

    try:
        logger.info("=" * 60)
        logger.info("Writer - 生成营销邮件")
        logger.info("=" * 60)
        if company_id:
            logger.info(f"公司 ID: {company_id}")
        if company_name:
            logger.info(f"公司名称: {company_name}")
        if llm_model:
            logger.info(f"LLM 模型: {llm_model}")
        logger.info("")

        # 运行异步任务
        result = asyncio.run(_run_generate(company_id, company_name, llm_model))

        # 输出结果
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ 完成！")
        logger.info("=" * 60)
        logger.info(f"公司 ID: {result['company_id']}")
        logger.info(f"公司名称: {result['company_name']}")
        logger.info(f"生成邮件数量: {len(result['emails'])}")

        if result["emails"]:
            logger.info("")
            logger.info("生成的邮件列表:")
            logger.info("-" * 60)
            for i, email in enumerate(result["emails"], 1):
                logger.info(f"{i}. 联系人: {email.contact_name or '未知'}")
                logger.info(f"   邮箱: {email.contact_email}")
                logger.info(f"   职位: {email.contact_role or '未知'}")
                logger.info(f"   主题: {email.subject or '未知'}")
                logger.info(f"   联系人ID: {email.contact_id}")
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


async def _run_generate(
    company_id: Optional[int],
    company_name: Optional[str],
    llm_model: Optional[str],
):
    """执行生成邮件异步任务"""
    async with AsyncSessionLocal() as session:
        try:
            service = WriterService(llm_model=llm_model)
            result = await service.generate_emails(
                company_id=company_id,
                company_name=company_name,
                db=session,
                llm_model=llm_model,
            )
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            logger.error(f"生成邮件流程失败: {e}", exc_info=True)
            raise
        finally:
            await session.close()


@writer_group.command(name="batch-generate")
@click.option(
    "--llm-model",
    type=str,
    help="指定 LLM 模型类型（如 gpt-4o, deepseek-chat）",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="显示详细日志输出",
    default=False,
)
def batch_generate(llm_model: Optional[str], verbose: bool):
    """
    为所有有邮箱的联系人生成邮件（按邮箱去重）

    示例:
        smart-lead writer batch-generate
        smart-lead writer batch-generate --llm-model "gpt-4o"
        smart-lead writer batch-generate --llm-model "deepseek-chat" --verbose
    """
    setup_logging(verbose)

    try:
        logger.info("=" * 60)
        logger.info("Writer - 批量生成营销邮件")
        logger.info("=" * 60)
        if llm_model:
            logger.info(f"LLM 模型: {llm_model}")
        logger.info("")

        # 运行异步任务
        result = asyncio.run(_run_batch_generate(llm_model))

        # 输出结果
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ 完成！")
        logger.info("=" * 60)
        logger.info(f"总联系人数量: {result['total_contacts']}")
        logger.info(f"生成邮件数量: {len(result['emails'])}")

        if result["emails"]:
            logger.info("")
            logger.info("生成的邮件列表（前10条）:")
            logger.info("-" * 60)
            for i, email in enumerate(result["emails"][:10], 1):
                logger.info(f"{i}. 联系人: {email.contact_name or '未知'}")
                logger.info(f"   邮箱: {email.contact_email}")
                logger.info(f"   职位: {email.contact_role or '未知'}")
                logger.info(f"   主题: {email.subject or '未知'}")
                logger.info(f"   联系人ID: {email.contact_id}")
                logger.info("")
            if len(result["emails"]) > 10:
                logger.info(f"... 还有 {len(result['emails']) - 10} 封邮件未显示")

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


async def _run_batch_generate(llm_model: Optional[str]):
    """执行批量生成邮件异步任务"""
    async with AsyncSessionLocal() as session:
        try:
            service = WriterService(llm_model=llm_model)
            result = await service.generate_emails_for_all_contacts(
                db=session,
                llm_model=llm_model,
            )
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            logger.error(f"批量生成邮件流程失败: {e}", exc_info=True)
            raise
        finally:
            await session.close()
