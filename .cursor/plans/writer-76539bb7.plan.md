<!-- 76539bb7-b0dc-4227-aca8-5ab463e08cf8 b6cccb92-eefb-43db-a323-7df47207526d -->
# Writer 模块实现计划

## 目标

实现 Writer 模块，提供 API 接口根据公司信息查询联系人并生成营销邮件。

## 架构设计

采用三层架构：Router → Service → Repository（复用现有）

## 实施步骤

### 1. 创建数据模型 (schemas/writer.py)

- 创建 `GenerateEmailRequest`：支持 `company_id` 或 `company_name`
- 创建 `GeneratedEmail`：包含 `contact_id`, `contact_name`, `contact_email`, `contact_role`, `subject`, `content_en`, `content_vn`, `full_content`
- 创建 `GenerateEmailResponse`：继承 `BaseResponse`，包含 `company_id`, `company_name`, `emails` 列表

### 2. 创建服务层 (writer/service.py)

- 实现 `WriterService` 类
- 初始化 LLM：使用 `get_llm()` 工厂函数
- 实现 `generate_emails()` 主方法：
  - 根据 `company_id` 或 `company_name` 查询公司
  - 调用 `get_contacts_by_company()` 获取联系人
  - 调用 `_deduplicate_contacts()` 去重（按邮箱，保留置信度最高）
  - 过滤出有邮箱的联系人
  - 并发调用 `_generate_email_for_contact()` 为每个联系人生成邮件
  - 返回邮件列表
- 实现 `_deduplicate_contacts()`：
  - 按邮箱（小写）去重
  - 保留置信度最高的联系人
  - 置信度相同时保留最新的（按 `created_at`）
- 实现 `_format_prompt()`：
  - 导入 `prompts.writer.W_VN_PROMPT.W_VN_PROMPT`
  - 格式化模板，填充公司信息和联系人信息
  - 在 Prompt 末尾添加 JSON 格式要求（subject, content_en, content_vn）
- 实现 `_generate_email_for_contact()`：
  - 异步调用 LLM
  - 使用 `_parse_email_response()` 解析响应
  - 错误处理：记录日志，返回 None
- 实现 `_parse_email_response()`：
  - 使用 `_extract_json_from_text()` 提取 JSON（复用 FindKP 的逻辑）
  - 解析 JSON 获取 subject, content_en, content_vn
  - 组合生成 full_content（英文 + 越南语）
  - 容错处理：如果解析失败，尝试从纯文本中提取

### 3. 创建路由层 (writer/router.py)

- 创建 `APIRouter`，prefix="/writer", tags=["Writer"]
- 创建服务实例
- 实现 `POST /writer/generate` 端点：
  - 接收 `GenerateEmailRequest`
  - 调用 `service.generate_emails()`
  - 返回 `GenerateEmailResponse`
  - 错误处理：404（公司不存在），500（其他错误）
- 实现 `GET /writer/health` 健康检查端点

### 4. 注册路由 (main.py)

- 导入 `writer.router`
- 使用 `app.include_router()` 注册路由
- 更新根端点返回信息，添加 Writer 模块

### 5. 复用代码

- 复用 `findkp/service.py` 中的 `_extract_json_from_text()` 方法（或提取为工具函数）
- 复用 `database/repository.py` 中的 `get_contacts_by_company()` 方法
- 复用 `database/repository.py` 中的 `get_company_by_name()` 方法（如不存在则创建 `get_company_by_id()`）

## 技术细节

### Prompt 增强

在 `W_VN_PROMPT` 末尾添加 JSON 格式要求：

```
请以 JSON 格式返回邮件内容，包含以下字段：
{
  "subject": "邮件主题",
  "content_en": "英文邮件正文",
  "content_vn": "越南语邮件正文"
}
```

### 去重逻辑

```python
email_map: Dict[str, Contact] = {}
for contact in contacts:
    if not contact.email:
        continue
    email_lower = contact.email.lower()
    if email_lower not in email_map:
        email_map[email_lower] = contact
    else:
        # 比较置信度，保留更高的
        existing_score = email_map[email_lower].confidence_score or 0.0
        current_score = contact.confidence_score or 0.0
        if current_score > existing_score or \
           (current_score == existing_score and contact.created_at > email_map[email_lower].created_at):
            email_map[email_lower] = contact
```

### 并发处理

使用 `asyncio.gather()` 并发生成邮件，无并发限制：

```python
tasks = [
    self._generate_email_for_contact(company, contact)
    for contact in deduplicated_contacts
]
results = await asyncio.gather(*tasks, return_exceptions=True)
emails = [r for r in results if r is not None and not isinstance(r, Exception)]
```

## 文件清单

- 新建：`schemas/writer.py`
- 新建：`writer/service.py`
- 新建：`writer/router.py`
- 修改：`main.py`（注册路由）
- 可选：提取 `_extract_json_from_text()` 为共享工具函数

## 测试要点

1. 公司不存在 → 404
2. 公司无联系人 → 返回空列表
3. 联系人无邮箱 → 跳过
4. 邮箱重复 → 保留置信度最高的
5. LLM 调用失败 → 记录日志，跳过该联系人，继续处理其他
6. 批量生成 → 验证所有邮件都正确生成

### To-dos

- [ ] 创建 schemas/writer.py，定义 GenerateEmailRequest, GeneratedEmail, GenerateEmailResponse 模型
- [ ] 创建 writer/service.py，实现 WriterService 类，包含去重、Prompt 格式化、LLM 调用、响应解析等核心逻辑
- [ ] 创建 writer/router.py，实现 POST /writer/generate 和 GET /writer/health 端点
- [ ] 在 main.py 中注册 writer 路由，更新根端点信息
- [ ] 在 W_VN_PROMPT 末尾添加 JSON 格式要求，确保 LLM 返回结构化数据