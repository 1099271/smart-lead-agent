<!-- 399e5cfe-0cf2-4660-b682-60f653207074 deece118-a52c-40f6-b799-33e8fef544df -->
# MailManager 模块实现计划

## 一、配置管理

### 1.1 更新 config.py

在 `[config.py](config.py)` 的 `Settings` 类中添加以下配置字段：

- `GOOGLE_SERVICE_ACCOUNT_FILE: str = ""` - Service Account JSON 文件路径
- `GOOGLE_WORKSPACE_USER_EMAIL: str = ""` - Google Workspace 用户邮箱
- `GOOGLE_WORKSPACE_DOMAIN: str = ""` - Google Workspace 域名
- `TRACKING_BASE_URL: str = ""` - 追踪服务器基础 URL
- `TRACKING_ENABLED: bool = True` - 是否启用追踪
- `EMAIL_SEND_RATE_LIMIT: int = 10` - 每分钟发送限制
- `EMAIL_DAILY_LIMIT: int = 2000` - 每日发送上限

### 1.2 更新 .env.example

已在 `.env.example` 中添加相关配置项，无需修改。

## 二、数据库模型

### 2.1 在 database/models.py 中添加枚举和模型

添加 `EmailStatus` 枚举：

```python
class EmailStatus(enum.Enum):
    pending = "pending"
    sending = "sending"
    sent = "sent"
    failed = "failed"
    bounced = "bounced"
```

添加 `EmailTrackingEventType` 枚举：

```python
class EmailTrackingEventType(enum.Enum):
    opened = "opened"
    clicked = "clicked"
    replied = "replied"
```

添加 `Email` 模型：

- 关联字段：`contact_id`, `company_id` (外键，可选)
- 邮件内容：`subject`, `html_content`, `text_content`
- 收件人：`to_email`, `to_name`
- 发件人：`from_email`, `from_name`
- 追踪：`tracking_id` (唯一索引), `tracking_pixel_url`
- 状态：`status` (枚举，索引), `gmail_message_id` (唯一), `error_message`
- 时间戳：`created_at`, `sent_at`, `first_opened_at`, `updated_at`
- 关系：`contact`, `company`, `tracking_events`

添加 `EmailTracking` 模型：

- `email_id` (外键，索引)
- `event_type` (枚举，索引)
- `ip_address`, `user_agent`, `referer`
- `created_at` (索引)
- 关系：`email`

## 三、仓储层扩展

### 3.1 在 database/repository.py 中扩展 Repository 类

添加邮件相关方法：

- `create_email_record()` - 创建邮件记录
- `get_email_by_id()` - 根据 ID 查询邮件
- `get_email_by_tracking_id()` - 根据追踪 ID 查询邮件
- `update_email_status()` - 更新邮件状态
- `update_email_sent_info()` - 更新发送信息（message_id, sent_at）
- `update_email_first_opened_at()` - 更新首次打开时间
- `create_tracking_event()` - 创建追踪事件
- `get_email_tracking_events()` - 查询邮件的追踪事件
- `get_emails_by_status()` - 根据状态查询邮件列表（支持分页）
- `get_daily_sent_count()` - 获取今日已发送数量（用于限制检查）

所有方法使用异步实现，遵循现有代码风格。

## 四、Gmail API 客户端

### 4.1 创建 mail_manager/gmail_client.py

实现 `GmailAPIClient` 类：

- `__init__()` - 初始化，使用 Service Account 认证，配置 Domain-wide Delegation
- `send_message()` - 异步发送邮件方法
  - 构建 MIME 消息（支持 HTML）
  - 编码为 base64url
  - 调用 Gmail API
  - 返回 message_id
- `_create_message()` - 私有方法，构建邮件消息
- 错误处理：捕获 `HttpError`，记录日志，抛出自定义异常
- 使用 `tenacity` 实现重试机制（指数退避，最多 3 次）

注意：Gmail API 客户端需要同步调用，但要在异步方法中使用 `asyncio.to_thread()` 包装。

## 五、工具函数

### 5.1 创建 mail_manager/utils.py

实现追踪相关工具函数：

- `generate_tracking_id()` - 生成唯一追踪 ID（使用 UUID4）
- `generate_tracking_pixel_url()` - 生成追踪像素 URL
- `embed_tracking_pixel()` - 在 HTML 中嵌入追踪像素（在 `</body>` 之前插入）
- `generate_1x1_png()` - 生成 1x1 透明 PNG 图片（使用 Pillow 或返回静态字节）

## 六、服务层

### 6.1 创建 mail_manager/service.py

实现 `MailManagerService` 类：

核心方法：

- `send_email()` - 发送单封邮件

  1. 验证请求（必须提供邮件内容或 contact_id）
  2. 如果提供 `contact_id`，从 Writer 模块获取邮件内容（调用 `WriterService.generate_emails()`）
  3. 生成 `tracking_id` 和追踪像素 URL
  4. 如果启用追踪，嵌入追踪像素到 HTML
  5. 创建 Email 记录（status=pending）
  6. 调用 Gmail API 发送（更新状态为 sending）
  7. 发送成功后更新状态为 sent，记录 message_id 和 sent_at
  8. 发送失败则更新状态为 failed，记录错误信息
  9. 返回结果

- `send_batch()` - 批量发送邮件
  - 使用 `asyncio.Semaphore` 控制并发（根据 `EMAIL_SEND_RATE_LIMIT`）
  - 检查每日发送上限
  - 并发发送多封邮件
  - 收集成功和失败结果
  - 返回汇总信息

- `track_email_open()` - 处理追踪请求

  1. 根据 `tracking_id` 查找邮件
  2. 如果邮件不存在，返回 404 PNG
  3. 创建 `EmailTracking` 事件（event_type=opened）
  4. 记录 IP、User-Agent、Referer
  5. 如果是首次打开，更新 `first_opened_at`
  6. 返回 1x1 透明 PNG

- `get_email_status()` - 查询邮件状态
  - 查询邮件基本信息
  - 查询追踪事件
  - 统计打开次数
  - 返回完整状态信息

- `get_emails_list()` - 查询邮件列表
  - 支持状态筛选
  - 支持分页（limit, offset）
  - 返回邮件列表

所有方法使用异步实现，遵循项目架构规范。

## 七、数据模型

### 7.1 创建 schemas/mail_manager.py

定义 Pydantic 模型：

请求模型：

- `SendEmailRequest` - 发送邮件请求
  - `to_email: EmailStr` (必需)
  - `to_name: Optional[str]`
  - `subject: Optional[str]` (如果提供邮件内容)
  - `html_content: Optional[str]` (如果提供邮件内容)
  - `contact_id: Optional[int]` (如果从 Writer 获取)
  - `company_id: Optional[int]` (如果从 Writer 获取)
  - `from_email: Optional[str]` (可选，默认使用配置)
  - `from_name: Optional[str]` (可选，默认使用配置)
  - 验证器：至少提供邮件内容或 contact_id 之一

- `SendBatchEmailRequest` - 批量发送请求
  - `emails: List[SendEmailRequest]`
  - `rate_limit: Optional[int]` (覆盖全局配置)

响应模型：

- `SendEmailResponse(BaseResponse)` - 发送邮件响应
  - `email_id: int`
  - `tracking_id: str`
  - `status: str`
  - `gmail_message_id: Optional[str]`
  - `sent_at: Optional[datetime]`

- `SendBatchEmailResponse(BaseResponse)` - 批量发送响应
  - `total: int`
  - `success: int`
  - `failed: int`
  - `results: List[SendEmailResponse]`

- `EmailTrackingEvent` - 追踪事件模型
  - `event_type: str`
  - `ip_address: Optional[str]`
  - `user_agent: Optional[str]`
  - `created_at: datetime`

- `EmailStatusResponse(BaseResponse)` - 邮件状态响应
  - `email_id: int`
  - `status: str`
  - `to_email: str`
  - `subject: str`
  - `sent_at: Optional[datetime]`
  - `first_opened_at: Optional[datetime]`
  - `open_count: int`
  - `tracking_events: List[EmailTrackingEvent]`

- `EmailListResponse(BaseResponse)` - 邮件列表响应
  - `emails: List[EmailStatusResponse]`
  - `total: int`
  - `limit: int`
  - `offset: int`

## 八、路由层

### 8.1 创建 mail_manager/router.py

实现 FastAPI 路由：

- `POST /mail_manager/send` - 发送单封邮件
  - 请求体：`SendEmailRequest`
  - 响应：`SendEmailResponse`
  - 调用 `MailManagerService.send_email()`
  - 异常处理：捕获异常，返回 500 错误

- `POST /mail_manager/send_batch` - 批量发送
  - 请求体：`SendBatchEmailRequest`
  - 响应：`SendBatchEmailResponse`
  - 调用 `MailManagerService.send_batch()`

- `GET /mail_manager/track/{tracking_id}` - 追踪像素端点
  - 路径参数：`tracking_id`
  - 响应：`Response` (1x1 PNG，Content-Type: image/png)
  - 调用 `MailManagerService.track_email_open()`
  - 从 `Request` 对象获取 IP、User-Agent 等信息
  - 快速响应，错误不影响 PNG 返回

- `GET /mail_manager/emails/{email_id}` - 查询邮件状态
  - 路径参数：`email_id`
  - 响应：`EmailStatusResponse`
  - 调用 `MailManagerService.get_email_status()`

- `GET /mail_manager/emails` - 查询邮件列表
  - 查询参数：`status` (可选), `limit` (默认 10), `offset` (默认 0)
  - 响应：`EmailListResponse`
  - 调用 `MailManagerService.get_emails_list()`

所有路由使用 `APIRouter`，设置 `prefix="/mail_manager"` 和 `tags=["MailManager"]`，使用 `async def`，指定 `response_model`。

## 九、主应用集成

### 9.1 更新 main.py

- 导入 `mail_manager.router`
- 注册路由：`app.include_router(mail_manager_router)`
- 更新根端点，将 MailManager 从 "待实现" 改为已实现

## 十、依赖项

### 10.1 更新 pyproject.toml

在 `dependencies` 列表中添加：

- `google-api-python-client>=2.0.0`
- `google-auth>=2.0.0`
- `tenacity>=8.0.0`
- `Pillow>=10.0.0` (用于生成追踪像素)

## 十一、实现顺序

1. **Phase 1: 配置和数据库**

   - 更新 `config.py`
   - 添加数据库模型
   - 扩展 Repository 方法

2. **Phase 2: 核心组件**

   - 创建 Gmail API 客户端
   - 创建工具函数
   - 创建服务层基础方法

3. **Phase 3: API 层**

   - 创建 schemas
   - 创建路由
   - 集成到主应用

4. **Phase 4: 完善功能**

   - 实现批量发送
   - 实现追踪端点
   - 实现查询 API

## 十二、设计模式说明

### 邮件发送器抽象层设计

采用**策略模式**和**工厂模式**：

- `EmailSender` 抽象基类定义统一接口
- `GmailSender`、`SMTPSender` 等具体实现类
- `create_email_sender()` 工厂函数根据配置创建对应发送器
- 服务层只依赖抽象接口，不依赖具体实现
- 未来添加新的发送方式只需实现 `EmailSender` 接口即可

优势：

- 易于扩展：添加新的发送方式不影响现有代码
- 易于测试：可以 Mock `EmailSender` 接口
- 易于切换：通过配置即可切换发送方式

## 十三、注意事项

- 所有数据库操作使用 `AsyncSession` 和 `await`
- Gmail API 调用需要异步包装（`asyncio.to_thread()`）
- 追踪端点需要快速响应（<100ms），错误处理不能阻塞
- 遵循项目架构规范：Router → Service → Repository
- 所有方法使用 `async def`，与 FastAPI 异步架构一致
- 错误处理：记录日志，返回适当的 HTTP 状态码
- 配置通过 `settings` 全局实例访问
- 邮件发送器通过工厂函数创建，服务层只依赖抽象接口

### To-dos

- [ ] 更新 config.py 添加 Google Workspace 和邮件追踪配置字段
- [ ] 在 database/models.py 中添加 EmailStatus、EmailTrackingEventType 枚举和 Email、EmailTracking 模型
- [ ] 在 database/repository.py 中扩展 Repository 类，添加邮件相关的 CRUD 方法
- [ ] 创建 mail_manager/gmail_client.py，实现 GmailAPIClient 类（认证、发送、重试）
- [ ] 创建 mail_manager/utils.py，实现追踪像素生成和嵌入工具函数
- [ ] 创建 mail_manager/service.py，实现 MailManagerService 类（发送、批量、追踪、查询）
- [ ] 创建 schemas/mail_manager.py，定义所有请求和响应 Pydantic 模型
- [ ] 创建 mail_manager/router.py，实现所有 API 路由端点
- [ ] 更新 main.py 注册 mail_manager 路由
- [ ] 更新 pyproject.toml 添加 Google API 和 tenacity、Pillow 依赖