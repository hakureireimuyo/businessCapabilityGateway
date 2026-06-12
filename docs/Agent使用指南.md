# Agent 使用指南

本文档面向 AI Agent（以及人工操作者），说明如何发现、理解并调用网关提供的业务能力。

---

## 1. 核心理念

```
你（Agent）只负责：选择"做什么"
网关 + 插件负责：决定"怎么做"
```

你永远不需要知道：
- 数据库有哪些表
- SQL 怎么写的
- 过滤/聚合/评分的具体算法

你只需要知道：
- 有哪些插件可用
- 每个插件能做什么
- 如何组合它们完成一次业务查询

---

## 2. 服务生命周期

网关是一个本地 HTTP 服务，使用前需要先启动：

```bash
# 启动（Agent 应在会话开始时执行）
python main.py start

# 默认监听 http://127.0.0.1:8765
```

服务启动后，所有通信通过 HTTP 协议完成。

---

## 3. 接口一览

所有路径中的 `<plugin>` 替换为实际插件名。

### 3.1 健康检查

```
GET /health
→ {"status": "ok"}
```

### 3.2 发现插件

```
GET /plugins
→ ["amazon", "steam", "erp"]
```

返回所有已加载的插件名列表。

### 3.3 查看插件能力

```
GET /plugins/<plugin>/actions
```

返回该插件所有可用 Node 的完整描述，包括：
- `name` — 调用时使用的节点名
- `type` — source / transform / sink
- `description` — 业务说明
- `parameters` — 参数 schema（名称、类型、是否必填、默认值）
- `input` — 接受的输入类型
- `output_schema` — 输出的字段和含义

### 3.4 查看所有能力

```
GET /capabilities
```

返回所有插件的完整能力描述。

### 3.5 执行管道

```
POST /execute
Content-Type: text/plain

<BCL 指令字符串>
```

返回统一格式的 JSON。

---

## 4. BCL 指令语法

### 4.1 基本格式

```text
<plugin>/<node_name>&<param1>=<value1>&<param2>=<value2>
> <node_name>&<param>=<value>
> <node_name>()
```

- 第一行：`插件名/节点名&参数1=值1&参数2=值2`
- 后续行：`> 节点名&参数=值`
- 无参数的节点：`节点名()`
- 换行符分隔节点

### 4.2 管道规则

管道描述了数据从数据库到最终结果的处理流程：

```
Source Node（数据来源）
  ↓
Transform Node（数据处理/过滤）
  ↓
Transform Node（可多个）
  ↓
Sink Node（输出结果）
```

**规则**：
- 必须以 Source 开头，以 Sink 结尾
- Transform 放在中间，可有多个
- Source 不能出现在中间，Sink 不能出现在中间

### 4.3 Sink 参数 ≠ 过滤条件

**重要区分**：Sink 节点的参数控制的是"怎么分析"，不是"分析什么"。缩小数据范围永远通过 Transform 节点完成。

```
❌ 错误理解：
   amazon/search_by_keyword&keyword=xxx > market_analysis&price_gte=10
   以为 market_analysis 的 price_gte 参数能过滤数据

✅ 正确用法：
   amazon/search_by_keyword&keyword=xxx > filter&price_gte=10 > market_analysis()
   Transform 负责过滤 → Sink 负责分析
```

| 参数类型 | 放在哪个节点 | 示例 |
|----------|-------------|------|
| 数据范围（价格、评分、分类……） | Transform（filter） | `filter&price_gte=10&rating_gte=4.0` |
| 分析方法（阈值、算法、输出条数……） | Sink | `find_opportunities&max_review=50` |

### 4.4 示例

```text
amazon/search_by_keyword&keyword=halloween garland&limit=50
> filter&price_gte=10&review_lt=100
> market_analysis()
```

这表示：
1. 在 amazon 数据库中搜索 "halloween garland"，最多 50 条
2. 过滤出价格 ≥ $10 且评论数 < 100 的产品
3. 对过滤结果执行市场分析

---

## 5. 统一返回格式

### 5.1 成功

```json
{
    "success": true,
    "data": {
        "market_size": 9,
        "avg_price": 23.33,
        "competition_score": 50
    },
    "message": "Execution succeeded (0ms)"
}
```

### 5.2 失败

```json
{
    "success": false,
    "error": {
        "code": "NODE_NOT_FOUND",
        "message": "Node 'filter' not found in plugin 'amazon'"
    }
}
```

### 5.3 错误码

| 错误码 | 含义 | 如何应对 |
|--------|------|---------|
| `INVALID_DSL` | BCL 语法错误 | 检查指令格式 |
| `PLUGIN_NOT_FOUND` | 插件名错误 | 用 GET /plugins 确认名称 |
| `NODE_NOT_FOUND` | 节点名错误 | 用 GET /plugins/{p}/actions 确认名称 |
| `INVALID_PARAMS` | 参数缺失或类型错误 | 根据 parameters schema 修正 |
| `INVALID_PIPELINE` | 管道结构非法 | 检查 Source-Sink 顺序 |
| `RESULT_TOO_LARGE` | 结果过大 | 增加过滤条件缩小范围 |
| `EXECUTION_TIMEOUT` | 超时 | 减少数据量或简化管道 |

---

## 6. 典型工作流

### 步骤 1：启动服务

```bash
python main.py start
```

### 步骤 2：发现可用插件

```
GET /plugins
→ ["amazon"]
```

### 步骤 3：查看 Amazon 有什么能力

```
GET /plugins/amazon/actions
```

从返回结果中了解：
- 有哪些 Source（搜索方式）
- 有哪些 Transform（可用的过滤/排序）
- 有哪些 Sink（可以产出的分析报告）

### 步骤 4：组合管道并执行

根据用户的业务问题选择合适的节点组合：

```
用户问："halloween garland 这个关键词的市场竞争怎么样？"

你组合：
amazon/search_by_keyword&keyword=halloween garland
> market_analysis()
```

```
用户问："$10-$50 价格区间内，评论少于 100 的蓝牙耳机有哪些机会？"

你组合：
amazon/search_by_keyword&keyword=bluetooth headphone
> filter&price_gte=10&price_lte=50&review_lt=100
> find_opportunities()
```

### 步骤 5：解释结果给用户

将返回的 JSON 数据翻译成自然语言回答。

---

## 7. 最佳实践

### 7.1 先发现再调用

**永远不要**硬编码节点名或参数。每次会话开始时先调用：
```
GET /plugins
GET /plugins/<name>/actions
```

因为插件的节点可能已更新。

### 7.2 使用精确参数缩小范围

模糊查询 → 更多数据 → 更慢 → 更可能超限。
尽量使用具体的参数值。

### 7.3 一次请求完成完整分析

不需要多次往返：
- ❌ 先查数据 → 拿到 handle → 再分析
- ✅ 一条 BCL 管道从头到尾

网关是无状态的，不支持分步操作。

### 7.4 处理错误

遇到错误时：
1. 读 `error.code`
2. 根据上表确定原因
3. 修正 BCL 指令重试

### 7.5 参数值中的特殊字符

参数值包含 `&`、`>`、`=` 等特殊字符时，用 `key=value` 格式直接传递，解析器会正确处理。空格不需要转义。

---

## 8. curl 调用参考

Agent 可以直接使用以下 curl 模式生成 HTTP 调用：

```bash
# 发现插件
curl -s http://localhost:8765/plugins

# 查看能力
curl -s http://localhost:8765/plugins/amazon/actions

# 执行管道
curl -s -X POST http://localhost:8765/execute \
  --data-binary "amazon/search_by_keyword&keyword=halloween garland
> filter&price_gte=10
> market_analysis()"
```

**注意**：`--data-binary` 而非 `-d`，以保留换行符。

---

## 9. Python 调用参考

```python
import urllib.request
import json

def call_gateway(bcl: str) -> dict:
    """调用网关执行 BCL 管道"""
    req = urllib.request.Request(
        "http://localhost:8765/execute",
        data=bcl.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

# 示例
result = call_gateway(
    "amazon/search_by_keyword&keyword=halloween garland\n"
    "> filter&price_gte=10\n"
    "> market_analysis()"
)
print(result["data"]["competition_score"])
```

---

## 10. 安全约束

作为 Agent，你必须理解并遵守以下约束：

1. **你永远拿不到未经处理的原始数据库数据** — 网关只返回 Sink 节点计算后的业务结果，不会返回数据库游标或未加工的数据行。但如果某个 Sink 的业务目标就是找到具体产品（如"发现最畅销的商品"），此时产品信息本身就是业务结果，可以被返回
2. **你不能探索数据库结构** — 没有"列出所有表"或"查看表字段"的接口
3. **你不能执行任意查询** — 只能调用插件预先定义好的 Node
4. **你只能编排业务流程** — 选择哪些 Node、传什么参数、按什么顺序
