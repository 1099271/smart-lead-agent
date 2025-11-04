from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from functools import lru_cache

# 在模块加载时，显式地从 .env 文件加载环境变量
# 这确保了无论从哪里启动应用，配置都能被正确加载
load_dotenv()


class Settings(BaseSettings):
    """
    应用配置模型,使用 Pydantic 进行类型验证和设置管理
    """

    # 数据库配置
    DB_HOST: str
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    # API 密钥
    SERPER_API_KEY: str
    OPENAI_API_KEY: str

    # OpenRouter 配置（用于国外 API：OpenAI、Anthropic 等）
    OPENROUTER_API_KEY: str = ""  # 可选，如果为空则使用 OPENAI_API_KEY
    OPENROUTER_SITE_URL: str = ""  # 可选，用于 OpenRouter 排名
    OPENROUTER_SITE_NAME: str = ""  # 可选，用于 OpenRouter 排名

    # 国内 API 配置
    DEEPSEEK_API_KEY: str = ""  # DeepSeek API Key（使用 langchain-deepseek）

    # LangChain 配置
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.0

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 允许 .env 文件中有额外的配置项（如邮件配置等）
    }


@lru_cache()
def get_settings() -> Settings:
    """
    获取并缓存配置实例。

    使用 lru_cache 装饰器可以确保 Settings 类只被实例化一次，
    这是一种高效的单例模式实现，避免了重复读取和解析环境变量。

    Returns:
        Settings: 应用的配置实例。
    """
    return Settings()


# 创建一个全局可访问的配置实例
settings = get_settings()
