"""
LLM 工厂模块 - 根据模型名称自动路由到相应的 API 提供商
"""

import os
from typing import Optional, Dict, Any, Tuple
from langchain.chat_models import init_chat_model
from config import settings
from .glm_wrapper import GLMLLMWrapper

from logs import logger


class LLMRouter:
    """LLM 路由类，负责判断模型应该使用哪个提供商"""


def get_llm(model: Optional[str] = None, temperature: Optional[float] = None, **kwargs):
    """
    获取 LLM 实例（工厂函数）

    根据模型名称自动路由到相应的 API 提供商：
    - 国外模型（gpt-*, claude-* 等）→ OpenRouter
    - 国内模型（deepseek-*, glm-*, qwen-* 等）→ 直接调用

    Args:
        model: 模型名称，默认使用 settings.LLM_MODEL
        temperature: 温度参数，默认使用 settings.LLM_TEMPERATURE
        **kwargs: 其他 LangChain init_chat_model 支持的参数

    Returns:
        ChatModel: LangChain ChatModel 实例

    Raises:
        ValueError: 当缺少必要的 API Key 时
    """
    # 使用默认值
    model = model or settings.LLM_MODEL
    temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE

    if model == "openrouter":
        return _create_openrouter_llm(model, temperature, **kwargs)
    elif model in ("deepseek", "qwen", "glm"):
        return _create_direct_llm(model, model, temperature, **kwargs)
    else:
        raise ValueError(f"不支持的 provider_type: {model}")


def _create_openrouter_llm(model: str, temperature: float, **kwargs):
    """
    创建通过 OpenRouter 调用的 LLM 实例

    Args:
        model: 模型名称
        temperature: 温度参数
        **kwargs: 其他参数

    Returns:
        ChatModel: LangChain ChatModel 实例
    """
    # 获取 OpenRouter API Key
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        raise ValueError(
            "OpenRouter API Key 未配置。请设置 OPENROUTER_API_KEY 或 OPENAI_API_KEY"
        )

    # 构建 default_headers（仅当有值时才添加）
    default_headers: Dict[str, str] = {}
    site_url = settings.OPENROUTER_SITE_URL
    site_name = settings.OPENROUTER_SITE_NAME

    if site_url:
        default_headers["HTTP-Referer"] = site_url
    if site_name:
        default_headers["X-Title"] = site_name

    logger.debug(
        f"OpenRouter 配置: base_url=https://openrouter.ai/api/v1, "
        f"headers={default_headers if default_headers else 'None'}"
    )

    # 构建 init_chat_model 参数
    init_kwargs = {
        "model": model,
        "model_provider": "openai",  # OpenRouter 使用 OpenAI 兼容接口
        "temperature": temperature,
        "api_key": api_key,
        "base_url": "https://openrouter.ai/api/v1",
        **kwargs,
    }

    # 只有当 headers 不为空时才添加
    if default_headers:
        init_kwargs["default_headers"] = default_headers

    return init_chat_model(**init_kwargs)


def _create_direct_llm(model: str, provider_name: str, temperature: float, **kwargs):
    """
    创建直接调用的 LLM 实例（国内 API）

    Args:
        model: 模型名称
        provider_name: 提供商名称（"deepseek", "glm", "qwen"）
        temperature: 温度参数
        **kwargs: 其他参数

    Returns:
        ChatModel: LangChain ChatModel 实例
    """
    if provider_name == "deepseek":
        return _create_deepseek_llm(temperature, **kwargs)
    elif provider_name == "glm":
        return _create_glm_llm(temperature, **kwargs)
    elif provider_name == "qwen":
        return _create_qwen_llm(temperature, **kwargs)
    else:
        raise ValueError(f"不支持的国内 API 提供商: {provider_name}")


def _create_deepseek_llm(temperature: float, **kwargs):
    """
    创建 DeepSeek LLM 实例

    Args:
        model: 模型名称（如 "deepseek-chat"）
        temperature: 温度参数
        **kwargs: 其他参数

    Returns:
        ChatModel: LangChain ChatModel 实例

    Raises:
        ValueError: 当 DEEPSEEK_API_KEY 未配置时
    """
    # 检查并设置环境变量
    if not settings.DEEPSEEK_API_KEY:
        raise ValueError("DeepSeek API Key 未配置。请设置 DEEPSEEK_API_KEY")

    return init_chat_model(
        model="deepseek-chat",
        model_provider="openai",
        api_key=settings.DEEPSEEK_API_KEY,
        temperature=temperature,
        **kwargs,
    )


def _create_glm_llm(temperature: float, **kwargs):
    """
    创建 GLM（智谱AI）LLM 实例（使用 Python SDK）

    Args:
        model: 模型名称（如 "glm-4", "glm-4-plus"）
        temperature: 温度参数
        **kwargs: 其他参数

    Returns:
        GLMLLMWrapper: GLM SDK 包装类实例（兼容 LangChain 接口）

    Raises:
        ValueError: 当 GLM_API_KEY 未配置时
    """
    if not settings.GLM_API_KEY:
        raise ValueError("GLM API Key 未配置。请设置 GLM_API_KEY")

    # 使用智谱AI Python SDK
    return GLMLLMWrapper(
        model="glm-4.6", temperature=temperature, api_key=settings.GLM_API_KEY, **kwargs
    )


def _create_qwen_llm(temperature: float, **kwargs):
    """
    创建 Qwen（通义千问）LLM 实例（使用 OpenAI 兼容接口）

    Args:
        model: 模型名称（如 "qwen-turbo", "qwen-plus", "qwen-max"）
        temperature: 温度参数
        **kwargs: 其他参数

    Returns:
        ChatModel: LangChain ChatModel 实例

    Raises:
        ValueError: 当 QWEN_API_KEY 未配置时
    """
    if not settings.QWEN_API_KEY:
        raise ValueError("Qwen API Key 未配置。请设置 QWEN_API_KEY")

    # 使用 OpenAI 兼容接口，只需设置不同的 base_url
    return init_chat_model(
        model="qwen-plus",
        model_provider="openai",  # 使用 OpenAI 兼容接口
        temperature=temperature,
        api_key=settings.QWEN_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # Qwen 兼容模式 API 地址
        **kwargs,
    )
