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
