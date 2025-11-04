"""FindKP 模块的 LLM Prompt 模板"""

EXTRACT_COMPANY_INFO_PROMPT = """
从以下搜索结果中提取公司的官方域名和行业信息。

{country_context}

搜索结果:
{search_results}

请以 JSON 格式返回:
{{
    "domain": "公司域名",
    "industry": "行业"
}}

如果找不到相关信息,请返回空字符串。
"""

EXTRACT_CONTACTS_PROMPT = """
从以下搜索结果中提取{department}部门的关键联系人信息。

{country_context}

搜索结果:
{search_results}

请提取所有找到的联系人,以 JSON 数组格式返回:
[
    {{
        "full_name": "姓名",
        "email": "邮箱",
        "role": "职位",
        "linkedin_url": "LinkedIn URL(如果有)",
        "twitter_url": "Twitter/X URL(如果有)",
        "confidence_score": 0.0-1.0
    }}
]

要求:
1. 只提取真实有效的邮箱地址
2. 避免通用邮箱如 contact@, info@, sales@
3. confidence_score 根据信息的完整性和可靠性评分(0-1)
4. 如果找不到联系人,返回空数组 []
5. 优先提取与{country_context}相关的联系人信息
"""
