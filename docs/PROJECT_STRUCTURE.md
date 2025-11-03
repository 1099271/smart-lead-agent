# Smart Lead Agent 项目结构文档

## 概述

本文档描述 Smart Lead Agent 项目的新架构,该架构于 2025-11-03 完成重构,采用模块化、扁平化的设计原则。

## 项目架构

系统分为三大板块:
- **FindKP**: 查找公司关键联系人(已实现)
- **MailManager**: 邮件管理和监控(待实现)
- **Writer**: 个性化营销内容生成(待实现)

## 技术栈

- **Web 框架**: FastAPI
- **AI 框架**: LangChain V1 + LangGraph
- **数据库**: MySQL + SQLAlchemy ORM
- **LLM**: OpenAI GPT-4o (通过 LangChain)
- **搜索服务**: Serper.dev API
- **依赖管理**: uv

## 目录结构

```
smart-lead-agent/
├── main.py                    # FastAPI 应用入口,路由注册
├── config.py                  # 配置管理(Settings)
├── pyproject.toml             # 依赖管理(uv)
├── .env.example               # 环境变量模板
│
├── schemas/                   # 全局共享的 Pydantic 模型
│   ├── __init__.py
│   ├── base.py                # 基础响应模型(BaseResponse)
│   └── contact.py             # 联系人相关模型(KPInfo, FindKPResponse)
│
├── findkp/                    # FindKP 板块(优先实现)
│   ├── __init__.py
│   ├── router.py              # API 路由(POST /findkp/search)
│   ├── service.py             # 业务逻辑(FindKPService)
│   └── prompts.py             # LLM Prompt 模板
│
├── mail_manager/              # MailManager 板块(待实现)
│   ├── __init__.py
│   ├── router.py
│   └── service.py
│
├── writer/                    # Writer 板块(待实现)
│   ├── __init__.py
│   ├── router.py
│   └── service.py
│
├── database/                  # 数据库层
│   ├── __init__.py
│   ├── connection.py          # 数据库连接管理
│   ├── models.py              # SQLAlchemy ORM 模型(Company, Contact)
│   ├── repository.py          # 仓储层(Repository)
│   └── sql/
│       └── 001_findkp_schema.sql  # FindKP 板块表结构
│
└── docs/                      # 文档
    ├── architecture_design.md
    ├── CURSOR_WORK.md
    └── PROJECT_STRUCTURE.md   # 本文档
```

## 设计原则

### 1. 模块化
- 每个板块独立,职责单一
- 通过 router(路由) + service(业务逻辑) 分离关注点

### 2. 扁平化
- 避免过度嵌套,保持简洁
- 顶层目录清晰表达业务板块

### 3. FastAPI 最佳实践
- 路由层(`router.py`): 定义 API 端点,处理 HTTP 请求/响应
- 服务层(`service.py`): 实现业务逻辑,调用外部服务
- 数据层(`repository.py`): 封装数据库操作,使用仓储模式

## 核心组件说明

### FindKP 板块

#### `findkp/router.py`
- API 端点定义
- 主要端点: `POST /findkp/search`
- 依赖注入: 数据库会话(`Depends(get_db)`)

#### `findkp/service.py`
- 业务逻辑实现
- 使用 LangChain V1 的 `init_chat_model`
- 调用 Serper.dev 搜索 API
- 使用 LLM 提取结构化联系人信息

#### `findkp/prompts.py`
- LLM Prompt 模板
- `EXTRACT_COMPANY_INFO_PROMPT`: 提取公司基本信息
- `EXTRACT_CONTACTS_PROMPT`: 提取联系人信息

### 数据库层

#### `database/models.py`
- `Company`: 公司表模型(支持 domain, industry 字段)
- `Contact`: 联系人表模型(支持 department, twitter_url, confidence_score)

#### `database/repository.py`
- `Repository`: 数据访问层
- 使用仓储模式封装 CRUD 操作
- 主要方法: `get_or_create_company()`, `create_contact()`, `get_contacts_by_company()`

### Schemas

#### `schemas/base.py`
- `BaseResponse`: 基础 API 响应模型

#### `schemas/contact.py`
- `CompanyQuery`: API 输入模型
- `KPInfo`: 单个联系人信息模型
- `FindKPResponse`: API 输出模型(继承自 BaseResponse)

## 配置管理

### `config.py`
使用 Pydantic Settings 管理配置:
- 数据库配置: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- API 密钥: `SERPER_API_KEY`, `OPENAI_API_KEY`
- LangChain 配置: `LLM_MODEL`, `LLM_TEMPERATURE`

### `.env.example`
环境变量模板,包含所有必需的配置项

## API 文档

### 全局端点
- `GET /`: 系统信息
- `GET /health`: 健康检查

### FindKP 板块
- `POST /findkp/search`: 搜索公司 KP
  - 请求体: `{"company_name": "公司名称"}`
  - 响应: 包含公司信息和联系人列表
- `GET /findkp/health`: 板块健康检查

## 数据流

```
客户端请求
    ↓
FastAPI 路由(router.py)
    ↓
业务服务(service.py)
    ├→ 调用 Serper.dev API(搜索)
    ├→ 调用 LangChain init_chat_model(提取信息)
    └→ 调用 Repository(数据库操作)
        ↓
    数据库(MySQL)
        ↓
    响应返回客户端
```

## LangChain V1 使用说明

### 为什么不使用 `create_agent`?

当前 FindKP 板块的需求是确定性的线性流程:
1. 搜索公司信息
2. 使用 LLM 提取结构化数据
3. 保存到数据库

不需要 Agent 的自主决策和工具调用循环。直接使用 `init_chat_model` 更简单、可控、延迟更低。

如果未来需要更复杂的多步骤推理、动态工具选择,可以升级为 `create_agent`。

### 使用方式

```python
from langchain.chat_models import init_chat_model

# 初始化 LLM（LangChain V1 标准方式）
llm = init_chat_model(
    model="gpt-4o",
    model_provider="openai",
    temperature=0,
    api_key=settings.OPENAI_API_KEY
)

# 调用 LLM
response = llm.invoke([{"role": "user", "content": prompt}])
result = json.loads(response.content)
```

## 开发指南

### 添加新板块

1. 创建板块目录: `mkdir new_module/`
2. 创建 `__init__.py`, `router.py`, `service.py`
3. 在 `router.py` 中定义 API 端点
4. 在 `service.py` 中实现业务逻辑
5. 在 `main.py` 中注册路由: `app.include_router(new_module_router)`

### 添加新的数据模型

1. 在 `database/models.py` 中定义 ORM 模型
2. 创建对应的 SQL 脚本: `database/sql/00X_xxx.sql`
3. 在 `database/repository.py` 中添加数据访问方法
4. 在 `schemas/` 中创建对应的 Pydantic 模型

### 运行项目

```bash
# 安装依赖
uv sync

# 运行应用
uv run uvicorn main:app --reload

# 访问 API 文档
# http://localhost:8000/docs
```

## 注意事项

1. **依赖管理**: 使用 `uv` 而非 `pip`
2. **配置管理**: 所有配置通过环境变量管理
3. **数据库**: 使用仓储模式封装数据库操作
4. **LangChain**: 使用 V1 版本的 API
5. **日志**: 所有模块使用标准 `logging` 模块

## 迁移说明

从旧架构迁移到新架构的主要变化:
- 移除 `core/` 目录,改为顶层模块化设计
- 移除 `openai` 和 `sendgrid` 依赖
- 使用 LangChain V1 的 `init_chat_model` 替代直接调用 OpenAI API
- 数据库表结构调整,支持更丰富的联系人信息
- Router + Service 分离设计

## 后续规划

- [ ] 实现 MailManager 板块
- [ ] 实现 Writer 板块
- [ ] 添加单元测试
- [ ] 添加集成测试
- [ ] 优化 LLM Prompt
- [ ] 添加缓存机制
- [ ] 添加监控和日志分析

