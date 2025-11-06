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
    JSON,
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
    public_emails = Column(JSON)  # 公共邮箱列表（JSON数组格式）
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
    email = Column(String(255), nullable=True, index=True)  # 邮箱(允许为空)
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


class SerperResponse(Base):
    """Serper API 响应参数表模型"""

    __tablename__ = "serper_responses"

    trace_id = Column(String(36), primary_key=True, comment="UUID traceid")
    q = Column(String(512), comment="搜索查询")
    type = Column(String(50), comment="搜索类型 (search/image/videos)")
    gl = Column(String(10), comment="国家代码")
    hl = Column(String(10), comment="语言代码")
    location = Column(String(100), comment="位置")
    tbs = Column(String(50), comment="时间范围")
    engine = Column(String(50), comment="搜索引擎")
    credits = Column(Integer, comment="消耗的 credits")
    created_at = Column(TIMESTAMP, server_default=func.now())


class SerperOrganicResult(Base):
    """Serper API 搜索结果表模型"""

    __tablename__ = "serper_organic_results"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(
        String(36), nullable=False, index=True, comment="关联响应的 traceid"
    )
    position = Column(Integer, comment="结果位置")
    title = Column(String(512), comment="标题")
    link = Column(String(1024), comment="链接")
    snippet = Column(Text, comment="摘要")
    date = Column(String(50), comment="日期（可选）")
    created_at = Column(TIMESTAMP, server_default=func.now())
