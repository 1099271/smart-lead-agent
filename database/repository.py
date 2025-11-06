from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any

from . import models
from schemas.contact import KPInfo


class Repository:
    """数据访问层 - 仓储模式（异步版本）"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_company(self, name: str) -> models.Company:
        """
        根据公司名称获取公司,如果不存在则创建（异步版本）
        """
        result = await self.db.execute(
            select(models.Company).filter(models.Company.name == name)
        )
        company = result.scalar_one_or_none()
        if not company:
            company = models.Company(name=name)
            self.db.add(company)
            await self.db.commit()
            await self.db.refresh(company)
        return company

    async def get_company_by_name(self, name: str) -> Optional[models.Company]:
        """
        根据公司名称获取公司（如果不存在则返回 None）
        """
        result = await self.db.execute(
            select(models.Company).filter(models.Company.name == name)
        )
        return result.scalar_one_or_none()

    async def create_contact(
        self, contact_info: KPInfo, company_id: int
    ) -> models.Contact:
        """
        创建一个新的联系人记录 - FindKP 板块（异步版本）
        
        注意：email 可以为空，允许存储没有邮箱的联系人
        """
        contact = models.Contact(
            company_id=company_id,
            full_name=contact_info.full_name,
            email=contact_info.email,  # 可以为 None
            role=contact_info.role,
            department=contact_info.department,
            linkedin_url=(
                str(contact_info.linkedin_url) if contact_info.linkedin_url else None
            ),
            twitter_url=(
                str(contact_info.twitter_url) if contact_info.twitter_url else None
            ),
            source=contact_info.source,
            confidence_score=contact_info.confidence_score,
        )
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def create_contacts_batch(
        self, contacts_info: List[KPInfo], company_id: int
    ) -> List[models.Contact]:
        """
        批量创建联系人记录 - FindKP 板块（异步版本）

        Args:
            contacts_info: 联系人信息列表
            company_id: 公司ID

        Returns:
            创建的联系人列表
            
        注意：email 可以为空，允许存储没有邮箱的联系人
        """
        contacts = []
        for contact_info in contacts_info:
            contact = models.Contact(
                company_id=company_id,
                full_name=contact_info.full_name,
                email=contact_info.email,  # 可以为 None
                role=contact_info.role,
                department=contact_info.department,
                linkedin_url=(
                    str(contact_info.linkedin_url)
                    if contact_info.linkedin_url
                    else None
                ),
                twitter_url=(
                    str(contact_info.twitter_url) if contact_info.twitter_url else None
                ),
                source=contact_info.source,
                confidence_score=contact_info.confidence_score,
            )
            self.db.add(contact)
            contacts.append(contact)

        # 批量提交
        await self.db.commit()

        # 刷新所有对象
        for contact in contacts:
            await self.db.refresh(contact)

        return contacts

    async def get_contacts_by_company(self, company_id: int) -> List[models.Contact]:
        """
        获取指定公司的所有联系人（异步版本）
        """
        result = await self.db.execute(
            select(models.Contact).filter(models.Contact.company_id == company_id)
        )
        return result.scalars().all()

    async def get_contact_by_email(self, email: str) -> Optional[models.Contact]:
        """
        根据邮箱地址查找联系人(注: 可能返回多个,这里只返回第一个)（异步版本）
        """
        result = await self.db.execute(
            select(models.Contact).filter(models.Contact.email == email)
        )
        return result.scalar_one_or_none()

    async def update_company_public_emails(
        self, company_id: int, public_emails: List[str]
    ) -> models.Company:
        """
        更新公司的公共邮箱列表

        Args:
            company_id: 公司ID
            public_emails: 公共邮箱列表（去重后的）

        Returns:
            更新后的 Company 对象
        """
        result = await self.db.execute(
            select(models.Company).filter(models.Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        if not company:
            raise ValueError(f"公司不存在: {company_id}")

        # 合并现有邮箱和新邮箱，去重
        existing_emails = company.public_emails or []
        if not isinstance(existing_emails, list):
            existing_emails = []

        # 合并并去重
        all_emails = list(set(existing_emails + public_emails))
        company.public_emails = all_emails

        await self.db.commit()
        await self.db.refresh(company)
        return company

    async def create_serper_response(
        self, trace_id: str, response_data: Dict[str, Any]
    ) -> models.SerperResponse:
        """
        创建 Serper API 响应记录（异步版本）

        Args:
            trace_id: UUID traceid
            response_data: API 响应数据，包含 searchParameters 和 credits

        Returns:
            创建的 SerperResponse 实例
        """
        # 提取 searchParameters 中的参数
        search_params = response_data.get("searchParameters", {})

        response = models.SerperResponse(
            trace_id=trace_id,
            q=search_params.get("q"),
            type=search_params.get("type"),
            gl=search_params.get("gl"),
            hl=search_params.get("hl"),
            location=search_params.get("location"),
            tbs=search_params.get("tbs"),
            engine=search_params.get("engine"),
            credits=response_data.get("credits"),
        )
        self.db.add(response)
        await self.db.commit()
        await self.db.refresh(response)
        return response

    async def create_serper_organic_results(
        self, trace_id: str, organic_results: List[Dict[str, Any]]
    ) -> List[models.SerperOrganicResult]:
        """
        批量创建 Serper API 搜索结果记录（异步版本）

        Args:
            trace_id: UUID traceid
            organic_results: organic 数组中的结果列表

        Returns:
            创建的 SerperOrganicResult 列表
        """
        results = []
        for item in organic_results:
            result = models.SerperOrganicResult(
                trace_id=trace_id,
                position=item.get("position"),
                title=item.get("title", ""),
                link=item.get("link", ""),
                snippet=item.get("snippet", ""),
                date=item.get("date"),
            )
            self.db.add(result)
            results.append(result)

        # 批量提交
        await self.db.commit()

        # 刷新所有对象
        for result in results:
            await self.db.refresh(result)

        return results
