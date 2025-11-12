<!-- e1b3799c-2e62-4aa4-8ffc-934f06099b8d 6eba13e4-c2dc-477e-bd2b-33d099809162 -->
# Writer 模块重构 - 支持新 Prompt 模板

## 目标

将 Writer 模块从旧的 `W_VN_PROMPT`（JSON 输出）迁移到新的 `W_VN_MAIL_GENERATOR`（HTML 输出），支持两阶段输出解析和完整的 HTML 邮件内容生成。

## 核心变更

### 1. 配置管理扩展 (`config.py`)

- 添加 Writer 模块所需的新配置项：
  - `SENDER_NAME`: 发送者姓名
  - `SENDER_TITLE_EN`: 发送者职位（英文）
  - `SENDER_COMPANY`: 发送者公司
  - `WHATSAPP_NUMBER`: WhatsApp 号码
  - `IMAGE_URL_CUSTOMS_RESULT`: 海关数据截图 URL
  - `IMAGE_URL_FILTERS`: 筛选器截图 URL
  - `TRIAL_URL`: 试用链接（默认值：`https://www.tendata.com/data/?email1110`）

### 2. Schema 更新 (`schemas/writer.py`)

- 更新 `GeneratedEmail` 模型：
  - 保留现有字段（`contact_id`, `contact_name`, `contact_email`, `contact_role`）
  - `subject`: 从 HTML 中提取的越南语主题行（`Chủ đề: ...`）
  - `html_content`: 完整的 HTML 邮件内容（直接用于邮件发送）
  - 移除 `content_en` 和 `content_vn`（不再需要分离的文本内容）
  - 移除 `full_content`（由 `html_content` 替代）

### 3. Service 层重构 (`writer/service.py`)

#### 3.1 更新导入

- 将 `from prompts.writer.W_VN_PROMPT import W_VN_PROMPT` 改为 `from prompts.writer.W_VN_MAIL_GENERATOR import W_VN_MAIL_GENERATOR`

#### 3.2 重写 `_format_prompt` 方法

- 支持新 Prompt 所需的所有参数：
  - 公司信息：`company_en_name`, `company_local_name`, `industry_cn`, `positioning_cn`, `brief_cn`
  - 联系人信息：`full_name`, `role_en`, `department_cn`, `email`
  - 资产信息：`image_url_customs_result`, `image_url_filters`, `has_screenshot_customs_result`, `has_screenshot_filters`
  - 发送者信息：`sender_name`, `sender_title_en`, `sender_company`, `sender_email`
  - 其他：`trial_url`, `whatsapp_number`
- 从 `config.py` 的 `settings` 读取配置值
- 处理空值情况（使用空字符串作为默认值）

#### 3.3 重写 `_parse_email_response` 方法

- 处理两阶段输出：

  1. **分离 Stage A (YAML) 和 Stage B (HTML)**：通过识别 `<!DOCTYPE html>` 或 `<html>` 标签定位 HTML 部分
  2. **提取主题行**：从 HTML 中提取越南语主题行

     - 查找 `<p style="font-weight: bold; color: #0056b3;">Chủ đề: [VI Subject]</p>` 模式
     - 提取 `[VI Subject]` 部分作为 `subject`

  1. **提取完整 HTML**：保留从 `<!DOCTYPE html>` 开始到 `</html>` 结束的完整 HTML 内容

- 移除 JSON 解析逻辑（`_extract_json_from_text` 方法不再需要）

#### 3.4 添加 HTML 解析辅助方法

- `_extract_subject_from_html(html: str) -> str`: 从 HTML 中提取越南语主题行
- `_separate_stages(content: str) -> tuple[str, str]`: 分离 Stage A YAML 和 Stage B HTML

### 4. 环境变量模板更新 (`.env.example`)

- 添加新配置项的示例值：
  ```
  # Writer 模块配置
  SENDER_NAME="Your Name"
  SENDER_TITLE_EN="Business Development Manager"
  SENDER_COMPANY="Tendata"
  WHATSAPP_NUMBER="+84xxxxxxxxx"
  IMAGE_URL_CUSTOMS_RESULT="https://example.com/customs-result.png"
  IMAGE_URL_FILTERS="https://example.com/filters.png"
  TRIAL_URL="https://www.tendata.com/data/?email1110"
  ```


## 实施步骤

1. **更新配置** (`config.py`)

   - 在 `Settings` 类中添加新配置字段
   - 设置 `TRIAL_URL` 的默认值

2. **更新 Schema** (`schemas/writer.py`)

   - 修改 `GeneratedEmail` 类，移除旧字段，添加 `html_content`

3. **重构 Service** (`writer/service.py`)

   - 更新导入语句
   - 重写 `_format_prompt` 方法
   - 重写 `_parse_email_response` 方法
   - 添加 HTML 解析辅助方法
   - 移除不再需要的 JSON 解析方法

4. **更新环境变量模板** (`.env.example`)

   - 添加新配置项示例

## 技术细节

### 主题行提取正则表达式

```python
import re

# 提取越南语主题行
pattern = r'<p[^>]*>Chủ đề:\s*([^<]+)</p>'
match = re.search(pattern, html, re.IGNORECASE)
subject = match.group(1).strip() if match else ""
```

### HTML 分离逻辑

```python
def _separate_stages(content: str) -> tuple[str, str]:
    """分离 Stage A (YAML) 和 Stage B (HTML)"""
    html_start = content.find('<!DOCTYPE html>')
    if html_start == -1:
        html_start = content.find('<html>')
    
    if html_start != -1:
        yaml_part = content[:html_start].strip()
        html_part = content[html_start:].strip()
        return yaml_part, html_part
    return "", content
```

## 注意事项

- 所有配置项都从 `.env` 文件读取，使用 `settings` 全局实例访问
- 字段映射时，数据库字段直接使用（不进行翻译）
- HTML 内容完整保留，不做任何修改
- 如果主题行提取失败，使用空字符串作为默认值
- 保持向后兼容：确保现有 API 接口（`/writer/generate`）正常工作

## 测试要点

- 验证所有配置项正确读取
- 验证 Prompt 格式化包含所有必需参数
- 验证 HTML 解析正确提取主题行和完整内容
- 验证生成的 `GeneratedEmail` 对象结构正确
- 验证空值处理（NULL 字段使用空字符串）

### To-dos

- [ ] 在 config.py 中添加 Writer 模块所需的新配置项（SENDER_NAME, SENDER_TITLE_EN, SENDER_COMPANY, WHATSAPP_NUMBER, IMAGE_URL_CUSTOMS_RESULT, IMAGE_URL_FILTERS, TRIAL_URL）
- [ ] 更新 schemas/writer.py 中的 GeneratedEmail 模型，移除 content_en/content_vn/full_content，添加 html_content 字段
- [ ] 更新 writer/service.py 的导入语句，从 W_VN_PROMPT 改为 W_VN_MAIL_GENERATOR
- [ ] 重写 _format_prompt 方法，支持新 Prompt 所需的所有参数（公司信息、联系人信息、资产信息、发送者信息等）
- [ ] 添加 HTML 解析辅助方法：_separate_stages（分离 YAML 和 HTML）和 _extract_subject_from_html（提取越南语主题行）
- [ ] 重写 _parse_email_response 方法，处理两阶段输出（YAML + HTML），提取主题行和完整 HTML 内容
- [ ] 移除不再需要的 _extract_json_from_text 方法
- [ ] 更新 .env.example 文件，添加新配置项的示例值