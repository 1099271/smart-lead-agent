# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Smart Lead Agent 是一个专门用来在外贸行业寻找线索的智能代理系统。系统采用模块化、扁平化架构,使用 FastAPI 作为 Web 框架,LangChain V1 作为 AI 框架,分为三大板块:
- **FindKP**: 查找公司关键联系人(已实现)
- **MailManager**: 邮件管理和监控(待实现)
- **Writer**: 个性化营销内容生成(待实现)

## 常用命令

### 环境管理（使用 uv）
```bash
# 安装依赖并创建虚拟环境
uv sync

# 激活虚拟环境（可选）
source .venv/bin/activate

# 运行应用
uv run python main.py

# 开发模式运行（推荐）
uv run uvicorn main:app --reload

# 添加新依赖
uv add package_name

# 安装开发依赖
uv sync --dev
```

### 数据库操作
```bash
# 初始化数据库（创建表结构）
mysql -u your_user -p your_database < database/sql/001_findkp_schema.sql

# 查看数据库配置
cat .env
```

### 代码质量
```bash
# 代码格式化
uv run black .

# 代码检查
uv run ruff check .

# 运行测试（如果存在）
uv run pytest
```

### API 交互
```bash
# 启动服务后测试 API
curl -X GET "http://localhost:8000/health"

# FindKP 板块 - 查找公司 KP
curl -X POST "http://localhost:8000/findkp/search" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "示例公司"}'
```

## 系统架构

### 目录结构
```
smart-lead-agent/
├── main.py                 # FastAPI 应用入口,路由注册
├── config.py               # 配置管理(Settings)
├── pyproject.toml          # 依赖管理(uv)
│
├── schemas/                # 全局共享的 Pydantic 模型
│   ├── base.py             # 基础响应模型
│   └── contact.py          # 联系人相关模型
│
├── findkp/                 # FindKP 板块(优先实现)
│   ├── router.py           # API 路由
│   ├── service.py          # 业务逻辑
│   └── prompts.py          # LLM Prompt 模板
│
├── mail_manager/           # MailManager 板块(待实现)
├── writer/                 # Writer 板块(待实现)
│
└── database/               # 数据库层
    ├── models.py           # SQLAlchemy ORM 模型
    ├── repository.py       # 仓储层
    ├── connection.py       # 数据库连接管理
    └── sql/                # SQL 脚本
        └── 001_findkp_schema.sql
```

### 核心组件
- **main.py**: FastAPI 应用入口,注册所有板块路由
- **config.py**: 配置管理,从环境变量加载所有设置
- **schemas/**: 全局共享的 Pydantic 数据模型
- **findkp/**: FindKP 板块(查找公司 KP)
  - `router.py`: API 路由定义
  - `service.py`: 业务逻辑,使用 LangChain V1 的 ChatOpenAI
  - `prompts.py`: LLM Prompt 模板
- **database/**: 数据库层
  - `models.py`: SQLAlchemy ORM 模型(Company, Contact)
  - `repository.py`: 数据访问层(仓储模式)
  - `connection.py`: 数据库连接管理

### FindKP 工作流程
1. 接收公司名称 → 2. 搜索公司基本信息(域名、行业) → 3. 搜索采购和销售部门 KP → 4. 使用 LLM 提取结构化联系人信息 → 5. 保存到数据库 → 6. 返回结果

### 数据库表结构(FindKP 板块)
- `companies`: 公司信息(name, domain, industry, status)
- `contacts`: 联系人信息(full_name, email, role, department, linkedin_url, twitter_url, confidence_score)

## 开发注意事项

### 配置管理
- 所有配置通过环境变量管理,参考 `.env.example`
- 必需配置: 数据库信息、SERPER_API_KEY、OPENAI_API_KEY
- LangChain 配置: LLM_MODEL(默认 gpt-4o), LLM_TEMPERATURE(默认 0.0)

### 依赖管理
- 项目使用 `uv` 进行依赖管理,不再使用 `pip`
- 主要依赖声明在 `pyproject.toml` 中
- 核心依赖: fastapi, langchain, langgraph, langchain-openai, sqlalchemy

### LangChain V1 使用规范
- 使用 `langchain_openai.ChatOpenAI` 初始化 LLM
- 调用方式: `llm.invoke([{"role": "user", "content": prompt}])`
- 当前 FindKP 不使用 `create_agent`,因为是确定性流程
- 未来复杂场景可考虑使用 Agent 和 Tool

### 代码组织原则
- **模块化**: 每个板块独立(findkp/, mail_manager/, writer/)
- **扁平化**: 避免过度嵌套,顶层目录清晰
- **Router + Service 分离**: router.py 定义 API,service.py 实现业务逻辑
- **仓储模式**: database/repository.py 封装数据库操作

### 错误处理
- 完整的错误处理和日志记录
- 公司状态自动更新(pending → processing → completed/failed)
- 使用标准 `logging` 模块记录日志

### API 设计
- FindKP 板块: `POST /findkp/search`
- 支持健康检查: `GET /health`, `GET /findkp/health`
- 自动生成 API 文档: `/docs` (Swagger) 和 `/redoc`

## 环境变量配置

创建 `.env` 文件并配置:

```bash
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_user
DB_PASSWORD=your_password
DB_NAME=smart_lead_agent

# API 密钥
SERPER_API_KEY=your_serper_key
OPENAI_API_KEY=your_openai_key

# LangChain 配置(可选)
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.0
```

## 项目特点

- **模块化设计**: 三大板块独立,职责单一,易于维护和扩展
- **扁平化架构**: 顶层目录清晰,避免过度嵌套
- **类型安全**: 使用 Pydantic 进行数据验证和类型检查
- **Router + Service 分离**: 路由和业务逻辑分离
- **仓储模式**: 封装数据库操作,提供清晰的数据访问 API
- **LangChain V1**: 使用最新的 LangChain V1 API