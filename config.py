from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from functools import lru_cache
from typing import Dict

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

    # Google Search API 配置
    GOOGLE_SEARCH_API_KEY: str = ""  # Google Custom Search API Key
    GOOGLE_SEARCH_CX: str = ""  # Google Custom Search Engine ID

    # OpenRouter 配置（用于国外 API：OpenAI、Anthropic 等）
    OPENROUTER_API_KEY: str = ""  # 可选，如果为空则使用 OPENAI_API_KEY
    OPENROUTER_SITE_URL: str = ""  # 可选，用于 OpenRouter 排名
    OPENROUTER_SITE_NAME: str = ""  # 可选，用于 OpenRouter 排名

    # 国内 API 配置
    DEEPSEEK_API_KEY: str = ""  # DeepSeek API Key（使用 langchain-deepseek）
    GLM_API_KEY: str = ""  # GLM（智谱AI）API Key
    QWEN_API_KEY: str = ""  # Qwen（通义千问）API Key
    QWEN_MODEL: str = ""  # Qwen 模型名称（如 qwen-turbo, qwen-plus, qwen-max）

    # LangChain 配置
    LLM_MODEL: str = "deepseek-chat"
    LLM_TEMPERATURE: float = 0.0

    # Writer 模块配置
    SENDER_NAME: str = ""  # 发送者姓名
    SENDER_TITLE_EN: str = ""  # 发送者职位（英文）
    SENDER_COMPANY: str = ""  # 发送者公司
    SENDER_EMAIL: str = ""  # 发送者邮箱（复用邮件配置中的 SENDER_EMAIL）
    WHATSAPP_NUMBER: str = ""  # WhatsApp 号码
    IMAGE_URL_CUSTOMS_RESULT: str = ""  # 海关数据截图 URL
    IMAGE_URL_FILTERS: str = ""  # 筛选器截图 URL
    TRIAL_URL: str = ""  # 试用链接

    # MailManager 模块配置
    EMAIL_SENDER_TYPE: str = "gmail"  # 邮件发送器类型（gmail/resend/smtp，未来扩展）
    # Gmail API OAuth 2.0 配置
    GOOGLE_OAUTH2_CREDENTIALS_FILE: str = (
        ""  # OAuth 2.0 客户端凭据文件路径（credentials.json）
    )
    GOOGLE_OAUTH2_TOKEN_FILE: str = (
        ""  # OAuth 2.0 令牌文件路径（token.json，用于存储用户的 access token 和 refresh token）
    )
    RESEND_API_KEY: str = ""  # Resend API Key（Resend 发送器使用）
    TRACKING_BASE_URL: str = ""  # 追踪服务器基础 URL
    TRACKING_ENABLED: bool = True  # 是否启用追踪
    EMAIL_SEND_RATE_LIMIT: int = 10  # 每分钟发送限制
    EMAIL_DAILY_LIMIT: int = 2000  # 每日发送上限（0=无限制）

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # 允许 .env 文件中有额外的配置项（如邮件配置等）
    }


# 国家-语言映射配置（用于 WRITER_V3 本地化）
# 格式: {国家名称: {"language_name": "语言名称", "language_code": "ISO 639-1 代码"}}
COUNTRY_LANGUAGE_MAP: Dict[str, Dict[str, str]] = {
    "Vietnam": {
        "language_name": "Vietnamese",
        "language_code": "vi",
    },
    "Thailand": {
        "language_name": "Thai",
        "language_code": "th",
    },
    "Indonesia": {
        "language_name": "Indonesian",
        "language_code": "id",
    },
    "Malaysia": {
        "language_name": "Malay",
        "language_code": "ms",
    },
    "Philippines": {
        "language_name": "Filipino",
        "language_code": "tl",
    },
    "Singapore": {
        "language_name": "English",
        "language_code": "en",
    },
    "India": {
        "language_name": "Hindi",
        "language_code": "hi",
    },
    "Japan": {
        "language_name": "Japanese",
        "language_code": "ja",
    },
    "South Korea": {
        "language_name": "Korean",
        "language_code": "ko",
    },
    "China": {
        "language_name": "Chinese",
        "language_code": "zh",
    },
    "Taiwan": {
        "language_name": "Traditional Chinese",
        "language_code": "zh-TW",
    },
    "Brazil": {
        "language_name": "Portuguese",
        "language_code": "pt",
    },
    "Mexico": {
        "language_name": "Spanish",
        "language_code": "es",
    },
    "Spain": {
        "language_name": "Spanish",
        "language_code": "es",
    },
    "France": {
        "language_name": "French",
        "language_code": "fr",
    },
    "Germany": {
        "language_name": "German",
        "language_code": "de",
    },
    "Italy": {
        "language_name": "Italian",
        "language_code": "it",
    },
    "United Kingdom": {
        "language_name": "English",
        "language_code": "en",
    },
    "United States": {
        "language_name": "English",
        "language_code": "en",
    },
    "Canada": {
        "language_name": "English",
        "language_code": "en",
    },
    "Australia": {
        "language_name": "English",
        "language_code": "en",
    },
}


def get_language_config(country_name: str) -> Dict[str, str]:
    """
    根据国家名称获取对应的语言配置

    Args:
        country_name: 国家名称（如 "Vietnam", "Thailand"）

    Returns:
        包含 language_name 和 language_code 的字典
        如果国家不存在，返回越南的默认配置

    Example:
        >>> config = get_language_config("Vietnam")
        >>> print(config)
        {'language_name': 'Vietnamese', 'language_code': 'vi'}
    """
    return COUNTRY_LANGUAGE_MAP.get(
        country_name,
        COUNTRY_LANGUAGE_MAP["Vietnam"],  # 默认返回越南配置
    )


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
