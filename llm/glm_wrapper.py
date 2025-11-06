"""
GLM（智谱AI）SDK 包装类 - 兼容 LangChain ChatModel 接口
"""

from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage
from zai import ZhipuAiClient
from config import settings
from logs import logger, log_llm_request, log_llm_response


class GLMLLMWrapper:
    """GLM（智谱AI）LLM 包装类，兼容 LangChain ChatModel 接口"""

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        api_key: Optional[str] = None,
        **kwargs,
    ):
        """
        初始化 GLM LLM 包装类

        Args:
            model: 模型名称（如 "glm-4", "glm-4-plus"）
            temperature: 温度参数
            api_key: API Key，如果未提供则从 settings.GLM_API_KEY 读取
            **kwargs: 其他参数（传递给 SDK）
        """
        self.model = model
        self.temperature = temperature
        self.api_key = api_key or settings.GLM_API_KEY
        if not self.api_key:
            raise ValueError("GLM API Key 未配置。请设置 GLM_API_KEY")

        # 初始化智谱AI SDK 客户端
        self.client = ZhipuAiClient(api_key=self.api_key)
        self.kwargs = kwargs

        logger.debug(f"GLM SDK 初始化: model={model}, temperature={temperature}")

    async def ainvoke(self, messages: List[Dict[str, str]], **kwargs) -> AIMessage:
        """
        异步调用 GLM（兼容 LangChain 接口）

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            **kwargs: 其他参数（传递给 SDK）

        Returns:
            AIMessage: LangChain 消息对象，包含 content 属性
        """
        # 转换消息格式（zhipuai SDK 使用标准格式）
        formatted_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_messages.append({"role": role, "content": content})

        # 合并参数
        request_params = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": self.temperature,
            **self.kwargs,
            **kwargs,
        }

        # 记录 LLM 请求
        request_log_path = log_llm_request(
            messages=formatted_messages,
            model=self.model,
            temperature=self.temperature,
            task_type="glm_async",
            **{k: v for k, v in kwargs.items() if k not in ["messages", "model"]},
        )

        logger.debug(
            f"GLM SDK 调用: model={self.model}, messages={len(formatted_messages)}"
        )

        # 调用智谱AI SDK（注意：SDK 是同步的，需要在线程池中运行）
        import asyncio

        def _sync_call():
            """同步调用 SDK"""
            response = self.client.chat.completions.create(**request_params)
            return response

        # 在线程池中执行同步调用
        response = await asyncio.to_thread(_sync_call)

        # 提取响应内容
        content = response.choices[0].message.content

        # 记录 LLM 响应
        log_llm_response(
            response_content=content,
            request_log_path=request_log_path,
            model=self.model,
            task_type="glm_async",
        )

        logger.debug(f"GLM SDK 响应: content_length={len(content)}")

        # 返回 LangChain 兼容的消息对象
        return AIMessage(content=content)

    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> AIMessage:
        """
        同步调用 GLM（兼容 LangChain 接口）

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            **kwargs: 其他参数（传递给 SDK）

        Returns:
            AIMessage: LangChain 消息对象，包含 content 属性
        """
        # 转换消息格式
        formatted_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_messages.append({"role": role, "content": content})

        # 合并参数
        request_params = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": self.temperature,
            **self.kwargs,
            **kwargs,
        }

        # 记录 LLM 请求
        request_log_path = log_llm_request(
            messages=formatted_messages,
            model=self.model,
            temperature=self.temperature,
            task_type="glm_sync",
            **{k: v for k, v in kwargs.items() if k not in ["messages", "model"]},
        )

        logger.debug(
            f"GLM SDK 同步调用: model={self.model}, messages={len(formatted_messages)}"
        )

        # 直接调用 SDK（同步）
        response = self.client.chat.completions.create(**request_params)

        # 提取响应内容
        content = response.choices[0].message.content

        # 记录 LLM 响应
        log_llm_response(
            response_content=content,
            request_log_path=request_log_path,
            model=self.model,
            task_type="glm_sync",
        )

        logger.debug(f"GLM SDK 同步响应: content_length={len(content)}")

        # 返回 LangChain 兼容的消息对象
        return AIMessage(content=content)
