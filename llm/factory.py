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

    # 国外模型列表（通过 OpenRouter）
    OPENROUTER_MODELS = [
        "gpt-",
        "claude-",
        "anthropic/",
        "openai/",
        "meta-llama/",
        "google/",
    ]

    # 国内模型列表（直接调用）
    DOMESTIC_MODELS = {
        # DeepSeek 模型
        "deepseek-chat": "deepseek",
        "deepseek-reasoner": "deepseek",
        # GLM（智谱AI）模型
        "glm-4": "glm",
        "glm-4-plus": "glm",
        "glm-4-flash": "glm",
        # Qwen（通义千问）模型
        "qwen-turbo": "qwen",
        "qwen-plus": "qwen",
        "qwen-max": "qwen",
        "qwen-7b-chat": "qwen",
        "qwen-14b-chat": "qwen",
        "qwen-72b-chat": "qwen",
    }

    @classmethod
    def get_provider(cls, model: str) -> Tuple[str, str]:
        """
        根据模型名称判断使用的提供商和路由方式

        Args:
            model: 模型名称（如 "gpt-4o", "deepseek-chat"）

        Returns:
            tuple: (provider_type, provider_name)
                - provider_type: "openrouter" | "direct"
                - provider_name: "openai" | "deepseek" | "qwen" | "doubao" 等
        """
        # 先检查国内模型映射
        if model in cls.DOMESTIC_MODELS:
            return ("direct", cls.DOMESTIC_MODELS[model])

        # 检查是否是国外模型（通过 OpenRouter）
        for prefix in cls.OPENROUTER_MODELS:
            if model.startswith(prefix):
                return ("openrouter", "openai")  # OpenRouter 使用 OpenAI 兼容接口

        # 默认使用 OpenRouter
        logger.warning(f"模型 {model} 未匹配到明确的路由规则，默认使用 OpenRouter")
        return ("openrouter", "openai")


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

    # 判断路由
    provider_type, provider_name = LLMRouter.get_provider(model)

    logger.info(
        f"创建 LLM 实例: model={model}, provider_type={provider_type}, "
        f"provider_name={provider_name}"
    )

    if provider_type == "openrouter":
        return _create_openrouter_llm(model, temperature, **kwargs)
    elif provider_type == "direct":
        return _create_direct_llm(model, provider_name, temperature, **kwargs)
    else:
        raise ValueError(f"不支持的 provider_type: {provider_type}")


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
        return _create_deepseek_llm(model, temperature, **kwargs)
    elif provider_name == "glm":
        return _create_glm_llm(model, temperature, **kwargs)
    elif provider_name == "qwen":
        return _create_qwen_llm(model, temperature, **kwargs)
    else:
        raise ValueError(f"不支持的国内 API 提供商: {provider_name}")


def _create_deepseek_llm(model: str, temperature: float, **kwargs):
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

    # 设置环境变量（langchain-deepseek 需要）
    os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY

    logger.debug(f"DeepSeek 配置: model={model}, provider=deepseek")

    # 使用 langchain-deepseek
    return init_chat_model(
        model=model, model_provider="deepseek", temperature=temperature, **kwargs
    )


def _create_glm_llm(model: str, temperature: float, **kwargs):
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

    logger.debug(f"GLM 配置: model={model}, 使用 Python SDK (zhipuai)")

    # 使用智谱AI Python SDK
    return GLMLLMWrapper(
        model=model, temperature=temperature, api_key=settings.GLM_API_KEY, **kwargs
    )


def _create_qwen_llm(model: str, temperature: float, **kwargs):
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

    # 如果配置了 QWEN_MODEL，使用配置的模型名称，否则使用传入的 model
    actual_model = settings.QWEN_MODEL or model

    logger.debug(
        f"Qwen 配置: model={actual_model}, base_url=https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 使用 OpenAI 兼容接口，只需设置不同的 base_url
    return init_chat_model(
        model=actual_model,
        model_provider="openai",  # 使用 OpenAI 兼容接口
        temperature=temperature,
        api_key=settings.QWEN_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # Qwen 兼容模式 API 地址
        **kwargs,
    )
