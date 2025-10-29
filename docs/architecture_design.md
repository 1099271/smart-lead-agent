# Smart Lead Agent - 架构设计文档

## 1. 概览

本文档概述了 "智能销售代理" (Smart Lead Agent) 的系统架构。该系统旨在自动化潜在客户的开发流程，从初步的公司研究到发送个性化的外联邮件。

系统的主要目标是接收一个公司名称作为输入，然后自主地寻找相关的采购联系人，生成一封有说服力的邮件，发送并跟踪其表现。

此设计强调模块化和可扩展性，以便于未来的功能增强，例如集成像 LangGraph 这样的更复杂的代理工作流框架。

## 2. 系统架构

### 2.1. 架构模式

系统采用 **模块化、流水线式架构**。整个业务流程被分解为一系列独立的、单一职责的组件（模块）。一个中央协调器（Orchestrator）驱动数据流通过这个流水线，将一个模块的输出作为下一个模块的输入。

这种方法有几个优点：

- **可维护性:** 每个组件都可以独立开发、测试和维护。
- **灵活性:** 组件可以轻松地被替换或升级（例如，将一个搜索服务提供商更换为另一个）。
- **可扩展性:** 它为从简单的线性脚本迁移到复杂的基于图的工作流（例如 LangGraph）提供了清晰的路径。

### 2.2. 系统上下文图

下图说明了系统的边界及其与外部服务的交互。

```mermaid
graph TD
    subgraph 智能销售代理系统 (Smart Lead Agent)
        A[API 端点 (FastAPI)]
        B[搜索模块 (Search Module)]
        C[分析模块 (Analysis Module)]
        D[生成模块 (Generation Module)]
        E[邮件模块 (Email Module)]
        F[数据存储 (DataStore)]
    end

    subgraph 外部服务 (External Services)
        G[MySQL 数据库]
        H[Serper.dev API]
        I[LLM API]
        J[SMTP 服务]
        K[专业邮件服务商 API (ESP)]
    end

    A --> B
    B --> C
    C --> D
    D --> E

    B -- 执行搜索 --> H
    C -- 使用LLM进行提取 --> I
    D -- 使用LLM进行写作 --> I
    E -- 通过SMTP发送 --> J
    E -- 通过ESP发送 --> K

    F <--> A
    F <--> B
    F <--> C
    F <--> D
    F <--> E

    F -- 管理数据于 --> G

    style `智能销售代理系统 (Smart Lead Agent)` fill:#2b303a,stroke:#4f8b9f,stroke-width:2px,color:#fff
    style `外部服务 (External Services)` fill:#3a3f4b,stroke:#888,stroke-width:2px,color:#fff
```

## 3. 核心组件

- `Orchestrator`: 流程驱动器。系统将使用 **FastAPI** 框架，因此协调器将表现为一个或多个 API 端点（例如，在 `main.py` 中定义）。这些端点将接收请求并触发潜在客户的开发流程。
- `ConfigManager`: 管理所有外部配置，如 API 密钥和数据库凭据，从环境变量中安全加载。
- `SearchModule`: 负责信息搜集。它使用预定义的搜索策略来查询 `Serper.dev` API，并返回原始搜索结果。
- `AnalysisModule`: 处理原始搜索结果，以提取结构化的联系人信息（姓名、职位、邮箱、LinkedIn）。这可能涉及规则解析和 LLM 驱动的分析。
- `GenerationModule`: 生成个性化的邮件内容。它接收结构化的联系人信息，并使用 LLM 根据预定义模板生成一封有说服力的邮件。
- `EmailModule`: 用于发送邮件的统一接口。它抽象了不同发送机制的复杂性，支持标准 SMTP 和专业邮件服务提供商（ESP）。
- `DataStore`: 数据访问层。它为所有数据库操作（CRUD）提供一个清晰、高级的 API，抽象了底层的 SQL 查询和 ORM 模型。

## 4. 数据库模式 (Schema)

系统依赖一个 MySQL 数据库和四个核心表来管理工作流和跟踪结果。

### 4.1. `companies` (公司表)

存储目标公司及其总体处理状态。

- `id` (PK, INT, AUTO_INCREMENT)
- `name` (VARCHAR(255), UNIQUE): 公司名称。
- `status` (ENUM('new', 'processing', 'contacted', 'failed'), DEFAULT 'new'): 该公司的当前处理阶段。
- `created_at` (TIMESTAMP)

### 4.2. `contacts` (联系人表)

存储为公司找到的潜在联系人详细信息。

- `id` (PK, INT, AUTO_INCREMENT)
- `company_id` (FK -> companies.id): 关联到父公司。
- `full_name` (VARCHAR(255)): 联系人全名。
- `email` (VARCHAR(255), UNIQUE): 联系人邮箱地址（核心目标）。
- `linkedin_url` (VARCHAR(512)): 联系人的 LinkedIn 个人资料 URL。
- `role` (VARCHAR(255)): 联系人的职位或角色。
- `source` (VARCHAR(1024)): 找到联系人信息的来源 URL。
- `created_at` (TIMESTAMP)

### 4.3. `emails` (邮件表)

记录系统生成的每一封邮件。

- `id` (PK, INT, AUTO_INCREMENT)
- `contact_id` (FK -> contacts.id): 邮件的接收者。
- `subject` (VARCHAR(255)): 邮件主题。
- `body` (TEXT): 由 LLM 生成的完整邮件内容。
- `status` (ENUM('pending', 'sent', 'failed', 'bounced'), DEFAULT 'pending'): 邮件的投递状态。
- `sent_at` (TIMESTAMP): 邮件发送时的时间戳。
- `error_message` (TEXT): 记录发送过程中遇到的任何错误。

### 4.4. `email_events` (邮件事件表)

对跟踪邮件表现至关重要。

- `id` (PK, INT, AUTO_INCREMENT)
- `email_id` (FK -> emails.id): 关联的邮件。
- `event_type` (ENUM('delivered', 'opened', 'clicked'), NOT NULL): 事件类型。
- `timestamp` (TIMESTAMP): 事件发生的时间。
- `metadata` (JSON): 可选字段，用于存储额外数据，例如被点击的具体 URL。

### 4.5. 物理建表语句

所有表的 `CREATE TABLE` SQL 语句已统一存放在 `database/sql/001_initial_schema.sql` 文件中，方便数据库的初始化和版本追溯。

## 5. 绩效追踪策略

为了有效地衡量活动成功与否，系统必须跟踪三个关键指标：退信率、打开率和点击率。

- **退信率 (Bounce Rate):** 根据永久无法投递的邮件计算。ESP 可以可靠地跟踪此指标，通过 webhook 报告退信。系统将相应邮件的 `emails.status` 更新为 `bounced`。
- **打开率 (Open Rate):** 通过在邮件中嵌入一个 1x1 的透明像素图片来跟踪。当图片被加载时，ESP 会记录一次“打开”事件，并通过 webhook 通知我们的系统。然后在 `email_events` 表中创建一条记录。
- **点击率 (Click-Through Rate):** 通过将邮件中的所有链接替换为特殊的跟踪链接来跟踪。当用户点击时，他们首先被重定向到 ESP 的服务器记录点击事件，然后再被发送到最终目的地。这也会触发一个 webhook 到我们的系统，在 `email_events` 表中创建一条记录。

**结论:** 为了实现准确可靠的跟踪，强烈建议使用 **专业的邮件服务提供商 (ESP)**，如 SendGrid 或 Mailgun。基于 SMTP 的发送不支持这些关键的跟踪功能。ESP 的 Webhook 可以直接对接到我们的 FastAPI 应用中，从而实现事件的实时捕获。

## 6. 建议的项目结构

```
smart-lead-agent/
├── main.py                 # FastAPI 应用入口及API端点定义
├── .env.example            # 环境变量模板
├── requirements.txt        # Python 依赖
├── config.py               # 配置加载器 (ConfigManager)
│
├── core/
│   ├── __init__.py
│   ├── schemas.py          # Pydantic 数据传输对象 (DTOs)
│   ├── search.py           # 搜索模块 (SearchModule)
│   ├── analysis.py         # 分析模块 (AnalysisModule)
│   ├── generation.py       # 生成模块 (GenerationModule)
│   └── email/
│       ├── __init__.py
│       ├── base_sender.py  # 发送器的抽象基类
│       ├── smtp_sender.py  # SMTP发送器实现
│       └── esp_sender.py   # ESP发送器实现
│
├── database/
│   ├── __init__.py
│   ├── connection.py       # 数据库连接管理
│   ├── models.py           # SQLAlchemy ORM 模型
│   ├── repository.py       # 数据存储层 (仓储模式)
│   └── sql/
│       └── 001_initial_schema.sql # 数据库初始化DDL脚本
│
└── tests/                    # (建议添加) 单元测试和集成测试

```

## 7. 组件接口定义 (Component Interface Definition)

本章节定义了核心组件的编程接口（契约）以及它们之间用于数据交换的数据结构。推荐使用 Pydantic 来定义这些数据结构，以实现自动的数据验证和清晰的结构。

### 7.1. 数据传输对象 (Data Transfer Objects - DTOs)

这些是在模块之间传递的结构化数据对象。建议将它们统一放在 `core/schemas.py` 文件中。

```python
# core/schemas.py
from pydantic import BaseModel, EmailStr, HttpUrl
from typing import List, Optional

class SearchResult(BaseModel):
    """单条搜索结果的结构"""
    title: str
    link: HttpUrl
    snippet: str

class ContactInfo(BaseModel):
    """从分析中提取出的结构化联系人信息"""
    full_name: Optional[str] = None
    email: EmailStr
    linkedin_url: Optional[HttpUrl] = None
    role: Optional[str] = None
    source: HttpUrl # 信息来源URL

class GeneratedEmail(BaseModel):
    """生成的邮件内容"""
    subject: str
    body: str

class SendStatus(BaseModel):
    """邮件发送结果"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
```

### 7.2. 核心模块接口 (Core Module Interfaces)

#### `SearchModule` (`core/search.py`)

- **职责:** 执行搜索查询。
- **接口:**
  ```python
  class SearchModule:
      def search_for_company(self, company_name: str, search_queries: List[str]) -> List[SearchResult]:
          """根据预设的查询列表，为指定公司执行搜索"""
          # ... 实现调用 Serper.dev API
          pass
  ```

#### `AnalysisModule` (`core/analysis.py`)

- **职责:** 从搜索结果中提取结构化的联系人信息。
- **接口:**
  ```python
  class AnalysisModule:
      def find_contact(self, search_results: List[SearchResult], company_name: str) -> Optional[ContactInfo]:
          """分析搜索结果，尝试找到最相关的采购负责人联系信息"""
          # ... 实现规则匹配和调用 LLM 进行信息提取
          pass
  ```

#### `GenerationModule` (`core/generation.py`)

- **职责:** 根据信息撰写个性化邮件。
- **接口:**
  ```python
  class GenerationModule:
      def generate_cold_email(self, contact: ContactInfo, company_name: str) -> GeneratedEmail:
          """根据联系人信息和公司名，生成一封个性化的开发信"""
          # ... 实现调用 LLM API 进行邮件撰写
          pass
  ```

#### `EmailModule` (`core/email/base_sender.py`)

- **职责:** 提供一个统一的邮件发送接口。
- **接口 (抽象基类):**

  ```python
  from abc import ABC, abstractmethod
  # from core.schemas import GeneratedEmail, SendStatus, EmailStr

  class BaseEmailSender(ABC):
      @abstractmethod
      def send(self, recipient_email: EmailStr, email_content: GeneratedEmail) -> SendStatus:
          """发送邮件的抽象方法"""
          pass
  ```

#### `Repository` (`database/repository.py`)

- **职责:** 封装所有数据库交互，实现仓储模式。
- **接口:**

  ```python
  # (这里的 'Company', 'Contact', 'Email' 是 database/models.py 中定义的 SQLAlchemy ORM 模型)
  # from .models import Company, Contact, Email
  # from core.schemas import ContactInfo, GeneratedEmail

  class Repository:
      def get_or_create_company(self, name: str) -> Company:
          # ...
          pass

      def create_contact(self, contact_info: ContactInfo, company_id: int) -> Contact:
          # ...
          pass

      def create_email(self, generated_email: GeneratedEmail, contact_id: int) -> Email:
          # ...
          pass

      def update_email_status(self, email_id: int, status: str, message_id: Optional[str] = None) -> None:
          # ...
          pass
  ```
