"""邮箱搜索策略生成器

负责生成基于域名的邮箱搜索查询，实现海外公司邮箱搜索策略。
"""

from typing import List, Dict, Optional, Any

from logs import logger


class EmailSearchStrategy:
    """邮箱搜索策略生成器，用于生成基于域名的邮箱搜索查询"""

    # 国家名称到国家代码的映射表（复用 SearchStrategy 的映射）
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

    def generate_email_search_queries(
        self,
        domain: str,
        company_name_en: str,
        department: str,
        country: Optional[str],
        stages: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        生成邮箱搜索查询列表（基于策略文档）

        策略阶段：
        - Stage 1 (A1-A3): 官网邮箱直搜、联系页聚焦、文件类邮箱搜索
        - Stage 2 (B1): 岗位/职能聚焦
        - Stage 3 (B2): 通用联系方式补充
        - Stage 4 (C1-C2): LinkedIn 搜索

        Args:
            domain: 公司域名（如 "example.com"）
            company_name_en: 公司英文名称
            department: 部门名称（"采购" 或 "销售"）
            country: 国家名称（可选）
            stages: 控制执行哪些阶段，默认全部执行。可选值: ["A1", "A2", "A3", "B1", "B2", "C1", "C2"]

        Returns:
            查询参数字典列表，用于批量搜索
        """
        queries = []
        country_params = self.get_country_params(country)
        seen_queries = set()  # 用于去重

        # 默认执行所有阶段
        if stages is None:
            stages = ["A1", "A2", "A3", "B1", "B2", "C1", "C2"]

        # 阶段 1：官方渠道（A1-A3）
        if "A1" in stages:
            # A1: 官网邮箱直搜
            query = f'site:{domain} "@{domain}"'
            if query not in seen_queries:
                seen_queries.add(query)
                query_params = {"q": query}
                if country_params["gl"]:
                    query_params["gl"] = country_params["gl"]
                if country_params["hl"]:
                    query_params["hl"] = country_params["hl"]
                if country_params["location"]:
                    query_params["location"] = country_params["location"]
                queries.append(query_params)

        if "A2" in stages:
            # A2: 联系页聚焦
            query = f'site:{domain} (inurl:contact OR inurl:contact-us OR inurl:about) "@{domain}"'
            if query not in seen_queries:
                seen_queries.add(query)
                query_params = {"q": query}
                if country_params["gl"]:
                    query_params["gl"] = country_params["gl"]
                if country_params["hl"]:
                    query_params["hl"] = country_params["hl"]
                if country_params["location"]:
                    query_params["location"] = country_params["location"]
                queries.append(query_params)

        if "A3" in stages:
            # A3: 文件类邮箱搜索
            query = f'site:{domain} filetype:pdf "@{domain}"'
            if query not in seen_queries:
                seen_queries.add(query)
                query_params = {"q": query}
                if country_params["gl"]:
                    query_params["gl"] = country_params["gl"]
                if country_params["hl"]:
                    query_params["hl"] = country_params["hl"]
                if country_params["location"]:
                    query_params["location"] = country_params["location"]
                queries.append(query_params)

        # 阶段 2：岗位定位（B1）
        if "B1" in stages:
            # B1: 岗位/职能聚焦 - 根据部门选择关键词
            if department == "采购":
                keywords = '"procurement" OR "purchasing" OR "buyer"'
            elif department == "销售":
                keywords = '"sales" OR "business development"'
            else:
                # 默认使用通用关键词
                keywords = '"sales" OR "business development" OR "procurement" OR "purchasing" OR "buyer"'

            query = f'site:{domain} ({keywords}) "@{domain}"'
            if query not in seen_queries:
                seen_queries.add(query)
                query_params = {"q": query}
                if country_params["gl"]:
                    query_params["gl"] = country_params["gl"]
                if country_params["hl"]:
                    query_params["hl"] = country_params["hl"]
                if country_params["location"]:
                    query_params["location"] = country_params["location"]
                queries.append(query_params)

        # 阶段 3：全局补扫（B2）
        if "B2" in stages:
            # B2: 通用联系方式补充
            query = f'site:{domain} ("email" OR "contact" OR "reach us" OR "get in touch") "@{domain}"'
            if query not in seen_queries:
                seen_queries.add(query)
                query_params = {"q": query}
                if country_params["gl"]:
                    query_params["gl"] = country_params["gl"]
                if country_params["hl"]:
                    query_params["hl"] = country_params["hl"]
                if country_params["location"]:
                    query_params["location"] = country_params["location"]
                queries.append(query_params)

        # 阶段 4：社媒反查（C1-C2）
        if "C1" in stages or "C2" in stages:
            # C1: LinkedIn 采购岗位
            if "C1" in stages and department == "采购":
                query = f'site:linkedin.com "{company_name_en}" ("procurement" OR "purchasing" OR "buyer")'
                if query not in seen_queries:
                    seen_queries.add(query)
                    query_params = {"q": query}
                    if country_params["gl"]:
                        query_params["gl"] = country_params["gl"]
                    if country_params["hl"]:
                        query_params["hl"] = country_params["hl"]
                    if country_params["location"]:
                        query_params["location"] = country_params["location"]
                    queries.append(query_params)

            # C2: LinkedIn 销售岗位
            if "C2" in stages and department == "销售":
                query = f'site:linkedin.com "{company_name_en}" ("sales" OR "business development")'
                if query not in seen_queries:
                    seen_queries.add(query)
                    query_params = {"q": query}
                    if country_params["gl"]:
                        query_params["gl"] = country_params["gl"]
                    if country_params["hl"]:
                        query_params["hl"] = country_params["hl"]
                    if country_params["location"]:
                        query_params["location"] = country_params["location"]
                    queries.append(query_params)

        logger.info(
            f"生成了 {len(queries)} 个{department}部门邮箱搜索查询（域名: {domain}）"
        )
        return queries
