"""批量 FindKP CLI 命令 - 从 trade_records 表中批量查询并执行 FindKP"""

import asyncio
import logging
from typing import Set, Tuple

import click
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import AsyncSessionLocal
from database.models import TradeRecord
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


@click.command(name="batch-findkp")
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="显示详细日志输出",
    default=False,
)
def batch_findkp(verbose: bool):
    """
    批量从 trade_records 表中查询公司并执行 FindKP 操作

    示例:
        smart-lead batch-findkp
        smart-lead batch-findkp --verbose
    """
    setup_logging(verbose)

    try:
        logger.info("=" * 60)
        logger.info("批量 FindKP - 从 trade_records 批量处理")
        logger.info("=" * 60)
        logger.info("")

        # 运行异步任务
        result = asyncio.run(_run_batch_findkp(verbose))

        # 输出结果统计
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ 批量处理完成！")
        logger.info("=" * 60)
        logger.info(f"总处理公司数: {result['total']}")
        logger.info(f"成功处理: {result['success']}")
        logger.info(f"失败数量: {result['failed']}")
        logger.info(f"总找到联系人: {result['total_contacts']}")

        if result["failed_companies"]:
            logger.info("")
            logger.info("失败的公司列表:")
            logger.info("-" * 60)
            for company in result["failed_companies"]:
                logger.info(f"  - {company}")

        logger.info("=" * 60)
        return 0

    except KeyboardInterrupt:
        logger.error("\n用户中断操作")
        return 130
    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=verbose)
        return 1


async def _run_batch_findkp(verbose: bool = False):
    """执行批量 FindKP 异步任务"""
    async with AsyncSessionLocal() as session:
        try:
            service = FindKPService()

            # 1. 查询 trade_records 表，获取 importer 和 importer_en
            logger.info("正在查询 trade_records 表...")
            query = select(TradeRecord.importer, TradeRecord.importer_en).filter(
                TradeRecord.importer.isnot(None), TradeRecord.importer != ""
            )
            result = await session.execute(query)
            rows = result.all()

            # 2. 去重：使用 set 存储 (importer, importer_en) 元组
            companies_set: Set[Tuple[str, str]] = set()
            for row in rows:
                importer = row.importer.strip() if row.importer else ""
                importer_en = row.importer_en.strip() if row.importer_en else ""
                if importer:
                    # 使用 importer_en 或 importer 作为英文名称
                    company_name_en = importer_en if importer_en else importer
                    companies_set.add((company_name_en, importer))

            companies = list(companies_set)
            total_companies = len(companies)

            if total_companies == 0:
                logger.warning("未找到任何公司记录")
                return {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "total_contacts": 0,
                    "failed_companies": [],
                }

            logger.info(f"找到 {total_companies} 个去重后的公司")
            logger.info("")

            # 3. 统计信息
            stats = {
                "total": total_companies,
                "success": 0,
                "failed": 0,
                "total_contacts": 0,
                "failed_companies": [],
            }

            # 4. 逐个处理公司
            for idx, (company_name_en, company_name_local) in enumerate(companies, 1):
                logger.info("")
                logger.info("-" * 60)
                logger.info(f"[{idx}/{total_companies}] 处理公司: {company_name_en}")
                logger.info(f"  本地名称: {company_name_local}")

                try:
                    # 执行 FindKP
                    result = await service.find_kps(
                        company_name_en=company_name_en,
                        company_name_local=company_name_local,
                        country="Vietnam",
                        db=session,
                    )

                    # 提交事务
                    await session.commit()

                    # 统计结果
                    contacts_count = len(result.get("contacts", []))
                    stats["success"] += 1
                    stats["total_contacts"] += contacts_count

                    logger.info(f"  ✓ 成功：找到 {contacts_count} 个联系人")
                    if result.get("company_domain"):
                        logger.info(f"  ✓ 公司域名: {result['company_domain']}")

                except Exception as e:
                    # 回滚事务
                    await session.rollback()
                    logger.error(f"  ✗ 失败: {e}", exc_info=verbose)
                    stats["failed"] += 1
                    stats["failed_companies"].append(
                        f"{company_name_en} ({company_name_local})"
                    )

            return stats

        except Exception as e:
            await session.rollback()
            logger.error(f"批量 FindKP 流程失败: {e}", exc_info=True)
            raise
        finally:
            await session.close()
