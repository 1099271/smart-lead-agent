"""CLI 主入口"""

import click
from cli.findkp import findkp
from cli.batch_findkp import batch_findkp
from cli.writer import writer_group
from cli.mail_manager import mail_group
from cli.compose_and_send import compose_and_send


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
cli.add_command(mail_group)
cli.add_command(compose_and_send)

if __name__ == "__main__":
    cli()
