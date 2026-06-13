# Agent 使用手册

> **版本**: v2.0
> **面向读者**: 外部 AI Agent
> **最后更新**: 2026-06-13

---

## 一、可用的 HTTP 端点

### `GET /health`

服务健康检查。

返回：

```json
{"status": "ok"}
```

---

### `GET /plugins`

列出所有已加载的插件名称。

返回：

```json
["amazon"]
```

---

### `GET /plugins/{plugin_name}/nodes`

列出插件所有节点的**概要**。只返回 Agent 扫描和判断需要的信息，不包含完整协议细节。

返回示例：

```json
[
  {"name": "keyword_search",    "plugin": "amazon", "description": "Search products by keyword",                   "is_entry": true,  "input_count": 0, "output_key": "products",           "output_type": "ProductCollection"},
  {"name": "filter",            "plugin": "amazon", "description": "Filter products by price/review/rating/category", "is_entry": false, "input_count": 1, "output_key": "filtered_products",   "output_type": "FilteredProductCollection"},
  {"name": "market_analysis",   "plugin": "amazon", "description": "Analyze market: size, avg price, competition",   "is_entry": false, "input_count": 1, "output_key": "market_analysis",    "output_type": "MarketAnalysis"},
  {"name": "market_score",      "plugin": "amazon", "description": "Aggregate market score from sales and reviews",  "is_entry": false, "input_count": 2, "output_key": "market_signal",      "output_type": "MarketSignal"},
  {"name": "chart_output",      "plugin": "amazon", "description": "Format analysis as chart visualization data",    "is_entry": false, "input_count": 1, "output_key": "chart",              "output_type": "ChartData"}
]
```

各字段含义：

| 字段 | 含义 |
|------|------|
| `name` | 节点名，也是 Graph 脚本中的方法名 |
| `description` | 一句话描述这个节点做什么 |
| `is_entry` | `true` 表示无输入，可作为图的起点 |
| `input_count` | 需要几个上游输入（为 0 则可独立启动） |
| `output_key` | 产出的 Artifact 的键名 |
| `output_type` | 产出的 Artifact 类型（决定哪些下游节点可接收它） |

---

### `GET /plugins/{plugin_name}/nodes/{node_name}`

查看**单个节点**的完整协议规范 —— 所有 input / output / parameter 的类型、是否必填、默认值、描述。

返回示例：

```json
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
    "keyword": {"type": "str", "required": true,  "default": null, "description": "Search keyword"},
    "limit":   {"type": "int", "required": false, "default": 50,   "description": "Max results to return"}
  }
}
```

每个节点声明三样东西：**需要什么输入** (`input_specs`)、**产出什么** (`output_spec`)、**接受什么参数** (`parameter_specs`)。Agent 根据这三项判断如何将节点连入 Graph。

---

### `POST /execute`

提交一个 Python 脚本来构建并执行图。

**重要**：请求体格式为 `text/plain`，内容是使用 Gateway SDK 的 Python 脚本。

请求：

```http
POST /execute
Content-Type: text/plain

g = Graph(plugin="amazon")
products = g.keyword_search(keyword="halloween garland")
analysis = g.market_analysis(products=products)
g.output(analysis)
result = g.execute()
```

成功返回：

```json
{
  "success": true,
  "data": {
    "market_analysis": {
      "market_size": 12,
      "avg_price": 23.62,
      "competition_score": 50
    }
  },
  "message": "Graph executed"
}
```

失败返回：

```json
{
  "success": false,
  "error": {
    "code": "INVALID_GRAPH",
    "message": "Type mismatch: a1.market_analysis → a2.sales"
  }
}
```

---

## 二、Python 脚本编写规范

### 核心对象

脚本中只能使用一个 SDK 类：**`Graph`**。它已经预先注入到脚本的执行命名空间中，无需 import。

### 三步构建模式

**第 1 步 — 创建 Graph 实例**

```python
g = Graph(plugin="amazon")
```

`plugin` 参数必须是 `/plugins` 返回的已有插件名。

**第 2 步 — 调用节点方法**

Graph 实例上可以直接调用 `/plugins/{plugin}/nodes` 中列出的任意 `name` 作为方法名。方法的参数分为两类：

| 参数类型 | 含义 | 示例 |
|----------|------|------|
| 字面量参数 | 对应节点的 `parameter_specs` | `keyword="test"`, `limit=50`, `price_gte=10.0` |
| Artifact 引用 | 传递另一个节点调用的返回值，建立数据边 | `products=products`, `sales=sales` |

每次调用返回一个 **Artifact 引用**（占位符），传递给下游节点即可建立数据连接：

```python
products = g.keyword_search(keyword="halloween garland")         # 入口节点
filtered = g.filter(products=products, price_gte=10.0)          # 上游的 products 传入
analysis = g.market_analysis(products=filtered)                 # 上游的 filtered 传入
```

**第 3 步 — 标记输出并执行**

```python
g.output(analysis)          # 标记哪些节点的产出是最终结果
result = g.execute()        # 赋值给 result 变量（必须）
```

**关键约束**：
- 脚本最后**必须有** `result = g.execute()`，且变量名必须是 `result`，否则网关无法提取结果。
- 脚本中**禁止**使用 `import`、`eval`、`exec`、`open`、`getattr` 等语句，沙箱会在执行前拦截。
- 脚本执行超时上限为 **10 秒**。
- 脚本最大 **100 KB**。

### 图模式示例

**简单链式** — 一个入口一个输出：
```python
g = Graph(plugin="amazon")
products = g.keyword_search(keyword="halloween garland")
analysis = g.market_analysis(products=products)
g.output(analysis)
result = g.execute()
```

**带过滤的链式**：
```python
g = Graph(plugin="amazon")
products = g.keyword_search(keyword="halloween garland", limit=50)
filtered = g.filter(products=products, price_gte=10.0, price_lte=50.0, rating_gte=4.0)
analysis = g.market_analysis(products=filtered)
g.output(analysis)
result = g.execute()
```

**并行分支** — sales 和 reviews 从同一入口分叉，网关自动并行执行：
```python
g = Graph(plugin="amazon")
products = g.keyword_search(keyword="halloween garland")
sales = g.sales_analysis(products=products)
reviews = g.review_analysis(products=products)
score = g.market_score(sales=sales, reviews=reviews)
g.output(score)
result = g.execute()
```

**多输出** — 同时产出图表和 JSON：
```python
g = Graph(plugin="amazon")
products = g.keyword_search(keyword="bluetooth headphone")
analysis = g.competition_analysis(products=products)
chart = g.chart_output(data=analysis)
js = g.json_output(data=analysis)
g.output(chart)
g.output(js)
result = g.execute()
```

---

## 三、错误码参考

| 错误码 | 含义 |
|--------|------|
| `EMPTY_REQUEST` | 请求体为空 |
| `INVALID_SCRIPT` | 脚本语法错误、包含禁止操作、或缺少 `result = g.execute()` |
| `PLUGIN_NOT_FOUND` | 插件不存在 |
| `NODE_NOT_FOUND` | 图中引用了不存在的节点 |
| `INVALID_PARAMS` | 参数缺失、类型错误或传入了未知参数 |
| `INVALID_GRAPH` | 图结构不合法（类型不匹配、循环依赖、必填输入未连接等） |
| `EXECUTION_TIMEOUT` | 脚本执行超过 10 秒 |
| `INTERNAL_ERROR` | 网关内部未预期错误 |

`INVALID_GRAPH` 错误的响应中可能包含 `errors` 数组，列出所有具体校验失败项（每个项的 `layer` 字段标识校验层）。

---

## 四、Agent 工作流建议

1. `GET /plugins` → 确认有哪些插件
2. `GET /plugins/{plugin}/nodes` → 扫描所有节点概要（`is_entry`、`output_type`、`input_count`），挑选与任务相关的候选节点
3. `GET /plugins/{plugin}/nodes/{node_name}` → 对每个候选节点获取完整 Spec，确认输入输出类型和参数约束
4. 根据 Spec 中声明的类型兼容关系，构造 Graph 脚本
5. `POST /execute` 提交脚本，解读返回的 `data`
