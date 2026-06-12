# 架构设计与 BCL 语言——确定结论

> **状态：已更新。** BCL 自建语言方案已被放弃，改用 Python SDK + 延迟执行 Graph。
> 本文档中图架构、Node 单输出、类型系统、跨域隔离等架构决策仍然有效。
> Agent 视角的使用文档见 [系统使用指南——Agent视角.md](系统使用指南——Agent视角.md)。

---

## 一、系统定位

本系统是 **面向 Agent 的业务能力编排层（Agent-Oriented Semantic Analysis Layer）**，本质是一个 **业务智能中间件**。

核心关系：

```
Agent（外部）
   │
   ▼ 生成 BCL
BCL（业务编排语言）
   │
   ▼ 解析执行
Graph Runtime（图运行时）
   │
   ▼ 产出
结构化分析结果
   │
   ▼ 返回
Agent（自行推理）
```

**边界原则：** 系统只负责产出结构化数据和分析指标，不做 AI 推理，不输出自然语言结论。"存在机会"之类的判断是 Agent 的职责，不是本系统的职责。

---

## 二、架构：从线性管道到 DAG（图架构）

### 2.1 废弃：Source → Transform → Sink

线性管道 `Source → Transform → Sink` 已被废弃，因为：
- 只能表达"单输入、单输出"的链式流程
- 无法支持分支、汇聚、并行执行
- 无法表达多分析器、多输出器的业务场景

### 2.2 新架构：Node + Graph + Artifact

三个核心概念：

| 概念 | 说明 |
|------|------|
| **Node** | 最小执行单元，声明 `inputs` / `output_key` / `output_type` / `parameters`，实现 `execute()` |
| **Graph** | 有向无环图（DAG），由 Node 通过 Artifact 依赖自动构成 |
| **Artifact** | 节点之间传递的数据产物，是图的"边" |

### 2.3 Node 定义

Node 统一抽象，不再分类为 Source/Transform/Sink。

**每个 Node 只有单一输出**。如需多个产出物，拆分到各自对应的节点分别调用，逻辑更清晰，也避免了 BCL 语法层面的歧义。

```python
class Node:
    name: str                       # 节点名称
    inputs: dict[str, ArtifactType] # 输入 Artifact key → 期望类型
    output_key: str                 # 输出 Artifact 的唯一 key
    output_type: ArtifactType       # 输出 Artifact 的类型
    parameters: dict[str, type]     # 字面量参数 → 参数类型

    def execute(self, context: ExecutionContext) -> None:
        ...
```

示例：

```python
class KeywordSearchNode:
    inputs = {}
    output_key = "products"
    output_type = ProductCollection
    parameters = {"keyword": str}

class MarketAnalysisNode:
    inputs = {"products": ProductCollection}
    output_key = "market_analysis"
    output_type = MarketAnalysis
    parameters = {}

class ChartOutputNode:
    inputs = {"market_analysis": MarketAnalysis}
    output_key = "chart"
    output_type = ChartData
    parameters = {}
```

BCL 变量名与节点的 `output_key` 可以不同——执行器通过变量赋值关联节点的唯一输出类型做类型检查：

```
my_data = keyword_search(keyword="halloween")

# 执行器：
#   my_data → 绑定到 KeywordSearchNode 的唯一输出
#   my_data 类型 = KeywordSearchNode.output_type = ProductCollection

market = market_analysis(@my_data)
```

### 2.4 ExecutionContext

替代原来的 `context.data: Any`，改为多槽位设计：

```python
class ExecutionContext:
    artifacts: dict[str, Any]    # 执行期间产生的所有中间产物（包括原始数据集和分析结果）
    outputs: dict[str, Any]      # 最终输出（由 output 声明，图执行完毕后返回给 Agent）
    metadata: dict[str, Any]     # 运行元信息（request_id、plugin、timestamp）
```

### 2.5 执行流程

```
BCL 文本
  ↓  Parser（语法解析）
AST
  ↓  Linter（静态检查：语法/符号/类型/图/业务规则）
已校验 AST
  ↓  Graph Builder（构建依赖图）
DAG
  ↓  拓扑排序 + 并行识别
执行计划
  ↓  Executor（按依赖就绪顺序调度执行）
Outputs
```

### 2.6 执行规则

- 节点**所有输入 Artifact 已就绪**时才可执行
- 无依赖关系的节点**允许并行执行**
- **禁止循环依赖**，必须在构图阶段检测并报错

---

## 三、Agent 接口层（原 BCL——已废弃）

> **BCL 自建语言方案已被放弃。** 改用 Python SDK + 延迟执行 Graph 对象。
> 以下内容保留作为设计演进记录。实际 Agent 调用方式见 [系统使用指南——Agent视角.md](系统使用指南——Agent视角.md)。
>
> **保留的设计原则：** 显式命名参数、禁止控制流、单一数据域、多输出通过多个节点实现。这些在 Python SDK 中通过 Graph 对象 API 设计和约定来保证。

### 3.1 设计原则（保留，移入 Python SDK 约定）

1. **一种概念只允许一种语法**（不给多种等价写法）
2. **节点调用格式统一**
3. **所有依赖通过变量引用表达**
4. **不支持流程控制语句**（禁止 `if`/`while`/`for`/`switch`/`lambda`）
5. BCL 是**业务编排语言**，不是通用编程语言
6. **布尔/条件逻辑不进入 BCL 语法。** 数据过滤通过普通 Node 的 parameters 承载（如 `price_lt=100`），单个 Node 内部参数天然为 AND 语义。复杂条件组合（OR、嵌套逻辑）通过图中多个 Node 的串并联来表达，而非在 BCL 中引入布尔表达式

### 3.2 核心语法（v1.0）

仅保留四种语法：

#### (1) 导入插件

```
import amazon
```

导入后，当前上下文进入该插件的业务域，后续所有能力名称自动从该插件解析。

**一次 BCL 程序只允许 `import` 一个插件。** 数据层绝不跨领域，每个插件各自完成自己领域内的完整分析链路。禁止在同一个 BCL 程序中导入多个不同数据库的插件。跨数据源的综合性分析由 Agent 在系统外部完成。

#### (2) 节点调用（变量赋值）

```
result = node_name(
    input1=@upstream_var,
    param=value
)
```

**所有参数必须显式命名。** 禁止位置参数。

- `input1=@upstream_var` → Artifact 引用，参数名 `input1` 必须匹配 Node 的 inputs key
- `param=value` → 字面量值，参数名必须匹配 Node 的 parameters key
- 每个节点调用必须有赋值目标（显式命名）

Linter 检查：参数名是否存在于 Node 的 `inputs` 或 `parameters` 声明中，不存在则报错。

#### (3) 引用上游 Artifact

通过 `@变量名` 引用上游产物：

```
market = market_score(
    sales=@sales,
    reviews=@reviews,
    min_review=100
)
```

- `@sales`、`@reviews` 为变量引用（上游节点输出）
- `min_review=100` 为字面量参数
- `@` 前缀消歧：解析器可无歧义区分变量引用与字面量

#### (4) 输出声明

```
output market
output chart
```

声明哪些 Artifact 是最终产物，返回给调用方（Agent）。

### 3.3 完整示例

```
import amazon

products = keyword_search(
    keyword="halloween garland"
)

sales = sales_analysis(
    products=@products
)

reviews = review_analysis(
    products=@products
)

market = market_score(
    sales=@sales,
    reviews=@reviews
)

chart = chart_output(
    market=@market
)

report = report_output(
    market=@market
)

output chart
output report
```

**BCL 变量名与 Node output_key 的关系：**

- BCL 变量名（如 `products`、`sales`）是用户/Agent 在 BCL 中取的别名，供后续 `@变量名` 引用
- Node 的 `output_key` 是该节点产出物在 `context.artifacts` 中的真实存储 key（如 `"products"`）
- 执行器根据赋值关系将 BCL 变量映射到对应节点的 `output_type`，用于类型检查
- 两者允许不同名，建议相同以保持可读性

对应自动构建的 DAG：

```
    keyword_search
         │
      products
      ┌───┴───┐
      ▼       ▼
    sales   reviews
      │       │
      └──┬────┘
         ▼
      market
      ┌──┴──┐
      ▼     ▼
    chart  report
```

### 3.4 布尔逻辑如何表达

BCL 不引入布尔表达式语法。条件过滤分两层处理：

**简单 AND 条件**——通过单个 Node 的 parameters 承载：

```
filtered = filter_products(
    products=@products,
    price_lt=100,
    rating_gt=4.0
)
```

节点内部参数之间天然为 AND 语义：`price < 100 AND rating > 4`。

**复杂条件（OR / 嵌套逻辑）**——通过图中多个 Node 的串并联表达：

```
# 需求: (price < 100 OR review > 4) AND (sales > 500)

# 前半段 OR：两条并行分支
candidates_1 = filter_by_price(products=@products, price_lt=100)
candidates_2 = filter_by_review(products=@products, rating_gt=4.0)
candidates = merge_sets(a=@candidates_1, b=@candidates_2)

# 后半段 AND：串联
final = filter_by_sales(products=@candidates, sales_gt=500)
```

图结构本身承担了条件组合职责，无需给 BCL 增加语法。

---

## 四、Artifact 类型系统

### 4.1 类型层次

Artifact 按语义分为三类：

| 类别 | 说明 | 示例 |
|------|------|------|
| **RawDataArtifact** | 原始数据集合 | `ProductCollection`、`ReviewCollection` |
| **MetricArtifact** | 分析指标 | `SalesMetrics`、`CompetitionMetrics` |
| **AggregationArtifact** | 聚合结果 | `MarketSignal`（组装多源指标） |

数据流向规定：

```
RawDataArtifact → MetricArtifact → AggregationArtifact   ✅ 允许
RawDataArtifact ↔ RawDataArtifact 跨业务域                ❌ 禁止
```

### 4.2 类型归属

所有 Artifact 类型归属于其声明的插件领域。不同插件的类型之间不存在转换或适配关系——因为一次 BCL 程序只运行在一个插件上下文中，数据不会跨领域流动。

跨数据库、跨插件的综合分析由 **Agent 自行完成**：Agent 分别调用不同插件获取各自的最终分析结果，然后在自身推理层做综合判断。系统本身不参与任何跨域数据融合。

### 4.3 类型定义与兼容检查

```python
class ArtifactType:
    """所有 Artifact 类型的基类"""
    pass

class ProductCollection(ArtifactType):
    pass

class FilteredProductCollection(ProductCollection):
    pass
```

类型兼容检查：`issubclass(actual, expected)`——子类型可赋值给父类型。

---

## 五、静态检查器（Linter）

静态检查器的重要性高于执行器：它让 AI 在生成阶段就能发现错误并修正，而不是等到运行时报错。

### 检查层次

| 层 | 检查内容 | 示例错误 |
|----|---------|---------|
| 1. 语法检查 | BCL 文本是否符合语法 | 缺少括号、关键字拼写错误 |
| 2. 符号检查 | 引用的变量是否已定义 | `@products` 但 `products` 未定义 |
| 3. 节点检查 | 调用的节点是否存在 | `aaa_bbb_ccc` 节点未注册 |
| 4. 参数检查 | 字面量参数类型是否正确 | `keyword=123`，期望 `str` |
| 5. Artifact 类型检查 | 输入类型是否匹配 | `MarketAnalysis` 流入期望 `ProductCollection` 的节点 |
| 6. 图检查 | 是否存在循环依赖 | A→B→C→A |
| 7. 业务规则检查 | 是否违反跨域约束（多插件 import、跨插件数据引用） | `import amazon` + `import tiktok` 同时出现 |
| 8. 输出检查 | output 引用的 Artifact 是否存在 | `output report` 但 `report` 未定义 |

### 输出格式

Linter 应输出**结构化 JSON 错误**，以便 AI 理解并自动修复：

```json
{
  "type": "ArtifactTypeMismatch",
  "line": 12,
  "node": "market_analysis",
  "input": "products",
  "expected": "ProductCollection",
  "actual": "ReviewAnalysis"
}
```

### 系统分层

```
Parser    →  BCL → AST
Linter    →  AST  → Error[]
GraphBuilder → AST → DAG
Executor  →  DAG  → Result
```

初期优先开发 Parser + Linter，再开发 Executor。

---

## 六、Artifact 生命周期

Artifact 为执行期间的临时产物，全部驻留内存。图执行完毕后，中间产物随 ExecutionContext 销毁而释放，仅将 `outputs` 中声明的最终结果返回给 Agent。

系统当前业务规模无需引入分级存储（文件/缓存/数据库），不做提前优化。若未来单次执行数据量显著增长，届时再考虑引入 `ReferenceArtifact` 等机制。

---

## 七、节点注册与能力发现（NodeRegistry）

Agent 通过 **NodeRegistry** 发现可用能力：

```python
{
    "name": "sales_analysis",
    "plugin": "amazon",
    "description": "Analyze product sales data",
    "inputs": {"products": "ProductCollection"},
    "output_key": "sales_metrics",
    "output_type": "SalesMetrics",
    "parameters": {"min_sales": "int"}
}
```

NodeRegistry 的重要性与 BCL 同等——Agent 依赖它来规划和生成 BCL。

---

## 八、Graph 构建策略

采用 **Route A：Agent 编写完整 BCL**。

- Agent 负责描述完整的分析流程（调用哪些节点、如何连接）
- Runtime 只负责解析、校验、构图、执行
- 不与"Agent 只描述目标、Runtime 自动规划"的路线混淆

这是由系统定位决定的：本系统是为 Agent **提供能力**，而非**替 Agent 做决策**。

---

## 九、跨数据库/跨插件分析——不在系统范围内

### 核心原则

**本系统不允许跨数据库、跨插件的数据融合。** 一次 BCL 执行严格限定在单一插件领域内。

### Agent 如何做多源分析

Agent 如需综合分析多个数据源（如 Amazon + Google Trends + TikTok），由 Agent 分别在多次独立的系统调用中获取各领域的最终分析结果，然后在自身推理层完成综合判断。

```
Agent
  ├─ 调用 Amazon 插件 → 获取 SalesMetrics、CompetitionMetrics 等
  ├─ 调用 Google 插件  → 获取 TrendMetrics
  ├─ 调用 TikTok 插件  → 获取 HeatMetrics
  │
  └─ Agent 自行综合推理 → 得出最终结论
```

系统只负责在每个插件领域内独立、完整地产出结构化分析数据，**不参与跨域数据的关联、转换或融合**。

---

## 十、关键设计决策速查

| # | 决策 | 状态 |
|---|------|------|
| 1 | 废弃 Source/Transform/Sink，采用 Node + Graph + Artifact | ✅ 确定 |
| 2 | ExecutionContext 简化：artifacts/outputs/metadata，中间产物用完即弃 | ✅ 确定 |
| 3 | Node 单一输出（output_key + output_type），多值拆分为多个节点分别调用 | ✅ 确定 |
| 4 | BCL 自建语言已废弃，改用 Python SDK + 延迟执行 Graph | 🔄 已更新 |
| 5 | Python SDK 中变量引用直接用 Python 变量名，无需 @ 前缀 | 🔄 已更新 |
| 6 | 引入 ArtifactType 类型系统，类型兼容用 issubclass | ✅ 确定 |
| 7 | 三层 Artifact：RawData → Metric → Aggregation | ✅ 确定 |
| 8 | 数据绝不跨领域，一次 BCL 执行仅限单一插件，跨源综合由 Agent 自行完成 | ✅ 确定 |
| 9 | 静态检查器分层：语法→符号→节点→参数→类型→图→业务→输出 | ✅ 确定 |
| 10 | Parser + Linter 优先于 Executor 开发 | ✅ 确定 |
| 11 | Agent 写完整 BCL（Route A），Runtime 不自动规划 | ✅ 确定 |
| 12 | 系统不做 AI 推理，只产出结构化数据 | ✅ 确定 |
| 13 | BCL 不支持 if/while/for 等控制流；布尔逻辑通过 Node 参数 + 图结构表达 | ✅ 确定 |
| 14 | 多表 Join 通过 Source 构造领域聚合对象解决，不修改协议 | ✅ 确定 |
| 15 | NodeRegistry 作为 Agent 能力发现机制 | ✅ 确定 |
