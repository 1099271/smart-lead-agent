"""
日志配置模块

使用 loguru 进行日志管理，LLM 请求和响应日志记录到独立文件。
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from loguru import logger
from typing import Optional

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent
LOGS_DIR = ROOT_DIR / "logs"

# 确保 logs 目录存在
LOGS_DIR.mkdir(exist_ok=True)
(LOGS_DIR / "llm" / "requests").mkdir(parents=True, exist_ok=True)
(LOGS_DIR / "llm" / "responses").mkdir(parents=True, exist_ok=True)

# 配置第三方库的日志级别（减少噪音）
# httpx 是一个 HTTP 客户端库，默认会在 INFO 级别记录请求日志
# 我们将其设置为 WARNING 级别，只记录重要的警告和错误
logging.getLogger("httpx").setLevel(logging.WARNING)

# 移除默认的 handler
logger.remove()

# 配置控制台输出
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# 配置文件输出（通用日志）
logger.add(
    LOGS_DIR / "app_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="00:00",  # 每天午夜轮转
    retention="30 days",  # 保留30天
    compression="zip",  # 压缩旧日志
    encoding="utf-8",
)


def get_llm_log_path(log_type: str, timestamp: Optional[datetime] = None) -> Path:
    """
    获取 LLM 日志文件路径

    Args:
        log_type: 日志类型 ("requests" 或 "responses")
        timestamp: 时间戳，如果为 None 则使用当前时间

    Returns:
        日志文件路径
    """
    if timestamp is None:
        timestamp = datetime.now()

    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")
    return LOGS_DIR / "llm" / log_type / f"{timestamp_str}.log"


def log_llm_request(messages: list, model: str, **kwargs) -> str:
    """
    记录 LLM 请求日志到独立文件

    Args:
        messages: 消息列表
        model: 模型名称
        **kwargs: 其他参数（temperature, max_tokens 等）

    Returns:
        日志文件路径（用于后续关联响应日志）
    """
    timestamp = datetime.now()
    log_path = get_llm_log_path("requests", timestamp)

    log_data = {
        "timestamp": timestamp.isoformat(),
        "model": model,
        "messages": messages,
        **kwargs,
    }

    import json

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    logger.info(f"LLM 请求已记录: {log_path}")
    return str(log_path)


def log_llm_response(
    response_content: str, request_log_path: Optional[str] = None, **kwargs
) -> str:
    """
    记录 LLM 响应日志到独立文件

    Args:
        response_content: 响应内容
        request_log_path: 关联的请求日志路径（可选）
        **kwargs: 其他响应信息（model, usage 等）

    Returns:
        日志文件路径
    """
    timestamp = datetime.now()
    log_path = get_llm_log_path("responses", timestamp)

    log_data = {
        "timestamp": timestamp.isoformat(),
        "response_content": response_content,
        "request_log_path": request_log_path,
        **kwargs,
    }

    import json

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    logger.info(f"LLM 响应已记录: {log_path}")
    return str(log_path)


# 导出 logger 供其他模块使用
__all__ = ["logger", "log_llm_request", "log_llm_response", "get_llm_log_path"]
