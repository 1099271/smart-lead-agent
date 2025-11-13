"""MailManager 工具函数"""

import uuid
from typing import Optional

from config import settings


def generate_tracking_id() -> str:
    """
    生成唯一追踪ID

    Returns:
        唯一追踪ID（UUID4 格式）
    """
    return str(uuid.uuid4())


def generate_tracking_pixel_url(tracking_id: str) -> str:
    """
    生成追踪像素URL

    Args:
        tracking_id: 追踪ID

    Returns:
        追踪像素URL
    """
    if not settings.TRACKING_BASE_URL:
        raise ValueError("TRACKING_BASE_URL 配置项未设置")

    base_url = settings.TRACKING_BASE_URL.rstrip("/")
    return f"{base_url}/mail_manager/track/{tracking_id}"


def embed_tracking_pixel(html_content: str, tracking_url: str) -> str:
    """
    在 HTML 中嵌入追踪像素

    Args:
        html_content: 原始 HTML 内容
        tracking_url: 追踪像素URL

    Returns:
        嵌入追踪像素后的 HTML 内容
    """
    # 构建追踪像素 HTML
    pixel_html = (
        f'<img src="{tracking_url}" '
        'width="1" '
        'height="1" '
        'style="display:none; width:1px; height:1px; border:0;" '
        'alt="" />'
    )

    # 在 </body> 之前插入追踪像素
    if "</body>" in html_content.lower():
        # 不区分大小写替换
        html_lower = html_content.lower()
        body_end_pos = html_lower.rfind("</body>")
        if body_end_pos != -1:
            return (
                html_content[:body_end_pos]
                + pixel_html
                + html_content[body_end_pos:]
            )
    else:
        # 如果没有 </body> 标签，在末尾添加
        return html_content + pixel_html

    return html_content


def generate_1x1_png() -> bytes:
    """
    生成 1x1 透明 PNG 图片

    Returns:
        PNG 图片的字节数据
    """
    # 使用最小的 1x1 透明 PNG 字节数据
    # 这是一个标准的 1x1 透明 PNG 图片的字节表示
    return bytes(
        [
            0x89,
            0x50,
            0x4E,
            0x47,
            0x0D,
            0x0A,
            0x1A,
            0x0A,
            0x00,
            0x00,
            0x00,
            0x0D,
            0x49,
            0x48,
            0x44,
            0x52,
            0x00,
            0x00,
            0x00,
            0x01,
            0x00,
            0x00,
            0x00,
            0x01,
            0x08,
            0x06,
            0x00,
            0x00,
            0x00,
            0x1F,
            0x15,
            0xC4,
            0x89,
            0x00,
            0x00,
            0x00,
            0x0A,
            0x49,
            0x44,
            0x41,
            0x54,
            0x78,
            0x9C,
            0x63,
            0x00,
            0x01,
            0x00,
            0x00,
            0x05,
            0x00,
            0x01,
            0x0D,
            0x0A,
            0x2D,
            0xB4,
            0x00,
            0x00,
            0x00,
            0x00,
            0x49,
            0x45,
            0x4E,
            0x44,
            0xAE,
            0x42,
            0x60,
            0x82,
        ]
    )

