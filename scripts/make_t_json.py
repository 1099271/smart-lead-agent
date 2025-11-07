#!/usr/bin/env python3
"""
贸易数据导入脚本

功能：
1. 扫描指定目录下的所有 .json 文件
2. 解析每个文件的 results.content 节点数据
3. 将数据批量导入到 trade_records 表
4. 支持增量导入（记录已处理的文件，跳过已处理）

使用方法：
    python scripts/make_t_json.py [--dir /path/to/json/files]
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.connection import AsyncSessionLocal
from database.repository import Repository

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def scan_json_files(directory: str) -> List[str]:
    """
    扫描目录下的所有 .json 文件

    Args:
        directory: 目录路径

    Returns:
        JSON 文件路径列表
    """
    directory_path = Path(directory)
    if not directory_path.exists():
        logger.error(f"目录不存在: {directory}")
        return []

    json_files = list(directory_path.glob("*.json"))
    json_files.sort()  # 按文件名排序
    logger.info(f"找到 {len(json_files)} 个 JSON 文件")
    return [str(f) for f in json_files]


async def parse_json_file(file_path: str) -> Optional[List[Dict[str, Any]]]:
    """
    解析 JSON 文件，提取 results.content 数据

    Args:
        file_path: JSON 文件路径

    Returns:
        results.content 数组，如果解析失败则返回 None
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 提取 results.content
        results = data.get("results", {})
        if not isinstance(results, dict):
            logger.warning(f"文件 {file_path} 的 results 不是字典类型")
            return None

        content = results.get("content", [])
        if not isinstance(content, list):
            logger.warning(f"文件 {file_path} 的 results.content 不是列表类型")
            return None

        logger.info(f"文件 {file_path} 包含 {len(content)} 条记录")
        return content

    except json.JSONDecodeError as e:
        logger.error(f"文件 {file_path} JSON 解析失败: {e}")
        return None
    except Exception as e:
        logger.error(f"读取文件 {file_path} 失败: {e}", exc_info=True)
        return None


async def import_file(
    file_path: str, repository: Repository, force: bool = False
) -> bool:
    """
    导入单个文件的数据

    Args:
        file_path: JSON 文件路径
        repository: Repository 实例
        force: 是否强制重新导入（忽略已处理记录）

    Returns:
        是否成功导入
    """
    # 检查文件是否已处理
    if not force:
        processed_file = await repository.get_processed_file(file_path)
        if processed_file:
            logger.info(
                f"文件 {file_path} 已处理过，跳过（记录数: {processed_file.records_count}）"
            )
            return True

    # 解析 JSON 文件
    content = await parse_json_file(file_path)
    if content is None:
        logger.error(f"文件 {file_path} 解析失败，跳过")
        return False

    if len(content) == 0:
        logger.warning(f"文件 {file_path} 没有数据，跳过")
        # 即使没有数据，也记录为已处理
        file_size = os.path.getsize(file_path)
        await repository.create_processed_file(file_path, file_size, 0)
        return True

    try:
        # 批量插入数据
        records = await repository.create_trade_records_batch(
            trade_records=content, source_file=file_path, auto_commit=True
        )

        # 记录已处理文件
        file_size = os.path.getsize(file_path)
        await repository.create_processed_file(
            file_path=file_path, file_size=file_size, records_count=len(records)
        )

        logger.info(f"文件 {file_path} 导入成功: {len(records)} 条记录")
        return True

    except Exception as e:
        logger.error(f"文件 {file_path} 导入失败: {e}", exc_info=True)
        return False


async def import_all_files(
    directory: str = "/home/www/downloads-tendata", force: bool = False
) -> None:
    """
    导入目录下所有 JSON 文件

    Args:
        directory: JSON 文件目录
        force: 是否强制重新导入所有文件
    """
    logger.info(f"开始导入目录: {directory}")

    # 扫描 JSON 文件
    json_files = await scan_json_files(directory)
    if not json_files:
        logger.warning("没有找到 JSON 文件")
        return

    # 创建数据库会话
    async with AsyncSessionLocal() as session:
        repository = Repository(session)

        success_count = 0
        fail_count = 0

        for file_path in json_files:
            logger.info(f"处理文件: {file_path}")
            success = await import_file(file_path, repository, force=force)
            if success:
                success_count += 1
            else:
                fail_count += 1

        logger.info(f"导入完成: 成功 {success_count} 个文件, 失败 {fail_count} 个文件")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="贸易数据导入脚本")
    parser.add_argument(
        "--dir",
        type=str,
        default="/home/www/downloads-tendata",
        help="JSON 文件目录路径（默认: /home/www/downloads-tendata）",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新导入所有文件（忽略已处理记录）",
    )

    args = parser.parse_args()

    # 运行异步导入
    asyncio.run(import_all_files(directory=args.dir, force=args.force))


if __name__ == "__main__":
    main()
