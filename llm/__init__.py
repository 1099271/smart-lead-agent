"""
LLM 模块 - 统一管理语言模型实例

提供统一的 LLM 工厂函数，支持：
- OpenRouter（用于国外 API：OpenAI、Anthropic 等）
- DeepSeek（国内 API，直接调用）
- 预留 Qwen、Doubao 扩展支持
"""

from .factory import get_llm, LLMRouter

__all__ = ["get_llm", "LLMRouter"]
