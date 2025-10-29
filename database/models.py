import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Enum,
    Text,
    ForeignKey,
    TIMESTAMP,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .connection import Base


class CompanyStatus(enum.Enum):
    new = "new"
    processing = "processing"
    contacted = "contacted"
    failed = "failed"


class EmailStatus(enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    bounced = "bounced"


class EmailEventType(enum.Enum):
    delivered = "delivered"
    opened = "opened"
    clicked = "clicked"


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(Enum(CompanyStatus), default=CompanyStatus.new)
    created_at = Column(TIMESTAMP, server_default=func.now())

    contacts = relationship(
        "Contact", back_populates="company", cascade="all, delete-orphan"
    )


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    full_name = Column(String(255))
    email = Column(String(255), unique=True, nullable=False, index=True)
    linkedin_url = Column(String(512))
    role = Column(String(255))
    source = Column(String(1024))
    created_at = Column(TIMESTAMP, server_default=func.now())

    company = relationship("Company", back_populates="contacts")
    emails = relationship(
        "Email", back_populates="contact", cascade="all, delete-orphan"
    )


class Email(Base):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    subject = Column(String(255))
    body = Column(Text)
    status = Column(Enum(EmailStatus), default=EmailStatus.pending)
    sent_at = Column(TIMESTAMP)
    error_message = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    contact = relationship("Contact", back_populates="emails")
    events = relationship(
        "EmailEvent", back_populates="email", cascade="all, delete-orphan"
    )


class EmailEvent(Base):
    __tablename__ = "email_events"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False)
    event_type = Column(Enum(EmailEventType), nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())
    metadata = Column(JSON)

    email = relationship("Email", back_populates="events")
