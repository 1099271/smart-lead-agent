---

### 🌍 海外公司邮箱搜索策略

| 策略编号                 | 搜索语句（q 参数示例）                                                                                   | 搜索目标说明                                        | 使用建议（适用场景）                                    |
| ------------------------ | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------- |
| **A1 官网邮箱直搜**      | `site:DOMAIN "@"+DOMAIN`                                                                                 | 查找官网所有公开邮箱                                | 起始查询；命中率最高，常拿到 info@、sales@ 等官方邮箱   |
| **A2 联系页聚焦**        | `site:DOMAIN (inurl:contact OR inurl:contact-us OR inurl:about) "@"+DOMAIN`                              | 搜索“Contact / About”页中的邮箱                     | 企业官网结构规范时优先执行；常含业务、客服、销售邮箱    |
| **A3 文件类邮箱搜索**    | `site:DOMAIN filetype:pdf "@"+DOMAIN`                                                                    | 提取官网 PDF（catalog、spec sheet、report）内的邮箱 | 制造商、出口企业常在产品目录或报价文件中包含邮箱        |
| **B1 岗位/职能聚焦**     | `site:DOMAIN ("sales" OR "business development" OR "procurement" OR "purchasing" OR "buyer") "@"+DOMAIN` | 搜索与采购/销售相关的岗位邮箱                       | 精准锁定采购或销售部门邮箱；海外工厂、贸易公司命中率高  |
| **B2 通用联系方式补充**  | `site:DOMAIN ("email" OR "contact" OR "reach us" OR "get in touch") "@"+DOMAIN`                          | 捕捉所有“联系方式”类页面的邮箱                      | 兜底策略，用于提取通用联系邮箱（info@、office@等）      |
| **C1 LinkedIn 采购岗位** | `site:linkedin.com "COMPANY_FULL" ("procurement" OR "purchasing" OR "buyer")`                            | 在 LinkedIn 上搜索采购相关联系人                    | 获取采购经理姓名，用于后续邮箱模式生成                  |
| **C2 LinkedIn 销售岗位** | `site:linkedin.com "COMPANY_FULL" ("sales" OR "business development")`                                   | 查找销售负责人或业务拓展人员                        | 获取销售团队姓名，结合域名生成邮箱                      |
| **D1 邮箱验证搜索**      | `"candidate@DOMAIN"`                                                                                     | 验证猜测邮箱是否出现在公开网页中                    | 与邮箱模式生成配合，用于确认 guessed email 是否真实存在 |
| **D2 邮箱模式生成**      | （程序内部逻辑）`first.last@DOMAIN`, `first@DOMAIN`, `f.last@DOMAIN` 等                                  | 通过姓名 + 域名自动生成邮箱候选                     | 结合 LinkedIn 姓名结果使用，验证后输出最可信邮箱        |

---

### ⚙️ 推荐执行顺序（API 调度逻辑）

| 阶段                   | 策略组       | 目的                  | 说明                             |
| ---------------------- | ------------ | --------------------- | -------------------------------- |
| **阶段 1：官方渠道**   | A1 + A2 + A3 | 快速抓取官网真实邮箱  | 通常能拿到最干净的官方地址       |
| **阶段 2：岗位定位**   | B1           | 聚焦采购 / 销售关键词 | 高命中采购或销售负责人邮箱       |
| **阶段 3：全局补扫**   | B2           | 兜底补充通用邮箱      | 当前两步无结果时执行             |
| **阶段 4：社媒反查**   | C1 + C2      | 获取姓名与职位        | 生成并验证真实联系人邮箱         |
| **阶段 5：验证与生成** | D1 + D2      | 邮箱验证与猜测        | 验证候选邮箱有效性后输出最终结果 |

---

### 🌐 海外关键词补充（可动态加入搜索语句）

| 语言     | 采购类关键词                             | 销售类关键词                                            |
| -------- | ---------------------------------------- | ------------------------------------------------------- |
| 英文     | procurement, purchasing, buyer, sourcing | sales, business development, account manager, marketing |
| 西班牙语 | compras, comprador, adquisiciones        | ventas, desarrollo de negocios                          |
| 越南语   | mua hàng, thu mua                        | bán hàng, phát triển kinh doanh                         |

> ✅ 在多语言国家（如越南、泰国、印尼、拉美），可动态添加对应语言关键词组合，提高召回率。

---

### 📊 输出建议（程序结果结构）

| 字段          | 示例值                                     | 说明                                     |
| ------------- | ------------------------------------------ | ---------------------------------------- |
| `email`       | `sales@company.com`                        | 抓取或推断的邮箱地址                     |
| `role`        | `sales / procurement / general`            | 根据上下文或岗位关键词分类               |
| `confidence`  | 0–100                                      | 置信度评分（来源 + 岗位匹配 + 验证结果） |
| `source_url`  | `https://company.com/contact`              | 邮箱所在页面或验证来源                   |
| `source_type` | `official / linkedin / guessed / verified` | 邮箱来源类型                             |
| `language`    | `en / es / vi / multi`                     | 搜索时使用的语言                         |

---

是否希望我接下来帮你把这一版转成
👉 **可直接调用 Google Search API 的 JSON schema（包含这些策略模板 + 动态变量）**？
你可以直接把公司名和域名传入程序就能自动循环查询。
