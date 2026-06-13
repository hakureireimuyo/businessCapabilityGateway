# Agent 使用手册

> **版本**: v2.0
> **面向读者**: 外部 AI Agent（你）
> **最后更新**: 2026-06-13

---

## 一、网关是什么

**Business Capability Gateway** 是一个面向 Agent 的节点协议平台。你可以把它理解为一个"能力超市"：

- **网关本身不执行业务逻辑**，它只负责：发现能力、校验组合、调度执行、返回结果。
- **所有业务能力封装在插件内部**，每个插件暴露一组节点（Node），每个节点就是一个可执行的业务操作。
- **你的工作**：查看有哪些节点可用、了解每个节点的输入/输出/参数协议、按规则组合节点形成图、提交执行、拿到结构化结果自行推理。

核心边界（必须遵守）：

- 系统只产出结构化数据和分析指标，**不做 AI 推理**。
- 数据**绝不跨插件领域混合**，一次执行限定在单一插件内。
- 跨领域综合分析由你在外部完成。

---

## 二、架构概念

### 2.1 Node（节点）—— 业务操作的最小单位

Node **不再有类型标签**（没有 Source / Transform / Sink 之分）。每个 Node 只声明三件事：

| 声明 | 含义 | 示例 |
|------|------|------|
| `input_specs` | 我需要消费哪些数据 | `{"products": ProductCollection}` |
| `output_spec` | 我产出什么数据 | `{"key": "market_analysis", "artifact_type": MarketAnalysis}` |
| `parameter_specs` | 我接受哪些字面量配置 | `{"keyword": str, "limit": int}` |

### 2.2 Artifact（产物）—— 节点间的数据协议

Artifact 是节点之间传递的数据对象。每个 Artifact 有一个**类型**（ArtifactType），类型之间存在**子类型关系**：

```
ArtifactType
  ├── ProductCollection          （原始商品数据）
  │     └── FilteredProductCollection  （过滤后的商品数据，是 ProductCollection 的子类型）
  ├── SalesMetrics               （销售指标）
  ├── ReviewMetrics              （评论指标）
  ├── MarketAnalysis             （市场分析）
  ├── MarketSignal               （聚合市场信号）
  ├── ChartData                  （图表数据）
  └── ReportData                 （报告数据）
```

**类型兼容规则**：子类型可以流入期望父类型的输入，反之不行。

```
FilteredProductCollection → 期望 ProductCollection 的输入   ✅ 允许
ProductCollection → 期望 FilteredProductCollection 的输入   ❌ 拒绝
SalesMetrics → 期望 ProductCollection 的输入               ❌ 拒绝（不相关）
```

### 2.3 Graph（图）—— 任务的组合描述

Graph 由三部分组成：

```
Graph:
  plugin: "amazon"               ← 环节1：哪个插件领域
  nodes: {...}                   ← 环节2：要运行哪些节点（node_id → 节点名+参数）
  edges: [...]                   ← 环节3：节点之间数据怎么流动
  outputs: [...]                 ← 环节4：哪些节点的输出是最终结果
```

**为什么是图而不是线性管道？** 因为图可以表达并行。当两个节点都只依赖同一个上游节点时，它们互不依赖，网关会并行执行它们。

### 2.4 执行模型 —— 依赖驱动的并行调度

```
Graph:
  search ──→ sales ──→ market_score ──→ chart
        └─→ reviews ─┘               └─→ report

执行过程:
  第1轮: [search] 无依赖，立即执行
  第2轮: [sales, reviews] 并行执行（都只依赖 search）
  第3轮: [market_score] 等待 sales 和 reviews 都完成
  第4轮: [chart, report] 并行执行（都只依赖 market_score）
  完成: 返回 {"chart": ..., "report": ...}
```

---

## 三、使用流程

### 3.1 启动服务

```bash
python main.py start --port 8765
```

健康检查：

```http
GET /health → {"status": "ok"}
```

### 3.2 步骤一：发现可用插件

```http
GET /plugins
```

返回：

```json
["amazon"]
```

### 3.3 步骤二：查看节点的协议规范

```http
GET /plugins/amazon/nodes
```

返回每个节点的完整 Spec：

```json
[
  {
    "name": "keyword_search",
    "plugin": "amazon",
    "description": "Search products by keyword, supports fuzzy matching on title and keyword fields",
    "input_specs": {},
    "output_spec": {
      "key": "products",
      "artifact_type": "ProductCollection",
      "description": "Matching products"
    },
    "parameter_specs": {
      "keyword": {"type": "str", "required": true, "description": "Search keyword"},
      "limit": {"type": "int", "required": false, "default": 50, "description": "Max results to return"}
    }
  },
  {
    "name": "market_analysis",
    "plugin": "amazon",
    "description": "Analyze market competition: size, avg price, competition score (0-100), sales distribution",
    "input_specs": {
      "products": {
        "artifact_type": "ProductCollection",
        "required": true,
        "description": "Products to analyze"
      }
    },
    "output_spec": {
      "key": "market_analysis",
      "artifact_type": "MarketAnalysis",
      "description": "Market analysis result"
    },
    "parameter_specs": {}
  }
]
```

**怎么读 Node Spec：**

| 字段 | 含义 | 你需要注意 |
|------|------|-----------|
| `input_specs` 为空 | 这个节点是图的入口，不需要上游 | 它可以作为起点的候选 |
| `input_specs` 非空 | 这个节点需要上游提供特定类型的 Artifact | 必须有一条边指向它的每个必填输入 |
| `output_spec.key` | 这个节点产出的 Artifact 的存储键 | 在 edge 中引用此 key |
| `output_spec.artifact_type` | Artifact 的具体类型 | 与下游的 input_specs.artifact_type 做兼容检查 |
| `parameter_specs` | 字面量参数 | 在 GraphNode.params 中提供，类型必须匹配 |

### 3.4 步骤三：根据 Spec 构造 Graph

**Graph JSON 格式：**

```json
{
  "plugin": "amazon",
  "nodes": {
    "<node_id>": {
      "node_name": "<注册的 Node 名>",
      "params": { "<参数名>": <值> }
    }
  },
  "edges": [
    {
      "from": "<上游 node_id>",
      "from_output": "<上游 output_spec.key>",
      "to": "<下游 node_id>",
      "to_input": "<下游 input_specs 中的输入名>"
    }
  ],
  "outputs": ["<node_id>", "<node_id>"]
}
```

**构造步骤：**

1. 选择入口节点（`input_specs` 为空的节点），分配 `node_id`
2. 选择下游节点，分配 `node_id`
3. 对每条数据流，建立 edge：上游的 `output_spec.key` → 下游的 `input_specs` 中的输入名
4. 检查类型兼容：上游 `output_spec.artifact_type` 是否是下游 `input_specs[input_name].artifact_type` 的子类
5. 选择最终要获取结果的节点，加入 `outputs`

> **关键思维模型**：node_id 是你给节点实例取的名字（如 `"s1"`, `"filter_1"`, `"analysis_1"`），node_name 是注册的节点名（如 `"keyword_search"`）。同一个 node_name 可以在同一张图中出现多次（不同的 node_id），只要参数不同。

### 3.5 步骤四：提交执行

```http
POST /execute
Content-Type: application/json

{ ... Graph JSON ... }
```

### 3.6 步骤五：解读结果

**成功返回：**

```json
{
  "success": true,
  "data": {
    "market_analysis": {
      "market_size": 12,
      "avg_price": 23.75,
      "competition_score": 25,
      "total_monthly_sales": 7635,
      "price_range": [8.50, 55.00]
    }
  },
  "message": "Graph executed (2 nodes)"
}
```

`data` 是一个字典，key 是 `outputs` 中每个节点产出的 `output_spec.key`，value 是该 Artifact 的 `data` 字段。

**失败返回：**

```json
{
  "success": false,
  "error": {
    "code": "TYPE_MISMATCH",
    "message": "Type mismatch: a1.market_analysis → a2.sales",
    "errors": [
      {
        "layer": "TYPE_MISMATCH",
        "edge": {"from": "a1", "from_output": "market_analysis", "to": "a2", "to_input": "sales"},
        "expected": "SalesMetrics",
        "actual": "MarketAnalysis",
        "message": "Type mismatch: a1.market_analysis → a2.sales"
      }
    ]
  }
}
```

`error.errors` 数组列出所有校验错误，每个错误包含 `layer`（错误层）、相关节点/边、以及人类可读的 `message`。

---

## 四、Graph 设计模式

### 4.1 简单链式（Serial Chain）

最基础的图：入口节点 → 分析节点。

```json
{
  "plugin": "amazon",
  "nodes": {
    "s1": {"node_name": "keyword_search", "params": {"keyword": "halloween garland"}},
    "a1": {"node_name": "market_analysis", "params": {}}
  },
  "edges": [
    {"from": "s1", "from_output": "products", "to": "a1", "to_input": "products"}
  ],
  "outputs": ["a1"]
}
```

```
search ──→ market_analysis
```

### 4.2 过滤链（Filter Chain）

入口 → 过滤 → 排序 → 分析。

```json
{
  "plugin": "amazon",
  "nodes": {
    "s1": {"node_name": "keyword_search", "params": {"keyword": "halloween garland", "limit": 50}},
    "f1": {"node_name": "filter", "params": {"price_gte": 10.0, "price_lte": 50.0, "rating_gte": 4.0}},
    "sort1": {"node_name": "sort", "params": {"by": "sales", "order": "desc"}},
    "a1": {"node_name": "market_analysis", "params": {}}
  },
  "edges": [
    {"from": "s1", "from_output": "products", "to": "f1", "to_input": "products"},
    {"from": "f1", "from_output": "filtered_products", "to": "sort1", "to_input": "products"},
    {"from": "sort1", "from_output": "sorted_products", "to": "a1", "to_input": "products"}
  ],
  "outputs": ["a1"]
}
```

```
search ──→ filter ──→ sort ──→ market_analysis
```

**类型兼容性**：`FilteredProductCollection` 是 `ProductCollection` 的子类型，所以 `filter` 的产出可以流入 `sort`（它期望 `ProductCollection`）。

### 4.3 并行分支（Parallel Branches）

入口分叉到两个独立的分析节点，网关自动并行执行。

```json
{
  "plugin": "amazon",
  "nodes": {
    "s1": {"node_name": "keyword_search", "params": {"keyword": "halloween garland"}},
    "sales": {"node_name": "sales_analysis", "params": {}},
    "reviews": {"node_name": "review_analysis", "params": {}}
  },
  "edges": [
    {"from": "s1", "from_output": "products", "to": "sales", "to_input": "products"},
    {"from": "s1", "from_output": "products", "to": "reviews", "to_input": "products"}
  ],
  "outputs": ["sales", "reviews"]
}
```

```
            ┌─→ sales_analysis ──→ (输出 sales_metrics)
search ──→──┤
            └─→ review_analysis ──→ (输出 review_metrics)
```

### 4.4 多输入汇合（Multi-input Aggregation）

并行分支 → 汇合节点，同时消费两个不同类型的 Artifact。

```json
{
  "plugin": "amazon",
  "nodes": {
    "s1": {"node_name": "keyword_search", "params": {"keyword": "halloween garland"}},
    "sales": {"node_name": "sales_analysis", "params": {}},
    "reviews": {"node_name": "review_analysis", "params": {}},
    "score": {"node_name": "market_score", "params": {"method": "weighted"}}
  },
  "edges": [
    {"from": "s1", "from_output": "products", "to": "sales", "to_input": "products"},
    {"from": "s1", "from_output": "products", "to": "reviews", "to_input": "products"},
    {"from": "sales", "from_output": "sales_metrics", "to": "score", "to_input": "sales"},
    {"from": "reviews", "from_output": "review_metrics", "to": "score", "to_input": "reviews"}
  ],
  "outputs": ["score"]
}
```

```
            ┌─→ sales_analysis ──┐
search ──→──┤                    ├─→ market_score ──→ (输出 market_signal)
            └─→ review_analysis ─┘
```

**关键点**：`market_score` 有两个必填输入（`sales` 和 `reviews`），只有两者都完成后它才会开始执行。网关自动处理这个等待。

### 4.5 多输出（Multi-output）

一个分析结果分叉为多种输出格式。

```json
{
  "plugin": "amazon",
  "nodes": {
    "s1": {"node_name": "keyword_search", "params": {"keyword": "bluetooth headphone"}},
    "a1": {"node_name": "competition_analysis", "params": {}},
    "o1": {"node_name": "chart_output", "params": {}},
    "o2": {"node_name": "json_output", "params": {}}
  },
  "edges": [
    {"from": "s1", "from_output": "products", "to": "a1", "to_input": "products"},
    {"from": "a1", "from_output": "competition_analysis", "to": "o1", "to_input": "data"},
    {"from": "a1", "from_output": "competition_analysis", "to": "o2", "to_input": "data"}
  ],
  "outputs": ["o1", "o2"]
}
```

```
                        ┌─→ chart_output ──→ (输出 chart)
search ──→ competition ─┤
                        └─→ json_output ──→ (输出 json)
```

---

## 五、图的合法性规则

网关在执行前会做七层校验。你需要确保你的 Graph 通过所有层：

| 层 | 检查内容 | 典型错误 | 如何避免 |
|----|---------|---------|---------|
| 1. 节点存在性 | 每个 `node_name` 是否在插件中注册 | `"ghost_node"` 未注册 | 先调 `/nodes` 确认有哪些节点 |
| 2. 参数合法性 | params 类型是否匹配、必填是否提供 | `keyword=123`（期望 str） | 核对 `parameter_specs` 的 type 和 required |
| 3. 输入完备性 | 每个必填 input 是否有上游边 | `market_score.sales` 无人提供 | 确保每个 `required=true` 的 input_specs 都有入边 |
| 4. 类型兼容 | 边的输出类型是否满足输入期望 | `ProductCollection` → 期望 `SalesMetrics` | 用 `issubclass` 逻辑自检 |
| 5. 无环 | 是否存在循环依赖 | A → B → C → A | 画出数据流确认无环 |
| 6. 输出合法 | outputs 引用的 node_id 是否存在 | `outputs: ["ghost"]` | 确保 outputs 中的 ID 在 nodes 里 |
| 7. 业务规则 | 是否存在跨插件引用 | 在 amazon 图中引用 tiktok 节点 | 一次只用一种插件 |

---

## 六、完整错误码参考

| 错误码 | 触发场景 | 含义 |
|--------|---------|------|
| `PLUGIN_NOT_FOUND` | 图中 `plugin` 不存在 | 插件未加载 |
| `NODE_NOT_FOUND` | `node_name` 未在插件中注册 | 节点名拼写错误或不存在 |
| `INVALID_PARAMS` | 参数缺失或类型错误 | 参数与 `parameter_specs` 不匹配 |
| `UNSATISFIED_INPUT` | 必填输入没有入边 | 忘记连接某个必填输入 |
| `TYPE_MISMATCH` | 边两端类型不兼容 | Artifact 类型对不上 |
| `CYCLIC_DEPENDENCY` | 图中有循环 | 数据流成环 |
| `DANGLING_OUTPUT` | output 引用不存在的 node_id | outputs 写错了 ID |
| `CROSS_PLUGIN` | 跨插件引用 | 不同插件的节点混用 |
| `EXECUTION_FAILED` | 节点执行异常 | 业务逻辑错误 |
| `DEADLOCK` | 存在无法满足的依赖 | 理论上不应出现（校验层会先拦截） |
| `INVALID_JSON` | 请求体不是合法 JSON | body 格式错误 |
| `EMPTY_REQUEST` | 请求体为空 | 忘了写 body |
| `INTERNAL_ERROR` | 网关内部未预期错误 | 服务器问题 |

---

## 七、当前可用节点速览（Amazon 插件）

### 数据获取（图入口，无输入）

| node_name | output | 关键参数 |
|-----------|--------|---------|
| `keyword_search` | `products` (ProductCollection) | `keyword`* (str), `limit` (int, 默认50) |
| `category_search` | `products` (ProductCollection) | `category`* (str) |

### 数据转换（ProductCollection → ProductCollection）

| node_name | output | 关键参数 |
|-----------|--------|---------|
| `filter` | `filtered_products` (FilteredProductCollection) | `price_gte`, `price_lte`, `review_lt`, `review_gte`, `rating_gte`, `category` |
| `sort` | `sorted_products` (ProductCollection) | `by`* (str: price/review/sales), `order` (str: asc/desc) |

### 分析节点（ProductCollection → 指标）

| node_name | output | 关键参数 |
|-----------|--------|---------|
| `market_analysis` | `market_analysis` (MarketAnalysis) | 无 |
| `opportunity_analysis` | `opportunity_list` (OpportunityList) | `max_review` (int, 默认100) |
| `competition_analysis` | `competition_analysis` (CompetitionAnalysis) | 无 |
| `sales_analysis` | `sales_metrics` (SalesMetrics) | 无 |
| `review_analysis` | `review_metrics` (ReviewMetrics) | 无 |

### 多输入节点（汇合）

| node_name | 输入 | output |
|-----------|------|--------|
| `market_score` | `sales` (SalesMetrics) + `reviews` (ReviewMetrics) | `market_signal` (MarketSignal) |

参数：`method` (str, 默认 "weighted")

### 输出节点（任意 Artifact → 格式化输出）

| node_name | 输入 | output | 说明 |
|-----------|------|--------|------|
| `chart_output` | `data` (任意 ArtifactType) | `chart` (ChartData) | 包装为图表数据 |
| `report_output` | `data` (任意 ArtifactType) | `report` (ReportData) | 生成 Markdown 报告 |
| `json_output` | `data` (任意 ArtifactType) | `json` (JSONData) | 透传原始 JSON |

> `chart_output`、`report_output`、`json_output` 的输入类型是 `ArtifactType`（基类），意味着**任何 Artifact 都可以流入**（所有 Artifact 类型都是 ArtifactType 的子类）。

---

## 八、Agent 最佳实践

### 8.1 先发现，后构图

不要在不知道有哪些节点的情况下猜测。每次都先调 `/plugins/{plugin}/nodes`，拿到完整的 Spec 列表后再构图。

### 8.2 类型对齐

构图时，检查每条边的类型兼容性：上游 output 的 `artifact_type` 是否是下游 input 的 `artifact_type` 的子类？不是子类就拒绝。网关会在校验阶段拦截，但不如图前自检高效。

### 8.3 利用并行

当需要做多个独立分析时（例如同时做销售分析和评论分析），让它们都从同一个入口节点分叉。网关会自动并行执行，不需要你调用多次。

### 8.4 一个请求完成一个分析任务

不要把一个复杂的多步骤分析拆成多次 `/execute` 调用。一次性构建完整的 Graph 提交。网关负责调度，你只负责构图。

### 8.5 关注错误数组

当 `success: false` 且 `code` 为 `INVALID_GRAPH` 时，`error.errors` 是一个数组，列出了所有校验失败项。修复时应该逐个处理，不要只看第一条。

### 8.6 同一节点可多次使用

同一个 `node_name` 可以在图中出现多次（不同的 `node_id`）。例如：

```json
{
  "nodes": {
    "search_halloween": {"node_name": "keyword_search", "params": {"keyword": "halloween"}},
    "search_christmas": {"node_name": "keyword_search", "params": {"keyword": "christmas"}},
    "analysis_h": {"node_name": "market_analysis", "params": {}},
    "analysis_c": {"node_name": "market_analysis", "params": {}}
  },
  "edges": [
    {"from": "search_halloween", "from_output": "products", "to": "analysis_h", "to_input": "products"},
    {"from": "search_christmas", "from_output": "products", "to": "analysis_c", "to_input": "products"}
  ],
  "outputs": ["analysis_h", "analysis_c"]
}
```

两个搜索 → 两个分析，全部在单个 Graph 中并行完成。

### 8.7 优先使用具体类型的分析节点

`chart_output`、`report_output`、`json_output` 接受任意 Artifact，但它们只是格式化包装器。真正的分析结果来自 `market_analysis`、`sales_analysis` 等具体节点。构图时，先让数据流经具体的分析节点，最后再用格式化节点包装输出。

---

## 九、完整示例

以下是一个完整的 Agent 使用流程，用 curl 演示：

```bash
# 1. 健康检查
curl http://localhost:8765/health
# → {"status":"ok"}

# 2. 发现插件
curl http://localhost:8765/plugins
# → ["amazon"]

# 3. 查看 Amazon 节点的完整协议
curl http://localhost:8765/plugins/amazon/nodes
# → [{...keyword_search...}, {...filter...}, {...market_analysis...}, ...]

# 4. 执行一个包含过滤+并行分析+汇合评分的图
curl -X POST http://localhost:8765/execute \
  -H "Content-Type: application/json" \
  -d '{
    "plugin": "amazon",
    "nodes": {
      "s1": {"node_name": "keyword_search", "params": {"keyword": "halloween garland", "limit": 30}},
      "f1": {"node_name": "filter", "params": {"price_gte": 10.0, "rating_gte": 3.5}},
      "sales": {"node_name": "sales_analysis", "params": {}},
      "reviews": {"node_name": "review_analysis", "params": {}},
      "score": {"node_name": "market_score", "params": {"method": "weighted"}}
    },
    "edges": [
      {"from": "s1", "from_output": "products", "to": "f1", "to_input": "products"},
      {"from": "f1", "from_output": "filtered_products", "to": "sales", "to_input": "products"},
      {"from": "f1", "from_output": "filtered_products", "to": "reviews", "to_input": "products"},
      {"from": "sales", "from_output": "sales_metrics", "to": "score", "to_input": "sales"},
      {"from": "reviews", "from_output": "review_metrics", "to": "score", "to_input": "reviews"}
    ],
    "outputs": ["score"]
  }'

# 返回:
# {
#   "success": true,
#   "data": {
#     "market_signal": {
#       "market_signal_score": 67,
#       "sales_contribution": 47,
#       "rating_contribution": 80,
#       "product_count": 10,
#       "method": "weighted"
#     }
#   },
#   "message": "Graph executed (5 nodes)"
# }
```

这个 Graph 的数据流：

```
keyword_search ──→ filter ──→ sales_analysis ──→ market_score ──→ (最终输出)
                          └─→ review_analysis ─┘
```

其中 `sales_analysis` 和 `review_analysis` 由网关自动并行执行。
