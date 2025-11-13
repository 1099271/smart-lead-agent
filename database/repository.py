from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any

from . import models
from schemas.contact import KPInfo


class Repository:
    """数据访问层 - 仓储模式（异步版本）"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_company(
        self,
        name: str,
        country: str,
        local_name: Optional[str] = None,
    ) -> models.Company:
        """
        根据公司名称获取公司,如果不存在则创建（异步版本）

        Args:
            name: 公司英文名称
            local_name: 公司本地名称（可选）
            country: 公司所在国家

        Returns:
            Company 对象
        """
        result = await self.db.execute(
            select(models.Company).filter(models.Company.name == name)
        )
        company = result.scalar_one_or_none()
        if not company:
            company = models.Company(name=name, local_name=local_name, country=country)
            self.db.add(company)
            await self.db.commit()
            await self.db.refresh(company)
        else:
            # 如果公司已存在，但 local_name 为空且传入了 local_name，则更新
            if not company.local_name and local_name:
                company.local_name = local_name
                await self.db.commit()
                await self.db.refresh(company)
            # 如果公司已存在，但 country 为空或需要更新，则更新
            if not company.country or (country and company.country != country):
                company.country = country
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

    async def get_company_by_id(self, company_id: int) -> Optional[models.Company]:
        """
        根据公司ID获取公司（如果不存在则返回 None）
        """
        result = await self.db.execute(
            select(models.Company).filter(models.Company.id == company_id)
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

    async def get_all_contacts_with_email_by_company(
        self, company_id: int
    ) -> List[models.Contact]:
        """
        获取指定公司的所有有邮箱的联系人（异步版本）

        Args:
            company_id: 公司ID

        Returns:
            有邮箱的联系人列表
        """
        result = await self.db.execute(
            select(models.Contact).filter(
                models.Contact.company_id == company_id,
                models.Contact.email.isnot(None),
                models.Contact.email != "",
            )
        )
        return result.scalars().all()

    async def get_contacts_by_company(self, company_id: int) -> List[models.Contact]:
        """
        获取指定公司的所有联系人（异步版本）
        """
        result = await self.db.execute(
            select(models.Contact).filter(models.Contact.company_id == company_id)
        )
        return result.scalars().all()

    async def get_contact_by_id(self, contact_id: int) -> Optional[models.Contact]:
        """
        根据联系人ID获取联系人（如果不存在则返回 None）
        """
        result = await self.db.execute(
            select(models.Contact).filter(models.Contact.id == contact_id)
        )
        return result.scalar_one_or_none()

    async def get_contact_by_email(self, email: str) -> Optional[models.Contact]:
        """
        根据邮箱地址查找联系人(注: 可能返回多个,这里只返回第一个)（异步版本）
        """
        result = await self.db.execute(
            select(models.Contact).filter(models.Contact.email == email)
        )
        return result.scalar_one_or_none()

    async def get_all_contacts_with_email(self) -> List[models.Contact]:
        """
        获取所有有邮箱的联系人（按邮箱去重，保留置信度最高的）

        返回:
            去重后的联系人列表（只包含有邮箱的联系人）
        """
        # 查询所有有邮箱的联系人
        result = await self.db.execute(
            select(models.Contact).filter(
                models.Contact.email.isnot(None), models.Contact.email != ""
            )
        )
        all_contacts = result.scalars().all()

        # 按邮箱去重，保留置信度最高的
        email_map: Dict[str, models.Contact] = {}
        for contact in all_contacts:
            if not contact.email:
                continue

            email_lower = contact.email.lower()
            if email_lower not in email_map:
                email_map[email_lower] = contact
            else:
                # 比较置信度，保留更高的
                existing = email_map[email_lower]
                existing_score = existing.confidence_score or 0.0
                current_score = contact.confidence_score or 0.0

                if current_score > existing_score:
                    email_map[email_lower] = contact
                elif current_score == existing_score:
                    # 置信度相同，保留最新的
                    if contact.created_at and existing.created_at:
                        if contact.created_at > existing.created_at:
                            email_map[email_lower] = contact

        return list(email_map.values())

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
        self, trace_id: str, response_data: Dict[str, Any], auto_commit: bool = True
    ) -> models.SerperResponse:
        """
        创建 Serper API 响应记录（异步版本）

        Args:
            trace_id: UUID traceid
            response_data: API 响应数据，包含 searchParameters 和 credits
            auto_commit: 是否自动提交，默认 True。如果为 False，只 flush，不 commit

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
        if auto_commit:
            await self.db.commit()
            await self.db.refresh(response)
        else:
            await self.db.flush()  # 只 flush，不 commit
        return response

    async def create_serper_organic_results(
        self,
        trace_id: str,
        organic_results: List[Dict[str, Any]],
        auto_commit: bool = True,
    ) -> List[models.SerperOrganicResult]:
        """
        批量创建 Serper API 搜索结果记录（异步版本）

        Args:
            trace_id: UUID traceid
            organic_results: organic 数组中的结果列表
            auto_commit: 是否自动提交，默认 True。如果为 False，只 flush，不 commit

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
        if auto_commit:
            await self.db.commit()
            # 刷新所有对象
            for result in results:
                await self.db.refresh(result)
        else:
            await self.db.flush()  # 只 flush，不 commit

        return results

    async def create_trade_records_batch(
        self,
        trade_records: List[Dict[str, Any]],
        source_file: str,
        auto_commit: bool = True,
    ) -> List[models.TradeRecord]:
        """
        批量创建贸易记录（异步版本）

        Args:
            trade_records: 贸易记录字典列表
            source_file: 来源文件路径
            auto_commit: 是否自动提交，默认 True

        Returns:
            创建的 TradeRecord 列表
        """
        records = []
        for item in trade_records:
            # 解析日期字符串
            date_value = None
            if item.get("date"):
                try:
                    date_str = item["date"]
                    # 处理 ISO 格式日期字符串
                    if "T" in date_str:
                        date_value = datetime.fromisoformat(
                            date_str.replace("Z", "+00:00")
                        )
                    else:
                        date_value = datetime.fromisoformat(date_str)
                except Exception:
                    date_value = None

            record = models.TradeRecord(
                trade_id=item.get("tradeId"),
                trade_date=date_value,
                importer=item.get("importer"),
                importer_country_code=item.get("importerCountryCode"),
                importer_id=item.get("importerId"),
                importer_en=item.get("importerEn"),
                importer_orig=item.get("importerOrig"),
                exporter=item.get("exporter"),
                exporter_country_code=item.get("exporterCountryCode"),
                exporter_orig=item.get("exporterOrig"),
                catalog=item.get("catalog"),
                state_of_origin=item.get("stateOfOrigin"),
                state_of_destination=item.get("stateOfDestination"),
                batch_id=item.get("batchId"),
                sum_of_usd=item.get("sumOfUSD"),
                gd_no=item.get("gdNo"),
                weight_unit_price=item.get("weightUnitPrice"),
                source_database=item.get("database"),
                product_tag=item.get("productTag"),
                goods_desc=item.get("goodsDesc"),
                goods_desc_vn=item.get("goodsDescVn"),
                hs_code=item.get("hsCode"),
                country_of_origin_code=item.get("countryOfOriginCode"),
                country_of_origin=item.get("countryOfOrigin"),
                country_of_destination=item.get("countryOfDestination"),
                country_of_destination_code=item.get("countryOfDestinationCode"),
                country_of_trade=item.get("countryOfTrade"),
                qty=item.get("qty"),
                qty_unit=item.get("qtyUnit"),
                qty_unit_price=item.get("qtyUnitPrice"),
                weight=item.get("weight"),
                transport_type=item.get("transportType"),
                payment=item.get("payment"),
                incoterm=item.get("incoterm"),
                trade_mode=item.get("tradeMode"),
                rep_num=item.get("repNum"),
                primary_flag=item.get("primary"),
                source_file=source_file,
            )
            self.db.add(record)
            records.append(record)

        # 批量提交
        if auto_commit:
            await self.db.commit()
            # 刷新所有对象
            for record in records:
                await self.db.refresh(record)
        else:
            await self.db.flush()

        return records

    async def get_processed_file(
        self, file_path: str
    ) -> Optional[models.ProcessedFile]:
        """
        查询已处理文件记录（异步版本）

        Args:
            file_path: 文件路径

        Returns:
            ProcessedFile 实例，如果不存在则返回 None
        """
        result = await self.db.execute(
            select(models.ProcessedFile).filter(
                models.ProcessedFile.file_path == file_path
            )
        )
        return result.scalar_one_or_none()

    async def create_processed_file(
        self, file_path: str, file_size: int, records_count: int
    ) -> models.ProcessedFile:
        """
        创建已处理文件记录（异步版本）

        Args:
            file_path: 文件路径
            file_size: 文件大小（字节）
            records_count: 导入的记录数

        Returns:
            创建的 ProcessedFile 实例
        """
        processed_file = models.ProcessedFile(
            file_path=file_path,
            file_size=file_size,
            records_count=records_count,
        )
        self.db.add(processed_file)
        await self.db.commit()
        await self.db.refresh(processed_file)
        return processed_file

    # ==================== MailManager 板块方法 ====================

    async def create_email_record(
        self,
        contact_id: Optional[int],
        company_id: Optional[int],
        subject: str,
        html_content: str,
        text_content: Optional[str],
        to_email: str,
        to_name: Optional[str],
        from_email: str,
        from_name: Optional[str],
        tracking_id: str,
        tracking_pixel_url: Optional[str],
        status: models.EmailStatus = models.EmailStatus.pending,
    ) -> models.Email:
        """
        创建邮件记录

        Args:
            contact_id: 关联联系人ID（可选）
            company_id: 关联公司ID（可选）
            subject: 邮件主题
            html_content: HTML 内容
            text_content: 纯文本内容（可选）
            to_email: 收件人邮箱
            to_name: 收件人姓名（可选）
            from_email: 发件人邮箱
            from_name: 发件人姓名（可选）
            tracking_id: 追踪ID
            tracking_pixel_url: 追踪像素URL（可选）
            status: 邮件状态（默认 pending）

        Returns:
            创建的 Email 实例
        """
        email = models.Email(
            contact_id=contact_id,
            company_id=company_id,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            to_email=to_email,
            to_name=to_name,
            from_email=from_email,
            from_name=from_name,
            tracking_id=tracking_id,
            tracking_pixel_url=tracking_pixel_url,
            status=status,
        )
        self.db.add(email)
        await self.db.commit()
        await self.db.refresh(email)
        return email

    async def get_email_by_id(self, email_id: int) -> Optional[models.Email]:
        """
        根据ID查询邮件

        Args:
            email_id: 邮件ID

        Returns:
            Email 实例，如果不存在则返回 None
        """
        result = await self.db.execute(
            select(models.Email).filter(models.Email.id == email_id)
        )
        return result.scalar_one_or_none()

    async def get_email_by_tracking_id(
        self, tracking_id: str
    ) -> Optional[models.Email]:
        """
        根据追踪ID查询邮件

        Args:
            tracking_id: 追踪ID

        Returns:
            Email 实例，如果不存在则返回 None
        """
        result = await self.db.execute(
            select(models.Email).filter(models.Email.tracking_id == tracking_id)
        )
        return result.scalar_one_or_none()

    async def update_email_status(
        self,
        email_id: int,
        status: models.EmailStatus,
        error_message: Optional[str] = None,
    ) -> Optional[models.Email]:
        """
        更新邮件状态

        Args:
            email_id: 邮件ID
            status: 新状态
            error_message: 错误信息（可选）

        Returns:
            更新后的 Email 实例，如果不存在则返回 None
        """
        email = await self.get_email_by_id(email_id)
        if not email:
            return None

        email.status = status
        if error_message:
            email.error_message = error_message

        await self.db.commit()
        await self.db.refresh(email)
        return email

    async def update_email_sent_info(
        self, email_id: int, message_id: str, sent_at: datetime
    ) -> Optional[models.Email]:
        """
        更新邮件发送信息

        Args:
            email_id: 邮件ID
            message_id: Gmail API 返回的消息ID
            sent_at: 发送时间

        Returns:
            更新后的 Email 实例，如果不存在则返回 None
        """
        email = await self.get_email_by_id(email_id)
        if not email:
            return None

        email.gmail_message_id = message_id
        email.sent_at = sent_at
        email.status = models.EmailStatus.sent

        await self.db.commit()
        await self.db.refresh(email)
        return email

    async def update_email_first_opened_at(
        self, email_id: int, opened_at: datetime
    ) -> Optional[models.Email]:
        """
        更新邮件首次打开时间

        Args:
            email_id: 邮件ID
            opened_at: 打开时间

        Returns:
            更新后的 Email 实例，如果不存在则返回 None
        """
        email = await self.get_email_by_id(email_id)
        if not email:
            return None

        # 只在首次打开时更新
        if not email.first_opened_at:
            email.first_opened_at = opened_at

        await self.db.commit()
        await self.db.refresh(email)
        return email

    async def create_tracking_event(
        self,
        email_id: int,
        event_type: models.EmailTrackingEventType,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> models.EmailTracking:
        """
        创建追踪事件

        Args:
            email_id: 邮件ID
            event_type: 事件类型
            ip_address: IP地址（可选）
            user_agent: User-Agent（可选）
            referer: 来源页面（可选）

        Returns:
            创建的 EmailTracking 实例
        """
        tracking_event = models.EmailTracking(
            email_id=email_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            referer=referer,
        )
        self.db.add(tracking_event)
        await self.db.commit()
        await self.db.refresh(tracking_event)
        return tracking_event

    async def get_email_tracking_events(
        self, email_id: int
    ) -> List[models.EmailTracking]:
        """
        查询邮件的追踪事件

        Args:
            email_id: 邮件ID

        Returns:
            追踪事件列表
        """
        result = await self.db.execute(
            select(models.EmailTracking)
            .filter(models.EmailTracking.email_id == email_id)
            .order_by(models.EmailTracking.created_at)
        )
        return list(result.scalars().all())

    async def get_emails_by_status(
        self,
        status: Optional[models.EmailStatus] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[models.Email]:
        """
        根据状态查询邮件列表（支持分页）

        Args:
            status: 邮件状态（可选，None 表示查询所有状态）
            limit: 每页数量
            offset: 偏移量

        Returns:
            邮件列表
        """
        query = select(models.Email)
        if status:
            query = query.filter(models.Email.status == status)

        query = (
            query.order_by(models.Email.created_at.desc()).limit(limit).offset(offset)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_daily_sent_count(self, date: Optional[datetime] = None) -> int:
        """
        获取指定日期的已发送邮件数量（用于限制检查）

        Args:
            date: 日期（可选，默认今天）

        Returns:
            已发送邮件数量
        """
        from sqlalchemy import func

        if date is None:
            date = datetime.now()

        # 获取当天的开始和结束时间
        start_of_day = datetime.combine(date.date(), datetime.min.time())
        end_of_day = datetime.combine(date.date(), datetime.max.time())

        result = await self.db.execute(
            select(func.count(models.Email.id)).filter(
                models.Email.status == models.EmailStatus.sent,
                models.Email.sent_at >= start_of_day,
                models.Email.sent_at <= end_of_day,
            )
        )
        return result.scalar() or 0
