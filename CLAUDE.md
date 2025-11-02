# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Smart Lead Agent 是一个专门用来在外贸行业寻找线索的 Agent，可以自动根据行业、客户寻找线索然后发送开发信。系统采用模块化架构，使用 FastAPI 作为 Web 框架，支持多种邮件发送方式。

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
mysql -u your_user -p your_database < database/sql/001_initial_schema.sql

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

# 生成潜在客户
curl -X POST "http://localhost:8000/generate-lead" \
  -H "Content-Type: application/json" \
  -d '{"company_name": "示例公司"}'
```

## 系统架构

### 核心组件
- **main.py**: FastAPI 应用入口，协调整个潜在客户开发流程
- **config.py**: 配置管理，从环境变量加载所有设置
- **core/**: 核心业务模块
  - `search.py`: 搜索模块，使用 Serper.dev API
  - `analysis.py`: 分析模块，使用 OpenAI GPT-4o 提取联系人信息
  - `generation.py`: 邮件生成模块，创建个性化开发信
  - `email/`: 邮件发送模块，支持 SMTP 和 ESP (SendGrid)
  - `schemas.py`: 数据传输对象（DTOs）
- **database/**: 数据库层
  - `models.py`: SQLAlchemy ORM 模型
  - `repository.py`: 数据访问层（仓储模式）
  - `connection.py`: 数据库连接管理

### 工作流程
1. 接收公司名称 → 2. 搜索联系人信息 → 3. AI分析提取联系人 → 4. 生成个性化邮件 → 5. 发送邮件 → 6. 记录结果到数据库

### 数据库表结构
- `companies`: 目标公司信息
- `contacts`: 找到的联系人详细信息
- `emails`: 系统生成的邮件记录
- `email_events`: 邮件事件追踪（打开率、点击率等）

## 开发注意事项

### 配置管理
- 所有配置通过环境变量管理，参考 `.env.example`
- 必需配置：数据库信息、SERPER_API_KEY、OPENAI_API_KEY
- 邮件配置：支持 SMTP 或 SendGrid 二选一

### 依赖管理
- 项目使用 `uv` 进行依赖管理，不再使用 `pip`
- 主要依赖声明在 `pyproject.toml` 中
- `requirements.txt` 仅保留作为兼容性参考

### 邮件发送策略
- 优先使用 ESP (SendGrid)，支持邮件追踪功能
- 如果未配置 ESP，回退到 SMTP
- SMTP 不支持邮件追踪（打开率、点击率）

### 错误处理
- 完整的错误处理和日志记录
- 公司状态自动更新（new → processing → contacted/failed）
- 邮件状态追踪（pending → sent/failed/bounced）

### API 设计
- 主要端点：`/generate-lead`
- 支持健康检查：`/health`
- 自动生成 API 文档：`/docs` (Swagger) 和 `/redoc`

## 环境变量配置

创建 `.env` 文件并配置：

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

# 邮件配置（选择其一）
# SendGrid 配置（推荐，支持追踪）
SENDGRID_API_KEY=your_sendgrid_key
ESP_SENDER_EMAIL=sender@example.com

# 或 SMTP 配置
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_smtp_user
SMTP_PASSWORD=your_smtp_password
SENDER_EMAIL=sender@example.com
```

## 项目特点

- **模块化设计**: 每个组件职责单一，易于维护和扩展
- **类型安全**: 使用 Pydantic 进行数据验证和类型检查
- **异步支持**: FastAPI 提供高性能异步处理
- **完整追踪**: 支持邮件发送状态和事件追踪
- **灵活配置**: 支持多种邮件发送方式和配置选项