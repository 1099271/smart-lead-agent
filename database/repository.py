from sqlalchemy.orm import Session
from typing import Optional, List

from . import models
from core import schemas


class Repository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_company(self, name: str) -> models.Company:
        """
        根据公司名称获取公司，如果不存在则创建。
        """
        company = (
            self.db.query(models.Company).filter(models.Company.name == name).first()
        )
        if not company:
            company = models.Company(name=name)
            self.db.add(company)
            self.db.commit()
            self.db.refresh(company)
        return company

    def create_contact(
        self, contact_info: schemas.ContactInfo, company_id: int
    ) -> models.Contact:
        """
        创建一个新的联系人记录。
        """
        contact = models.Contact(
            company_id=company_id,
            full_name=contact_info.full_name,
            email=contact_info.email,
            linkedin_url=(
                str(contact_info.linkedin_url) if contact_info.linkedin_url else None
            ),
            role=contact_info.role,
            source=str(contact_info.source),
        )
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def get_contact_by_email(self, email: str) -> Optional[models.Contact]:
        """
        根据邮箱地址查找联系人。
        """
        return (
            self.db.query(models.Contact).filter(models.Contact.email == email).first()
        )

    def create_email(
        self, generated_email: schemas.GeneratedEmail, contact_id: int
    ) -> models.Email:
        """
        创建一封新的邮件记录。
        """
        email = models.Email(
            contact_id=contact_id,
            subject=generated_email.subject,
            body=generated_email.body,
            status=models.EmailStatus.pending,
        )
        self.db.add(email)
        self.db.commit()
        self.db.refresh(email)
        return email

    def update_email_status(
        self,
        email_id: int,
        status: models.EmailStatus,
        error_message: Optional[str] = None,
    ) -> None:
        """
        更新邮件的发送状态。
        """
        email = self.db.query(models.Email).filter(models.Email.id == email_id).first()
        if email:
            email.status = status
            if error_message:
                email.error_message = error_message
            self.db.commit()

    def create_email_event(
        self,
        email_id: int,
        event_type: models.EmailEventType,
        metadata: Optional[dict] = None,
    ) -> models.EmailEvent:
        """
        记录一个邮件事件（如打开、点击）。
        """
        event = models.EmailEvent(
            email_id=email_id, event_type=event_type, metadata=metadata
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event
