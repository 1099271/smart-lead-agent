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
    BigInteger,
    DateTime,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .connection import Base


class CompanyStatus(enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    ignore = "ignore"  # 查询不到官网/域名，忽略该公司


class Company(Base):
    """公司表模型 - FindKP 板块"""

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    local_name = Column(String(255))  # 公司本地名称
    domain = Column(String(255))  # 公司域名
    country = Column(
        String(100), nullable=False, index=True
    )  # 公司所在国家（用于本地化）
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


class TradeRecord(Base):
    """贸易记录表模型"""

    __tablename__ = "trade_records"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(String(64), index=True, comment="贸易ID")
    trade_date = Column(DateTime, index=True, comment="贸易日期")

    # 进口商信息
    importer = Column(String(512), index=True, comment="进口商名称")
    importer_country_code = Column(String(10), index=True, comment="进口商国家代码")
    importer_id = Column(String(64), comment="进口商ID")
    importer_en = Column(String(512), comment="进口商英文名称")
    importer_orig = Column(String(512), comment="进口商原始名称")

    # 出口商信息
    exporter = Column(String(512), index=True, comment="出口商名称")
    exporter_country_code = Column(String(10), index=True, comment="出口商国家代码")
    exporter_orig = Column(String(512), comment="出口商原始名称")

    # 贸易基本信息
    catalog = Column(String(50), index=True, comment="目录类型(imports/exports)")
    state_of_origin = Column(String(100), comment="原产地")
    state_of_destination = Column(String(100), comment="目的地")
    batch_id = Column(BigInteger, index=True, comment="批次ID")
    sum_of_usd = Column(DECIMAL(15, 2), comment="美元金额")
    gd_no = Column(String(64), comment="报关单号")
    weight_unit_price = Column(DECIMAL(15, 4), comment="重量单价")
    source_database = Column(String(50), comment="数据库来源")

    # 产品信息
    product_tag = Column(JSON, comment="产品标签(JSON数组)")
    goods_desc = Column(Text, comment="商品描述")
    goods_desc_vn = Column(Text, comment="商品描述(越南语)")
    hs_code = Column(String(20), comment="HS编码")

    # 国家/地区信息
    country_of_origin_code = Column(String(10), comment="原产国代码")
    country_of_origin = Column(String(100), comment="原产国")
    country_of_destination = Column(String(100), comment="目的国")
    country_of_destination_code = Column(String(10), comment="目的国代码")
    country_of_trade = Column(String(100), comment="贸易国家")

    # 数量信息
    qty = Column(DECIMAL(15, 4), comment="数量")
    qty_unit = Column(String(20), comment="数量单位")
    qty_unit_price = Column(DECIMAL(15, 4), comment="数量单价")
    weight = Column(DECIMAL(15, 4), comment="重量")

    # 贸易方式
    transport_type = Column(String(50), comment="运输类型")
    payment = Column(String(50), comment="支付方式")
    incoterm = Column(String(20), comment="贸易术语")
    trade_mode = Column(String(255), comment="贸易模式")

    # 其他信息
    rep_num = Column(Integer, comment="代表编号")
    primary_flag = Column(String(10), comment="主要标识")
    source_file = Column(String(512), index=True, comment="来源文件路径")

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.current_timestamp()
    )


class ProcessedFile(Base):
    """已处理文件记录表模型"""

    __tablename__ = "processed_files"

    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(
        String(512), unique=True, nullable=False, index=True, comment="文件路径"
    )
    file_size = Column(BigInteger, comment="文件大小(字节)")
    processed_at = Column(
        TIMESTAMP, server_default=func.now(), index=True, comment="处理时间"
    )
    records_count = Column(Integer, default=0, comment="导入的记录数")


class EmailStatus(enum.Enum):
    """邮件状态枚举"""

    pending = "pending"  # 待发送
    sending = "sending"  # 发送中
    sent = "sent"  # 已发送
    failed = "failed"  # 发送失败
    bounced = "bounced"  # 退信


class EmailTrackingEventType(enum.Enum):
    """邮件追踪事件类型枚举"""

    opened = "opened"  # 邮件被打开
    clicked = "clicked"  # 链接被点击
    replied = "replied"  # 邮件被回复


class Email(Base):
    """邮件记录表模型 - MailManager 板块"""

    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    # 关联信息
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

    # 邮件基本信息
    subject = Column(String(512), nullable=False)
    html_content = Column(Text, nullable=False)  # HTML 内容（已嵌入追踪像素）
    text_content = Column(Text)  # 纯文本内容（可选）

    # 收件人信息
    to_email = Column(String(255), nullable=False, index=True)
    to_name = Column(String(255))  # 收件人姓名

    # 发件人信息
    from_email = Column(String(255), nullable=False)
    from_name = Column(String(255))

    # 追踪信息
    tracking_id = Column(String(64), unique=True, nullable=False, index=True)
    tracking_pixel_url = Column(String(512))  # 追踪像素URL

    # 状态信息
    status = Column(Enum(EmailStatus), default=EmailStatus.pending, index=True)
    gmail_message_id = Column(String(255), unique=True)  # Gmail API 返回的消息ID
    error_message = Column(Text)  # 错误信息（如果发送失败）

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.now())
    sent_at = Column(TIMESTAMP)  # 实际发送时间
    first_opened_at = Column(TIMESTAMP)  # 首次打开时间
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.current_timestamp()
    )

    # 关系
    contact = relationship("Contact", backref="emails")
    company = relationship("Company", backref="emails")
    tracking_events = relationship("EmailTracking", back_populates="email")


class EmailTracking(Base):
    """邮件追踪事件表模型 - MailManager 板块"""

    __tablename__ = "email_tracking"

    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=False, index=True)

    # 事件类型
    event_type = Column(Enum(EmailTrackingEventType), nullable=False, index=True)

    # 追踪信息
    ip_address = Column(String(45))  # IPv4 或 IPv6
    user_agent = Column(String(512))  # 浏览器 User-Agent
    referer = Column(String(512))  # 来源页面

    # 时间戳
    created_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    # 关系
    email = relationship("Email", back_populates="tracking_events")
