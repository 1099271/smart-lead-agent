"""FindKP 业务逻辑服务"""
import httpx
import json
import logging
from typing import List, Dict
from langchain.chat_models import init_chat_model
from config import settings
from database.repository import Repository
from schemas.contact import KPInfo
from .prompts import EXTRACT_COMPANY_INFO_PROMPT, EXTRACT_CONTACTS_PROMPT

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FindKPService:
    """FindKP 服务类,负责搜索和提取公司 KP 信息"""

    def __init__(self):
        # 使用 LangChain V1 的 init_chat_model（标准方式）
        self.llm = init_chat_model(
            model=settings.LLM_MODEL,
            model_provider="openai",
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
        )
        self.http_client = httpx.Client(timeout=30.0)

    def __del__(self):
        """清理资源"""
        if hasattr(self, "http_client"):
            self.http_client.close()

    def search_serper(self, query: str) -> List[Dict]:
        """
        调用 Serper.dev API 进行搜索

        Args:
            query: 搜索查询字符串

        Returns:
            搜索结果列表
        """
        try:
            response = self.http_client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": settings.SERPER_API_KEY,
                    "Content-Type": "application/json",
                },
                json={"q": query},
            )
            response.raise_for_status()
            return response.json().get("organic", [])
        except Exception as e:
            logger.error(f"Serper API 调用失败: {e}")
            return []

    def extract_with_llm(self, prompt: str) -> Dict:
        """
        使用 LLM 提取结构化信息

        Args:
            prompt: 提示词

        Returns:
            提取的结构化数据
        """
        try:
            # 使用 LangChain V1 的调用方式（同步调用）
            response = self.llm.invoke([{"role": "user", "content": prompt}])
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"LLM 返回的 JSON 解析失败: {e}")
            return {}
        except Exception as e:
            logger.error(f"LLM 提取信息失败: {e}")
            return {}

    def find_kps(self, company_name: str, db) -> Dict:
        """
        主流程: 查找公司的 KP 联系人

        Args:
            company_name: 公司名称
            db: 数据库会话

        Returns:
            包含公司信息和联系人列表的字典
        """
        repo = Repository(db)

        try:
            # 1. 搜索公司基本信息
            logger.info(f"开始搜索公司基本信息: {company_name}")
            company_results = self.search_serper(f"{company_name} official website")
            company_info = self.extract_with_llm(
                EXTRACT_COMPANY_INFO_PROMPT.format(
                    search_results=json.dumps(company_results, ensure_ascii=False)
                )
            )

            # 2. 创建或获取公司记录
            company = repo.get_or_create_company(company_name)
            company.domain = company_info.get("domain")
            company.industry = company_info.get("industry")
            company.status = "processing"
            db.commit()
            logger.info(f"公司记录已创建/更新: {company.name}")

            # 3. 搜索采购部门 KP
            logger.info(f"搜索采购部门 KP: {company_name}")
            procurement_results = self.search_serper(
                f"{company_name} procurement manager contact email"
            )
            procurement_contacts = self.extract_with_llm(
                EXTRACT_CONTACTS_PROMPT.format(
                    department="采购",
                    search_results=json.dumps(procurement_results, ensure_ascii=False),
                )
            )

            # 确保返回的是列表
            if not isinstance(procurement_contacts, list):
                procurement_contacts = []

            # 4. 搜索销售部门 KP
            logger.info(f"搜索销售部门 KP: {company_name}")
            sales_results = self.search_serper(
                f"{company_name} sales manager contact email"
            )
            sales_contacts = self.extract_with_llm(
                EXTRACT_CONTACTS_PROMPT.format(
                    department="销售",
                    search_results=json.dumps(sales_results, ensure_ascii=False),
                )
            )

            # 确保返回的是列表
            if not isinstance(sales_contacts, list):
                sales_contacts = []

            # 5. 保存联系人
            all_contacts = []
            for contact_data in procurement_contacts + sales_contacts:
                try:
                    # 添加部门信息
                    if contact_data in procurement_contacts:
                        contact_data["department"] = "采购"
                    else:
                        contact_data["department"] = "销售"

                    # 添加来源信息(使用第一个搜索结果的链接)
                    if not contact_data.get("source"):
                        if contact_data["department"] == "采购" and procurement_results:
                            contact_data["source"] = procurement_results[0].get(
                                "link", "N/A"
                            )
                        elif sales_results:
                            contact_data["source"] = sales_results[0].get("link", "N/A")
                        else:
                            contact_data["source"] = "N/A"

                    # 创建 KPInfo 对象并保存
                    kp_info = KPInfo(**contact_data)
                    contact = repo.create_contact(kp_info, company.id)
                    all_contacts.append(kp_info)
                    logger.info(f"联系人已保存: {contact.email}")
                except Exception as e:
                    logger.error(f"保存联系人失败: {e}, 数据: {contact_data}")
                    continue

            # 6. 更新公司状态
            company.status = "completed"
            db.commit()
            logger.info(f"FindKP 流程完成: {company_name}, 找到 {len(all_contacts)} 个联系人")

            return {
                "company_id": company.id,
                "company_domain": company.domain,
                "contacts": all_contacts,
            }

        except Exception as e:
            logger.error(f"FindKP 流程失败: {e}", exc_info=True)
            # 更新公司状态为失败
            try:
                company = repo.get_or_create_company(company_name)
                company.status = "failed"
                db.commit()
            except Exception:
                pass
            raise

