import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Enum,
    Text,
    ForeignKey,
    TIMESTAMP,
    DECIMAL,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .connection import Base


class CompanyStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Company(Base):
    """公司表模型 - FindKP 板块"""

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    domain = Column(String(255))  # 公司域名
    industry = Column(String(100))  # 行业
    positioning = Column(Text)  # 公司定位描述
    brief = Column(Text)  # 公司简要介绍/简报
    status = Column(Enum(CompanyStatus), default=CompanyStatus.pending)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.current_timestamp()
    )

    contacts = relationship(
        "Contact", back_populates="company", cascade="all, delete-orphan"
    )


class Contact(Base):
    """联系人表模型 - FindKP 板块"""

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    full_name = Column(String(255))
    email = Column(String(255), nullable=False, index=True)  # 允许重复
    role = Column(String(255))
    department = Column(String(100), index=True)  # 采购/销售
    linkedin_url = Column(String(512))
    twitter_url = Column(String(512))  # Twitter/X
    phone = Column(String(50))
    source = Column(String(1024))
    confidence_score = Column(DECIMAL(3, 2))  # 0-1
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.current_timestamp()
    )

    company = relationship("Company", back_populates="contacts")
