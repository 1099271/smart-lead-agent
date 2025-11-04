"""搜索策略生成器

负责生成优化的搜索查询，利用公司名和国家信息提升搜索效果。
"""

import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class SearchStrategy:
    """搜索策略生成器，用于生成优化的搜索查询"""

    # 国家名称到国家代码的映射表（常见国家）
    COUNTRY_CODE_MAP = {
        "Vietnam": "vn",
        "China": "cn",
        "USA": "us",
        "United States": "us",
        "India": "in",
        "Japan": "jp",
        "Korea": "kr",
        "South Korea": "kr",
        "Thailand": "th",
        "Singapore": "sg",
        "Malaysia": "my",
        "Indonesia": "id",
        "Philippines": "ph",
        "Taiwan": "tw",
        "Hong Kong": "hk",
        "UK": "gb",
        "United Kingdom": "gb",
        "Germany": "de",
        "France": "fr",
        "Italy": "it",
        "Spain": "es",
        "Brazil": "br",
        "Mexico": "mx",
        "Canada": "ca",
        "Australia": "au",
        "New Zealand": "nz",
    }

    # 国家名称到语言代码的映射表
    LANGUAGE_CODE_MAP = {
        "Vietnam": "vi",
        "China": "zh",
        "USA": "en",
        "United States": "en",
        "India": "en",
        "Japan": "ja",
        "Korea": "ko",
        "South Korea": "ko",
        "Thailand": "th",
        "Singapore": "en",
        "Malaysia": "en",
        "Indonesia": "id",
        "Philippines": "en",
        "Taiwan": "zh",
        "Hong Kong": "zh",
        "UK": "en",
        "United Kingdom": "en",
        "Germany": "de",
        "France": "fr",
        "Italy": "it",
        "Spain": "es",
        "Brazil": "pt",
        "Mexico": "es",
        "Canada": "en",
        "Australia": "en",
        "New Zealand": "en",
    }

    def get_country_params(self, country: Optional[str]) -> Dict[str, Optional[str]]:
        """
        获取国家相关的搜索参数

        Args:
            country: 国家名称，如 "Vietnam", "China" 等

        Returns:
            包含 gl, hl, location 的字典
        """
        if not country:
            return {"gl": None, "hl": None, "location": None}

        gl = self.COUNTRY_CODE_MAP.get(country)
        hl = self.LANGUAGE_CODE_MAP.get(country)
        location = country

        return {"gl": gl, "hl": hl, "location": location}

    def generate_company_queries(
        self, company_name: str, country: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        生成公司信息搜索查询列表

        Args:
            company_name: 公司名称
            country: 国家名称（可选）

        Returns:
            查询参数字典列表，用于批量搜索
        """
        queries = []

        # 基础查询：公司官网
        base_query = f"{company_name} official website"
        if country:
            base_query += f" {country}"

        query_params = {"q": base_query}
        country_params = self.get_country_params(country)
        if country_params["gl"]:
            query_params["gl"] = country_params["gl"]
        if country_params["hl"]:
            query_params["hl"] = country_params["hl"]
        if country_params["location"]:
            query_params["location"] = country_params["location"]

        queries.append(query_params)

        return queries

    def generate_contact_queries(
        self, company_name: str, country: Optional[str], department: str
    ) -> List[Dict[str, Any]]:
        """
        生成联系人搜索查询列表

        Args:
            company_name: 公司名称
            country: 国家名称（可选）
            department: 部门名称（"采购" 或 "销售"）

        Returns:
            查询参数字典列表，用于批量搜索
        """
        queries = []
        country_params = self.get_country_params(country)

        # 根据部门生成不同的搜索查询
        if department == "采购":
            query_templates = [
                f"{company_name} procurement manager",
                f"{company_name} purchasing manager",
                f"{company_name} purchasing contact",
                f"{company_name} procurement director",
            ]
        elif department == "销售":
            query_templates = [
                f"{company_name} sales manager",
                f"{company_name} sales director",
                f"{company_name} sales contact",
                f"{company_name} business development manager",
            ]
        else:
            # 默认使用通用查询
            query_templates = [
                f"{company_name} {department} manager",
                f"{company_name} {department} contact",
            ]

        # 为每个查询模板添加国家信息和联系关键词
        for template in query_templates:
            query = template
            if country:
                query += f" {country}"
            query += " contact email"

            query_params = {"q": query}
            if country_params["gl"]:
                query_params["gl"] = country_params["gl"]
            if country_params["hl"]:
                query_params["hl"] = country_params["hl"]
            if country_params["location"]:
                query_params["location"] = country_params["location"]

            queries.append(query_params)

        return queries

