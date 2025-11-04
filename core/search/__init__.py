"""搜索提供者模块

提供统一的搜索接口，支持多种搜索提供商（Serper、Google等）。
"""

from core.search.base import BaseSearchProvider
from core.search.serper_provider import SerperSearchProvider
from core.search.google_provider import GoogleSearchProvider

__all__ = [
    "BaseSearchProvider",
    "SerperSearchProvider",
    "GoogleSearchProvider",
]
