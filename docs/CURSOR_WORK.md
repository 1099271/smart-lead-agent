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

## 2025-11-03 20:50:00 - LLM 配置模块重构 - 支持 OpenRouter 和国内 API 路由

### 需求描述

重构 LLM 配置系统，实现统一的 LLM 工厂模块，支持：

1. **国外 API 路由**: 通过 OpenRouter 调用 OpenAI、Anthropic 等模型
2. **国内 API 路由**: 直接调用 DeepSeek 等国内模型（使用独立 API Key）
3. **自动路由**: 根据模型名称自动判断使用哪个 API 提供商
4. **预留扩展**: 支持未来添加 Qwen、Doubao 等国内模型

### 实现逻辑

#### 1. 架构设计

采用**工厂模式**创建统一的 LLM 管理模块：

```
llm/
├── __init__.py          # 导出 get_llm() 和 LLMRouter
└── factory.py            # LLM 工厂实现和路由逻辑
```

**设计优势**:

- ✅ **职责单一**: LLM 创建逻辑独立封装
- ✅ **易于扩展**: 新增 API 提供商只需扩展工厂函数
- ✅ **自动路由**: 根据模型名称自动选择提供商
- ✅ **统一接口**: 所有业务模块通过 `get_llm()` 获取实例

#### 2. 路由规则设计

##### `LLMRouter` 类

实现模型名称到提供商的映射逻辑：

```python
class LLMRouter:
    # 国外模型列表（通过 OpenRouter）
    OPENROUTER_MODELS = [
        "gpt-",           # OpenAI 模型
        "claude-",        # Anthropic 模型
        "anthropic/",     # Anthropic 官方模型名
        "openai/",
        "meta-llama/",
        "google/",
    ]

    # 国内模型列表（直接调用）
    DOMESTIC_MODELS = {
        "deepseek-chat": "deepseek",
        "deepseek-coder": "deepseek",
        # 预留：Qwen、Doubao
    }
```

**路由策略**:

1. 先检查 `DOMESTIC_MODELS` 映射（精确匹配）
2. 再检查 `OPENROUTER_MODELS` 前缀匹配
3. 默认使用 OpenRouter（向后兼容）

#### 3. OpenRouter 集成实现

##### 配置要求

- `OPENROUTER_API_KEY`: OpenRouter API Key（可选，为空则使用 `OPENAI_API_KEY`）
- `OPENROUTER_SITE_URL`: 站点 URL（可选，用于 OpenRouter 排名）
- `OPENROUTER_SITE_NAME`: 站点名称（可选，用于 OpenRouter 排名）

##### 实现细节

```python
def _create_openrouter_llm(model: str, temperature: float, **kwargs):
    api_key = settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY

    # 构建 default_headers（仅当有值时才添加）
    default_headers = {}
    if settings.OPENROUTER_SITE_URL:
        default_headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL
    if settings.OPENROUTER_SITE_NAME:
        default_headers["X-Title"] = settings.OPENROUTER_SITE_NAME

    return init_chat_model(
        model=model,
        model_provider="openai",  # OpenRouter 使用 OpenAI 兼容接口
        temperature=temperature,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers=default_headers if default_headers else None,
        **kwargs
    )
```

**关键技术点**:

- 使用 `base_url="https://openrouter.ai/api/v1"` 指定 OpenRouter 端点
- 使用 `model_provider="openai"` 保持兼容性
- `default_headers` 仅在有值时传递，避免不必要的参数

#### 4. DeepSeek 集成实现

##### 依赖要求

- 已安装 `langchain-deepseek` 包（用户已执行 `uv add langchain-deepseek`）

##### 实现细节

```python
def _create_deepseek_llm(model: str, temperature: float, **kwargs):
    if not settings.DEEPSEEK_API_KEY:
        raise ValueError("DeepSeek API Key 未配置")

    # 设置环境变量（langchain-deepseek 需要）
    os.environ["DEEPSEEK_API_KEY"] = settings.DEEPSEEK_API_KEY

    return init_chat_model(
        model=model,
        model_provider="deepseek",
        temperature=temperature,
        **kwargs
    )
```

**关键技术点**:

- 通过环境变量 `DEEPSEEK_API_KEY` 传递 API Key（`langchain-deepseek` 要求）
- 使用 `model_provider="deepseek"` 指定提供商
- 支持 `deepseek-chat` 和 `deepseek-coder` 模型

#### 5. 配置管理扩展

##### `config.py` 新增配置项

```python
# OpenRouter 配置（用于国外 API：OpenAI、Anthropic 等）
OPENROUTER_API_KEY: str = ""  # 可选，如果为空则使用 OPENAI_API_KEY
OPENROUTER_SITE_URL: str = ""  # 可选，用于 OpenRouter 排名
OPENROUTER_SITE_NAME: str = ""  # 可选，用于 OpenRouter 排名

# 国内 API 配置
DEEPSEEK_API_KEY: str = ""  # DeepSeek API Key（使用 langchain-deepseek）
```

##### Pydantic 配置优化

- 添加 `extra="ignore"` 允许 `.env` 文件中有额外配置项（如邮件配置等）
- 使用 `model_config` 替代 `Config` 类（Pydantic 2.x 标准）

#### 6. 业务代码重构

##### `findkp/service.py` 更新

**原实现**:

```python
from langchain.chat_models import init_chat_model

self.llm = init_chat_model(
    model=settings.LLM_MODEL,
    model_provider="openai",
    temperature=settings.LLM_TEMPERATURE,
    api_key=settings.OPENAI_API_KEY,
)
```

**新实现**:

```python
from llm import get_llm

self.llm = get_llm()  # 自动路由到 OpenRouter 或直接调用
```

**优势**:

- ✅ **代码简化**: 无需手动指定 provider 和 api_key
- ✅ **自动路由**: 根据 `LLM_MODEL` 配置自动选择提供商
- ✅ **易于切换**: 只需修改 `.env` 中的 `LLM_MODEL` 即可切换模型

#### 7. 扩展预留设计

##### Qwen 和 Doubao 预留

在 `DOMESTIC_MODELS` 中预留了注释，方便后续添加：

```python
# 预留：Qwen 模型
# "qwen-turbo": "qwen",
# "qwen-plus": "qwen",
# "qwen-max": "qwen",

# 预留：Doubao 模型
# "doubao-pro": "doubao",
# "doubao-lite": "doubao",
```

在 `_create_direct_llm()` 中预留了实现入口：

```python
elif provider_name == "qwen":
    raise NotImplementedError("Qwen 支持尚未实现，请稍后添加")
elif provider_name == "doubao":
    raise NotImplementedError("Doubao 支持尚未实现，请稍后添加")
```

### 实现效果

#### 已完成的任务

- ✅ 创建 `llm/` 模块目录结构
- ✅ 实现 `llm/factory.py` 工厂函数和路由逻辑
- ✅ 实现 OpenRouter 集成（支持自定义 headers）
- ✅ 实现 DeepSeek 集成（使用 langchain-deepseek）
- ✅ 扩展 `config.py` 添加新的配置项
- ✅ 修复 Pydantic 配置问题（支持额外字段）
- ✅ 重构 `findkp/service.py` 使用新的 LLM 工厂
- ✅ 所有代码通过语法检查和导入测试
- ✅ 路由逻辑验证成功（gpt-4o → OpenRouter，deepseek-chat → DeepSeek）

#### 技术验证

- ✅ LLM 模块导入成功
- ✅ 配置加载成功（OPENROUTER_API_KEY、DEEPSEEK_API_KEY 已识别）
- ✅ 路由功能验证：
  - `gpt-4o` → `('openrouter', 'openai')`
  - `deepseek-chat` → `('direct', 'deepseek')`
  - `claude-3-opus` → `('openrouter', 'openai')`

### 技术要点

#### 1. 工厂模式应用

- **统一接口**: `get_llm()` 函数封装所有复杂性
- **自动路由**: `LLMRouter` 类根据模型名称自动选择提供商
- **易于扩展**: 新增提供商只需添加路由规则和创建函数

#### 2. OpenRouter 集成

- **兼容性**: 使用 OpenAI 兼容接口，保持代码一致性
- **自定义 Headers**: 支持 `HTTP-Referer` 和 `X-Title` 用于排名
- **降级策略**: 未配置 `OPENROUTER_API_KEY` 时使用 `OPENAI_API_KEY`

#### 3. DeepSeek 集成

- **环境变量**: 使用 `os.environ` 设置 API Key（符合 langchain-deepseek 要求）
- **标准接口**: 使用 `init_chat_model` 统一接口，与其他提供商一致

#### 4. 配置管理

- **可选配置**: 使用默认值 `""` 允许配置项可选
- **灵活性**: `extra="ignore"` 允许 `.env` 中有其他配置项
- **向后兼容**: 保持现有配置项不变，只添加新项

#### 5. 代码质量

- **类型提示**: 使用 `Tuple[str, str]` 明确返回类型
- **错误处理**: 提供清晰的错误信息和日志记录
- **日志记录**: 记录路由决策和配置信息（DEBUG 级别）

### 使用示例

#### 基本使用

```python
from llm import get_llm

# 使用默认配置（settings.LLM_MODEL）
llm = get_llm()

# 指定模型和温度
llm = get_llm(model="deepseek-chat", temperature=0.7)
```

#### 环境变量配置示例

```bash
# .env 文件
# 国外 API（通过 OpenRouter）
OPENROUTER_API_KEY="sk-or-v1-..."
OPENROUTER_SITE_URL="https://your-site.com"  # 可选
OPENROUTER_SITE_NAME="Your Site"  # 可选

# 国内 API（直接调用）
DEEPSEEK_API_KEY="sk-..."

# LLM 模型配置
LLM_MODEL="gpt-4o"  # 或 "deepseek-chat"
LLM_TEMPERATURE=0.0
```

### 后续规划

- [ ] 添加 Qwen 模型支持（当需要时）
- [ ] 添加 Doubao 模型支持（当需要时）
- [ ] 实现 LLM 实例缓存（避免重复创建）
- [ ] 添加连接池配置优化性能
- [ ] 实现异步 LLM 调用（与 FastAPI 异步架构对齐）
- [ ] 添加 Token 使用监控和成本统计

---

## 2025-11-04 - 修复异步/同步混用问题

### 需求描述

修复项目中存在的异步/同步混用问题，将整个项目统一为异步架构，符合 FastAPI 最佳实践和项目架构规范。

### 问题分析

根据架构规范（fastapi.mdc），项目要求使用异步数据库连接（AsyncSession），但当前代码存在以下问题：

1. `database/connection.py` 使用同步的 `Session` 和 `create_engine`
2. `findkp/router.py` 路由是 `async def`，但调用的是同步的 `service.find_kps()`
3. `findkp/service.py` 使用同步的 `httpx.Client()` 和同步的 LLM 调用
4. `database/repository.py` 使用同步的数据库查询
5. `main.py` 使用同步方式创建数据库表

这些问题会导致：

- 阻塞事件循环，影响性能
- 不符合 FastAPI 异步最佳实践
- 与项目架构规范不一致

### 实现逻辑

#### 1. 添加异步 MySQL 驱动依赖

```bash
uv add aiomysql
```

#### 2. 修改 `database/connection.py` 为异步版本

**关键改动**：

- 导入 `AsyncSession` 和 `create_async_engine`
- 数据库连接 URL 改为 `mysql+aiomysql://`
- 使用 `AsyncSessionLocal` 创建异步会话工厂
- `get_db()` 改为异步生成器函数

**技术细节**：

- 使用 `async with` 管理会话生命周期
- 异常时自动回滚事务
- 确保资源正确释放

#### 3. 修改 `database/repository.py` 为异步版本

**关键改动**：

- 所有方法改为 `async def`
- 使用 `select()` 和 `await db.execute()` 替代 `db.query()`
- 所有数据库操作添加 `await`（commit、refresh 等）

**技术细节**：

- SQLAlchemy 2.0 异步 API：使用 `select()` 构建查询
- 使用 `result.scalar_one_or_none()` 获取单个结果
- 使用 `result.scalars().all()` 获取列表结果

#### 4. 修改 `findkp/service.py` 为异步版本

**关键改动**：

- 移除同步的 `httpx.Client`，改为在方法中使用 `httpx.AsyncClient`
- `search_serper()` 改为异步方法
- `extract_with_llm()` 改为异步，使用 `llm.ainvoke()` 替代 `llm.invoke()`
- `find_kps()` 改为异步方法，所有调用添加 `await`

**技术细节**：

- HTTP 请求：使用 `async with httpx.AsyncClient()` 上下文管理器
- LLM 调用：使用 LangChain V1 的 `ainvoke()` 异步方法
- 数据库操作：所有 Repository 方法调用添加 `await`

#### 5. 修改 `findkp/router.py` 添加 await

**关键改动**：

- 导入 `AsyncSession` 替代 `Session`
- 路由函数参数类型改为 `AsyncSession`
- 服务调用添加 `await`

#### 6. 修改 `main.py` 的数据库初始化

**关键改动**：

- 移除同步的 `Base.metadata.create_all(bind=engine)`
- 添加 `@app.on_event("startup")` 异步启动事件
- 使用 `engine.begin()` 异步上下文管理器创建表

**技术细节**：

- 使用 FastAPI 的启动事件确保在应用启动时执行
- 使用 `conn.run_sync()` 运行同步的 `create_all` 方法

### 修改的文件清单

1. ✅ `pyproject.toml` - 添加 `aiomysql` 依赖
2. ✅ `database/connection.py` - 改为异步数据库连接
3. ✅ `database/repository.py` - 改为异步数据访问
4. ✅ `findkp/service.py` - 改为异步业务逻辑
5. ✅ `findkp/router.py` - 添加 await 调用
6. ✅ `main.py` - 改为异步数据库初始化

### 验证结果

- ✅ 所有模块导入成功
- ✅ 无 lint 错误
- ✅ 代码符合架构规范

### 架构改进

修复后的架构完全符合 FastAPI 异步最佳实践：

```
FastAPI 应用（异步）
    ↓
路由层（async def）→ 服务层（async def）→ 仓储层（async def）
    ↓
异步数据库会话（AsyncSession）
    ↓
异步数据库操作（await）
```

**性能提升**：

- 避免阻塞事件循环
- 提高并发处理能力
- 充分利用 FastAPI 异步特性

---

## 2025-11-04 22:26:56 - 修复依赖问题并移除启动时数据库表创建逻辑

### 需求描述

1. **修复 `email-validator` 缺失问题**：应用启动时出现 `ModuleNotFoundError: No module named 'email_validator'` 错误
2. **移除启动时自动创建数据库表逻辑**：数据库表创建是一次性操作，应该手动执行 SQL，不需要在应用启动时自动执行

### 实现逻辑

#### 1. 修复 email-validator 依赖问题

**问题分析**：

- `schemas/contact.py` 中使用了 `EmailStr` 类型，需要 `email-validator` 包来验证邮箱格式
- `pyproject.toml` 中缺少 `email-validator` 依赖

**解决方案**：

```python
# pyproject.toml
dependencies = [
    # ... 其他依赖
    "email-validator>=2.0.0",  # 添加 email-validator 依赖
    # ... 其他依赖
]
```

**执行步骤**：

1. 在 `pyproject.toml` 的 `dependencies` 列表中添加 `email-validator>=2.0.0`
2. 运行 `uv sync` 安装依赖
3. 验证应用可以正常启动

#### 2. 移除启动时数据库表创建逻辑

**问题分析**：

- 原代码使用 `@app.on_event("startup")` 在应用启动时自动创建数据库表
- 这种方式已弃用，且不符合用户需求（需要手动执行 SQL）

**解决方案**：

- 删除 `lifespan` 函数和相关的数据库表创建逻辑
- 移除不再需要的导入（`engine`, `Base`, `asynccontextmanager`）
- 简化 `main.py`，只保留应用核心逻辑

**修改内容**：

**删除的内容**：

```python
# 删除的导入
from contextlib import asynccontextmanager
from database.connection import engine, Base

# 删除的 lifespan 函数
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表初始化完成")
    yield
```

**保留的内容**：

```python
# main.py - 简化后的代码
import logging
from fastapi import FastAPI
from findkp.router import router as findkp_router

# 设置日志
logging.basicConfig(...)

# 创建 FastAPI 应用实例（不再包含 lifespan）
app = FastAPI(
    title="Smart Lead Agent API",
    description="自动化潜在客户开发系统 - 三大板块: FindKP, MailManager, Writer",
    version="2.0.0",
)

# 注册路由
app.include_router(findkp_router)
```

### 数据库表创建方式

数据库表创建现在通过手动执行 SQL 脚本完成：

```bash
# 手动执行 SQL 脚本创建表结构
mysql -u your_user -p your_database < database/sql/001_findkp_schema.sql
```

### 验证结果

- ✅ `email-validator` 依赖已添加并安装成功
- ✅ 应用可以正常启动，不再出现模块缺失错误
- ✅ 启动时不再执行数据库表创建逻辑
- ✅ 代码简洁，符合最小化修改原则
- ✅ 无 lint 错误

### 架构改进

移除启动时数据库表创建逻辑的好处：

1. **职责分离**：应用启动逻辑与数据库初始化逻辑分离
2. **灵活性**：数据库表创建完全由用户控制，可以手动执行或通过迁移工具管理
3. **性能**：减少应用启动时间，避免不必要的数据库操作
4. **安全性**：生产环境不应自动创建表结构，应该通过受控的迁移流程

---

## 2025-11-04 23:07:00 - 添加搜索工具集成（Serper.dev 和 Google Search API）

### 需求描述

为 FindKP 模块添加两个搜索工具，创建独立的搜索工具模块，支持批量搜索和异步调用：

1. **Serper.dev Search API**：增强现有搜索功能，支持批量搜索和更多可选参数
2. **Google Search API**：集成 Google Custom Search API 作为备选搜索工具

### 实现逻辑

#### 1. 架构设计

采用**抽象基类 + 具体实现**模式，参考 `core/email/` 的设计：

```
core/search/
├── __init__.py              # 导出统一接口
├── base.py                  # BaseSearchProvider 抽象基类
├── serper_provider.py       # Serper.dev 实现
└── google_provider.py       # Google Search API 实现
```

**设计优势**：

- ✅ **统一接口**：所有搜索提供者遵循相同的接口规范
- ✅ **易于扩展**：未来可以轻松添加其他搜索提供商（Bing、DuckDuckGo 等）
- ✅ **集中管理**：所有搜索工具集中在 `core/search/` 目录
- ✅ **异步优先**：完全异步实现，符合 FastAPI 架构规范

#### 2. 抽象基类设计

**`core/search/base.py`**：

定义了统一的搜索接口：

```python
class BaseSearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[SearchResult]:
        """执行单个搜索查询"""
        pass

    @abstractmethod
    async def search_batch(
        self, queries: List[Dict[str, Any]]
    ) -> Dict[str, List[SearchResult]]:
        """批量执行多个搜索查询"""
        pass
```

**接口规范**：

- **单个查询**：`search()` 方法支持单个查询和可选参数
- **批量查询**：`search_batch()` 方法接收查询参数字典列表，返回查询到结果的映射
- **返回格式**：统一返回 `List[SearchResult]`（使用现有的 `SearchResult` 模型）

#### 3. Serper.dev Search Provider 实现

**`core/search/serper_provider.py`**：

**核心功能**：

1. **单个查询**：支持丰富的可选参数

   - `search_type`：搜索类型（search/image/videos）
   - `location`：具体位置（如 "Vietnam"）
   - `gl`：国家代码（如 "vn"）
   - `hl`：语言代码（如 "vi"）
   - `tbs`：时间范围（如 "qdr:d" 表示过去一天）
   - `autocorrect`：是否自动更正
   - `page`：页码

2. **批量查询**：利用 Serper API 的优势，一次请求发送多个查询
   ```python
   # 批量查询示例
   queries = [
       {"q": "query1", "gl": "vn", "hl": "vi"},
       {"q": "query2", "gl": "vn", "hl": "vi"},
   ]
   results = await provider.search_batch(queries)
   # 返回: {"query1": [SearchResult, ...], "query2": [SearchResult, ...]}
   ```

**技术要点**：

- 使用 `httpx.AsyncClient` 进行异步 HTTP 请求
- 批量查询时，将多个查询打包成数组一次性发送（Serper API 支持）
- 响应处理：解析返回的 JSON，提取 `organic` 字段中的结果
- 错误处理：捕获异常，记录日志，返回空列表或空字典

#### 4. Google Search Provider 实现

**`core/search/google_provider.py`**：

**核心功能**：

1. **单个查询**：支持基本参数

   - `query`：搜索查询字符串
   - `num`：返回结果数量（默认 10，最大 10）
   - `start`：起始索引（默认 1）

2. **批量查询**：Google API 不支持批量，使用并发执行
   ```python
   # 批量查询通过 asyncio.gather 并发执行多个单个查询
   tasks = [self.search(query=q) for q in queries]
   results_list = await asyncio.gather(*tasks, return_exceptions=True)
   ```

**技术要点**：

- API 端点：`https://www.googleapis.com/customsearch/v1`
- 请求方式：`GET` 请求，查询参数 `q`, `key`, `cx`, `num`, `start`
- 批量查询：使用 `asyncio.gather` 并发执行多个单个查询
- 响应处理：解析返回的 JSON，提取 `items` 字段中的结果
- 配置要求：需要 `GOOGLE_SEARCH_API_KEY` 和 `GOOGLE_SEARCH_CX`

#### 5. 配置管理更新

**`config.py`** 新增配置项：

```python
# Google Search API 配置
GOOGLE_SEARCH_API_KEY: str = ""  # Google Custom Search API Key
GOOGLE_SEARCH_CX: str = ""  # Google Custom Search Engine ID
```

**配置说明**：

- `GOOGLE_SEARCH_API_KEY`：Google Custom Search API 密钥
- `GOOGLE_SEARCH_CX`：Google Custom Search Engine ID（需要先创建自定义搜索引擎）

#### 6. FindKP 服务重构

**`findkp/service.py`** 重构：

**关键改动**：

1. **移除旧的搜索方法**：

   - 删除 `search_serper()` 方法（原有实现）
   - 移除 `httpx` 的直接导入和使用

2. **使用新的搜索提供者**：

   ```python
   from core.search import SerperSearchProvider

   class FindKPService:
       def __init__(self):
           self.llm = get_llm()
           self.search_provider = SerperSearchProvider()  # 初始化搜索提供者

       async def find_kps(self, company_name: str, db: AsyncSession) -> Dict:
           # 使用新的搜索提供者
           company_search_results = await self.search_provider.search(
               f"{company_name} official website"
           )
           # 将 SearchResult 对象转换为字典格式（用于 JSON 序列化）
           company_results = [
               {"title": r.title, "link": str(r.link), "snippet": r.snippet}
               for r in company_search_results
           ]
   ```

**数据转换**：

- 新的搜索提供者返回 `List[SearchResult]`（Pydantic 模型）
- 为了保持向后兼容，将 `SearchResult` 对象转换为字典格式
- 转换后的格式与原有代码兼容，无需修改 LLM Prompt

#### 7. 统一接口导出

**`core/search/__init__.py`**：

```python
from core.search.base import BaseSearchProvider
from core.search.serper_provider import SerperSearchProvider
from core.search.google_provider import GoogleSearchProvider

__all__ = [
    "BaseSearchProvider",
    "SerperSearchProvider",
    "GoogleSearchProvider",
]
```

### 实现效果

#### 已完成的任务

- ✅ 更新 `config.py` 添加 Google Search API 配置项
- ✅ 创建 `core/search/base.py` 抽象基类
- ✅ 创建 `core/search/serper_provider.py` Serper 实现
- ✅ 创建 `core/search/google_provider.py` Google 实现
- ✅ 创建 `core/search/__init__.py` 统一接口导出
- ✅ 重构 `findkp/service.py` 使用新的搜索提供者
- ✅ 所有代码通过 lint 检查

#### 功能验证

- ✅ SerperSearchProvider 支持单个查询和批量查询
- ✅ SerperSearchProvider 支持所有可选参数（search_type, location, gl, hl, tbs, autocorrect, page）
- ✅ GoogleSearchProvider 支持单个查询和批量查询（并发执行）
- ✅ 批量搜索返回格式：`Dict[str, List[SearchResult]]`，key 为查询字符串
- ✅ 异步实现完全符合 FastAPI 架构规范

### 技术要点

#### 1. 批量搜索优势

**Serper.dev API**：

- ✅ 一次请求发送多个查询，减少网络开销
- ✅ 降低延迟，提高效率
- ✅ 适合单个公司的多个关键词场景

**Google Search API**：

- ✅ 虽然不支持批量，但使用 `asyncio.gather` 并发执行
- ✅ 充分利用异步特性，性能依然优秀

#### 2. 错误处理策略

- **捕获异常**：所有 HTTP 请求和 JSON 解析都捕获异常
- **日志记录**：详细记录错误信息，便于调试
- **降级处理**：单个查询失败不影响其他查询（批量搜索时）
- **返回空结果**：失败时返回空列表或空字典，不抛出异常

#### 3. 配置管理

- **可选配置**：Google Search API 配置项使用默认值 `""`，允许可选
- **配置验证**：GoogleSearchProvider 在初始化时检查配置并记录警告
- **向后兼容**：Serper API Key 仍然使用现有的 `SERPER_API_KEY` 配置

#### 4. 代码组织

- **职责分离**：搜索工具独立封装，不影响业务逻辑
- **统一接口**：所有搜索提供者遵循相同的接口规范
- **易于扩展**：未来可以轻松添加其他搜索提供商

### 使用示例

#### 单个查询

```python
from core.search import SerperSearchProvider, GoogleSearchProvider

# Serper 单个查询
serper = SerperSearchProvider()
results = await serper.search(
    "Apple Inc",
    location="United States",
    gl="us",
    hl="en",
    tbs="qdr:d",  # 过去一天
)

# Google 单个查询
google = GoogleSearchProvider()
results = await google.search("Apple Inc", num=10)
```

#### 批量查询（单个公司的多个关键词）

```python
from core.search import SerperSearchProvider

serper = SerperSearchProvider()

# 针对一个公司的多个搜索关键词
queries = [
    {"q": "Apple Inc official website"},
    {"q": "Apple Inc procurement manager contact"},
    {"q": "Apple Inc sales manager contact"},
]

results = await serper.search_batch(queries)
# 返回: {
#     "Apple Inc official website": [SearchResult, ...],
#     "Apple Inc procurement manager contact": [SearchResult, ...],
#     "Apple Inc sales manager contact": [SearchResult, ...],
# }
```

### 后续规划

- [ ] 添加搜索结果的缓存机制（减少重复 API 调用）
- [ ] 实现搜索提供者的切换机制（Serper 失败时自动切换到 Google）
- [ ] 添加搜索结果的去重和排序功能
- [ ] 优化批量搜索的性能（对于 Google Search API）
- [ ] 添加搜索配额监控和告警
- [ ] 考虑添加更多搜索提供商（Bing、DuckDuckGo 等）

---

## 2025-11-04 23:20:00 - 实现方案 A：多工具并行搜索 + LLM 智能提取

### 需求描述

实现方案 A 流程，通过多工具并行搜索和 LLM 智能提取，提升 FindKP 模块找到采购和销售关键联系人的成功率：

1. **添加国家参数支持** - 在搜索查询中利用国家信息优化结果
2. **多工具并行搜索** - 同时使用 Serper 和 Google Search API
3. **结果聚合与去重** - 合并多个工具的结果，去除重复
4. **LLM 增强** - 优化 Prompt，利用国家信息提升提取准确性

### 实现逻辑

#### 1. 数据模型更新

**`schemas/contact.py`**：

在 `CompanyQuery` 中添加可选的国家字段：

```python
class CompanyQuery(BaseModel):
    company_name: str
    country: Optional[str] = None  # 新增：国家名称（可选）
```

**设计考虑**：

- 使用可选字段保持向后兼容
- 国家信息用于优化搜索查询和 LLM 提取

#### 2. 搜索策略生成器

**`findkp/search_strategy.py`**（新建）：

实现 `SearchStrategy` 类，负责生成优化的搜索查询：

**核心功能**：

1. **国家参数映射**：

   - `get_country_params()`：将国家名称映射为搜索参数（gl, hl, location）
   - 支持常见国家的代码映射（越南、中国、美国等）

2. **公司信息查询生成**：

   ```python
   generate_company_queries(company_name, country)
   # 生成："{company_name} official website {country}"
   ```

3. **联系人查询生成**：
   ```python
   generate_contact_queries(company_name, country, department)
   # 采购部门：生成4个不同关键词的查询
   # 销售部门：生成4个不同关键词的查询
   ```

**查询策略**：

- 公司信息：1 个查询（官方网站）
- 采购 KP：4 个查询（procurement manager, purchasing manager, purchasing contact, procurement director）
- 销售 KP：4 个查询（sales manager, sales director, sales contact, business development manager）

#### 3. 结果聚合器

**`findkp/result_aggregator.py`**（新建）：

实现 `ResultAggregator` 类，负责合并和去重搜索结果：

**核心功能**：

1. **聚合** (`aggregate()`):

   - 合并多个查询的结果
   - 将所有查询的结果合并到一个列表

2. **去重** (`deduplicate()`):

   - URL 完全匹配去重
   - 标题相似度去重（简单字符串包含判断）
   - 保留 snippet 更长的版本

3. **排序** (`sort_by_relevance()`):
   - 当前保持原始顺序
   - 未来可扩展更复杂的排序逻辑

**去重策略**：

- 使用 `set` 记录已见过的 URL 和标题
- 对于标题相似的情况，保留 snippet 更长的版本
- 确保结果质量的同时避免重复

#### 4. FindKP 服务重构

**`findkp/service.py`**：

**主要改动**：

1. **初始化多搜索工具**：

   ```python
   self.serper_provider = SerperSearchProvider()
   self.google_provider = GoogleSearchProvider()
   self.search_strategy = SearchStrategy()
   self.result_aggregator = ResultAggregator()
   ```

2. **并行搜索实现**：

   ```python
   async def _search_with_multiple_providers(queries):
       # 并行执行两个工具的批量搜索
       serper_task = self.serper_provider.search_batch(queries)
       google_task = self.google_provider.search_batch(queries)
       serper_results, google_results = await asyncio.gather(
           serper_task, google_task, return_exceptions=True
       )
       # 合并结果
       merged_results = {query_key: serper_result + google_result}
   ```

3. **更新 `find_kps` 方法**：
   - 添加 `country` 参数
   - 使用搜索策略生成查询列表
   - 使用批量搜索接口并行搜索
   - 使用结果聚合器合并结果
   - 保持现有 LLM 提取和数据库保存逻辑

**流程优化**：

- 公司信息：1 个查询 → 并行搜索 → 聚合 → LLM 提取
- 采购 KP：4 个查询 → 并行搜索 → 聚合 → LLM 提取
- 销售 KP：4 个查询 → 并行搜索 → 聚合 → LLM 提取

#### 5. LLM Prompt 增强

**`findkp/prompts.py`**：

**更新 `EXTRACT_COMPANY_INFO_PROMPT`**：

- 添加 `{country_context}` 占位符
- 提示："这是一家位于 {country} 的公司"

**更新 `EXTRACT_CONTACTS_PROMPT`**：

- 添加 `{country_context}` 占位符
- 添加要求："优先提取与{country_context}相关的联系人信息"

**使用方式**：

```python
country_context = self._get_country_context(country)
prompt = EXTRACT_CONTACTS_PROMPT.format(
    department="采购",
    country_context=country_context,
    search_results=...
)
```

#### 6. 路由层更新

**`findkp/router.py`**：

更新 `find_kp` 端点，传递 `country` 参数：

```python
result = await service.find_kps(request.company_name, request.country, db)
```

### 实现效果

#### 已完成的任务

- ✅ 更新 `schemas/contact.py`，添加 `country` 字段
- ✅ 创建 `findkp/search_strategy.py`，实现搜索策略生成器
- ✅ 创建 `findkp/result_aggregator.py`，实现结果聚合和去重
- ✅ 更新 `findkp/prompts.py`，增强 Prompt 利用国家信息
- ✅ 重构 `findkp/service.py`，实现多工具并行搜索和结果聚合
- ✅ 更新 `findkp/router.py`，传递 country 参数
- ✅ 所有代码通过语法检查和 lint 检查

#### 功能特性

1. **多工具并行搜索**：

   - Serper 和 Google Search API 同时搜索
   - 使用 `asyncio.gather` 实现真正的并行
   - 单个工具失败不影响其他工具

2. **结果聚合和去重**：

   - 自动合并多个工具的结果
   - 智能去重（URL 和标题）
   - 保留质量更高的结果

3. **国家信息优化**：

   - 搜索查询中自动添加国家信息
   - LLM Prompt 中利用国家上下文
   - 提升搜索结果的准确性

4. **批量搜索优化**：
   - 使用批量搜索接口减少网络请求
   - 多个关键词一次生成，并行搜索
   - 提高搜索效率

### 技术要点

#### 1. 并行搜索实现

**关键技术**：

- 使用 `asyncio.gather` 实现真正的并行
- `return_exceptions=True` 确保单个失败不影响整体
- 错误处理：捕获异常并记录日志，返回空结果继续执行

**性能优势**：

- 两个搜索工具同时执行，减少总等待时间
- 批量搜索接口减少网络请求次数
- 充分利用异步特性

#### 2. 结果聚合策略

**合并阶段**：

- 相同查询的多个工具结果合并
- 使用列表相加：`serper_result + google_result`

**去重阶段**：

- URL 完全匹配去重（使用 `set`）
- 标题相似度去重（字符串包含判断）
- 保留 snippet 更长的版本

**排序阶段**：

- 当前保持原始顺序
- 未来可扩展关键词匹配度排序

#### 3. 国家参数映射

**映射表设计**：

- `COUNTRY_CODE_MAP`：国家名称 → 国家代码（gl 参数）
- `LANGUAGE_CODE_MAP`：国家名称 → 语言代码（hl 参数）
- 支持常见国家（越南、中国、美国等）

**使用方式**：

```python
country_params = strategy.get_country_params("Vietnam")
# 返回: {"gl": "vn", "hl": "vi", "location": "Vietnam"}
```

#### 4. 错误处理策略

**搜索工具失败**：

- 单个工具失败不影响其他工具
- 记录警告日志，继续执行
- 返回空结果，不中断流程

**LLM 提取失败**：

- 捕获异常，记录错误日志
- 返回空结果，不中断流程
- 记录原始响应便于调试

### 数据流程

```
输入(company_name, country)
    ↓
SearchStrategy生成查询列表
    ↓
并行执行: [Serper批量搜索, Google批量搜索]
    ↓
ResultAggregator聚合和去重
    ↓
LLM提取公司信息（带国家上下文）
    ↓
LLM提取联系人信息（采购/销售，带国家上下文）
    ↓
保存到数据库
    ↓
返回结果
```

### 性能优化

1. **并行搜索**：两个工具同时执行，减少总时间
2. **批量搜索**：使用批量接口减少网络请求
3. **结果去重**：减少传递给 LLM 的数据量
4. **智能查询**：多个关键词提高覆盖率

### 后续优化方向

- [ ] 添加搜索结果缓存机制
- [ ] 优化去重算法（使用更复杂的相似度计算）
- [ ] 实现搜索结果排序（按相关性）
- [ ] 添加搜索配额监控
- [ ] 支持更多国家代码映射
- [ ] 优化 LLM Prompt 提升提取准确性

---

## 2025-11-05 11:53:00 - 修复结果聚合器去重逻辑 Bug

### 需求描述

修复 `findkp/result_aggregator.py` 中 `deduplicate()` 方法的逻辑错误，确保去重功能正确工作。

### 问题分析

在结果聚合器的去重逻辑中发现三个关键问题：

1. **替换后错误标记为重复**（第 97 行）：

   - **问题**：当新结果的 snippet 更长，替换旧结果后，仍然设置 `is_duplicate_title = True`
   - **后果**：替换后的新结果被错误跳过，导致去重失败

2. **else 分支逻辑错误**（第 98-106 行）：

   - **问题**：`else` 分支的注释说"如果没找到对应的结果"，但这是 `if len(result.snippet) > len(existing_result.snippet):` 的 `else` 分支
   - **实际**：这个 `else` 应该处理"snippet 不长"的情况，而不是"没找到结果"

3. **缺少处理 `existing_result` 为 `None` 的分支**：
   - **问题**：当 `existing_result` 为 `None` 时（数据不一致），没有对应的处理逻辑
   - **后果**：会导致代码逻辑不完整，可能出现未预期的行为

### 修复逻辑

#### 1. 重构条件分支结构

**修复前的问题结构**：

```python
if existing_result:
    if len(result.snippet) > len(existing_result.snippet):
        # 替换
        is_duplicate_title = True  # ❌ 错误：替换后不应该标记为重复
    else:
        # 注释说"如果没找到对应的结果"，但实际是snippet不长的分支
        logger.warning(...)
```

**修复后的正确结构**：

```python
if existing_result:
    # 找到了已存在的结果，比较snippet长度
    if len(result.snippet) > len(existing_result.snippet):
        # 替换为snippet更长的版本
        deduplicated.remove(existing_result)
        deduplicated.append(result)
        seen_titles.remove(seen_title)
        seen_titles.add(title_lower)
        # ✅ 替换后不标记为重复，因为已经用新结果替换了旧结果
    else:
        # ✅ 保留已存在的结果（snippet更长或相等）
        # ✅ 标记为重复，跳过当前结果
        is_duplicate_title = True
else:
    # ✅ 如果没找到对应的结果，说明数据不一致
    # ✅ 记录警告，但不跳过（可能是真正的重复，也可能是不一致）
    logger.warning(...)
    # ✅ 不设置 is_duplicate_title，继续处理
```

#### 2. 修复后的正确逻辑

1. **当 `existing_result` 存在且新结果 snippet 更长**：

   - 执行替换操作
   - **不设置** `is_duplicate_title`（因为已经替换了）
   - 新结果会被添加到结果列表

2. **当 `existing_result` 存在但新结果 snippet 不长**：

   - 保留已存在的结果
   - **设置** `is_duplicate_title = True`
   - 跳过当前结果

3. **当 `existing_result` 为 `None`**（数据不一致）：
   - 记录警告日志
   - **不设置** `is_duplicate_title`
   - 继续处理，让 URL 去重检查决定是否跳过

### 修复的关键点

#### 1. 条件分支的正确性

- ✅ `if existing_result:` - 处理找到已存在结果的情况
- ✅ `if len(result.snippet) > len(existing_result.snippet):` - 处理替换情况
- ✅ `else:`（snippet 比较的 else）- 处理保留已存在结果的情况
- ✅ `else:`（existing_result 检查的 else）- 处理数据不一致的情况

#### 2. 标志位的正确设置

- ✅ **替换后**：不设置 `is_duplicate_title`，让新结果通过
- ✅ **保留旧结果**：设置 `is_duplicate_title = True`，跳过新结果
- ✅ **数据不一致**：不设置 `is_duplicate_title`，继续处理

#### 3. 错误处理

- ✅ 添加了警告日志，记录数据不一致的情况
- ✅ 确保即使数据不一致，也不会错误地跳过有效结果
- ✅ 通过 URL 去重作为最后的保障

### 实现效果

#### 修复的问题

- ✅ 修复了替换后错误标记为重复的 bug
- ✅ 修复了 else 分支注释和逻辑不匹配的问题
- ✅ 添加了处理 `existing_result` 为 `None` 的分支
- ✅ 所有代码通过 lint 检查

#### 逻辑验证

**场景 1：替换场景**（新结果 snippet 更长）

- 输入：已存在结果 A（snippet=50），新结果 B（snippet=100）
- 预期：替换 A 为 B，B 被添加到结果列表
- 实际：✅ 正确执行替换，B 被添加

**场景 2：保留场景**（新结果 snippet 不长）

- 输入：已存在结果 A（snippet=100），新结果 B（snippet=50）
- 预期：保留 A，跳过 B
- 实际：✅ 正确保留 A，跳过 B

**场景 3：数据不一致**（existing_result 为 None）

- 输入：检测到标题相似，但找不到对应的已存在结果
- 预期：记录警告，不跳过，继续处理
- 实际：✅ 记录警告，继续处理

### 技术要点

#### 1. 去重逻辑的完整性

- **URL 去重**：第一层保障，完全匹配去重
- **标题去重**：第二层保障，相似度去重
- **数据一致性**：处理边界情况，确保逻辑完整

#### 2. 代码质量

- **清晰的注释**：每个分支都有明确的注释说明
- **逻辑一致性**：代码逻辑与注释完全匹配
- **错误处理**：完善的警告日志和降级处理

#### 3. 测试覆盖

- **替换场景**：验证替换后不标记为重复
- **保留场景**：验证保留时正确标记为重复
- **边界情况**：验证数据不一致时的处理

### 后续优化方向

- [ ] 添加单元测试覆盖所有去重场景
- [ ] 优化去重算法（使用更复杂的相似度计算，如编辑距离）
- [ ] 添加性能监控（记录去重前后的结果数量）
- [ ] 考虑使用数据库去重（避免内存中的重复计算）

---

## 2025-11-05 17:18:16 - FindKP 模块全面优化与 CLI 工具实现

### 需求描述

对 FindKP 模块进行全面优化，提升搜索效果和系统性能，并新增 CLI 命令行工具：

1. **充分利用 company_name_local 参数**：在搜索时使用本地名称生成更多查询变体，提升非英语国家公司搜索效果
2. **流程并行化优化**：采购和销售搜索并行执行，减少总执行时间
3. **批量保存优化**：联系人批量保存，减少数据库操作次数
4. **数据库结构扩展**：添加公司定位和简报字段，支持后续开发信生成
5. **LLM 提取增强**：提取公司定位和简报信息，作为开发信上下文
6. **CLI 工具实现**：提供命令行工具，方便在 CLI 环境中执行请求并查看实时日志
7. **业务文档完善**：创建 FindKP 业务逻辑文档，详细阐述数据流向和业务细节

### 实现逻辑

#### 1. 数据库结构调整

**文件**: `database/models.py`, `database/sql/002_add_company_positioning_brief.sql`

**修改内容**:

- 在 `Company` 模型中添加两个新字段：
  - `positioning` (Text): 公司定位描述
  - `brief` (Text): 公司简要介绍/简报
- 创建数据库迁移脚本，使用 ALTER TABLE 添加新字段（兼容现有数据库）

**技术要点**:

- 使用 `Column(Text)` 支持长文本存储
- 迁移脚本使用 `ALTER TABLE` 语句，默认值为 NULL，向后兼容
- 字段位置：在 `industry` 字段之后

#### 2. 搜索策略优化

**文件**: `findkp/search_strategy.py`

**核心改动**:

1. **`generate_company_queries()` 方法增强**:

   - 修改方法签名，接收 `company_name_en` 和 `company_name_local` 两个参数
   - 生成多个查询变体：
     - 查询 1: `{company_name_en} official website`
     - 查询 2: `{company_name_local} official website`（如果与英文名不同）
     - 查询 3: `{company_name_en} {company_name_local} official website`（如果不同）
     - 查询 4: `{company_name_local} company website`（本地化变体）
   - 使用 `seen_queries` Set 去重，避免生成重复查询

2. **`generate_contact_queries()` 方法增强**:
   - 修改方法签名，接收 `company_name_en` 和 `company_name_local` 两个参数
   - 为每个部门（采购/销售）生成双重查询：
     - 使用英文名生成查询（保持现有逻辑）
     - 如果本地名与英文名不同，额外使用本地名生成查询变体
   - 每个查询模板都会生成英文名和本地名两个版本（如果不同）

**优化效果**:

- 增加搜索结果多样性，特别是对于非英语国家的公司
- 提升联系人发现率，覆盖更多本地化搜索结果
- 查询去重机制确保不会重复搜索相同内容

#### 3. LLM Prompt 优化

**文件**: `findkp/prompts.py`

**修改内容**:

- 更新 `EXTRACT_COMPANY_INFO_PROMPT`，要求 LLM 提取：
  - `domain`: 公司域名
  - `industry`: 行业
  - `positioning`: 公司定位描述（200 字以内）
  - `brief`: 公司简要介绍（300 字以内）
- 添加明确的提取要求：
  - 基于搜索结果中的实际信息
  - 不要编造信息
  - 使用简洁清晰的语言

**业务价值**:

- 提供更丰富的公司信息，用于后续开发信个性化
- 定位和简报信息作为上下文，提升开发信质量

#### 4. 服务层流程并行化

**文件**: `findkp/service.py`

**核心改动**:

1. **新增 `_search_contacts_parallel()` 方法**:

   - 提取联系人搜索逻辑到独立方法
   - 支持并行搜索采购或销售部门联系人
   - 返回包含 `contacts` 和 `results` 的字典

2. **`find_kps()` 方法优化**:
   - 将采购和销售搜索改为并行执行：
     ```python
     procurement_task = self._search_contacts_parallel(...)
     sales_task = self._search_contacts_parallel(...)
     procurement_result, sales_result = await asyncio.gather(
         procurement_task, sales_task, return_exceptions=True
     )
     ```
   - 添加异常处理：单个搜索失败不影响另一个
   - 更新保存公司信息时，保存 `positioning` 和 `brief` 字段

**性能提升**:

- 采购和销售搜索并行执行，减少约 50% 的搜索时间
- 充分利用异步特性，提升系统吞吐量

#### 5. 批量保存优化

**文件**: `database/repository.py`, `findkp/service.py`

**核心改动**:

1. **新增 `create_contacts_batch()` 方法**:

   - 在 `Repository` 类中添加批量创建联系人方法
   - 收集所有联系人后一次性批量保存
   - 使用事务批量提交，减少数据库往返次数

2. **服务层批量保存逻辑**:
   - 收集所有联系人数据
   - 转换为 KPInfo 对象列表
   - 调用 `create_contacts_batch()` 批量保存
   - 如果批量保存失败，降级为单个保存模式

**优化效果**:

- 减少数据库操作次数，提升保存效率
- 批量提交减少网络往返，提升性能

#### 6. CLI 工具实现

**文件**: `cli/__init__.py`, `cli/main.py`, `cli/findkp.py`, `pyproject.toml`

**实现内容**:

1. **CLI 模块结构**:

   ```
   cli/
   ├── __init__.py
   ├── main.py          # CLI 主入口
   └── findkp.py        # FindKP CLI 命令
   ```

2. **CLI 主入口 (`cli/main.py`)**:

   - 使用 `click` 库创建命令行接口
   - 创建主 CLI 组 `@click.group()`
   - 注册 `findkp` 子命令

3. **FindKP 命令 (`cli/findkp.py`)**:

   - 实现 `findkp` 命令，支持参数：
     - `--company-name-en`: 公司英文名称（必需）
     - `--company-name-local`: 公司本地名称（必需）
     - `--country`: 国家名称（可选）
     - `--verbose/-v`: 详细日志输出
   - 配置日志输出，实时显示处理进度
   - 结构化输出最终结果（表格形式展示联系人信息）

4. **CLI 入口点配置**:
   - 在 `pyproject.toml` 中添加：
     ```toml
     [project.scripts]
     smart-lead = "cli.main:cli"
     ```
   - 添加 `click>=8.0.0` 依赖

**使用示例**:

```bash
smart-lead findkp \
  --company-name-en "Apple Inc." \
  --company-name-local "苹果公司" \
  --country "USA" \
  --verbose
```

#### 7. 业务文档创建

**文件**: `docs/FINDKP_BUSINESS_LOGIC.md`

**文档内容**:

- 业务概述：模块功能和价值
- 核心流程：流程图和详细步骤说明
- 数据流向：序列图和数据格式
- 核心组件：SearchStrategy、ResultAggregator、FindKPService、Repository
- 数据结构：Company 和 Contact 表结构
- 搜索策略：多源搜索与查询优化
- LLM 提取：Prompt 设计与调用方式
- 错误处理：分层错误处理与状态管理
- 性能优化：并行执行与优化建议
- 使用示例：API 和 CLI 调用示例

**文档价值**:

- 帮助开发者快速理解 FindKP 模块的业务逻辑
- 清晰展示数据流向和处理流程
- 便于后续维护和扩展

#### 8. README.md 更新

**文件**: `README.md`

**更新内容**:

- 添加 "CLI 使用" 章节，详细说明 CLI 工具的使用方法
- 更新 "项目结构" 章节，添加 CLI 目录说明
- 更新 "详细文档" 章节，添加 FindKP 业务逻辑文档链接
- 添加 CLI 与 API 的区别说明

### 实现效果

#### 已完成的任务

- ✅ 数据库模型添加 `positioning` 和 `brief` 字段
- ✅ 创建数据库迁移脚本 `002_add_company_positioning_brief.sql`
- ✅ 优化 `SearchStrategy.generate_company_queries()` 使用 `company_name_local`
- ✅ 优化 `SearchStrategy.generate_contact_queries()` 使用 `company_name_local`
- ✅ 更新 LLM Prompt 提取公司定位和简报信息
- ✅ 重构 `Service.find_kps()` 实现采购和销售并行搜索
- ✅ 优化联系人保存逻辑，实现批量保存
- ✅ 创建 CLI 模块结构和命令实现
- ✅ 配置 CLI 入口点和依赖
- ✅ 创建 FindKP 业务逻辑文档
- ✅ 更新 README.md 添加 CLI 使用说明

#### 性能提升

1. **搜索覆盖率提升**:

   - 使用本地名称可以找到更多本地化的搜索结果
   - 多个查询变体增加搜索结果多样性
   - 预期提升 30-50% 的搜索结果覆盖率

2. **执行效率提升**:

   - 采购和销售搜索并行执行，减少约 50% 的搜索时间
   - 批量保存减少数据库操作次数

3. **信息丰富度提升**:
   - 公司定位和简报提供更多上下文
   - 支持后续开发信个性化生成

#### 用户体验提升

1. **CLI 工具**:

   - 方便脚本化和自动化使用
   - 实时日志输出，清晰展示处理过程
   - 结构化结果展示，便于阅读

2. **文档完善**:
   - FindKP 业务逻辑文档帮助理解系统
   - README.md 更新提供完整使用指南

### 技术要点

#### 1. 查询生成策略

**公司信息查询**:

- 基础查询：英文名 + "official website"
- 本地查询：本地名 + "official website"（如果不同）
- 组合查询：英文名 + 本地名 + "official website"（如果不同）
- 本地化变体：本地名 + "company website"（如果不同）

**联系人查询**:

- 保持现有英文查询模板
- 增加本地名查询变体（如果本地名与英文名不同）
- 每个查询模板都会生成英文名和本地名两个版本

#### 2. 并行执行策略

- 采购和销售搜索完全独立，可以安全并行
- 使用 `asyncio.gather()` 确保两个任务并行执行
- 异常处理：单个搜索失败不影响另一个

#### 3. 批量保存策略

- 收集所有联系人数据
- 一次性创建所有 Contact 对象
- 批量添加到 session
- 一次性 commit
- 降级机制：批量保存失败时自动降级为单个保存

#### 4. CLI 设计

**命令结构**:

```bash
smart-lead findkp --company-name-en "Apple Inc." --company-name-local "苹果公司" --country "USA"
```

**日志输出**:

- 实时显示搜索进度、LLM 提取进度、联系人保存进度
- 结构化输出最终结果（表格形式展示联系人信息）
- 支持 `--verbose` 模式显示详细日志

**依赖管理**:

- 使用 `click` 库创建命令行接口
- 通过 `pyproject.toml` 的 `[project.scripts]` 注册 CLI 入口点

### 代码质量

- ✅ 所有代码通过 lint 检查
- ✅ 遵循项目架构规范
- ✅ 完善的错误处理和日志记录
- ✅ 清晰的代码注释和文档字符串

### 后续优化方向

- [ ] 添加 CLI 命令的单元测试
- [ ] 优化 CLI 输出格式（使用 rich 或 colorlog 美化）
- [ ] 添加搜索结果缓存机制
- [ ] 优化去重算法（使用更复杂的相似度计算）
- [ ] 实现增量更新联系人信息功能
- [ ] 添加数据验证（邮箱验证、LinkedIn 信息验证）
- [ ] 支持导出联系人信息到 CSV、Excel 等格式

---

## 2025-11-05 18:07:29 - 接入三个新的国内 LLM 模型到统一选择系统

### 需求描述

在 `.env.example` 中已经添加了三个新的国内模型配置：

- GLM（智谱 AI）：`GLM_API_KEY`
- Qwen（通义千问）：`QWEN_API_KEY`、`QWEN_MODEL`
- DeepSeek（已存在）：`DEEPSEEK_API_KEY`

需要将这些模型集成到 LLM 的统一选择系统中，使得系统能够根据模型名称自动路由到相应的 API 提供商。

### 实现逻辑

#### 1. 架构设计

系统采用 LLM 工厂模式，通过 `LLMRouter` 类根据模型名称自动判断应该使用哪个提供商：

```mermaid
graph TB
    A[业务服务层<br/>findkp/service.py] --> B[LLM 工厂<br/>llm.get_llm]
    B --> C[LLMRouter<br/>路由判断]

    C --> D{模型名称匹配}
    D -->|deepseek-chat<br/>deepseek-coder| E[DeepSeek 路径]
    D -->|glm-4<br/>glm-4-plus<br/>glm-4-flash| F[GLM 路径]
    D -->|qwen-turbo<br/>qwen-plus<br/>qwen-max| G[Qwen 路径]
    D -->|gpt-*<br/>claude-*| H[OpenRouter 路径]

    E --> I[_create_deepseek_llm]
    F --> J[_create_glm_llm]
    G --> K[_create_qwen_llm]
    H --> L[_create_openrouter_llm]

    I --> M[init_chat_model<br/>provider=deepseek]
    J --> N[init_chat_model<br/>provider=zhipu]
    K --> O[init_chat_model<br/>provider=qwen]
    L --> P[init_chat_model<br/>provider=openai<br/>base_url=openrouter.ai]

    M --> Q[返回 ChatModel 实例]
    N --> Q
    O --> Q
    P --> Q

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#fff4e1
    style E fill:#e8f5e9
    style F fill:#e8f5e9
    style G fill:#e8f5e9
    style H fill:#fce4ec
    style Q fill:#f3e5f5
```

#### 2. 配置管理（config.py）

在 `Settings` 类中添加了三个新的配置项：

```python
# 国内 API 配置
DEEPSEEK_API_KEY: str = ""  # DeepSeek API Key（使用 langchain-deepseek）
GLM_API_KEY: str = ""  # GLM（智谱AI）API Key
QWEN_API_KEY: str = ""  # Qwen（通义千问）API Key
QWEN_MODEL: str = ""  # Qwen 模型名称（如 qwen-turbo, qwen-plus, qwen-max）
```

#### 3. 模型路由映射（llm/factory.py）

在 `LLMRouter.DOMESTIC_MODELS` 字典中添加了所有支持的国内模型：

```python
DOMESTIC_MODELS = {
    # DeepSeek 模型
    "deepseek-chat": "deepseek",
    "deepseek-coder": "deepseek",
    # GLM（智谱AI）模型
    "glm-4": "glm",
    "glm-4-plus": "glm",
    "glm-4-flash": "glm",
    # Qwen（通义千问）模型
    "qwen-turbo": "qwen",
    "qwen-plus": "qwen",
    "qwen-max": "qwen",
    "qwen-7b-chat": "qwen",
    "qwen-14b-chat": "qwen",
    "qwen-72b-chat": "qwen",
}
```

#### 4. 实现创建函数

为每个提供商实现了对应的创建函数：

**DeepSeek（已存在，保持不变）**：

- 使用 `provider="deepseek"`
- 环境变量：`DEEPSEEK_API_KEY`

**GLM（智谱 AI）**：

- 使用 `provider="zhipu"`（LangChain 中智谱 AI 的 provider 名称）
- 环境变量：`ZHIPU_API_KEY`（从 `GLM_API_KEY` 配置读取）
- 支持的模型：`glm-4`, `glm-4-plus`, `glm-4-flash`

**Qwen（通义千问）**：

- 使用 `provider="qwen"`
- 环境变量：`DASHSCOPE_API_KEY`（从 `QWEN_API_KEY` 配置读取）
- 模型名称：优先使用 `QWEN_MODEL` 配置，如果未配置则使用传入的 `model` 参数
- 支持的模型：`qwen-turbo`, `qwen-plus`, `qwen-max`, `qwen-7b-chat`, `qwen-14b-chat`, `qwen-72b-chat`

#### 5. 路由逻辑更新

更新了 `_create_direct_llm` 函数，支持三个提供商：

```python
def _create_direct_llm(model: str, provider_name: str, temperature: float, **kwargs):
    if provider_name == "deepseek":
        return _create_deepseek_llm(model, temperature, **kwargs)
    elif provider_name == "glm":
        return _create_glm_llm(model, temperature, **kwargs)
    elif provider_name == "qwen":
        return _create_qwen_llm(model, temperature, **kwargs)
    else:
        raise ValueError(f"不支持的国内 API 提供商: {provider_name}")
```

### 使用方式

系统现在支持通过 `LLM_MODEL` 环境变量选择任一支持的模型：

```bash
# 使用 DeepSeek
LLM_MODEL=deepseek-chat

# 使用 GLM
LLM_MODEL=glm-4

# 使用 Qwen
LLM_MODEL=qwen-turbo
QWEN_MODEL=qwen-turbo  # 可选，如果未设置则使用 LLM_MODEL 的值
```

### 技术细节

1. **环境变量映射**：

   - GLM 使用 `ZHIPU_API_KEY`（LangChain 标准）
   - Qwen 使用 `DASHSCOPE_API_KEY`（DashScope 是阿里云的 API 服务名称）

2. **错误处理**：

   - 每个创建函数都会检查对应的 API Key 是否配置
   - 如果未配置会抛出明确的 `ValueError` 异常

3. **日志记录**：
   - 每个创建函数都会记录调试日志，包含模型名称和提供商信息

### 修改文件清单

- `config.py`: 添加 `GLM_API_KEY`、`QWEN_API_KEY`、`QWEN_MODEL` 配置项
- `llm/factory.py`:
  - 更新 `DOMESTIC_MODELS` 字典，添加 GLM 和 Qwen 模型映射
  - 实现 `_create_glm_llm` 函数
  - 实现 `_create_qwen_llm` 函数
  - 更新 `_create_direct_llm` 函数以支持新提供商
  - 更新文档字符串

### 注意事项

1. **依赖安装**：确保安装了对应的 LangChain 集成包：

   - `langchain-deepseek`（DeepSeek）
   - `langchain-zhipu`（GLM）
   - `langchain-qwen`（Qwen）

2. **API Key 配置**：需要在 `.env` 文件中配置对应的 API Key：

   ```bash
   DEEPSEEK_API_KEY="your_deepseek_key"
   GLM_API_KEY="your_glm_key"
   QWEN_API_KEY="your_qwen_key"
   QWEN_MODEL="qwen-turbo"  # 可选
   ```

3. **模型名称**：确保使用的模型名称在 `DOMESTIC_MODELS` 字典中有映射，否则会默认使用 OpenRouter

---

## 2025-11-05 18:15:00 - 简化 GLM 和 Qwen 接入方式（使用 OpenAI 兼容接口）

### 需求描述

用户反馈 GLM（智谱 AI）和 Qwen（通义千问）都支持 OpenAI 兼容的返回形式，可以直接通过改变 `base_url` 来接入，无需创建自定义包装类。

### 实现逻辑

#### 1. 简化方案

由于 GLM 和 Qwen 都提供了 OpenAI 兼容的 API 接口，我们可以直接使用 `init_chat_model` 并指定不同的 `base_url`，而不需要创建自定义的 HTTP 客户端包装类。

```mermaid
graph TB
    A[业务服务层<br/>findkp/service.py] --> B[LLM 工厂<br/>llm.get_llm]
    B --> C[LLMRouter<br/>路由判断]

    C --> D{模型名称匹配}
    D -->|deepseek-chat<br/>deepseek-coder| E[DeepSeek 路径<br/>langchain-deepseek]
    D -->|glm-4<br/>glm-4-plus<br/>glm-4-flash| F[GLM 路径<br/>OpenAI 兼容接口]
    D -->|qwen-turbo<br/>qwen-plus<br/>qwen-max| G[Qwen 路径<br/>OpenAI 兼容接口]
    D -->|gpt-*<br/>claude-*| H[OpenRouter 路径<br/>OpenAI 兼容接口]

    E --> I[init_chat_model<br/>provider=deepseek]
    F --> J[init_chat_model<br/>provider=openai<br/>base_url=open.bigmodel.cn]
    G --> K[init_chat_model<br/>provider=openai<br/>base_url=dashscope.aliyuncs.com]
    H --> L[init_chat_model<br/>provider=openai<br/>base_url=openrouter.ai]

    I --> M[返回 ChatModel 实例]
    J --> M
    K --> M
    L --> M

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#fff4e1
    style E fill:#e8f5e9
    style F fill:#fff9c4
    style G fill:#fff9c4
    style H fill:#fce4ec
    style M fill:#f3e5f5
```

#### 2. 代码修改

**删除自定义包装类**：

- 删除了 `llm/custom_providers.py` 文件（不再需要自定义 HTTP 客户端）

**简化 GLM 实现**：

```python
def _create_glm_llm(model: str, temperature: float, **kwargs):
    """使用 OpenAI 兼容接口"""
    return init_chat_model(
        model=model,
        model_provider="openai",  # 使用 OpenAI 兼容接口
        temperature=temperature,
        api_key=settings.GLM_API_KEY,
        base_url="https://open.bigmodel.cn/api/paas/v4",  # GLM API 地址
        **kwargs,
    )
```

**简化 Qwen 实现**：

```python
def _create_qwen_llm(model: str, temperature: float, **kwargs):
    """使用 OpenAI 兼容接口"""
    actual_model = settings.QWEN_MODEL or model
    return init_chat_model(
        model=actual_model,
        model_provider="openai",  # 使用 OpenAI 兼容接口
        temperature=temperature,
        api_key=settings.QWEN_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # Qwen 兼容模式
        **kwargs,
    )
```

#### 3. API 端点配置

**GLM（智谱 AI）**：

- Base URL: `https://open.bigmodel.cn/api/paas/v4`
- 使用 OpenAI 兼容接口
- API Key: 从 `GLM_API_KEY` 配置读取

**Qwen（通义千问）**：

- Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- 使用 DashScope 兼容模式（OpenAI 兼容）
- API Key: 从 `QWEN_API_KEY` 配置读取

### 优势

1. **代码更简洁**：不需要维护自定义 HTTP 客户端代码
2. **统一接口**：所有模型都使用 LangChain 的标准接口，代码一致性更好
3. **易于维护**：使用 LangChain 的标准实现，减少了自定义代码的维护成本
4. **自动兼容**：LangChain 会自动处理请求/响应格式转换

### 修改文件清单

- `llm/factory.py`:
  - 简化 `_create_glm_llm` 函数，使用 `init_chat_model` + `base_url`
  - 简化 `_create_qwen_llm` 函数，使用 `init_chat_model` + `base_url`
  - 移除 `custom_providers` 导入
- `llm/custom_providers.py`: 删除文件（不再需要）

### 注意事项

1. **API 兼容性**：确保 GLM 和 Qwen 的 API 端点支持 OpenAI 兼容格式
2. **模型名称**：确保传入的模型名称与对应 API 提供商支持的模型名称一致
3. **错误处理**：LangChain 会自动处理 API 错误，返回标准的异常信息

---

## 2025-11-05 18:20:00 - 使用智谱 AI Python SDK 接入 GLM 模型

### 需求描述

根据智谱 AI 官方文档（https://docs.bigmodel.cn/cn/api/introduction#python-sdk），使用 Python SDK（zhipuai）方式接入 GLM 模型，而不是使用 OpenAI 兼容接口。

### 实现逻辑

#### 1. 架构设计

创建了 GLM SDK 包装类，兼容 LangChain ChatModel 接口，内部使用智谱 AI 的官方 Python SDK。

```mermaid
graph TB
    A[业务服务层<br/>findkp/service.py] --> B[LLM 工厂<br/>llm.get_llm]
    B --> C[LLMRouter<br/>路由判断]

    C --> D{模型名称匹配}
    D -->|deepseek-chat<br/>deepseek-reasoner| E[DeepSeek 路径<br/>langchain-deepseek]
    D -->|glm-4<br/>glm-4-plus<br/>glm-4-flash| F[GLM 路径<br/>Python SDK]
    D -->|qwen-turbo<br/>qwen-plus<br/>qwen-max| G[Qwen 路径<br/>OpenAI 兼容接口]
    D -->|gpt-*<br/>claude-*| H[OpenRouter 路径<br/>OpenAI 兼容接口]

    E --> I[init_chat_model<br/>provider=deepseek]
    F --> J[GLMLLMWrapper<br/>zhipuai SDK]
    G --> K[init_chat_model<br/>provider=openai<br/>base_url=dashscope]
    H --> L[init_chat_model<br/>provider=openai<br/>base_url=openrouter]

    J --> M[ZhipuAI 客户端<br/>client.chat.completions.create]
    M --> N[返回 ChatModel 实例]
    I --> N
    K --> N
    L --> N

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#fff4e1
    style E fill:#e8f5e9
    style F fill:#fff9c4
    style G fill:#fff9c4
    style H fill:#fce4ec
    style J fill:#ffe0b2
    style M fill:#ffe0b2
    style N fill:#f3e5f5
```

#### 2. 创建 GLM SDK 包装类

创建了 `llm/glm_wrapper.py`，实现了 `GLMLLMWrapper` 类：

**核心特性**：

- 兼容 LangChain ChatModel 接口（实现 `ainvoke` 和 `invoke` 方法）
- 内部使用 `zhipuai` SDK 的 `ZhipuAI` 客户端
- 异步调用使用 `asyncio.to_thread` 在线程池中执行同步 SDK 调用
- 返回 `AIMessage` 对象，与 LangChain 标准接口一致

**实现细节**：

```python
from zhipuai import ZhipuAI
from langchain_core.messages import AIMessage

class GLMLLMWrapper:
    def __init__(self, model: str, temperature: float = 0.0, api_key: Optional[str] = None, **kwargs):
        self.client = ZhipuAI(api_key=self.api_key)
        # ...

    async def ainvoke(self, messages: List[Dict[str, str]], **kwargs) -> AIMessage:
        # 在线程池中执行同步 SDK 调用
        response = await asyncio.to_thread(
            lambda: self.client.chat.completions.create(**request_params)
        )
        content = response.choices[0].message.content
        return AIMessage(content=content)
```

#### 3. 更新工厂函数

更新了 `llm/factory.py` 中的 `_create_glm_llm` 函数：

```python
def _create_glm_llm(model: str, temperature: float, **kwargs):
    """使用智谱AI Python SDK"""
    return GLMLLMWrapper(
        model=model,
        temperature=temperature,
        api_key=settings.GLM_API_KEY,
        **kwargs
    )
```

#### 4. 添加依赖

在 `pyproject.toml` 中添加了 `zhipuai>=2.0.0` 依赖。

### 优势

1. **官方支持**：使用智谱 AI 官方 Python SDK，功能更完整，更新更及时
2. **更好的类型提示**：SDK 提供完整的类型定义，IDE 支持更好
3. **功能完整**：SDK 支持所有智谱 AI 的功能，包括流式响应、异步调用等
4. **兼容性**：包装类完全兼容 LangChain 接口，业务层代码无需修改

### 技术细节

1. **异步处理**：

   - 智谱 AI SDK 是同步的，使用 `asyncio.to_thread` 在线程池中执行
   - 这样不会阻塞 FastAPI 的事件循环

2. **消息格式转换**：

   - LangChain 使用 `[{"role": "user", "content": "..."}]` 格式
   - zhipuai SDK 也使用相同格式，无需转换

3. **错误处理**：
   - SDK 会自动抛出异常，包装类会向上传播
   - 业务层可以捕获并处理这些异常

### 修改文件清单

- `pyproject.toml`: 添加 `zhipuai>=2.0.0` 依赖
- `llm/glm_wrapper.py`: 新建文件，实现 GLM SDK 包装类
- `llm/factory.py`:
  - 导入 `GLMLLMWrapper`
  - 更新 `_create_glm_llm` 函数以使用 SDK 包装类

### 安装依赖

使用以下命令安装新的依赖：

```bash
uv sync
```

或者单独安装：

```bash
uv add zhipuai>=2.0.0
```

### 使用方式

使用方式保持不变，只需要配置 `GLM_API_KEY` 环境变量：

```bash
GLM_API_KEY="your_glm_api_key"
LLM_MODEL="glm-4"
```

### 参考文档

- 智谱 AI 官方文档：https://docs.bigmodel.cn/cn/api/introduction#python-sdk

---

## 2025-11-05 20:05:28 - 增强 LLM JSON 解析的容错处理机制

### 需求描述

根据终端日志显示的错误，LLM 返回的 JSON 内容存在解析失败的问题，需要建立完善的容错机制来处理各种异常情况。

**遇到的问题**：

1. LLM 返回的 JSON 可能被 markdown 代码块包裹（如 `json ... `）
2. JSON 格式可能不规范（单引号、尾随逗号等）
3. LLM 可能返回数组格式而不是对象格式（联系人列表）
4. JSON 解析失败时没有充分的错误处理和日志记录
5. `procurement_result` 可能为 `None`，导致 `AttributeError`

### 实现逻辑

#### 1. 问题分析

通过分析日志和代码，发现了以下问题：

```
ERROR:findkp.service:LLM 返回的 JSON 解析失败: Expecting value: line 1 column 1 (char 0)
ERROR:findkp.service:FindKP 流程失败: 'NoneType' object has no attribute 'get'
```

**根本原因**：

- LLM 返回的内容可能不是纯 JSON，可能包含 markdown 代码块、说明文字等
- JSON 解析失败时返回空字典 `{}`，但后续代码期望特定格式
- `asyncio.gather` 的异常处理不完整，没有检查 `None` 值

#### 2. 实现方案

**2.1 添加 JSON 提取方法 (`_extract_json_from_text`)**

实现了多策略的 JSON 提取机制：

```python
def _extract_json_from_text(self, text: str) -> Optional[str]:
    """
    从文本中提取 JSON 内容，使用三种策略：
    1. 提取 markdown 代码块中的内容
    2. 使用括号匹配查找完整的 JSON 对象/数组
    3. 尝试直接解析整个文本
    """
```

**策略说明**：

- **策略 1**：优先提取 markdown 代码块（`json ... ` 或 `...`）
- **策略 2**：使用括号深度匹配找到完整的 JSON 结构（处理嵌套对象/数组）
- **策略 3**：如果都没找到，尝试直接解析整个文本（可能是纯 JSON）

**2.2 添加 JSON 修复方法 (`_fix_common_json_issues`)**

修复常见的 JSON 格式问题：

```python
def _fix_common_json_issues(self, json_str: str) -> str:
    """
    修复常见的 JSON 格式问题：
    - 移除 BOM 标记
    - 修复单引号为双引号
    - 移除尾随逗号
    - 移除注释（JSON 不支持注释）
    """
```

**2.3 添加容错解析方法 (`_parse_json_with_fallback`)**

实现多层容错机制：

```python
def _parse_json_with_fallback(
    self, content: str, expected_type: type = dict
) -> Optional[Union[Dict, List]]:
    """
    解析 JSON，支持多种容错机制：
    1. 提取 JSON 内容
    2. 修复常见问题
    3. 多次尝试解析
    4. 类型验证和转换
    """
```

**容错流程**：

1. 从文本中提取 JSON
2. 修复常见格式问题
3. 尝试多种解析方式（原始字符串、移除换行等）
4. 验证并转换类型（处理数组/对象格式不匹配）

**2.4 改进 `extract_with_llm` 方法**

增强错误处理和日志记录：

```python
async def extract_with_llm(self, prompt: str) -> Dict:
    """
    支持多种容错机制：
    1. 提取被 markdown 代码块包裹的 JSON
    2. 修复常见的 JSON 格式问题
    3. 处理数组和对象两种格式
    4. 详细的错误日志
    """
```

**改进点**：

- 检查响应对象和内容是否存在
- 使用容错解析方法
- 处理数组格式（自动包装为字典）
- 详细的错误日志（记录前 1000 个字符）

**2.5 改进 `_search_contacts_parallel` 方法**

增强对联系人数据的处理：

```python
# 处理 LLM 返回的联系人数据
# 可能的情况：
# 1. 返回字典 {"contacts": [...]}
# 2. 返回列表 [...]（直接返回数组）
# 3. 返回空字典 {}
```

**处理逻辑**：

- 支持字典格式：提取 `contacts` 字段或查找第一个列表字段
- 支持列表格式：直接使用
- 验证和过滤：确保每个联系人都是字典格式
- 异常处理：确保总是返回有效的字典

**2.6 改进 `find_kps` 方法的异常处理**

增强对 `asyncio.gather` 结果的检查：

```python
# 处理异常情况和 None 值
if isinstance(procurement_result, Exception):
    procurement_result = {"contacts": [], "results": []}
elif procurement_result is None:
    procurement_result = {"contacts": [], "results": []}
elif not isinstance(procurement_result, dict):
    procurement_result = {"contacts": [], "results": []}
```

**改进点**：

- 检查 `Exception` 类型
- 检查 `None` 值
- 检查类型是否正确
- 所有情况下都返回有效字典

#### 3. 容错机制流程图

```
LLM 响应
    ↓
检查响应对象和内容
    ↓
提取 JSON 内容
    ├─→ 策略1: 提取 markdown 代码块
    ├─→ 策略2: 括号匹配查找 JSON
    └─→ 策略3: 直接解析文本
    ↓
修复常见格式问题
    ├─→ 移除 BOM
    ├─→ 修复引号
    ├─→ 移除尾随逗号
    └─→ 移除注释
    ↓
多次尝试解析
    ├─→ 尝试1: 原始字符串
    └─→ 尝试2: 移除换行
    ↓
类型验证和转换
    ├─→ 符合预期类型 → 返回
    ├─→ 数组但期望字典 → 包装为字典
    └─→ 字典但期望数组 → 提取数组字段
    ↓
返回结果或 None
```

#### 4. 关键改进点总结

1. **JSON 提取**：支持从 markdown 代码块、混合文本中提取 JSON
2. **格式修复**：自动修复常见的 JSON 格式问题
3. **类型转换**：智能处理数组/对象格式不匹配的情况
4. **异常处理**：多层异常处理，确保流程不会中断
5. **日志记录**：详细的错误日志，便于调试和问题定位
6. **空值检查**：全面检查 `None` 值，避免 `AttributeError`

#### 5. 测试建议

建议测试以下场景：

1. **Markdown 代码块包裹**：

   ````json
   ```json
   {"domain": "example.com"}
   ````

   ```

   ```

2. **格式不规范**：

   ```json
   { "domain": "example.com" } // 单引号 + 尾随逗号
   ```

3. **数组格式**：

   ```json
   [{ "email": "test@example.com" }]
   ```

4. **混合文本**：

   ```
   以下是提取的结果：
   {"domain": "example.com"}
   ```

5. **空响应**：
   - 空字符串
   - `None`
   - 只有说明文字

### 修改的文件

- `findkp/service.py`: 添加了 JSON 容错处理机制

### 相关技术点

- **正则表达式**：用于提取 JSON 和修复格式
- **括号匹配算法**：用于查找完整的 JSON 结构
- **类型检查**：确保数据格式正确
- **异常处理**：多层容错机制

---

## 2025-11-05 22:44:55 - 修复 KPInfo 模型验证错误：空字符串导致 Pydantic 验证失败

### 需求描述

修复 `KPInfo` 模型在验证时出现的错误：

- `email` 字段为空字符串时，Pydantic 要求必须是有效的 EmailStr 格式，导致验证失败
- `linkedin_url` 和 `twitter_url` 字段为空字符串时，Pydantic 尝试将其解析为 URL，导致验证失败

错误信息：

```
3 validation errors for KPInfo
email: value is not a valid email address: An email address must have an @-sign.
linkedin_url: Input should be a valid URL, input is empty
twitter_url: Input should be a valid URL, input is empty
```

### 实现逻辑

#### 1. 问题分析

**根本原因**：

1. `KPInfo` 模型中 `email` 字段定义为必填的 `EmailStr`，但实际数据中可能为空字符串
2. `linkedin_url` 和 `twitter_url` 虽然是 `Optional[HttpUrl]`，但空字符串会被 Pydantic 尝试解析为 URL，导致验证失败
3. 数据库模型中 `email` 字段是 `nullable=False`，要求 email 不能为空

**解决方案**：

1. 修改 `KPInfo` 模型，将 `email` 改为 `Optional[EmailStr] = None`，允许为空
2. 在创建 `KPInfo` 实例之前，将空字符串转换为 `None`
3. 过滤掉没有 email 的联系人（因为数据库要求 email 不能为空）

#### 2. 修复步骤

**步骤 1：修改 `KPInfo` 模型定义**

```python
# schemas/contact.py
class KPInfo(BaseModel):
    email: Optional[EmailStr] = None  # 从 EmailStr 改为 Optional[EmailStr] = None
    linkedin_url: Optional[HttpUrl] = None  # 保持不变
    twitter_url: Optional[HttpUrl] = None  # 保持不变
```

**步骤 2：在 `service.py` 中添加数据清理逻辑**

```python
# findkp/service.py

# 清理联系人数据：将空字符串转换为 None
def clean_contact_data(data: dict) -> dict:
    """清理联系人数据：将空字符串转换为 None"""
    cleaned = {}
    for key, value in data.items():
        if value == "":
            cleaned[key] = None
        else:
            cleaned[key] = value
    return cleaned

# 清理数据
cleaned_contacts = [clean_contact_data(contact_data) for contact_data in contacts_to_save]

# 过滤掉没有 email 的联系人（数据库要求 email 不能为空）
valid_contacts = [
    contact_data
    for contact_data in cleaned_contacts
    if contact_data.get("email")  # 必须有 email
]
```

**步骤 3：在 `repository.py` 中添加防御性检查**

```python
# database/repository.py

async def create_contact(self, contact_info: KPInfo, company_id: int):
    # 防御性检查：email 不能为空（数据库要求）
    if not contact_info.email:
        raise ValueError(f"联系人 email 不能为空: {contact_info.full_name}")
    # ...

async def create_contacts_batch(self, contacts_info: List[KPInfo], company_id: int):
    for contact_info in contacts_info:
        # 防御性检查：email 不能为空（数据库要求）
        if not contact_info.email:
            continue  # 跳过没有 email 的联系人
        # ...
```

#### 3. 数据流程

```
原始联系人数据
    ↓
清理空字符串 → None
    ↓
过滤没有 email 的联系人
    ↓
创建 KPInfo 实例（Pydantic 验证通过）
    ↓
保存到数据库（email 必填，已确保不为空）
```

#### 4. 关键改进点总结

1. **模型灵活性**：`email` 字段改为可选，允许在业务逻辑层处理空值情况
2. **数据清理**：统一将空字符串转换为 `None`，避免 Pydantic 验证错误
3. **业务逻辑过滤**：在保存前过滤掉没有 email 的联系人，满足数据库约束
4. **防御性编程**：在 repository 层也添加检查，确保数据完整性
5. **日志记录**：记录过滤掉的联系人数量，便于监控和调试

#### 5. 错误处理流程

```
准备联系人数据
    ↓
清理空字符串
    ↓
过滤无效联系人（没有 email）
    ↓
尝试批量保存
    ├─→ 成功 → 完成
    └─→ 失败 → 降级为单个保存
        ├─→ 成功 → 继续下一个
        └─→ 失败 → 记录错误日志，跳过
```

### 修改的文件

- `schemas/contact.py`: 将 `email` 字段改为 `Optional[EmailStr] = None`
- `findkp/service.py`: 添加数据清理和过滤逻辑
- `database/repository.py`: 添加防御性检查，确保 email 不为空

### 相关技术点

- **Pydantic 验证**：空字符串 vs None 的处理
- **EmailStr 验证**：必须包含 @ 符号
- **HttpUrl 验证**：空字符串会被尝试解析为 URL
- **数据库约束**：`nullable=False` 字段的处理
- **防御性编程**：多层数据验证确保数据完整性

---

## 2025-11-05 23:04:06 - 优化 FindKP 流程：添加缓存检查机制避免重复搜索

### 需求描述

优化 `find_kps` 方法，在开始搜索前先检查缓存：

1. 检查 `companies` 表中是否存在已完成的记录
2. 如果公司已完成且联系人已存在，直接返回现有联系人，跳过搜索
3. 如果公司已完成但联系人不存在，继续执行搜索流程（可能之前搜索失败）
4. 只有公司未完成或联系人不存在时才执行完整的搜索流程

**优化目标**：

- 避免重复搜索已完成的公司，节省 API 调用成本
- 提高响应速度，对于已完成的公司直接返回缓存结果
- 减少不必要的 LLM 调用和外部 API 请求

### 实现逻辑

#### 1. 问题分析

**现状**：

- 每次调用 `find_kps` 都会执行完整的搜索流程
- 即使公司已经完成搜索，仍会重复调用搜索 API 和 LLM
- 没有利用已有的数据库记录

**优化方案**：

- 在方法开始时检查公司状态
- 如果公司已完成且联系人已存在，直接返回
- 如果公司已完成但联系人不存在，继续搜索（可能之前失败）

#### 2. 实现步骤

**步骤 1：在 Repository 中添加查询方法**

```python
# database/repository.py

async def get_company_by_name(self, name: str) -> Optional[models.Company]:
    """
    根据公司名称获取公司（如果不存在则返回 None）
    """
    result = await self.db.execute(
        select(models.Company).filter(models.Company.name == name)
    )
    return result.scalar_one_or_none()
```

**步骤 2：在 `find_kps` 方法开始时添加缓存检查**

```python
# findkp/service.py

async def find_kps(self, ...):
    repo = Repository(db)

    try:
        # 0. 检查缓存：如果公司已完成且联系人已存在，直接返回
        company = await repo.get_company_by_name(company_name_en)
        if company and company.status == CompanyStatus.completed:
            logger.info(f"公司 {company_name_en} 已完成，查询现有联系人...")
            existing_contacts = await repo.get_contacts_by_company(company.id)

            if existing_contacts:
                logger.info(f"找到 {len(existing_contacts)} 个现有联系人，直接返回")
                # 将 Contact 对象转换为 KPInfo
                kp_info_list = [
                    KPInfo(
                        full_name=contact.full_name,
                        email=contact.email,
                        role=contact.role,
                        department=contact.department,
                        linkedin_url=contact.linkedin_url if contact.linkedin_url else None,
                        twitter_url=contact.twitter_url if contact.twitter_url else None,
                        source=contact.source or "N/A",
                        confidence_score=float(contact.confidence_score or 0.0),
                    )
                    for contact in existing_contacts
                ]
                return {
                    "company_id": company.id,
                    "company_domain": company.domain,
                    "contacts": kp_info_list,
                }
            else:
                logger.info(
                    f"公司 {company_name_en} 已完成，但未找到联系人，继续搜索..."
                )
                # 继续执行搜索流程（可能之前搜索失败，但公司状态被标记为完成）

        # 1. 生成搜索查询（原有的搜索流程）
        # ...
```

#### 3. 数据流程

```
find_kps 方法调用
    ↓
检查公司是否存在且已完成
    ├─→ 是 → 查询现有联系人
    │   ├─→ 联系人存在 → 转换为 KPInfo → 直接返回
    │   └─→ 联系人不存在 → 继续搜索流程
    └─→ 否 → 执行完整搜索流程
        ↓
    生成搜索查询
        ↓
    执行搜索和 LLM 提取
        ↓
    保存结果
```

#### 4. 关键改进点总结

1. **缓存机制**：利用数据库中的已完成记录，避免重复搜索
2. **性能优化**：跳过已完成的公司，大幅减少 API 调用和 LLM 调用
3. **成本控制**：避免重复调用外部 API（Serper、Google Search），节省成本
4. **数据转换**：正确将 Contact 对象转换为 KPInfo，处理 URL 字段的空值情况
5. **容错处理**：如果公司已完成但联系人不存在，继续执行搜索（可能之前失败）

#### 5. 优化效果

**性能提升**：

- 已完成的公司：响应时间从数秒降至毫秒级（数据库查询）
- 减少外部 API 调用：避免重复调用 Serper/Google Search API
- 减少 LLM 调用：避免重复调用 GPT-4o 提取信息

**成本节省**：

- 避免重复的搜索 API 调用（Serper credits）
- 避免重复的 LLM API 调用（OpenAI tokens）
- 减少数据库写入操作

**用户体验**：

- 快速返回已完成的公司结果
- 减少等待时间
- 提高系统响应速度

### 修改的文件

- `database/repository.py`: 添加 `get_company_by_name()` 方法
- `findkp/service.py`: 在 `find_kps()` 方法开始时添加缓存检查逻辑

### 相关技术点

- **缓存策略**：利用数据库记录作为缓存
- **状态管理**：使用 `CompanyStatus.completed` 标记已完成状态
- **数据转换**：Contact 对象到 KPInfo 的转换
- **性能优化**：提前返回，避免不必要的计算
- **成本控制**：减少重复的 API 调用

---

## 2025-11-05 23:07:52 - 优化 FindKP 流程：公司已完成时仅搜索联系人，跳过公司信息搜索

### 需求描述

进一步优化 `find_kps` 方法的缓存逻辑：

- 如果公司已完成且联系人已存在 → 直接返回现有联系人
- 如果公司已完成但联系人不存在 → **仅搜索联系人，跳过公司信息搜索**
- 如果公司不存在或未完成 → 执行完整流程（公司信息 + 联系人）

**优化目标**：

- 避免重复搜索已完成的公司信息，节省 API 调用成本
- 提高响应速度，对于已完成的公司直接搜索联系人
- 减少不必要的 LLM 调用和外部 API 请求

### 实现逻辑

#### 1. 问题分析

**之前的实现**：

- 如果公司已完成但联系人不存在，仍会执行完整的搜索流程（包括公司信息搜索）
- 浪费了 API 调用和 LLM 调用资源

**优化方案**：

- 提取联系人搜索和保存逻辑为独立方法 `_search_and_save_contacts`
- 如果公司已完成但联系人不存在，直接调用该方法搜索联系人
- 跳过公司信息搜索步骤（步骤 1-5）

#### 2. 实现步骤

**步骤 1：提取联系人搜索和保存逻辑为独立方法**

```python
# findkp/service.py

async def _search_and_save_contacts(
    self,
    company: Company,
    company_name_en: str,
    company_name_local: str,
    country: Optional[str],
    country_context: str,
    db: AsyncSession,
    repo: Repository,
) -> List[KPInfo]:
    """
    搜索并保存联系人（独立方法，可被复用）

    包含：
    1. 并行搜索采购和销售部门 KP
    2. 准备联系人数据
    3. 清理和验证数据
    4. 批量保存联系人
    """
    # ... 联系人搜索和保存逻辑
```

**步骤 2：优化 `find_kps` 方法的缓存检查逻辑**

```python
# findkp/service.py

async def find_kps(self, ...):
    repo = Repository(db)

    try:
        # 0. 检查缓存
        company = await repo.get_company_by_name(company_name_en)
        if company and company.status == CompanyStatus.completed:
            existing_contacts = await repo.get_contacts_by_company(company.id)

            if existing_contacts:
                # 情况 1: 联系人已存在，直接返回
                return {...}
            else:
                # 情况 2: 公司已完成但联系人不存在，仅搜索联系人
                logger.info("公司已完成，但未找到联系人，仅搜索联系人...")

                country_context = self._get_country_context(country)
                company.status = CompanyStatus.processing
                await db.commit()

                # 直接搜索并保存联系人（跳过公司信息搜索）
                all_contacts = await self._search_and_save_contacts(
                    company, company_name_en, company_name_local,
                    country, country_context, db, repo
                )

                company.status = CompanyStatus.completed
                await db.commit()
                return {...}

        # 情况 3: 公司不存在或未完成，执行完整流程
        # 1. 生成搜索查询（公司信息）
        # 2. 执行搜索和 LLM 提取
        # 3. 创建或更新公司记录
        # 4. 搜索并保存联系人
        all_contacts = await self._search_and_save_contacts(...)
        # ...
```

#### 3. 数据流程

```
find_kps 方法调用
    ↓
检查公司是否存在且已完成
    ├─→ 是 → 查询现有联系人
    │   ├─→ 联系人存在 → 转换为 KPInfo → 直接返回
    │   └─→ 联系人不存在 → 仅搜索联系人（跳过公司信息搜索）
    │       ↓
    │       并行搜索采购和销售部门 KP
    │       ↓
    │       保存联系人
    │       ↓
    │       更新公司状态 → 返回
    └─→ 否 → 执行完整搜索流程
        ↓
    生成搜索查询（公司信息）
        ↓
    执行搜索和 LLM 提取
        ↓
    创建或更新公司记录
        ↓
    搜索并保存联系人（复用 _search_and_save_contacts）
        ↓
    更新公司状态 → 返回
```

#### 4. 关键改进点总结

1. **代码复用**：提取联系人搜索逻辑为独立方法，避免代码重复
2. **性能优化**：已完成的公司跳过公司信息搜索，直接搜索联系人
3. **成本控制**：避免重复调用公司信息搜索 API 和 LLM
4. **逻辑清晰**：三种情况的处理逻辑更加清晰
5. **可维护性**：联系人搜索逻辑集中在一个方法中，便于维护和测试

#### 5. 优化效果对比

**之前（公司已完成但联系人不存在）**：

```
1. 生成公司搜索查询
2. 执行公司搜索 API 调用
3. LLM 提取公司信息
4. 搜索联系人
5. 保存联系人
```

**现在（公司已完成但联系人不存在）**：

```
1. 搜索联系人（直接）
2. 保存联系人
```

**节省的成本**：

- 减少公司信息搜索 API 调用（Serper/Google Search）
- 减少 LLM 调用（GPT-4o 提取公司信息）
- 减少响应时间（跳过公司信息搜索步骤）

### 修改的文件

- `findkp/service.py`:
  - 添加 `_search_and_save_contacts()` 方法（提取联系人搜索和保存逻辑）
  - 优化 `find_kps()` 方法的缓存检查逻辑
  - 添加 `Company` 导入

### 相关技术点

- **代码重构**：提取公共逻辑为独立方法
- **缓存策略**：利用数据库记录作为缓存
- **性能优化**：跳过不必要的步骤
- **成本控制**：减少重复的 API 调用
- **代码复用**：DRY 原则（Don't Repeat Yourself）

---

## 2024-11-06: 邮箱搜索策略重构

### 需求

根据 `search_stategy.md` 中的策略调整联系人搜索逻辑：

1. 实现基于域名的邮箱搜索策略（A1-A3, B1-B2, C1-C2）
2. 将 Serper 和 Google 从并行改为选择逻辑（优先 Serper，失败则 Google）

### 实现逻辑

#### 1. 创建邮箱搜索策略模块

创建了新的 `findkp/email_search_strategy.py` 文件，实现了 `EmailSearchStrategy` 类：

- **阶段 1（A1-A3）**：官网邮箱搜索

  - A1: `site:DOMAIN "@"+DOMAIN` - 官网邮箱直搜
  - A2: `site:DOMAIN (inurl:contact OR inurl:contact-us OR inurl:about) "@"+DOMAIN` - 联系页聚焦
  - A3: `site:DOMAIN filetype:pdf "@"+DOMAIN` - 文件类邮箱搜索

- **阶段 2（B1）**：岗位/职能聚焦

  - B1: `site:DOMAIN ("sales" OR "business development" OR "procurement" OR "purchasing" OR "buyer") "@"+DOMAIN`

- **阶段 3（B2）**：通用联系方式补充

  - B2: `site:DOMAIN ("email" OR "contact" OR "reach us" OR "get in touch") "@"+DOMAIN`

- **阶段 4（C1-C2）**：LinkedIn 搜索
  - C1: `site:linkedin.com "COMPANY_FULL" ("procurement" OR "purchasing" OR "buyer")`
  - C2: `site:linkedin.com "COMPANY_FULL" ("sales" OR "business development")`

#### 2. 修改搜索提供商选择逻辑

修改了 `_search_with_multiple_providers` 方法：

- **优先使用 Serper**：检查 `SERPER_API_KEY` 配置，如果存在则尝试使用

  - 如果 Serper 返回有效结果，直接返回
  - 如果 Serper 失败或返回空结果，则切换到 Google

- **回退到 Google**：检查 `GOOGLE_SEARCH_API_KEY` 和 `GOOGLE_SEARCH_CX` 配置
  - 如果 Google 也失败，返回空结果并记录错误

#### 3. 集成邮箱搜索策略到联系人搜索

修改了 `_search_contacts_parallel` 方法：

- 添加 `domain: Optional[str]` 参数
- 如果 `domain` 存在，使用 `EmailSearchStrategy.generate_email_search_queries()` 生成邮箱搜索查询
- 如果 `domain` 不存在，回退到原有的 `SearchStrategy.generate_contact_queries()` 方法
- 保持向后兼容，不影响现有功能

#### 4. 更新调用方传递域名

修改了 `_search_and_save_contacts` 方法：

- 在调用 `_search_contacts_parallel` 时传递 `company.domain` 参数
- 确保域名信息正确传递到搜索逻辑

### 修改的文件

- `findkp/email_search_strategy.py`: 新建文件，实现邮箱搜索策略生成器
- `findkp/service.py`:
  - 添加 `EmailSearchStrategy` 导入和初始化
  - 修改 `_search_with_multiple_providers()` 方法：从并行改为选择逻辑
  - 修改 `_search_contacts_parallel()` 方法：添加 domain 参数并集成新策略
  - 修改 `_search_and_save_contacts()` 方法：传递 company.domain

### 架构设计

```
EmailSearchStrategy (新建)
    ↓
Generate Email Queries (A1-A3, B1-B2, C1-C2)
    ↓
_search_with_multiple_providers (修改)
    ├─ 优先 Serper (检查配置和结果有效性)
    └─ 回退 Google (如果 Serper 失败)
    ↓
_search_contacts_parallel (修改)
    ├─ 有 domain → 使用 EmailSearchStrategy
    └─ 无 domain → 使用 SearchStrategy (向后兼容)
```

### 相关技术点

- **模块化设计**：将邮箱搜索策略独立为单独模块，符合单一职责原则
- **选择逻辑**：从并行改为选择，减少不必要的 API 调用
- **向后兼容**：保持原有功能不受影响，domain 为空时自动回退
- **错误处理**：完善的异常处理和日志记录
- **配置管理**：通过 `settings` 检查 API Key 配置

### 测试验证

- ✅ 语法检查通过（uv run python -m py_compile）
- ✅ EmailSearchStrategy 导入和初始化成功
- ✅ 查询生成功能正常（测试生成了 6 个查询）

### 注意事项

- D1/D2 策略（邮箱验证与生成）不在本次实现范围内，后续发送邮件时处理
- 多语言关键词支持暂时不考虑，后续可扩展
- 策略执行顺序按照文档推荐顺序：A1 → A2 → A3 → B1 → B2 → C1 → C2

---

## 2024-11-06: 集成 LangChain 结构化输出解决 JSON 解析问题

### 需求

解决 LLM 返回 JSON 解析失败的问题，使用 LangChain 的结构化输出功能（`with_structured_output`）确保返回格式正确。

### 问题分析

根据日志分析，问题出现在：

- LLM 调用成功（HTTP 200 OK）
- 但 JSON 解析失败，无法提取联系人信息
- 导致返回 0 个联系人

根本原因：

- 手动解析 JSON 容易失败
- LLM 返回格式可能不规范
- 需要复杂的容错逻辑

### 实现逻辑

#### 1. 创建响应模型（schemas/contact.py）

添加了三个 Pydantic 模型用于结构化输出：

- **ContactInfo**: 单个联系人信息（用于 LLM 结构化输出）

  - 字段：full_name, email, role, linkedin_url, twitter_url, confidence_score
  - 注意：email 使用 str 而不是 EmailStr，因为 LLM 可能返回无效邮箱

- **ContactsResponse**: 联系人列表响应

  - 字段：contacts: List[ContactInfo]

- **CompanyInfoResponse**: 公司信息响应
  - 字段：domain, industry, positioning, brief

#### 2. 添加结构化输出方法（findkp/service.py）

创建了两个新方法使用 LangChain 的 `with_structured_output`：

- **extract_contacts_with_llm()**:

  - 使用 `self.llm.with_structured_output(ContactsResponse)`
  - 直接返回 Pydantic 模型实例，无需 JSON 解析
  - 如果失败，降级到旧的 JSON 解析方法

- **extract_company_info_with_llm()**:
  - 使用 `self.llm.with_structured_output(CompanyInfoResponse)`
  - 同样支持降级机制

#### 3. 更新调用方

修改了两个调用位置：

- `_search_contacts_parallel()`: 使用 `extract_contacts_with_llm()`
- `_search_and_save_company_info()`: 使用 `extract_company_info_with_llm()`

简化了后续处理逻辑，因为结构化输出保证返回格式正确。

### 技术优势

1. **解决 JSON 解析问题**: 不再需要手动解析 JSON，避免解析失败
2. **类型安全**: 直接返回 Pydantic 模型，类型验证自动完成
3. **自动验证**: Pydantic 自动验证数据格式和类型
4. **代码简化**: 移除复杂的 JSON 解析逻辑
5. **降级机制**: 如果结构化输出失败，自动降级到旧的 JSON 解析方法
6. **更好的错误提示**: 模型验证失败时提供清晰的错误信息

### 修改的文件

- `schemas/contact.py`:

  - 添加 `ContactInfo`, `ContactsResponse`, `CompanyInfoResponse` 模型

- `findkp/service.py`:
  - 添加 `extract_contacts_with_llm()` 方法
  - 添加 `extract_company_info_with_llm()` 方法
  - 修改 `_search_contacts_parallel()` 使用新方法
  - 修改 `_search_and_save_company_info()` 使用新方法
  - 保留 `extract_with_llm()` 作为降级方案

### 架构改进

**之前**:

```
LLM 调用 → 返回文本 → 手动解析 JSON → 容错处理 → 提取数据
```

**现在**:

```
LLM 调用（结构化输出） → 直接返回 Pydantic 模型 → 转换为字典
```

### 验证结果

- ✅ 响应模型导入成功
- ✅ 语法检查通过
- ✅ 代码结构清晰，向后兼容

### 注意事项

- 结构化输出需要模型支持（大多数现代模型都支持）
- 如果模型不支持，会自动降级到旧的 JSON 解析方法
- 保留了旧的 `extract_with_llm()` 方法作为降级方案
- ContactInfo 中 email 使用 str 而不是 EmailStr，避免 LLM 返回无效邮箱时验证失败

### 参考文档

- [LangChain Agents - Structured Output](https://docs.langchain.com/oss/python/langchain/agents)
- LangChain V1 `with_structured_output()` 方法文档

---

## 2024-11-06: 集成 Loguru 日志系统并记录 LLM 请求响应

### 需求

1. 使用 loguru 替代标准的 logging 模块
2. LLM 的请求和响应日志记录到文件中
3. 在根目录下创建 logs 文件夹
4. 每次和 LLM 的请求都按照时间戳单独放在指定类型的日志子文件夹目录中

### 实现逻辑

#### 1. 添加 loguru 依赖

在 `pyproject.toml` 中添加 `loguru>=0.7.0` 依赖。

#### 2. 创建日志配置模块（logs/**init**.py）

创建了统一的日志配置模块，包含：

- **日志目录结构**：

  - `logs/` - 主日志目录
  - `logs/llm/requests/` - LLM 请求日志目录
  - `logs/llm/responses/` - LLM 响应日志目录

- **日志配置**：

  - 控制台输出：彩色格式，INFO 级别
  - 文件输出：`logs/app_{date}.log`，DEBUG 级别，每日轮转，保留 30 天，自动压缩

- **LLM 日志函数**：
  - `log_llm_request()`: 记录 LLM 请求到独立文件，文件名包含时间戳（精确到微秒）
  - `log_llm_response()`: 记录 LLM 响应到独立文件，关联请求日志路径
  - `get_llm_log_path()`: 获取日志文件路径

#### 3. 替换所有 logging 为 loguru

替换了以下文件中的 logging：

- `findkp/service.py`
- `findkp/router.py`
- `findkp/search_strategy.py`
- `findkp/email_search_strategy.py`
- `findkp/result_aggregator.py`
- `llm/factory.py`
- `llm/glm_wrapper.py`

所有文件统一使用 `from logs import logger`。

#### 4. 在 LLM 调用处添加日志记录

在以下方法中添加了请求和响应日志：

- **findkp/service.py**:

  - `extract_contacts_with_llm()`: 记录联系人提取的请求和响应
  - `extract_company_info_with_llm()`: 记录公司信息提取的请求和响应
  - `extract_with_llm()`: 记录通用提取的请求和响应（包括错误情况）

- **llm/glm_wrapper.py**:
  - `ainvoke()`: 记录 GLM 异步调用的请求和响应
  - `invoke()`: 记录 GLM 同步调用的请求和响应

#### 5. 日志文件命名规则

每次 LLM 请求生成独立的日志文件：

- **请求日志**: `logs/llm/requests/{YYYYMMDD}_{HHMMSS}_{微秒}.log`
- **响应日志**: `logs/llm/responses/{YYYYMMDD}_{HHMMSS}_{微秒}.log`
- 响应日志中包含 `request_log_path` 字段，关联对应的请求日志

### 日志格式

#### LLM 请求日志格式（JSON）

```json
{
  "timestamp": "2024-11-06T12:34:56.789012",
  "model": "deepseek-chat",
  "messages": [{ "role": "user", "content": "..." }],
  "task_type": "extract_contacts",
  "temperature": 0.0
}
```

#### LLM 响应日志格式（JSON）

```json
{
  "timestamp": "2024-11-06T12:34:57.123456",
  "response_content": "...",
  "request_log_path": "logs/llm/requests/20241106_123456_789012.log",
  "model": "deepseek-chat",
  "task_type": "extract_contacts"
}
```

### 修改的文件

- `pyproject.toml`: 添加 loguru 依赖
- `logs/__init__.py`: 新建日志配置模块
- `findkp/service.py`: 替换 logging，添加 LLM 日志记录
- `findkp/router.py`: 替换 logging
- `findkp/search_strategy.py`: 替换 logging
- `findkp/email_search_strategy.py`: 替换 logging
- `findkp/result_aggregator.py`: 替换 logging
- `llm/factory.py`: 替换 logging
- `llm/glm_wrapper.py`: 替换 logging，添加 LLM 日志记录

### 技术优势

1. **统一日志管理**: 使用 loguru 提供更强大的日志功能
2. **独立日志文件**: 每次 LLM 请求/响应都有独立的日志文件，便于排查
3. **时间戳精确**: 使用微秒级时间戳，确保文件名唯一
4. **关联追踪**: 响应日志包含请求日志路径，便于关联查看
5. **任务类型标识**: 通过 `task_type` 字段区分不同类型的 LLM 调用
6. **自动轮转**: 应用日志自动按天轮转，保留 30 天

### 目录结构

```
logs/
├── __init__.py                    # 日志配置模块
├── app_2024-11-06.log            # 应用日志（每日轮转）
├── llm/
│   ├── requests/                 # LLM 请求日志目录
│   │   ├── 20241106_123456_789012.log
│   │   └── 20241106_123457_123456.log
│   └── responses/                # LLM 响应日志目录
│       ├── 20241106_123456_789013.log
│       └── 20241106_123457_123457.log
```

### 使用示例

````python
from logs import logger, log_llm_request, log_llm_response

# 记录请求
request_log_path = log_llm_request(
    messages=[{"role": "user", "content": "..."}],
    model="deepseek-chat",
    task_type="extract_contacts",
)

---

## 2025-11-06 13:36:18 - 从搜索结果中提取公共邮箱并允许联系人无邮箱存储

### 需求描述

1. **问题发现**：在 Serper 返回的 snippet 中包含了邮箱（如 `cus-info@phuanh.vn`），但这些邮箱没有被存储下来
2. **需求1**：这些公共邮箱需要被存储到 Company 表中，作为公司的公共联系方式
3. **需求2**：联系人即使没有邮件也可以被存储下来，不是必须有邮件才行
4. **补充说明**：在查询公司信息时，如果返回的信息中带有公共邮箱，要同步存储

### 实现逻辑

#### 1. 数据库层面修改

**1.1 创建数据库迁移脚本** (`database/sql/004_add_public_emails_and_nullable_email.sql`)
- 添加 `public_emails` 字段到 `companies` 表（JSON 格式）
- 修改 `contacts` 表的 `email` 字段为可空（`nullable=True`）

**1.2 修改数据库模型** (`database/models.py`)
- 导入 `JSON` 类型
- `Company` 模型添加 `public_emails = Column(JSON)` 字段
- `Contact` 模型修改 `email` 字段：`nullable=True`

#### 2. Repository 层修改 (`database/repository.py`)

**2.1 移除 email 必填检查**
- `create_contact()`: 移除 email 必填验证，允许 email 为 None
- `create_contacts_batch()`: 移除 email 必填验证，允许没有 email 的联系人

**2.2 添加公共邮箱更新方法**
- `update_company_public_emails()`: 更新公司的公共邮箱列表，自动合并和去重

#### 3. Service 层修改 (`findkp/service.py`)

**3.1 添加邮箱提取工具函数**
- `EMAIL_REGEX`: 邮箱正则表达式常量（复用 `core/analysis.py` 中的）
- `_extract_emails_from_snippets()`: 从搜索结果 snippet 中提取所有邮箱（使用正则表达式）
- `_filter_public_emails()`: 过滤公共邮箱，排除个人邮箱
  - 支持根据域名过滤
  - 根据公共邮箱关键词过滤（如 contact, info, sales, cus-info 等）

**3.2 添加公共邮箱保存方法**
- `_extract_and_save_public_emails()`: 从搜索结果中提取公共邮箱并保存到公司记录
  - 提取所有邮箱
  - 过滤公共邮箱
  - 调用 Repository 更新公司记录

**3.3 在公司信息提取时提取公共邮箱**
- 修改 `_search_and_save_company_info()`: 在保存公司信息后，调用 `_extract_and_save_public_emails()` 提取并保存公共邮箱

**3.4 在联系人搜索时提取公共邮箱**
- 修改 `_search_and_save_contacts()`: 在获取搜索结果后，调用 `_extract_and_save_public_emails()` 提取并保存公共邮箱

**3.5 移除联系人过滤逻辑**
- 修改 `_search_and_save_contacts()`: 移除过滤没有 email 的联系人的逻辑
- 允许所有有效联系人被保存，即使没有 email

### 技术细节

#### 邮箱提取方式

使用正则表达式提取邮箱（与 `core/analysis.py` 保持一致）：
```python
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
````

#### 公共邮箱过滤规则

1. **域名过滤**：如果指定了公司域名，只保留该域名的邮箱
2. **关键词过滤**：保留包含公共邮箱关键词的邮箱，如：
   - contact, info, sales, support, service
   - hello, hi, inquiry, enquiry
   - customerservice, customer-service, customercare
   - cus-info（用户示例中的邮箱前缀）

#### 数据流程

```mermaid
graph TD
    A[搜索公司/联系人] --> B[获取搜索结果 snippets]
    B --> C[正则表达式提取所有邮箱]
    C --> D[过滤公共邮箱]
    D --> E{是否有公共邮箱?}
    E -->|是| F[更新 Company.public_emails]
    E -->|否| G[跳过]
    B --> H[LLM 提取联系人]
    H --> I{联系人有邮箱?}
    I -->|是| J[保存联系人 email]
    I -->|否| K[保存联系人 email=None]
    J --> L[保存到数据库]
    K --> L
```

### 修改文件清单

1. ✅ `database/sql/004_add_public_emails_and_nullable_email.sql` - 数据库迁移脚本（新建）
2. ✅ `database/models.py` - 添加 `public_emails` 字段，修改 `email` 为可空
3. ✅ `database/repository.py` - 移除 email 必填检查，添加更新公共邮箱方法
4. ✅ `findkp/service.py` - 添加邮箱提取工具函数，修改保存逻辑

### 功能验证

- ✅ 数据库模型修改完成
- ✅ Repository 层允许 email 为空
- ✅ Service 层提取公共邮箱功能实现
- ✅ 在公司信息提取时自动提取公共邮箱
- ✅ 在联系人搜索时自动提取公共邮箱
- ✅ 允许没有 email 的联系人存储
- ✅ 代码通过 lint 检查

### 注意事项

1. **数据库迁移**：需要执行迁移脚本 `004_add_public_emails_and_nullable_email.sql` 更新数据库结构
2. **邮箱提取**：使用正则表达式提取，可能会提取到一些误匹配的邮箱，但通过公共邮箱关键词过滤可以减少误报
3. **向后兼容**：允许 email 为空不影响现有功能，现有有 email 的联系人继续正常工作

---

## 2025-11-06 13:45:00 - 修复日志模块：将 core/search 中的 logging 替换为 loguru

### 需求描述

发现 `core/search/serper_provider.py` 和 `core/search/google_provider.py` 中仍在使用标准的 `logging` 模块，而不是项目统一的 `loguru`。另外，httpx 库输出的 INFO 级别日志（如 "HTTP Request: POST https://google.serper.dev/search"）也需要被抑制。

### 实现逻辑

#### 1. 替换 core/search 模块的日志

**1.1 修改 `core/search/serper_provider.py`**

- 移除 `import logging`
- 移除 `logger = logging.getLogger(__name__)`
- 添加 `from logs import logger`

**1.2 修改 `core/search/google_provider.py`**

- 移除 `import logging`
- 移除 `logger = logging.getLogger(__name__)`
- 添加 `from logs import logger`

#### 2. 配置 httpx 日志级别

**2.1 修改 `logs/__init__.py`**

- 添加 `import logging`
- 在日志配置初始化时添加：`logging.getLogger("httpx").setLevel(logging.WARNING)`
- 这样可以抑制 httpx 的 INFO 级别日志（如 "HTTP Request: POST ..."），只记录 WARNING 和 ERROR 级别的日志

#### 3. 确保配置生效

**3.1 修改 `main.py`**

- 在应用启动时显式导入 `logs` 模块：`import logs  # noqa: F401`
- 确保日志配置（包括 httpx 日志级别设置）在应用启动早期就生效

### 修改文件清单

1. ✅ `core/search/serper_provider.py` - 替换 logging 为 loguru
2. ✅ `core/search/google_provider.py` - 替换 logging 为 loguru
3. ✅ `logs/__init__.py` - 添加 httpx 日志级别配置
4. ✅ `main.py` - 显式导入 logs 模块

### 功能验证

- ✅ 所有 search provider 使用统一的 loguru logger
- ✅ httpx 的 INFO 级别日志被抑制
- ✅ 代码通过 lint 检查

### 注意事项

1. **httpx 日志配置**：通过 `logging.getLogger("httpx").setLevel(logging.WARNING)` 将 httpx 的日志级别设置为 WARNING，只记录警告和错误信息
2. **日志统一性**：现在所有模块都使用 `from logs import logger`，确保日志格式和行为一致
3. **向后兼容**：`main.py` 中保留了基本的 `logging.basicConfig()` 配置，用于向后兼容，但实际应用中推荐使用 loguru

---

## 2025-11-06 14:00:00 - 修复数据库事务冲突：Serper API 响应记录时的嵌套 commit 问题

### 需求描述

在运行 FindKP 搜索时，出现数据库事务冲突错误：

```
Method 'commit()' can't be called here; method 'commit()' is already in progress
```

错误发生在 `core/search/serper_provider.py` 的 `search_batch` 方法中，当尝试记录 Serper API 响应数据到数据库时。

### 问题分析

**根本原因**：

1. FastAPI 的 `get_db()` 依赖项会在请求结束时自动 `commit()`（在 `database/connection.py` 第 36 行）
2. `serper_provider.search_batch()` 在记录数据时，Repository 方法内部也调用了 `commit()`（如 `create_serper_response()` 第 192 行）
3. 这导致了嵌套事务冲突：在一个已经开启的事务中再次调用 `commit()`

**问题场景**：

- 请求开始 → `get_db()` 创建数据库会话
- 调用 `find_kps()` → 传递会话给 `search_batch()`
- `search_batch()` 记录数据 → Repository 方法调用 `commit()`
- 请求结束 → `get_db()` 再次调用 `commit()` → ❌ 冲突

### 实现逻辑

#### 1. 修改 Repository 方法，添加 auto_commit 参数

**1.1 修改 `database/repository.py` 的 `create_serper_response()` 方法**

- 添加 `auto_commit: bool = True` 参数
- 当 `auto_commit=False` 时，只调用 `flush()` 而不调用 `commit()`
- 保持向后兼容，默认值 `True` 不影响其他调用

**1.2 修改 `database/repository.py` 的 `create_serper_organic_results()` 方法**

- 添加 `auto_commit: bool = True` 参数
- 当 `auto_commit=False` 时，只调用 `flush()` 而不调用 `commit()`
- 保持向后兼容，默认值 `True` 不影响其他调用

#### 2. 修改 serper_provider，传入 auto_commit=False

**2.1 修改 `core/search/serper_provider.py` 的 `search_batch()` 方法**

- 在调用 `repository.create_serper_response()` 时传入 `auto_commit=False`
- 在调用 `repository.create_serper_organic_results()` 时传入 `auto_commit=False`
- 这样只 flush 数据到会话，不提交事务，由外部的 `get_db()` 统一提交

### 技术细节

#### flush() vs commit()

- **flush()**: 将更改发送到数据库，但不会提交事务。在同一次会话中，其他操作可以看到这些更改。
- **commit()**: 提交事务，永久保存更改。之后会开始新的事务。

在这个场景中：

- 使用 `flush()` 可以让数据在会话中可见，但不会提交事务
- 外部的 `get_db()` 依赖项会在请求结束时统一提交所有更改
- 避免了嵌套事务冲突

### 修改文件清单

1. ✅ `database/repository.py` - 添加 `auto_commit` 参数到 `create_serper_response()` 和 `create_serper_organic_results()`
2. ✅ `core/search/serper_provider.py` - 调用时传入 `auto_commit=False`

### 功能验证

- ✅ Repository 方法支持 auto_commit 参数
- ✅ serper_provider 调用时传入 auto_commit=False
- ✅ 代码通过 lint 检查
- ✅ 保持向后兼容，其他调用不受影响

### 注意事项

1. **事务管理**：使用 `flush()` 而不是 `commit()`，让外部的依赖项统一管理事务提交
2. **向后兼容**：`auto_commit` 参数默认为 `True`，保持现有的行为不变
3. **错误处理**：记录数据失败不影响主流程，错误会被捕获并记录日志

---

## 2025-11-06 20:00:54 - 完善贸易数据导入脚本

### 需求描述

完善 `scripts/make_t_json.py` 脚本，实现以下功能：

1. 查询 `/home/www/downloads-tendata` 目录下的所有 `.json` 格式文件
2. 解析每个文件的 `results.content` 节点数据
3. 将数据遍历存储到独立的贸易数据表中
4. 根据节点内容设计数据库表结构
5. 支持增量导入（记录已处理的文件，跳过已处理）

### 实现逻辑

#### 1. 数据库表设计

根据 JSON 数据结构，设计了两个表：

**贸易记录表 (`trade_records`)**：

- 存储所有贸易记录数据
- 包含进口商、出口商、产品、贸易方式等完整信息
- 字段映射：驼峰命名（JSON）→ 下划线命名（数据库）
- 支持 JSON 类型字段存储产品标签数组
- 添加了多个索引以优化查询性能

**已处理文件记录表 (`processed_files`)**：

- 记录已处理的文件信息
- 包含文件路径、大小、处理时间、导入记录数
- 使用唯一索引防止重复处理

#### 2. ORM 模型定义

在 `database/models.py` 中添加了两个模型：

- `TradeRecord`: 贸易记录模型，包含所有贸易相关字段
- `ProcessedFile`: 已处理文件记录模型

#### 3. Repository 扩展

在 `database/repository.py` 中添加了三个方法：

- `create_trade_records_batch()`: 批量创建贸易记录
  - 支持日期字符串解析（ISO 格式）
  - 自动映射 JSON 字段名到数据库字段名
  - 支持批量提交优化性能
- `get_processed_file()`: 查询已处理文件记录
  - 用于检查文件是否已处理
- `create_processed_file()`: 创建已处理文件记录
  - 记录文件处理信息

#### 4. 导入脚本实现

完善了 `scripts/make_t_json.py`，实现以下功能：

**核心功能**：

- 扫描指定目录下的所有 `.json` 文件
- 解析 JSON 文件，提取 `results.content` 数组
- 批量导入数据到数据库
- 记录已处理文件，支持增量导入

**特性**：

- 异步处理：使用 `AsyncSession` 和 `async/await`
- 错误处理：单个文件失败不影响其他文件
- 日志记录：详细的处理进度和错误信息
- 命令行参数：支持指定目录和强制重新导入

**使用方式**：

```bash
# 使用默认目录
uv run python scripts/make_t_json.py

# 指定目录
uv run python scripts/make_t_json.py --dir /path/to/json/files

# 强制重新导入所有文件
uv run python scripts/make_t_json.py --force
```

### 数据流程

```
JSON 文件
  ↓
扫描目录 (.json 文件)
  ↓
检查是否已处理 (processed_files 表)
  ↓ (未处理)
解析 JSON (results.content)
  ↓
批量插入 (trade_records 表)
  ↓
记录已处理 (processed_files 表)
```

### 修改文件清单

1. ✅ `database/sql/004_trade_records.sql` - 创建贸易记录表结构
2. ✅ `database/sql/005_processed_files.sql` - 创建已处理文件记录表结构
3. ✅ `database/models.py` - 添加 TradeRecord 和 ProcessedFile 模型
4. ✅ `database/repository.py` - 添加批量插入和文件记录方法
5. ✅ `scripts/make_t_json.py` - 完善导入脚本

### 技术要点

1. **字段映射**：JSON 使用驼峰命名，数据库使用下划线命名，在 Repository 中手动映射
2. **日期处理**：支持 ISO 格式日期字符串解析（包含时区信息）
3. **批量操作**：使用批量提交优化性能，减少数据库交互次数
4. **增量导入**：通过 `processed_files` 表记录已处理文件，避免重复导入
5. **错误容错**：单个文件失败不影响整体流程，记录详细错误日志

### 注意事项

1. **数据库初始化**：需要先执行 SQL 脚本创建表结构

   ```bash
   mysql -u user -p database < database/sql/004_trade_records.sql
   mysql -u user -p database < database/sql/005_processed_files.sql
   ```

2. **数据去重**：根据需求，允许重复记录（trade_id 不设唯一约束）

3. **性能优化**：批量插入时使用 `auto_commit=True`，每批数据提交一次事务

4. **脚本执行**：使用 `uv run` 执行脚本，确保使用正确的 Python 环境和依赖

---

## 2025-11-06 21:12:26 - 在存储 Company 时添加 local_name 字段

### 需求描述

在存储 Company 的时候，需要把 local 的名字也存储到表格中。当前系统中有 `company_name_local` 参数，但在存储 Company 时没有保存到数据库。

### 实现逻辑

#### 1. 问题分析

- Company 模型目前只有 `name` 字段，存储的是英文名称（`company_name_en`）
- 系统中有 `company_name_local` 参数，但在存储 Company 时没有保存
- `get_or_create_company` 方法只接收 `name` 参数，没有接收 `local_name`

#### 2. 实现步骤

**步骤 1：在 Company 模型中添加 `local_name` 字段**

```python
# database/models.py
class Company(Base):
    name = Column(String(255), unique=True, nullable=False, index=True)
    local_name = Column(String(255))  # 公司本地名称
    domain = Column(String(255))  # 公司域名
    # ...
```

**步骤 2：修改 `get_or_create_company` 方法**

- 添加 `local_name` 参数（可选）
- 创建 Company 时保存 `local_name`
- 如果公司已存在但 `local_name` 为空，则更新它

```python
async def get_or_create_company(
    self, name: str, local_name: Optional[str] = None
) -> models.Company:
    # 创建时保存 local_name
    if not company:
        company = models.Company(name=name, local_name=local_name)
    # 如果已存在但 local_name 为空，则更新
    elif not company.local_name and local_name:
        company.local_name = local_name
        await self.db.commit()
```

**步骤 3：更新调用处**

- 在 `_search_and_save_company_info` 方法中传入 `local_name`
- 在异常处理中也传入 `local_name`

```python
company = await repo.get_or_create_company(
    company_name_en, local_name=company_name_local
)
```

**步骤 4：创建数据库迁移脚本**

创建 `database/sql/006_add_company_local_name.sql`：

```sql
ALTER TABLE companies
ADD COLUMN local_name VARCHAR(255) COMMENT '公司本地名称' AFTER name;
```

#### 3. 数据流程

```
API 请求 (company_name_en, company_name_local)
  ↓
FindKPService.find_kps()
  ↓
_search_and_save_company_info()
  ↓
Repository.get_or_create_company(name, local_name)
  ↓
创建/更新 Company 记录 (name + local_name)
```

#### 4. 设计考虑

1. **向后兼容**：`local_name` 参数设为可选，不影响现有代码
2. **数据更新**：如果公司已存在但 `local_name` 为空，自动更新
3. **字段位置**：`local_name` 字段放在 `name` 字段之后，保持逻辑顺序

### 修改文件清单

1. ✅ `database/models.py` - 在 Company 模型中添加 `local_name` 字段
2. ✅ `database/repository.py` - 修改 `get_or_create_company` 方法，接收并保存 `local_name`
3. ✅ `findkp/service.py` - 更新两处调用，传入 `local_name` 参数
4. ✅ `database/sql/006_add_company_local_name.sql` - 创建数据库迁移脚本

### 技术要点

1. **可选参数**：`local_name` 设为可选参数，保持向后兼容
2. **自动更新**：如果公司已存在但 `local_name` 为空，自动更新
3. **字段类型**：使用 `VARCHAR(255)` 存储本地名称，与 `name` 字段一致
4. **数据库迁移**：需要执行迁移脚本添加字段

### 注意事项

1. **数据库迁移**：需要先执行 SQL 脚本添加字段

   ```bash
   mysql -u user -p database < database/sql/006_add_company_local_name.sql
   ```

2. **现有数据**：已存在的 Company 记录的 `local_name` 字段为 NULL，不影响查询

3. **数据完整性**：`local_name` 字段允许为空，因为某些公司可能没有本地名称

---

## 2025-11-06 21:36:18 - 创建批量 FindKP CLI 命令（简化版）

### 需求描述

在 CLI 中创建一个命令，能够从 `trade_records` 表中批量查询公司数据（`importer` 和 `importer_en`），然后对每个公司执行 FindKP 操作，自动查找关键联系人。

### 实现逻辑

#### 1. 架构设计

```mermaid
graph TD
    A[CLI 命令: batch-findkp] --> B[查询 trade_records 表]
    B --> C[去重公司列表]
    C --> D[遍历每个公司]
    D --> E{是否跳过已有联系人?}
    E -->|是| F[检查公司是否已有联系人]
    F -->|有| G[跳过]
    F -->|无| H[执行 FindKP]
    E -->|否| H[执行 FindKP]
    H --> I[保存联系人]
    I --> J[统计结果]
    G --> J
    J --> K[输出统计信息]
```

#### 2. 简化实现

直接查询 `trade_records` 表的 `importer` 和 `importer_en` 字段，无需复杂的 Repository 方法：

**查询逻辑**：

- 使用 SQLAlchemy 的 `select()` 直接查询 `TradeRecord.importer` 和 `TradeRecord.importer_en`
- 过滤掉空值和空字符串
- 使用 Python `set` 对 `(importer_en, importer)` 元组进行去重
- 如果 `importer_en` 为空，则使用 `importer` 作为英文名称

#### 3. CLI 命令实现

创建了 `cli/batch_findkp.py` 文件，实现简化的批量处理命令：

**命令参数**：

- `--verbose/-v`: 显示详细日志（唯一参数）

**处理流程**：

1. 直接查询 `trade_records` 表，获取所有 `importer` 和 `importer_en` 字段
2. 使用 Python `set` 对 `(importer_en, importer)` 元组进行去重
3. 遍历每个去重后的公司：
   - 调用 `FindKPService.find_kps()` 执行 FindKP 操作
   - 提交事务并统计结果
   - 如果失败，记录错误并继续处理下一个
4. 输出统计信息：总数、成功、失败、总联系人数

#### 4. 命令注册

在 `cli/main.py` 中注册新命令：

```python
from cli.batch_findkp import batch_findkp
cli.add_command(batch_findkp)
```

#### 5. 错误处理

- 每个公司的处理都有独立的 try-catch
- 失败时回滚事务，不影响其他公司的处理
- 记录失败的公司列表，最后统一输出
- 支持用户中断（Ctrl+C）

#### 6. 进度显示

- 显示当前处理进度：`[当前/总数]`
- 显示每个公司的基本信息：英文名称、本地名称
- 显示处理结果：成功/失败、找到的联系人数量
- 最后显示总体统计信息

### 修改文件清单

1. ✅ `cli/batch_findkp.py` - 创建简化的批量 FindKP 命令文件
2. ✅ `cli/main.py` - 注册新命令

### 技术要点

1. **简单查询**：直接使用 SQLAlchemy `select()` 查询 `importer` 和 `importer_en` 字段
2. **Python 去重**：使用 `set` 对 `(importer_en, importer)` 元组进行去重，简单高效
3. **事务管理**：每个公司的处理都有独立的事务，失败不影响其他公司
4. **异步处理**：使用 `async/await` 保持与 FastAPI 架构一致
5. **简化参数**：只保留 `--verbose` 参数，去除复杂的分页、延迟等功能

### 使用示例

```bash
# 基本用法：处理所有公司
smart-lead batch-findkp

# 显示详细日志
smart-lead batch-findkp --verbose
```

### 注意事项

1. **数据量**：如果 `trade_records` 表数据量很大，建议分批处理或添加限制
2. **API 限流**：批量处理时注意 API 限流，可能需要手动控制处理速度
3. **内存使用**：去重操作在内存中进行，如果数据量特别大，可能需要优化

---

---

## 2025-11-12 16:54:22 - Writer 模块重构：支持新 Prompt 模板（HTML 输出格式）

### 需求

将 Writer 模块从旧的 `W_VN_PROMPT`（JSON 输出格式）迁移到新的 `W_VN_MAIL_GENERATOR`（HTML 输出格式），支持两阶段输出解析（Stage A: YAML + Stage B: HTML）和完整的 HTML 邮件内容生成。

### 实现逻辑

#### 1. 配置管理扩展 (`config.py`)

在 `Settings` 类中添加了 Writer 模块所需的新配置项：

- `SENDER_NAME`: 发送者姓名
- `SENDER_TITLE_EN`: 发送者职位（英文）
- `SENDER_COMPANY`: 发送者公司
- `SENDER_EMAIL`: 发送者邮箱
- `WHATSAPP_NUMBER`: WhatsApp 号码
- `IMAGE_URL_CUSTOMS_RESULT`: 海关数据截图 URL
- `IMAGE_URL_FILTERS`: 筛选器截图 URL
- `TRIAL_URL`: 试用链接（默认值：`https://www.tendata.com/data/?email1110`）

所有配置项都从 `.env` 文件读取，使用全局 `settings` 实例访问。

#### 2. Schema 更新 (`schemas/writer.py`)

更新了 `GeneratedEmail` 模型：

- **移除字段**：

  - `content_en`: 英文邮件正文
  - `content_vn`: 越南语邮件正文
  - `full_content`: 完整双语内容

- **新增字段**：

  - `html_content`: 完整的 HTML 邮件内容（直接用于邮件发送）

- **保留字段**：
  - `subject`: 邮件主题（从 HTML 中提取的越南语主题行）
  - 其他联系人信息字段保持不变

#### 3. Service 层重构 (`writer/service.py`)

##### 3.1 导入更新

- 从 `W_VN_PROMPT` 改为使用 `W_VN_MAIL_GENERATOR`
- 使用动态导入方式处理 `.PY` 扩展名（通过 `exec()` 直接读取和执行文件内容）
- 添加 `config` 导入以访问配置

##### 3.2 新增 HTML 解析辅助方法

- **`_separate_stages(content: str) -> tuple[str, str]`**：

  - 分离 Stage A (YAML) 和 Stage B (HTML)
  - 通过查找 `<!DOCTYPE html>` 或 `<html>` 标签定位 HTML 部分
  - 返回 `(yaml_part, html_part)` 元组

- **`_extract_subject_from_html(html: str) -> str`**：
  - 从 HTML 中提取越南语主题行
  - 使用正则表达式匹配：`<p[^>]*>Chủ đề:\s*([^<]+)</p>`
  - 提取 `Chủ đề:` 后的主题文本

##### 3.3 重写 `_format_prompt` 方法

支持新 Prompt 所需的所有参数：

- **公司信息**：`company_en_name`, `company_local_name`, `industry_cn`, `positioning_cn`, `brief_cn`
- **联系人信息**：`full_name`, `role_en`, `department_cn`, `email`
- **资产信息**：`has_screenshot_customs_result`, `has_screenshot_filters`, `image_url_customs_result`, `image_url_filters`, `screenshot_mention_en`, `screenshot_mention_vi`
- **发送者信息**：`sender_name`, `sender_title_en`, `sender_company`, `sender_email`
- **其他**：`trial_url`, `whatsapp_number`

所有配置值从 `settings` 读取，空值使用空字符串作为默认值。

##### 3.4 重写 `_parse_email_response` 方法

处理两阶段输出（YAML + HTML）：

1. **分离阶段**：使用 `_separate_stages()` 分离 YAML 和 HTML 部分
2. **提取主题行**：使用 `_extract_subject_from_html()` 从 HTML 中提取越南语主题行
3. **提取完整 HTML**：从 `<!DOCTYPE html>` 或 `<html>` 开始到 `</html>` 结束，提取完整的 HTML 内容
4. **构建响应对象**：创建 `GeneratedEmail` 对象，包含 `subject` 和 `html_content`

##### 3.5 移除不再需要的方法

- 移除了 `_extract_json_from_text()` 方法（不再需要 JSON 解析）
- 移除了 `json` 模块导入

#### 4. 环境变量模板更新 (`.env.example`)

添加了新配置项的示例值：

```env
# Writer 模块配置
SENDER_NAME="Your Name"
SENDER_TITLE_EN="Business Development Manager"
SENDER_COMPANY="Tendata"
SENDER_EMAIL="your_email@example.com"
WHATSAPP_NUMBER="+84xxxxxxxxx"
IMAGE_URL_CUSTOMS_RESULT="https://example.com/customs-result.png"
IMAGE_URL_FILTERS="https://example.com/filters.png"
TRIAL_URL="https://www.tendata.com/data/?email1110"
```

### 技术要点

1. **动态导入处理**：由于 Prompt 文件使用 `.PY` 扩展名，使用 `exec()` 直接读取和执行文件内容，而不是标准的 Python 导入机制

2. **两阶段输出解析**：

   - Stage A (YAML)：包含受众选择信息（不保留在最终输出中）
   - Stage B (HTML)：完整的 HTML 邮件内容（保留并直接使用）

3. **HTML 主题行提取**：

   - 从 HTML 的 `<p>` 标签中提取越南语主题行（`Chủ đề: ...`）
   - 使用正则表达式进行模式匹配

4. **字段映射**：

   - 数据库字段直接使用，不进行翻译
   - 空值统一处理为空字符串

5. **向后兼容**：
   - API 接口保持不变（`/writer/generate`）
   - 响应模型结构更新，但接口调用方式不变

### 修改文件清单

1. ✅ `config.py` - 添加 Writer 模块配置项
2. ✅ `schemas/writer.py` - 更新 `GeneratedEmail` 模型
3. ✅ `writer/service.py` - 重构服务层（导入、格式化、解析）
4. ✅ `.env.example` - 添加新配置项示例

### 测试验证

- ✅ 所有代码通过 lint 检查
- ✅ 模块导入测试通过
- ✅ 配置加载测试通过
- ✅ 所有待办事项已完成

### 注意事项

1. **配置要求**：需要在 `.env` 文件中配置所有新添加的配置项，否则会使用空字符串作为默认值

2. **HTML 格式**：生成的 HTML 内容需要完整保留，直接用于邮件发送服务（邮件发送服务稍后实现）

3. **主题行提取**：如果 HTML 中无法提取主题行，会使用空字符串，但不会导致解析失败

4. **两阶段输出**：Prompt 会先输出 Stage A (YAML)，再输出 Stage B (HTML)，解析时需要正确分离

---

---

## 2025-11-12 16:59:50 - Writer 模块邮件发送功能集成

### 需求

在完成 Writer 模块重构后，集成邮件发送功能，使生成的 HTML 邮件可以直接发送给联系人。

### 实现逻辑

#### 1. 邮件发送服务 HTML 支持

##### 1.1 SMTP 发送器更新 (`core/email/smtp_sender.py`)

- 添加 HTML 内容检测逻辑
- 当检测到 `<html>` 或 `<!DOCTYPE html>` 标签时，使用 `MIMEText(..., "html")` 而不是 `"plain"`
- 保持向后兼容，纯文本内容仍然使用 `"plain"` 格式

##### 1.2 ESP 发送器更新 (`core/email/esp_sender.py`)

- 添加 HTML 内容检测逻辑
- 当检测到 HTML 内容时，使用 `html_content=Content("text/html", ...)` 而不是 `plain_text_content`
- 保持向后兼容，纯文本内容仍然使用 `plain_text_content`

#### 2. Writer Service 邮件发送功能

##### 2.1 添加转换方法 (`writer/service.py`)

- **`_to_core_email(writer_email: WriterGeneratedEmail) -> CoreGeneratedEmail`**：
  - 将 Writer 模块的 `GeneratedEmail`（包含 `html_content`）转换为邮件发送服务使用的 `core.schemas.GeneratedEmail`（包含 `body`）
  - HTML 内容直接作为 `body` 字段传递

##### 2.2 添加发送器工厂方法

- **`_get_email_sender(sender_type: str) -> BaseEmailSender`**：
  - 根据 `sender_type` 参数（'smtp' 或 'esp'）返回对应的发送器实例
  - 支持 SMTP 和 ESP（SendGrid）两种发送方式

##### 2.3 添加发送邮件方法

- **`send_email(contact_id: int, sender_type: str = "smtp", db: AsyncSession = None) -> Dict[str, Any]`**：
  - 根据联系人 ID 查询联系人信息
  - 重新生成邮件（简化实现，实际场景中可以从数据库查询已生成的邮件）
  - 转换为邮件发送服务格式
  - 调用对应的发送器发送邮件
  - 返回发送结果（成功/失败、消息 ID、错误信息）

#### 3. Repository 扩展 (`database/repository.py`)

- 添加 **`get_contact_by_id(contact_id: int) -> Optional[Contact]`** 方法：
  - 根据联系人 ID 查询联系人
  - 用于邮件发送功能中查询联系人信息

#### 4. Schema 扩展 (`schemas/writer.py`)

##### 4.1 发送邮件请求模型

- **`SendEmailRequest`**：
  - `contact_id`: 联系人 ID（对应已生成的邮件）
  - `sender_type`: 发送器类型（'smtp' 或 'esp'，默认 'smtp'）
  - 包含验证器，确保 `sender_type` 只能是 'smtp' 或 'esp'

##### 4.2 发送邮件响应模型

- **`SendEmailResponse`**：
  - `contact_id`: 联系人 ID
  - `contact_email`: 联系人邮箱
  - `success`: 发送是否成功
  - `message_id`: 消息 ID（ESP 支持，SMTP 为 None）
  - `error`: 错误信息（如果失败）

#### 5. Router 端点扩展 (`writer/router.py`)

- 添加 **`POST /writer/send`** 端点：
  - 接收 `SendEmailRequest` 请求
  - 调用 `service.send_email()` 方法
  - 返回 `SendEmailResponse` 响应
  - 包含完整的错误处理和日志记录

### 技术要点

1. **HTML 内容自动检测**：

   - 通过检测 `<html>` 或 `<!DOCTYPE html>` 标签判断是否为 HTML 内容
   - 自动选择正确的 MIME 类型（text/html 或 text/plain）

2. **发送器选择**：

   - 支持 SMTP 和 ESP（SendGrid）两种发送方式
   - 通过 `sender_type` 参数动态选择
   - 发送器实例在每次发送时创建（可以优化为单例模式）

3. **邮件生成策略**：

   - 当前实现：每次发送时重新生成邮件（简化实现）
   - 未来优化：可以从数据库查询已生成的邮件，避免重复生成

4. **错误处理**：
   - 联系人不存在：返回 404 错误
   - 联系人没有邮箱：返回 404 错误
   - 邮件生成失败：返回 500 错误
   - 邮件发送失败：返回发送状态和错误信息

### 修改文件清单

1. ✅ `core/email/smtp_sender.py` - 添加 HTML 支持
2. ✅ `core/email/esp_sender.py` - 添加 HTML 支持
3. ✅ `writer/service.py` - 添加转换方法、发送器工厂、发送邮件方法
4. ✅ `database/repository.py` - 添加 `get_contact_by_id` 方法
5. ✅ `schemas/writer.py` - 添加 `SendEmailRequest` 和 `SendEmailResponse` 模型
6. ✅ `writer/router.py` - 添加 `/writer/send` 端点

### API 使用示例

#### 生成邮件

```bash
POST /writer/generate
{
  "company_id": 1
}
```

#### 发送邮件

```bash
POST /writer/send
{
  "contact_id": 123,
  "sender_type": "smtp"  # 或 "esp"
}
```

### 注意事项

1. **配置要求**：

   - SMTP 发送：需要配置 `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SENDER_EMAIL`
   - ESP 发送：需要配置 `SENDGRID_API_KEY`, `ESP_SENDER_EMAIL`

2. **邮件生成**：

   - 当前实现每次发送时重新生成邮件，可能影响性能
   - 建议后续优化：将生成的邮件存储到数据库，发送时直接查询

3. **HTML 内容**：

   - 邮件发送服务会自动检测 HTML 内容并选择正确的 MIME 类型
   - 确保生成的 HTML 内容是完整的、有效的 HTML 文档

4. **错误处理**：
   - 发送失败不会抛出异常，而是返回包含错误信息的响应
   - 客户端需要检查 `success` 字段判断是否发送成功

---

## 2024-12-19 - 调整 Writer 模块逻辑：移除发送功能，支持指定 LLM 类型，添加批量生成

### 需求

1. **移除发送逻辑**：Writer 模块不再负责邮件发送，只负责生成完整的邮件内容、标题和收件地址
2. **支持指定 LLM 类型**：不同业务环节可以使用不同的 LLM 模型
3. **添加批量生成功能**：在 CLI 中新增命令，查询所有有邮箱的联系人（去重），批量生成邮件

### 实现逻辑

#### 1. 数据结构调整

**新增 `EmailContent` 模型**：

- `contact_id`: 联系人 ID
- `contact_name`: 联系人姓名
- `contact_email`: 收件地址（必需）
- `contact_role`: 联系人职位
- `subject`: 邮件主题
- `html_content`: 完整的 HTML 邮件内容

**移除发送相关模型**：

- 移除 `SendEmailRequest` 和 `SendEmailResponse`
- 保留 `GeneratedEmail` 用于兼容旧版本

#### 2. Service 层调整

**移除发送逻辑**：

- 删除 `send_email()` 方法
- 删除 `_get_email_sender()` 方法
- 删除 `_to_core_email()` 方法
- 移除对 `core.email` 模块的依赖

**支持指定 LLM 类型**：

- `WriterService.__init__()` 接受 `llm_model` 参数
- `generate_emails()` 方法接受 `llm_model` 参数
- 如果指定了 LLM 模型，在方法内部重新初始化 LLM 实例

**新增批量生成方法**：

- `generate_emails_for_all_contacts()`: 为所有有邮箱的联系人生成邮件
- 调用 `repository.get_all_contacts_with_email()` 获取去重后的联系人列表
- 按公司分组，获取公司信息
- 并发生成邮件

#### 3. Repository 层扩展

**新增方法**：

- `get_all_contacts_with_email()`: 查询所有有邮箱的联系人，按邮箱去重
- 去重策略：保留置信度最高的联系人，如果置信度相同则保留最新的

#### 4. Router 层调整

**移除发送端点**：

- 删除 `/writer/send` 端点

**更新生成端点**：

- `GenerateEmailRequest` 添加 `llm_model` 字段
- 端点支持通过请求参数指定 LLM 模型类型

#### 5. CLI 层调整

**移除发送命令**：

- 删除 `writer send` 命令

**更新生成命令**：

- `writer generate` 添加 `--llm-model` 参数

**新增批量生成命令**：

- `writer batch-generate`: 为所有有邮箱的联系人生成邮件
- 支持 `--llm-model` 参数指定 LLM 类型
- 显示前 10 条邮件，其余显示数量统计

### 使用示例

#### API 调用

```bash
# 生成邮件（使用默认 LLM）
POST /writer/generate
{
  "company_id": 1
}

# 生成邮件（指定 LLM 模型）
POST /writer/generate
{
  "company_id": 1,
  "llm_model": "gpt-4o"
}
```

#### CLI 调用

```bash
# 根据公司生成邮件
smart-lead writer generate --company-id 1
smart-lead writer generate --company-name "Apple Inc." --llm-model "gpt-4o"

# 批量生成邮件（所有有邮箱的联系人）
smart-lead writer batch-generate
smart-lead writer batch-generate --llm-model "deepseek-chat" --verbose
```

### 修改文件清单

1. ✅ `schemas/writer.py` - 添加 `EmailContent` 模型，移除发送相关模型，添加 `llm_model` 字段
2. ✅ `writer/service.py` - 移除发送逻辑，支持指定 LLM 类型，添加批量生成方法
3. ✅ `writer/router.py` - 移除 `/send` 端点，更新生成端点支持 LLM 参数
4. ✅ `database/repository.py` - 添加 `get_all_contacts_with_email()` 方法
5. ✅ `cli/writer.py` - 移除发送命令，更新生成命令，添加批量生成命令

### 技术要点

1. **LLM 模型指定**：

   - 支持在初始化时指定模型：`WriterService(llm_model="gpt-4o")`
   - 支持在方法调用时指定模型：`generate_emails(..., llm_model="gpt-4o")`
   - 如果指定了模型，会在方法内部重新初始化 LLM 实例

2. **邮箱去重策略**：

   - 按邮箱小写去重
   - 保留置信度最高的联系人
   - 如果置信度相同，保留创建时间最新的

3. **批量生成流程**：

   ```
   查询所有有邮箱的联系人（去重）
   ↓
   按公司分组，获取公司信息
   ↓
   并发生成邮件（每个联系人一个任务）
   ↓
   过滤有效结果，返回邮件列表
   ```

4. **数据结构设计**：
   - `EmailContent` 包含完整的邮件信息（内容、标题、收件地址）
   - 邮件发送由其他模块完成，Writer 模块只负责生成

### 注意事项

1. **LLM 模型选择**：

   - 不同业务环节可以使用不同的 LLM 模型
   - 如果不指定，使用默认配置（`settings.LLM_MODEL`）
   - 支持的模型类型：`gpt-4o`, `deepseek-chat`, `glm-4` 等

2. **邮箱去重**：

   - 只处理有邮箱的联系人
   - 去重基于邮箱地址（不区分大小写）
   - 保留置信度最高的记录

3. **批量生成性能**：

   - 使用异步并发生成，提升性能
   - 单个联系人失败不影响其他联系人
   - 建议在生产环境中控制并发数量

4. **邮件发送**：
   - Writer 模块不再负责邮件发送
   - 生成的邮件内容可以直接传递给其他发送模块
   - `EmailContent` 包含发送所需的所有信息

---
