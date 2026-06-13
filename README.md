# Business Capability Gateway

## 项目简介

**Business Capability Gateway（业务能力网关）** 是一个面向 AI Agent 的轻量级协议网关。
它不执行任何业务逻辑，只负责插件发现与加载、脚本沙箱执行、结果标准化返回。
Agent 将要执行的能力组合编写为 Python 脚本提交给网关，网关在沙箱中安全执行并返回结果——Agent 只能拿到最终业务结果，无法接触中间数据和原始数据。
所有复杂业务能力都封装在插件内部，网关本身对业务一无所知。

## 核心理念

- 网关负责协议
- 插件负责业务
- 数据库负责存储

**Agent 永远不能接触原始数据。**
所有数据查询、过滤、分析、评分都在插件内部处理，Agent 只能拿到最终业务结果。

## 主要功能

- 插件自动发现与加载
- 通过 Python SDK 脚本组合插件能力
- 节点注册与协议发现（输入/输出/参数类型约束）
- 脚本沙箱安全执行（AST 校验 + 受限 builtins + 超时控制）
- 统一成功/失败响应格式

## 目录结构

```
businessCapabilityGateway/
├── api/                       # HTTP 接口层
├── core/                      # 网关核心模块
│   ├── plugin/                # 插件加载器
│   ├── protocol/              # Node / Artifact 协议定义
│   ├── registry/              # 节点注册中心
│   ├── runtime/               # ExecutionContext、响应封装
│   └── sandbox/               # AST 校验 + 沙箱执行
├── docs/                      # 项目说明与开发规范
├── gateway_sdk/               # Agent 侧 Python SDK
├── plugins/                   # 插件目录
├── sandbox/                   # 本地测试脚本（直接运行，不走服务）
├── tests/                     # 测试
├── gateway.py                 # SDK 入口（Agent 直接使用）
├── main.py                    # 服务启动/停止入口
├── test_client.py             # 集成测试客户端
├── requirements.txt           # 依赖
└── README.md                  # 项目说明
```

## 架构概览

```
Agent（外部）
  │
  │  1. 编写 Python 脚本（使用 Gateway SDK 的 Graph API）
  │  2. POST /execute  将脚本以 text/plain 提交
  │
  ▼
Gateway Sandbox
  │
  ├─ AST 校验        —— 拦截 import / eval / open 等危险操作
  ├─ exec (受限)     —— 在受限 __builtins__ 下执行整个脚本
  │   └─ 脚本执行期间：Graph().xxx() 调用即校验并执行 Node
  └─ 提取 result     —— 从脚本命名空间取出 result 变量
  │
  ▼
Agent  ←  JSON Response  {"success": true, "data": {...}}

Agent 全程只知道：发送了什么脚本、拿到了什么结果。
中间执行过程对 Agent 完全透明（不可见）。
```

## API 说明

### 健康检查

```http
GET /health
```

### 能力发现

列出所有插件：

```http
GET /plugins
```

列出指定插件的所有节点：

```http
GET /plugins/{plugin_name}/nodes
```

### 执行能力

Agent 通过 Python SDK 脚本提交执行请求：

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
    "message": "Type mismatch: ..."
  }
}
```

## SDK 用法示例

### 简单链式

```python
from gateway import Graph

g = Graph(plugin="amazon")
products = g.keyword_search(keyword="halloween garland")
filtered = g.filter(products=products, price_gte=10.0, price_lte=50.0)
analysis = g.market_analysis(products=filtered)
g.output(analysis)
result = g.execute()
```

### 并行分支

```python
g = Graph(plugin="amazon")
products = g.keyword_search(keyword="halloween garland")
sales = g.sales_analysis(products=products)
reviews = g.review_analysis(products=products)
score = g.market_score(sales=sales, reviews=reviews)
g.output(score)
result = g.execute()
```

### 多输出

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

## 执行机制

网关不维护显式的图数据结构，也不做集中式的图校验。图结构由 **Python 自身语法**隐式表达：

- Agent 编写的 Python 脚本中，变量赋值和数据传递自然形成节点间的依赖关系（下游节点必须先拿到上游的输出）
- Python 解释器的执行顺序天然保证 DAG——循环依赖在语法层面就无法表达
- `g.xxx()` 调用时即时校验参数/输入/类型，校验通过后立即执行 Node
- `g.output()` 标记最终产出，`g.execute()` 收集已标记结果为 dict

**对 Agent 而言，整个过程是黑盒**：提交一段 Python 脚本 → 拿到成功/失败的 JSON 结果。中间执行了什么节点、数据如何流转，Agent 一概不知。

## 常见错误码

- `EMPTY_REQUEST`：请求体为空
- `INVALID_SCRIPT`：脚本语法错误或包含禁止操作
- `PLUGIN_NOT_FOUND`：插件不存在
- `NODE_NOT_FOUND`：节点不存在
- `INVALID_PARAMS`：参数校验失败
- `INVALID_GRAPH`：脚本执行中校验失败（类型不匹配、必填输入未连接、参数不合法等）
- `EXECUTION_TIMEOUT`：脚本执行超时
- `INTERNAL_ERROR`：内部错误

## 插件开发指南

- 插件由 `plugins/<plugin_name>/plugin.py` 注册节点
- 插件只暴露 `Node`，不直接暴露 Repository、Service 等内部实现
- Node 必须无状态，每次 execute() 独立执行
- Node 通过 `input_specs` / `output_spec` / `parameter_specs` 声明协议
- 插件内部应遵循：Node → Service → Repository
- 新增插件时不需要修改网关核心代码

### 定义 Artifact 类型

```python
from core.protocol.artifact import ArtifactType

class MyAnalysisResult(ArtifactType):
    pass
```

### 实现 Node

```python
from core.protocol.node import Node
from core.protocol.artifact import Artifact, InputSpec, OutputSpec, ParameterSpec

class MyNode(Node):
    name = "my_node"
    plugin = "my_plugin"
    description = "Does something useful"

    input_specs = {
        "products": InputSpec(name="products", artifact_type=ProductCollection, required=True),
    }
    output_spec = OutputSpec(key="result", artifact_type=MyAnalysisResult)
    parameter_specs = {
        "threshold": ParameterSpec("threshold", float, required=False, default=0.5),
    }

    def execute(self, inputs, params, context):
        data = inputs["products"].data
        threshold = params.get("threshold", 0.5)
        # ... business logic ...
        return Artifact(key="result", type=MyAnalysisResult, data=result, produced_by="my_node")
```

### 注册插件

```python
# plugins/my_plugin/plugin.py
from core.registry.node_registry import register_nodes

def register():
    register_nodes("my_plugin", [MyNode(), ...])
```

## 运行方式

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 启动服务：

```bash
python main.py           # 默认 127.0.0.1:8765
python main.py start     # 同上，显式子命令
python main.py --port 9000
python main.py start --host 0.0.0.0 --port 8765
```

3. 运行集成测试：

```bash
# 先启动服务
python main.py start
# 另开终端运行测试
python test_client.py
```

4. 停止服务：

```bash
python main.py stop
python main.py status    # 查看运行状态
```

## 备注

此项目面向未来扩展，支持新增插件而不改网关核心，遵循"Open for Extension, Closed for Modification"的设计原则。
