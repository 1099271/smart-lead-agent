# CURSOR_WORK_25_11_12.md

## 2025-11-12 22:51 - 更新 Writer 服务以支持 WRITER_V3 本地化参数

## 2025-11-12 22:59 - 重构本地化配置：基于 Company.country 动态获取语言配置

### 需求描述

根据 `WRITER_V3.py` 中的新增本地化参数，更新 `service.py` 以支持动态本地化功能。WRITER_V3 引入了三个新的本地化参数，用于根据目标国家动态调整邮件的语言、称谓、结语和文化口吻。

### 实现逻辑

#### 1. 配置文件更新 (`config.py`)

在 `Settings` 类中添加了三个新的本地化配置项：

```python
# 本地化配置（用于 WRITER_V3）
TARGET_COUNTRY_NAME: str = "Vietnam"  # 目标国家名称（用于动态调整语言、称谓、结语和文化口吻）
TARGET_LANGUAGE_NAME: str = "Vietnamese"  # 目标语言名称
TARGET_LANGUAGE_CODE: str = "vi"  # 目标语言代码（ISO 639-1）
```

**设计说明**：

- 这些配置项提供了默认值（越南），确保向后兼容
- 可以通过环境变量 `.env` 文件覆盖这些默认值
- 使用 ISO 639-1 标准语言代码，便于国际化支持

#### 2. 服务层更新 (`writer/service.py`)

**2.1 更新 Prompt 导入**

```python
# 从 WRITER_V2 切换到 WRITER_V3
from prompts.writer.WRITER_V3 import BRIEF_PROMPT
```

**2.2 更新 `_format_prompt` 方法**

在 Prompt 格式化时添加了三个新的本地化参数：

```python
# 本地化上下文（WRITER_V3 新增）
target_country_name=settings.TARGET_COUNTRY_NAME or "Vietnam",
target_language_name=settings.TARGET_LANGUAGE_NAME or "Vietnamese",
target_language_code=settings.TARGET_LANGUAGE_CODE or "vi",
```

**2.3 更新截图提及格式**

根据 WRITER_V3 的要求，更新了 `screenshot_mention_en` 的格式：

```python
# 从 "as shown in the attached screenshots" 改为 "as shown in the screenshots below"
screenshot_mention_en="as shown in the screenshots below (customs results & smart filters)",
```

**2.4 移除不再需要的参数**

移除了 `screenshot_mention_vi` 参数，因为 WRITER_V3 要求 LLM 自动将英文的截图提及翻译为目标语言。

### 技术细节

#### 参数传递流程

```
配置文件 (config.py)
    ↓
Settings 实例 (settings)
    ↓
_format_prompt 方法
    ↓
BRIEF_PROMPT.format()
    ↓
LLM Prompt (包含本地化上下文)
```

#### 本地化参数的作用

1. **target_country_name**:

   - 用于动态调整商务礼仪（如对韩国/日本必须极其正式和谦逊）
   - 影响称谓和结语的生成

2. **target_language_name**:

   - 用于生成目标语言的主题行
   - 用于 LLM 自动翻译截图提及等文本

3. **target_language_code**:
   - 用于 HTML 的 `lang` 属性
   - 符合 HTML 标准，便于浏览器和辅助技术识别

### 影响范围

- ✅ **配置文件** (`config.py`): 新增三个配置项
- ✅ **服务层** (`writer/service.py`): 更新 Prompt 导入和格式化逻辑
- ✅ **向后兼容**: 提供默认值，不影响现有功能
- ✅ **可扩展性**: 通过环境变量可以轻松切换目标市场

### 使用示例

在 `.env` 文件中配置不同的目标市场：

```env
# 越南市场（默认）
TARGET_COUNTRY_NAME=Vietnam
TARGET_LANGUAGE_NAME=Vietnamese
TARGET_LANGUAGE_CODE=vi

# 或者切换到其他市场
# TARGET_COUNTRY_NAME=Thailand
# TARGET_LANGUAGE_NAME=Thai
# TARGET_LANGUAGE_CODE=th
```

### 注意事项

1. 确保 `.env` 文件中的配置项名称与 `Settings` 类中的字段名完全一致（大写）
2. 语言代码应遵循 ISO 639-1 标准
3. 国家名称建议使用英文标准名称，便于 LLM 理解

---

## 2025-11-12 22:59 - 重构本地化配置：基于 Company.country 动态获取语言配置

### 需求描述

重构本地化配置系统，从基于全局配置改为基于公司所在国家动态获取语言配置。主要改进：

1. 维护一套国家-语言映射配置（国家名称 → 语言名称 + ISO 语言代码）
2. 在 Company 数据结构中增加 `country` 字段，不允许为空
3. 在生成 Prompt 时从 `company.country` 获取国家，然后根据映射配置读取对应的语言名称和代码

### 实现逻辑

#### 1. 创建国家-语言映射配置 (`config.py`)

**移除旧的单个配置项**，改为维护一个完整的国家-语言映射字典：

```python
# 国家-语言映射配置（用于 WRITER_V3 本地化）
# 格式: {国家名称: {"language_name": "语言名称", "language_code": "ISO 639-1 代码"}}
COUNTRY_LANGUAGE_MAP: Dict[str, Dict[str, str]] = {
    "Vietnam": {
        "language_name": "Vietnamese",
        "language_code": "vi",
    },
    "Thailand": {
        "language_name": "Thai",
        "language_code": "th",
    },
    # ... 支持 20+ 个国家
}
```

**添加辅助函数**：

```python
def get_language_config(country_name: str) -> Dict[str, str]:
    """
    根据国家名称获取对应的语言配置

    Returns:
        包含 language_name 和 language_code 的字典
        如果国家不存在，返回越南的默认配置
    """
    return COUNTRY_LANGUAGE_MAP.get(
        country_name,
        COUNTRY_LANGUAGE_MAP["Vietnam"],  # 默认返回越南配置
    )
```

**设计优势**：

- 集中管理：所有国家-语言映射在一个地方维护
- 易于扩展：添加新国家只需在字典中添加一项
- 容错处理：未知国家自动回退到默认配置（越南）
- 类型安全：使用类型提示确保数据结构正确

#### 2. 数据库模型更新 (`database/models.py`)

在 `Company` 模型中添加 `country` 字段：

```python
class Company(Base):
    # ... 其他字段
    country = Column(String(100), nullable=False, index=True)  # 公司所在国家（用于本地化）
    # ... 其他字段
```

**字段特性**：

- `nullable=False`: 不允许为空，确保每个公司都有国家信息
- `index=True`: 添加索引以提高按国家查询的性能

#### 3. 数据库迁移脚本 (`database/sql/007_add_company_country.sql`)

创建迁移脚本添加 `country` 字段：

```sql
-- 添加 country 字段
ALTER TABLE companies
ADD COLUMN country VARCHAR(100) NOT NULL DEFAULT 'Vietnam' COMMENT '公司所在国家（用于本地化）' AFTER domain;

-- 添加索引以提高查询性能
CREATE INDEX idx_country ON companies(country);
```

**注意事项**：

- 使用 `DEFAULT 'Vietnam'` 确保现有数据有默认值
- 如果表中已有数据，建议手动更新 `country` 字段的值

#### 4. 仓储层更新 (`database/repository.py`)

更新 `get_or_create_company` 方法，添加 `country` 参数：

```python
async def get_or_create_company(
    self,
    name: str,
    local_name: Optional[str] = None,
    country: str = "Vietnam",  # 新增参数，默认越南
) -> models.Company:
    # 创建时保存 country
    if not company:
        company = models.Company(
            name=name, local_name=local_name, country=country
        )
    # 如果已存在但 country 为空或需要更新，则更新
    elif not company.country or (country and company.country != country):
        company.country = country
        await self.db.commit()
        await self.db.refresh(company)
    return company
```

#### 5. 服务层更新 (`writer/service.py`)

更新 `_format_prompt` 方法，从 `company.country` 动态获取语言配置：

```python
from config import settings, get_language_config

def _format_prompt(self, company: Company, contact: Contact) -> str:
    # 从 company.country 获取本地化配置
    country_name = company.country or "Vietnam"
    language_config = get_language_config(country_name)
    target_language_name = language_config["language_name"]
    target_language_code = language_config["language_code"]

    prompt = BRIEF_PROMPT.format(
        # ... 其他参数
        # 本地化上下文（从 company.country 动态获取）
        target_country_name=country_name,
        target_language_name=target_language_name,
        target_language_code=target_language_code,
        # ... 其他参数
    )
```

**关键改进**：

- 不再依赖全局配置，而是根据每个公司的国家动态获取
- 支持多市场：不同国家的公司可以自动使用对应的语言配置
- 容错处理：如果 `company.country` 为空，使用默认值 "Vietnam"

#### 6. FindKP 服务更新 (`findkp/service.py`)

更新 `_search_and_save_company_info` 方法，传递 `country` 参数：

```python
company = await repo.get_or_create_company(
    company_name_en,
    local_name=company_name_local,
    country=country or "Vietnam",  # 传递国家参数
)
```

### 数据流程

```
API 请求 (company_name_en, company_name_local, country)
    ↓
FindKPService._search_and_save_company_info()
    ↓
Repository.get_or_create_company(name, local_name, country)
    ↓
创建/更新 Company 记录 (包含 country 字段)
    ↓
WriterService._format_prompt(company, contact)
    ↓
从 company.country 获取国家名称
    ↓
get_language_config(country_name) 查询映射表
    ↓
获取 language_name 和 language_code
    ↓
填充到 Prompt 模板
```

### 支持的国家列表

当前支持 20+ 个国家，包括：

- **东南亚**: Vietnam, Thailand, Indonesia, Malaysia, Philippines, Singapore
- **东亚**: Japan, South Korea, China, Taiwan
- **南亚**: India
- **欧洲**: United Kingdom, France, Germany, Italy, Spain
- **美洲**: United States, Canada, Mexico, Brazil
- **大洋洲**: Australia

### 修改文件清单

1. ✅ `config.py` - 创建国家-语言映射配置和辅助函数
2. ✅ `database/models.py` - 在 Company 模型中添加 country 字段
3. ✅ `database/sql/007_add_company_country.sql` - 创建数据库迁移脚本
4. ✅ `database/repository.py` - 更新 get_or_create_company 方法
5. ✅ `writer/service.py` - 更新 \_format_prompt 方法，从 company.country 获取配置
6. ✅ `findkp/service.py` - 更新调用处，传递 country 参数

### 技术优势

1. **灵活性**: 每个公司可以有不同的国家配置，支持多市场运营
2. **可维护性**: 国家-语言映射集中管理，易于更新和扩展
3. **类型安全**: 使用类型提示和字典结构，减少配置错误
4. **容错性**: 未知国家自动回退到默认配置，不会导致系统崩溃
5. **性能**: country 字段添加索引，提高查询效率

### 迁移注意事项

1. **数据库迁移**: 执行 SQL 脚本前，确保备份数据库
2. **现有数据**: 如果表中已有公司数据，需要手动更新 `country` 字段
3. **默认值**: 新创建的公司如果没有指定 country，默认使用 "Vietnam"
4. **向后兼容**: `get_or_create_company` 方法的 `country` 参数有默认值，不影响现有调用

### 使用示例

```python
# 创建越南公司
company = await repo.get_or_create_company(
    name="ABC Company",
    local_name="Công ty ABC",
    country="Vietnam"
)

# 创建泰国公司
company = await repo.get_or_create_company(
    name="XYZ Corp",
    local_name="บริษัท XYZ",
    country="Thailand"
)

# 生成邮件时自动使用对应的语言配置
# Vietnam → Vietnamese (vi)
# Thailand → Thai (th)
```
