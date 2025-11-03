# CURSOR_WORK 工作日志

本文档记录所有通过 Cursor 完成的任务需求和实现逻辑，按时间顺序追加。

---

## 2025-11-01 14:58:05 - 创建 CURSOR_WORK.md 工作日志文档

### 需求描述

针对 Smart Lead Agent 项目创建对应的 `CURSOR_WORK.md` 文件，用于记录后续所有通过 Cursor 完成的任务和实现逻辑。

### 实现逻辑

#### 1. 项目结构分析

- 读取了项目的关键文件以了解整体架构：
  - `README.md`: 了解项目基本功能和特性
  - `main.py`: 了解 FastAPI 应用入口和主要流程
  - `pyproject.toml`: 了解项目依赖和配置
  - `docs/architecture_design.md`: 了解详细的架构设计
  - 核心模块文件：`core/search.py`, `core/analysis.py`, `core/generation.py`

#### 2. 项目功能概览

Smart Lead Agent 是一个自动化外贸线索开发系统，主要功能包括：

- **自动搜索**: 使用 Serper.dev API 搜索目标公司的采购联系人信息
- **AI 分析**: 使用 GPT-4o 从搜索结果中提取结构化的联系人信息
- **个性化邮件**: 基于联系人信息自动生成个性化的开发信
- **邮件发送**: 支持 SMTP 和 ESP (SendGrid) 两种邮件发送方式
- **数据追踪**: 完整的数据库记录，支持邮件事件追踪

#### 3. 技术架构

- **Web 框架**: FastAPI
- **数据库**: MySQL + SQLAlchemy ORM
- **AI 服务**: OpenAI GPT-4o
- **搜索服务**: Serper.dev API
- **邮件服务**: SendGrid (ESP) / SMTP
- **依赖管理**: uv (Python 包管理器)

#### 4. 文档结构设计

创建的 `CURSOR_WORK.md` 文档包含以下特性：

- **时间戳标题**: 每次任务以时间和对话总结为标题
- **需求描述**: 详细记录任务需求
- **实现逻辑**: 分步骤说明实现过程和原理
- **追加模式**: 后续任务向后追加，不覆盖已有内容

#### 5. 文档位置

- 文件路径: `docs/CURSOR_WORK.md`
- 符合项目规范：文档统一存放在 `docs/` 目录下

### 实现效果

- ✅ 成功创建 `docs/CURSOR_WORK.md` 文件
- ✅ 建立了工作日志的标准格式
- ✅ 为后续任务记录建立了模板基础

### 技术要点

- 文件使用 Markdown 格式，便于阅读和维护
- 采用时间顺序记录，便于追溯开发历史
- 结构清晰，包含需求、逻辑、效果等完整信息

---

## 2025-11-03 - 项目架构重构 - FindKP 板块实现

### 需求描述

根据新的业务需求,将项目重构为三大板块(FindKP/MailManager/Writer),调整技术栈为 FastAPI + LangChain V1,重新设计数据库结构,并优先实现 FindKP 板块。

### 业务调整

#### 原架构问题
- 旧架构使用 `core/` 目录,模块嵌套较深
- 直接使用 OpenAI API,未使用 LangChain 框架
- 邮件发送功能过早集成(SendGrid/SMTP)
- 只支持单个联系人,不支持多 KP 场景

#### 新业务需求
将系统拆分为三大独立板块:
1. **FindKP 板块**: 查找公司的关键联系人(采购/销售 KP),支持多联系人输出
2. **MailManager 板块**: 邮件管理和监控(待实现)
3. **Writer 板块**: 个性化营销内容生成(待实现)

### 技术栈调整

#### 移除的依赖
- `openai` - 改用 LangChain 的 LLM 模块
- `sendgrid` - MailManager 板块暂不实现

#### 新增的依赖
- `langchain-openai` - LangChain 的 OpenAI 集成

#### 核心技术
- **Web 框架**: FastAPI
- **AI 框架**: LangChain V1 + LangGraph
- **数据库**: MySQL + SQLAlchemy ORM
- **LLM**: OpenAI GPT-4o (通过 LangChain)
- **搜索服务**: Serper.dev API

### 实现逻辑

#### 1. 项目结构重构

采用扁平化、模块化设计:

```
smart-lead-agent/
├── main.py                 # FastAPI 应用入口
├── config.py               # 配置管理
├── schemas/                # 全局 Pydantic 模型
├── findkp/                 # FindKP 板块
│   ├── router.py           # API 路由
│   ├── service.py          # 业务逻辑
│   └── prompts.py          # Prompt 模板
├── mail_manager/           # MailManager 板块(待实现)
├── writer/                 # Writer 板块(待实现)
└── database/               # 数据库层
    ├── models.py
    ├── repository.py
    └── sql/
```

**设计原则**:
- **模块化**: 每个板块独立,职责单一
- **扁平化**: 避免过度嵌套,顶层目录清晰
- **FastAPI 最佳实践**: Router + Service 分离

#### 2. 数据库表结构重新设计

##### companies 表
新增字段以支持更丰富的公司信息:
- `domain` - 公司域名
- `industry` - 行业
- `status` - 改为 pending/processing/completed/failed
- `updated_at` - 更新时间

##### contacts 表
支持多个联系人和更丰富的信息:
- `department` - 部门(采购/销售)
- `twitter_url` - Twitter/X URL
- `phone` - 电话
- `confidence_score` - 置信度评分(0-1)
- `updated_at` - 更新时间
- 移除 `email` 的 UNIQUE 约束,允许一人多邮箱

SQL 脚本: `database/sql/001_findkp_schema.sql`

#### 3. FindKP 板块核心实现

##### `schemas/contact.py`
定义数据模型:
- `CompanyQuery`: API 输入(公司名称)
- `KPInfo`: 单个 KP 信息
- `FindKPResponse`: API 输出(继承自 BaseResponse)

##### `findkp/prompts.py`
LLM Prompt 模板:
- `EXTRACT_COMPANY_INFO_PROMPT`: 提取公司基本信息
- `EXTRACT_CONTACTS_PROMPT`: 提取联系人信息

##### `findkp/service.py`
使用 LangChain V1 实现业务逻辑:

```python
from langchain_openai import ChatOpenAI

class FindKPService:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY
        )
        self.http_client = httpx.Client(timeout=30.0)
    
    def find_kps(self, company_name: str, db) -> dict:
        # 1. 搜索公司基本信息
        # 2. 使用 LLM 提取公司信息(域名、行业)
        # 3. 搜索采购部门 KP
        # 4. 搜索销售部门 KP
        # 5. 使用 LLM 提取联系人信息
        # 6. 保存到数据库
        # 7. 返回结果
```

**关键技术点**:
- 使用 `langchain_openai.ChatOpenAI` 而非直接调用 OpenAI API
- 调用方式: `llm.invoke([{"role": "user", "content": prompt}])`
- 不使用 `create_agent`,因为当前是确定性线性流程

##### `findkp/router.py`
API 路由定义:
- `POST /findkp/search`: 搜索公司 KP
- `GET /findkp/health`: 健康检查

##### `main.py`
简化为纯路由注册:
- 移除复杂的 lifespan 管理
- 注册 FindKP 路由: `app.include_router(findkp_router)`

#### 4. 数据库层调整

##### `database/models.py`
更新 ORM 模型以支持新表结构:
- `Company`: 新增 domain, industry, updated_at
- `Contact`: 新增 department, twitter_url, phone, confidence_score, updated_at
- 移除 `Email` 和 `EmailEvent` 模型(MailManager 板块使用)

##### `database/repository.py`
更新仓储方法:
- `create_contact()`: 支持新字段(department, twitter_url, confidence_score)
- `get_contacts_by_company()`: 获取公司的所有联系人

#### 5. 配置管理调整

##### `config.py`
移除邮件相关配置,新增 LangChain 配置:
- `LLM_MODEL`: 默认 "gpt-4o"
- `LLM_TEMPERATURE`: 默认 0.0

##### `.env.example`
更新环境变量模板,移除邮件配置

#### 6. 文档更新

##### `docs/PROJECT_STRUCTURE.md`
新建项目结构文档,详细说明:
- 目录结构和设计原则
- 各组件职责和使用方式
- LangChain V1 使用说明
- 开发指南和注意事项

##### `CLAUDE.md`
更新开发规则文档:
- 更新项目概述和架构说明
- 更新核心组件列表
- 新增 LangChain V1 使用规范
- 更新 API 交互示例

### 实现效果

#### 已完成的任务
- ✅ 更新 pyproject.toml 依赖
- ✅ 创建新的目录结构(schemas/, findkp/, mail_manager/, writer/)
- ✅ 创建 database/sql/001_findkp_schema.sql
- ✅ 实现 schemas/contact.py 数据模型
- ✅ 实现 findkp/prompts.py Prompt 模板
- ✅ 实现 findkp/service.py 业务逻辑
- ✅ 实现 findkp/router.py API 端点
- ✅ 更新 main.py 注册路由
- ✅ 更新 config.py 配置文件
- ✅ 更新 database/models.py 和 repository.py
- ✅ 删除旧的 core/ 目录
- ✅ 创建 docs/PROJECT_STRUCTURE.md
- ✅ 更新 CLAUDE.md Rules 文档
- ✅ 更新 CURSOR_WORK.md 记录

#### 项目现状
- FindKP 板块已完成并可用
- MailManager 和 Writer 板块待实现
- 数据库表结构已更新
- 代码结构清晰,模块化良好

### 技术要点

#### 1. LangChain V1 使用
- **不使用 create_agent**: 当前 FindKP 是确定性线性流程,不需要 Agent 的自主决策
- **直接使用 ChatOpenAI**: 更简单、可控、延迟更低
- **未来升级路径**: 如需复杂推理,可升级为 create_agent

#### 2. 架构设计
- **扁平化**: 顶层目录清晰,避免 core/ 嵌套
- **模块化**: 每个板块独立,通过 router + service 分离
- **仓储模式**: database/repository.py 封装数据库操作

#### 3. 数据库设计
- **支持多 KP**: contacts 表允许一个公司有多个联系人
- **置信度评分**: confidence_score 字段评估信息可靠性
- **部门区分**: department 字段区分采购/销售

#### 4. 代码组织
- **Router 层**: 定义 API 端点,处理 HTTP 请求/响应
- **Service 层**: 实现业务逻辑,调用外部服务和数据库
- **Repository 层**: 封装数据库 CRUD 操作

### 后续规划

- [ ] 实现 MailManager 板块
- [ ] 实现 Writer 板块
- [ ] 添加单元测试和集成测试
- [ ] 优化 LLM Prompt 提高提取准确率
- [ ] 添加缓存机制减少 API 调用
- [ ] 考虑使用 LangChain create_agent 实现更复杂的推理

---

