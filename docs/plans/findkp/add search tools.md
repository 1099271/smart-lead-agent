# 添加搜索工具集成

## 目标

在 FindKP 模块中集成 Serper.dev Search API 和 Google Search API，创建独立的搜索工具模块，支持批量搜索和异步调用。

## 实现步骤

### 1. 更新配置管理

- **文件**: `config.py`
- 添加 `GOOGLE_SEARCH_API_KEY: str` 配置项
- 添加 `GOOGLE_SEARCH_CX: str` 配置项（搜索引擎 ID）
- **文件**: `.env.example`
- 添加 `GOOGLE_SEARCH_API_KEY` 和 `GOOGLE_SEARCH_CX` 配置示例

### 2. 创建搜索工具模块结构

- **目录**: `core/search/`
- 创建 `__init__.py` - 导出统一接口（`BaseSearchProvider`, `SerperSearchProvider`, `GoogleSearchProvider`）
- 创建 `base.py` - 定义抽象基类 `BaseSearchProvider`
- 抽象方法：`async def search(query: str) -> List[SearchResult]`
- 抽象方法：`async def search_batch(queries: List[Dict[str, Any]]) -> Dict[str, List[SearchResult]]`
- 创建 `serper_provider.py` - 实现 Serper.dev API
- 类：`SerperSearchProvider(BaseSearchProvider)`
- 支持单个查询和批量查询
- 支持可选参数：`search_type`, `location`, `gl`, `hl`, `tbs`, `autocorrect`, `page`
- 使用 `httpx.AsyncClient` 进行异步调用
- 批量查询时，将多个查询打包成一个请求发送（Serper API 支持）
- 创建 `google_provider.py` - 实现 Google Search API
- 类：`GoogleSearchProvider(BaseSearchProvider)`
- 支持单个查询和批量查询（循环调用单个查询）
- 使用 `httpx.AsyncClient` 进行异步调用
- 参数：`query`, `num`, `start`

### 3. 重构 FindKP 服务

- **文件**: `findkp/service.py`
- 导入新的搜索提供者：`from core.search import SerperSearchProvider`
- 替换现有的 `search_serper` 方法为使用 `SerperSearchProvider`
- 更新 `find_kps` 方法中的搜索调用，使用新的搜索提供者实例
- 保持现有业务逻辑不变

### 4. 数据模型

- **文件**: `core/schemas.py`
- 使用现有的 `SearchResult` 模型（无需修改）

## 技术细节

### SerperSearchProvider 实现要点

- 批量搜索：将多个查询打包成数组，一次性发送到 `https://google.serper.dev/search`
- 请求格式：`POST` 请求，`payload` 为 JSON 数组，每个元素是一个查询参数字典
- 响应处理：解析返回的 JSON，提取 `organic` 字段中的结果
- 错误处理：捕获异常，记录日志，返回空列表或空字典

### GoogleSearchProvider 实现要点

- API 端点：`https://www.googleapis.com/customsearch/v1`
- 请求方式：`GET` 请求，查询参数 `q`, `key`, `cx`, `num`, `start`
- 批量搜索：循环调用单个查询，使用 `asyncio.gather` 并发执行
- 响应处理：解析返回的 JSON，提取 `items` 字段中的结果

### 异步设计

- 所有方法使用 `async def`
- 使用 `httpx.AsyncClient` 进行 HTTP 请求
- 批量查询时使用 `asyncio.gather` 并发执行（Google Search）

## 代码组织原则

- 遵循项目架构规范：工具放在 `core/search/` 目录
- 异步优先：所有方法使用异步
- 错误处理：完整的异常捕获和日志记录
- 配置管理：统一通过 `config.py` 访问配置

## 注意事项

- 保持向后兼容：不影响现有 `findkp/service.py` 的业务逻辑
- Serper API 批量查询的优势：一次请求多个查询，减少网络开销
- Google Search API 有每日免费配额限制（100 次），需要监控使用量
- 批量搜索返回格式：`Dict[str, List[SearchResult]]`，key 为查询关键词或查询参数字符串
