from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List

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

    async def create_contact(
        self, contact_info: KPInfo, company_id: int
    ) -> models.Contact:
        """
        创建一个新的联系人记录 - FindKP 板块（异步版本）
        """
        contact = models.Contact(
            company_id=company_id,
            full_name=contact_info.full_name,
            email=contact_info.email,
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
