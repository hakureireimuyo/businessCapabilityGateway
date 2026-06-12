# 系统使用指南——Agent 视角

> 本文档面向使用本系统的 AI Agent，描述如何通过 Python SDK 或 HTTP 接口编排业务分析能力。

---

## 一、系统是什么

Business Capability Gateway 是一个**业务分析中间件**。Agent 调用它来执行结构化的数据分析——搜索产品、统计指标、生成报告，然后 Agent 拿到结果后自行做推理和综合判断。

**系统不做 AI 推理**——它只产出结构化数据。

```
Agent（你）
  │
  ├─ 编写 Python 脚本，描述分析流程
  │    或
  ├─ 通过 HTTP POST 提交脚本
  │
  ▼
Gateway 执行 DAG → 返回结构化结果
  │
  ▼
Agent（你）拿到数据，自行推理
```

---

## 二、核心概念

### 2.1 图（Graph）

一次分析是一个**有向无环图（DAG）**。每个节点产出数据，后续节点消费它。没有依赖的节点自动并行执行。

```
keyword_search ──→ sales_analysis ──┐
       │                            ├──→ chart_output
       └──→ review_analysis ────────┘
```

Agent 用 Python 代码描述这张图，Gateway 负责校验、拓扑排序、并行执行。

### 2.2 插件（Plugin）

每个插件代表一个业务领域（如 Amazon）。**一次执行只能使用一个插件**，数据不会跨插件混合。

如需跨领域综合（如 Amazon + TikTok），Agent 多次调用不同插件，自行综合结果。

### 2.3 Artifact 类型层次

节点之间传递的数据有类型：

| 层次 | 含义 | 示例 |
|------|------|------|
| RawData（原始数据） | 从数据库查出的集合 | `ProductCollection` |
| Metric（指标） | 对原始数据的统计结果 | `SalesMetrics`、`CompetitionMetrics` |
| Aggregation（聚合） | 组装多个指标的结果 | `MarketSignal` |

流向: RawData → Metric → Aggregation。类型不匹配会在 `execute()` 前被检测并报错。

---

## 三、Python SDK

### 3.1 Graph 对象

```python
from gateway import Graph

g = Graph(plugin="amazon")   # 进入 Amazon 业务域
```

`Graph` 的方法对应插件注册的节点。**调用方法不会执行任何实际逻辑**——只注册节点和依赖关系。返回的是占位符对象（`ArtifactPlaceholder`），可在后续调用中引用。

### 3.2 编排流程

```python
from gateway import Graph

g = Graph(plugin="amazon")

# 1. 获取数据
products = g.keyword_search(keyword="halloween garland")

# 2. 分支分析（并行执行）
sales = g.sales_analysis(products=products)
reviews = g.review_analysis(products=products)

# 3. 汇合
market = g.market_score(sales=sales, reviews=reviews)

# 4. 多输出
g.output(g.chart_output(market=market))
g.output(g.report_output(market=market))

# 5. 执行
result = g.execute()
# result = {"chart": {...}, "report": {...}}
```

### 3.3 调用规则

| 规则 | 说明 |
|------|------|
| 参数全部命名 | 禁止位置参数。`products=products`，不是 `products` |
| Artifact 引用 | 直接用 Python 变量，不需要 `@` 前缀 |
| 字面量参数 | 直接写值：`keyword="halloween"`, `price_lt=100` |
| 必须有赋值 | 每次调用必须有变量接收：`x = g.some_node(...)` |
| 声明输出 | 最终产物用 `g.output(...)` 标记 |
| 显式执行 | 调用 `g.execute()` 才真正运行 |

### 3.4 禁止的写法

**不要写控制流。** 这些语法会导致执行结果不符合预期：

```python
# ❌ 禁止：条件执行
if score > 80:
    g.chart_output(market=market)

# ❌ 禁止：循环
for kw in keywords:
    g.keyword_search(keyword=kw)

# ❌ 禁止：列表推导
results = [g.keyword_search(keyword=kw) for kw in keywords]
```

原因：`Graph` 方法返回的是占位符对象，不是真实数据。`score > 80` 对占位符无意义，会报 TypeError。循环和列表推导中每次调用都是注册新节点，形成不可预期的图结构。

**正确做法：**

- 条件过滤 → 使用 `filter` 节点（见 §3.5）
- 多条独立分析 → 多次调用 `g.execute()`，在外部做综合
- 循环遍历 → Agent 循环内每次新建 `Graph`、调用 `execute`

### 3.5 条件过滤（替代 if）

**简单 AND 条件**——通过 filter 节点的参数：

```python
filtered = g.filter_products(
    products=products,
    price_lt=100,
    rating_gt=4.0
)
```

节点参数间天然为 AND 语义。单一字面量条件放在需要的节点参数中即可（如 `keyword_search(keyword="...", min_price=50)`）。

**复杂条件（OR、嵌套）**——通过图结构组合：

```python
# 需求: (price < 100 OR rating > 4) AND (sales > 500)

# OR：两条并行分支
c1 = g.filter_price(products=products, price_lt=100)
c2 = g.filter_rating(products=products, rating_gt=4.0)
candidates = g.merge_sets(a=c1, b=c2)

# AND：串联
final = g.filter_sales(products=candidates, sales_gt=500)
```

---

## 四、HTTP 接口

### 4.1 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/plugins` | 已加载的插件列表 |
| GET | `/plugins/<name>/actions` | 某插件的所有节点定义 |
| POST | `/execute` | **执行分析**，body 为 Python 脚本文本 |

### 4.2 执行请求

```
POST /execute
Content-Type: text/plain

from gateway import Graph

g = Graph(plugin="amazon")

products = g.keyword_search(keyword="halloween garland")
sales = g.sales_analysis(products=products)
market = g.market_analysis(products=products)

g.output(g.chart_output(market=market))

result = g.execute()
```

### 4.3 返回格式

成功：
```json
{
    "success": true,
    "data": {
        "chart": {
            "market_size": 523,
            "avg_price": 18.7,
            "competition_score": 72
        }
    },
    "message": "Pipeline executed successfully"
}
```

失败：
```json
{
    "success": false,
    "error": {
        "code": "TYPE_MISMATCH",
        "message": "Type mismatch: sales_analysis expects ProductCollection, got SalesMetrics"
    }
}
```

---

## 五、节点能力目录

Agent 规划分析流程前，先查 `/plugins/<name>/actions` 了解可用节点。

### 5.1 节点定义格式

```json
{
    "name": "sales_analysis",
    "plugin": "amazon",
    "description": "统计产品销量指标：平均销量、增长率、销量分布",
    "inputs": {"products": "ProductCollection"},
    "output_key": "sales_metrics",
    "output_type": "SalesMetrics",
    "parameters": {
        "min_sales": {"type": "int", "required": false, "default": 0}
    }
}
```

### 5.2 Amazon 插件能力清单（当前）

#### 数据获取

| 节点 | 说明 | 输入 | 输出 | 参数 |
|------|------|------|------|------|
| `keyword_search` | 按关键词搜索商品 | — | ProductCollection | `keyword` (str, 必填) |
| `category_search` | 按类目搜索商品 | — | ProductCollection | `category` (str, 必填) |

#### 数据转换

| 节点 | 说明 | 输入 | 输出 | 参数 |
|------|------|------|------|------|
| `filter_products` | 多条件筛选 | ProductCollection | FilteredProductCollection | `price_lt`, `price_gte`, `review_lt`, `review_gte`, `sales_lt`, `sales_gte`（均为 float/int，可选） |
| `sort_products` | 排序 | ProductCollection | ProductCollection | `by` (str: "price"/"review"/"sales"), `order` (str: "asc"/"desc") |

#### 分析

| 节点 | 说明 | 输入 | 输出 | 参数 |
|------|------|------|------|------|
| `market_analysis` | 市场分析（规模、均价、竞争度） | ProductCollection | MarketAnalysis | — |
| `opportunity_analysis` | 机会分析（低竞争高潜力商品） | ProductCollection | OpportunityList | `max_review` (int, 可选, 默认 100) |
| `competition_analysis` | 竞争结构分析 | ProductCollection | CompetitionAnalysis | — |
| `sales_analysis` | 销量统计分析 | ProductCollection | SalesMetrics | — |
| `review_analysis` | 评论统计分析 | ProductCollection | ReviewMetrics | — |

#### 输出

| 节点 | 说明 | 输入 | 输出 | 参数 |
|------|------|------|------|------|
| `chart_output` | 生成图表数据 | 任意 Metric/Aggregation | ChartData | — |
| `report_output` | 生成 Markdown 报告 | 任意 Metric/Aggregation | ReportData | — |
| `json_output` | 原始 JSON 输出 | 任意 Artifact | JSONData | — |

---

## 六、示例

### 6.1 单表分析

```python
from gateway import Graph

g = Graph(plugin="amazon")

products = g.keyword_search(keyword="bluetooth headphone")
market = g.market_analysis(products=products)
g.output(g.json_output(market=market))

result = g.execute()
```

### 6.2 多分析器并行

```python
from gateway import Graph

g = Graph(plugin="amazon")

products = g.keyword_search(keyword="halloween garland")

# 三个分析并行执行（互不依赖）
market = g.market_analysis(products=products)
competition = g.competition_analysis(products=products)
sales = g.sales_analysis(products=products)

g.output(g.json_output(market=market))
g.output(g.json_output(competition=competition))
g.output(g.chart_output(market=sales))

result = g.execute()
```

### 6.3 带过滤的链路

```python
from gateway import Graph

g = Graph(plugin="amazon")

products = g.keyword_search(keyword="halloween garland")

# 筛选低价低评论商品，找机会
low_end = g.filter_products(
    products=products,
    price_lt=50,
    review_lt=500
)

opportunities = g.opportunity_analysis(products=low_end, max_review=300)
g.output(g.report_output(market=opportunities))

result = g.execute()
```

### 6.4 多输出

```python
from gateway import Graph

g = Graph(plugin="amazon")

products = g.keyword_search(keyword="halloween garland")
market = g.market_analysis(products=products)

g.output(g.chart_output(market=market))
g.output(g.report_output(market=market))
g.output(g.json_output(market=market))

result = g.execute()
# result = {"chart": {...}, "report": {...}, "json": {...}}
```

---

## 七、Agent 工作流

### 7.1 规划阶段

1. 调用 `GET /plugins/<name>/actions` 获取该插件可用节点
2. 根据用户需求，确定需要哪些数据和分析维度
3. 设计图结构：从数据获取 → 筛选/转换 → 分析 → 输出

### 7.2 编码阶段

按 §3.2 的格式写出 Python 脚本。所有 `g.xxx()` 调用只注册，不执行。

### 7.3 提交执行

通过 `POST /execute` 提交脚本，或本地 `g.execute()`。

### 7.4 错误处理

如果返回 `success: false`，检查 `error.code`：

| 错误码 | 含义 | 如何处理 |
|--------|------|---------|
| `TYPE_MISMATCH` | 节点间类型不兼容 | 检查 inputs/outputs 类型是否正确 |
| `NODE_NOT_FOUND` | 节点名不存在 | 检查是否拼错节点名，或是否在正确的插件域内 |
| `INVALID_PARAMS` | 参数类型或必填缺失 | 对照节点定义修正参数 |
| `CYCLIC_DEPENDENCY` | 图中存在循环引用 | 检查变量引用是否形成环 |
| `CROSS_PLUGIN` | 跨插件调用 | 拆分为多次独立调用 |

### 7.5 跨领域综合分析

```
Agent:
  ├─ POST /execute   (amazon 脚本)   → {sales: ..., competition: ...}
  ├─ POST /execute   (google 脚本)   → {trend: ...}
  ├─ POST /execute   (tiktok 脚本)   → {heat: ...}
  │
  └─ Agent 自行综合三份结果 → 给出最终判断
```

---

## 八、与旧版的主要差异

| | 旧版（Pipeline + BCL） | 新版（Graph + Python SDK） |
|---|---|---|
| Agent 编程方式 | 自建 BCL 语言 | 原生 Python |
| 架构模型 | 线性管道 Source→Transform→Sink | DAG + 并行执行 |
| 参数风格 | 位置参数 + `&key=value` | 全部命名参数 |
| 节点输出 | 多输出（outputs dict） | 单输出（output_key + output_type） |
| 控制流 | BCL 语法层硬禁止 | Python 约定 + Graph 占位符自然防错 |
| 类型检查 | 需自建 Linter | mypy + Graph.validate() 复用 Python 生态 |
| 跨插件 | BCL 语法允许 import 多个 | Graph 构造参数锁定单一插件，约定禁止 |

BCL 自建语言已被放弃——它和原生 Python SDK 相比没有实质优势，却需要整套语言工具链（解析器、AST、Linter、错误信息），而 Python 生态已经提供了所有这些。

---

## 九、类型系统速览

### 9.1 Amazon 插件类型

```
ArtifactType
  ├── ProductCollection (RawData)
  │     └── FilteredProductCollection (RawData)
  ├── MarketAnalysis (Metric)
  ├── OpportunityList (Metric)
  ├── CompetitionAnalysis (Metric)
  ├── SalesMetrics (Metric)
  ├── ReviewMetrics (Metric)
  ├── ChartData (Aggregation)
  ├── ReportData (Aggregation)
  └── JSONData (Aggregation)
```

### 9.2 兼容规则

- 子类型可传递给期望父类型的输入（`FilteredProductCollection` → `ProductCollection` 允许）
- RawData 不能直接流入期望 Metric 的输入，反之亦然
- 跨插件类型直连被禁止

---

## 十、本地开发

```bash
# 启动网关
python main.py start

# 停止
python main.py stop

# 状态
python main.py status
```

SDK 本地模式下无需 HTTP，直接 `g.execute()` 即可在进程内执行。

```python
# 本地使用示例
from gateway import Graph

g = Graph(plugin="amazon")
products = g.keyword_search(keyword="test")
g.output(g.json_output(market=g.market_analysis(products=products)))
print(g.execute())
```
