# AI Agent 插件开发指南

> **面向读者**: AI Agent（Claude、GPT 等）
> **适用场景**: 用户要求为其已有的真实数据库编写 Business Capability Gateway 插件
> **参考实现**: `plugins/amazon_db/` — 基于真实 SQLite 数据库的完整插件
> **最后更新**: 2026-06-13

---

## 一、核心原则

**业务逻辑从数据结构出发，而不是从模板出发。**

不要一上来就复制 mock 插件的模板开始写代码。你必须先理解用户的数据库里实际存了什么，再和用户确认他想要什么分析能力，最后才按照项目规范落地。

正确的开发顺序：

```
理解真实数据结构 → 确认用户需求 → 澄清技术决策 → 按规范实现
```

---

## 二、前置工作（必须先做）

### 2.1 全面理解数据库结构

在写任何一行代码之前，你必须完成以下调查：

1. **数据库类型与连接方式**
   - 是什么数据库？SQLite / PostgreSQL / MySQL / 其他？
   - 数据库文件路径或连接字符串是什么？
   - 项目中是否已有 ORM 模型定义（如 SQLAlchemy）？
   - 是否需要安装额外的数据库驱动？

2. **完整了解每张表**
   - 列出所有表名和行数
   - 对每张表，逐列确认：列名、类型、含义、是否可空、默认值
   - 表之间的关联关系（外键、JOIN 逻辑）
   - 哪些列有索引（影响查询性能）

3. **数据抽样验证**
   - 对每张表抽样几条数据，确认实际存储格式
   - 例如：`rating` 是 0-5 的浮点数还是 1-100 的整数？`price` 单位是美元还是美分？
   - 不要假设 — 必须实际查询验证

**示例输出（你应该向用户展示的调查结果）**：

```
数据库: SQLite, database/database.db
表:
  product (18,831 行): asin, title, price, rating, review_count, monthly_sales,
    sales_amount, fba_fee, gross_margin, parent_category, parent_category_rank,
    sub_category, sub_category_rank, launch_date, launch_days, is_deleted, ...
  product_keyword (28,900 行): asin, sheet_name, category, keyword
  product_variant (189 行): parent_asin, child_asin, price, monthly_sales, ...
  monthly_sales (0 行): asin, month, sales, revenue
```

### 2.2 确认用户需求

数据库结构搞清楚后，**必须向用户确认**他想通过插件实现什么能力。不要自己替用户做决定。

**你必须向用户提出的问题**：

1. **入口查询**：用户希望通过什么方式检索数据？
   - 关键词搜索？（涉及哪些表的哪些列？）
   - 按类目/标签筛选？
   - 按 ID 精确查找？
   - 是否支持组合查询？

2. **分析能力**：用户希望从数据中提取什么洞察？
   - 市场分析？（规模、均价、竞争度）
   - 利润分析？（毛利率、费用结构）
   - 趋势分析？（时间维度）
   - 排名分析？（类目排名、竞品对比）
   - 机会发现？（低竞争高利润的产品）

3. **输出格式**：用户期望什么形式的输出？
   - 结构化 JSON（默认）
   - 图表数据
   - 报告文本

4. **数据范围**：是全量数据分析，还是给定时间范围/类目范围的分析？

**向用户确认需求时，用自然语言描述你理解的能力清单，让用户确认或修正。**

### 2.3 澄清关键技术决策

在开始编码前，以下问题**必须和用户逐一确认**：

| # | 决策点 | 需要确认的内容 |
|---|--------|---------------|
| 1 | **数据库连接** | 连接字符串/路径如何获取？用环境变量还是硬编码相对路径？ |
| 2 | **ORM 选型** | 用项目已有的 ORM（SQLAlchemy）还是原生 SQL？如果已有模型定义，放哪里？ |
| 3 | **是否建新表** | 插件是否允许在数据库中创建新表（如缓存表、分析结果表）？ |
| 4 | **是否修改数据** | 插件是只读分析，还是需要写入/更新数据？ |
| 5 | **线程安全** | 网关用 ThreadPoolExecutor 并行调度节点，数据库连接是否支持多线程？SQLite 需要 `check_same_thread=False` |
| 6 | **数据量** | 单表多少行？全量加载到内存是否可行（> 10 万行建议走 SQL 分页）？ |
| 7 | **性能要求** | 单次请求预期响应时间？是否需要缓存？ |
| 8 | **数据敏感度** | Agent 能接触什么级别的数据？是否需要脱敏？ |
| 9 | **插件命名** | 新建独立插件还是替换/升级现有插件？插件名是什么？ |
| 10 | **增量开发** | 一次性实现全部节点，还是先做 MVP 跑通再扩展？ |

**这些问题的答案将直接影响架构设计。不要跳过。**

---

## 三、编码实现

前置工作全部完成后，才开始按项目规范编写代码。

### 3.1 项目规范速览

编写插件时需遵循以下规范（详细参考 `docs/插件开发文档.md`）：

**目录结构**：
```
plugins/<plugin_name>/
├── plugin.py              # register() 入口
├── artifact_types.py      # ArtifactType 层次
├── nodes/                 # Node 实现
│   ├── source_nodes.py    # 入口节点（无 input_specs）
│   ├── transform_nodes.py # 转换节点（过滤/排序）
│   └── sink_nodes.py      # 分析/输出节点
├── services/              # 纯业务逻辑（不接触 Artifact）
└── repository/            # 数据访问层
    ├── db.py              # 数据库连接（可选）
    ├── models.py          # ORM 模型（可选）
    └── xyz_repository.py  # 数据查询
```

**三层严格分离**：
```
Node 层     →  拆包 Artifact → 调用 Service → 打包返回 Artifact
Service 层  →  接收 ProductCollection → 返回 dict（纯 Python，不 import Artifact）
Repository 层 → SQL 查询 → 返回 ProductCollection（不包含业务逻辑）
```

**Node 协议声明**：每个 Node 声明三样：
- `input_specs`：我需要消费哪些 Artifact
- `output_spec`：我产出什么 Artifact
- `parameter_specs`：我接受哪些字面量参数

**关键约束**：
- Node 无状态，每次 `execute()` 独立执行
- Node 不直接调用其他 Node
- 不修改 `core/` 目录任何代码
- 插件放在 `plugins/` 下即可被自动发现
- `plugin.py` 中必须有 `register()` 函数，调用 `register_nodes()`

### 3.2 实现顺序

**按以下顺序实现，每步验证完再做下一步**：

```
Phase 1: 数据库连接层
  ├── repository/db.py     — engine + session 工厂
  ├── repository/models.py — ORM 模型（如果有）
  └── 验证：能成功连接数据库并查询

Phase 2: 数据容器
  ├── 定义 Product dataclass（映射真实表列）
  ├── 实现 ProductCollection（链式过滤 + 聚合方法）
  ├── 实现 ProductRepository（SQL 查询方法）
  └── 验证：每个查询方法返回正确的数据

Phase 3: 类型协议
  ├── artifact_types.py — 定义业务类型层次
  └── 验证：类型兼容关系正确

Phase 4: 业务逻辑
  ├── services/xxx_service.py — 纯 Python 分析算法
  └── 验证：输入 ProductCollection，输出正确的 dict

Phase 5: Node 实现
  ├── nodes/source_nodes.py    — 入口节点
  ├── nodes/transform_nodes.py — 过滤/排序节点
  ├── nodes/sink_nodes.py      — 分析/输出节点
  └── 验证：每个 Node 的协议声明正确

Phase 6: 注册 + 端到端测试
  ├── plugin.py — register() 函数
  ├── 启动服务，验证插件被自动发现
  ├── curl /plugins 确认节点已注册
  └── POST /execute 执行真实图，验证端到端
```

### 3.3 参考实现

完整参考实现见 `plugins/amazon_db/`，这是一个基于真实 SQLite 数据库（18,831 行 product + 28,900 行 product_keyword）的 Amazon 商品分析插件。

关键文件速查：

| 想知道怎么…… | 看这个文件 |
|-------------|-----------|
| 连接 SQLite 数据库 | `plugins/amazon_db/repository/db.py` |
| 定义 ORM 模型 | `plugins/amazon_db/repository/models.py` |
| 写 SQL 查询 + 内存过滤容器 | `plugins/amazon_db/repository/product_repository.py` |
| 定义 ArtifactType 层次 | `plugins/amazon_db/artifact_types.py` |
| 写纯业务分析逻辑 | `plugins/amazon_db/services/market_service.py` |
| 实现图入口节点（无输入） | `plugins/amazon_db/nodes/source_nodes.py` |
| 实现过滤/排序节点 | `plugins/amazon_db/nodes/transform_nodes.py` |
| 实现分析/输出节点 | `plugins/amazon_db/nodes/sink_nodes.py` |
| 注册所有节点 | `plugins/amazon_db/plugin.py` |

### 3.4 Session 管理

网关是单线程顺序执行，但为了保证每次 `execute()` 调用的独立性，Session 仍应在每个查询方法内部创建和关闭：

```python
class ProductRepository:
    def search_by_keyword(self, keyword: str) -> ProductCollection:
        session = get_session()       # 每次查询新建 session
        try:
            rows = session.query(...).all()
            return ProductCollection([Product.from_orm(r) for r in rows])
            # ↑ 结果完全物化为普通 Python 对象，不携带 ORM 状态
        finally:
            session.close()            # 必须关闭
```

- ❌ 不要在 `__init__` 中创建 Session 然后复用 — 多次 `execute()` 调用会拿到过期连接
- ❌ 不要在 Artifact 中传递 ORM 对象 — Artifact 应只包含普通 Python 对象
- ❌ 不要使用模块级全局 Session

---

## 四、完整决策检查清单

在和用户沟通及实现过程中，确认以下每一项都有明确答案：

### 数据库理解
- [ ] 数据库类型和连接方式已确认
- [ ] 所有表名和行数已列出
- [ ] 每张表的关键列（名称、类型、含义）已理解
- [ ] 表间关联关系已明确
- [ ] 实际数据抽样已验证

### 用户需求
- [ ] 入口查询方式已确认（关键词 / 类目 / ID / 组合）
- [ ] 分析能力清单已确认
- [ ] 输出格式已确认
- [ ] 数据范围已确认

### 技术决策
- [ ] 数据库连接方式已确定
- [ ] ORM 方案已选定
- [ ] 是否允许建新表已明确
- [ ] 读写权限已明确
- [ ] 数据量方案（全量内存 / SQL 分页）已确定
- [ ] 插件名称已确定
- [ ] 开发模式（MVP 渐进 / 全量）已确定

### 实现验证
- [ ] Phase 1 数据库连接已验证
- [ ] Phase 2 数据查询已验证
- [ ] Phase 3 类型协议已验证
- [ ] Phase 4 业务逻辑已验证
- [ ] Phase 5 Node 协议已验证
- [ ] Phase 6 端到端图执行已验证
