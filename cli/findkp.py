"""FindKP CLI 命令"""

import asyncio
import logging
import sys
from typing import Optional

import click
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import AsyncSessionLocal
from findkp.service import FindKPService

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


@click.command(name="findkp")
@click.option(
    "--company-name-en",
    required=True,
    help="公司英文名称",
    prompt="请输入公司英文名称",
)
@click.option(
    "--company-name-local",
    required=True,
    help="公司本地名称",
    prompt="请输入公司本地名称",
)
@click.option("--country", help="国家名称（可选）")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="显示详细日志输出",
    default=False,
)
def findkp(company_name_en: str, company_name_local: str, country: Optional[str], verbose: bool):
    """
    查找公司的关键联系人(KP)

    示例:
        smart-lead findkp --company-name-en "Apple Inc." --company-name-local "苹果公司" --country "USA"
    """
    setup_logging(verbose)

    try:
        logger.info("=" * 60)
        logger.info("FindKP - 查找公司关键联系人")
        logger.info("=" * 60)
        logger.info(f"公司英文名: {company_name_en}")
        logger.info(f"公司本地名: {company_name_local}")
        if country:
            logger.info(f"国家: {country}")
        logger.info("")

        # 运行异步任务
        result = asyncio.run(_run_findkp(company_name_en, company_name_local, country))

        # 输出结果
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ 完成！")
        logger.info("=" * 60)
        logger.info(f"公司 ID: {result['company_id']}")
        logger.info(f"公司域名: {result['company_domain'] or '未找到'}")
        logger.info(f"找到联系人数量: {len(result['contacts'])}")

        if result["contacts"]:
            logger.info("")
            logger.info("联系人列表:")
            logger.info("-" * 60)
            for i, contact in enumerate(result["contacts"], 1):
                logger.info(f"{i}. {contact.full_name or '未知'}")
                logger.info(f"   邮箱: {contact.email}")
                logger.info(f"   职位: {contact.role or '未知'}")
                logger.info(f"   部门: {contact.department or '未知'}")
                logger.info(f"   置信度: {contact.confidence_score:.2f}")
                if contact.linkedin_url:
                    logger.info(f"   LinkedIn: {contact.linkedin_url}")
                logger.info("")

        logger.info("=" * 60)
        return 0

    except KeyboardInterrupt:
        logger.error("\n用户中断操作")
        return 130
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=verbose)
        return 1


async def _run_findkp(
    company_name_en: str, company_name_local: str, country: Optional[str]
):
    """执行 FindKP 异步任务"""
    async with AsyncSessionLocal() as session:
        try:
            service = FindKPService()
            result = await service.find_kps(company_name_en, company_name_local, country, session)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            logger.error(f"FindKP 流程失败: {e}", exc_info=True)
            raise
        finally:
            await session.close()

