"""CLI 主入口"""

import click
from cli.findkp import findkp
from cli.batch_findkp import batch_findkp
from cli.writer import writer_group


# 创建主 CLI 组
@click.group()
@click.version_option(version="2.0.0")
def cli():
    """Smart Lead Agent - 自动化潜在客户开发系统"""
    pass


# 注册子命令
cli.add_command(findkp)
cli.add_command(batch_findkp)
cli.add_command(writer_group)

if __name__ == "__main__":
    cli()
