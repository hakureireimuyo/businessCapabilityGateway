# 02 — Tag 数据库实现

> **所属项目**：Business Capability Gateway + Tag Alignment + Gallery Pipeline
> **本文档定位**：Pipeline 第 2 阶段——Tag 索引结构、fuzzy matching 算法、Tag Alignment Plugin 节点定义、Plugin API 协议
> **上游文档**：[01-用户意图与Agent语义拆解](./01-用户意图与Agent语义拆解.md)
> **下游文档**：[03-Tag与URL转换](./03-Tag与URL转换.md)
> **最后更新**：2026-06-14

---

## 一、概述

### 1.1 文档定位

Tag Alignment Plugin 是本 Pipeline 中唯一与 tag 数据库交互的组件。它不参与语义理解，只做字符串匹配和 count 排序。

```
Agent（发出 {token, aliases[], site}）
  │
  ▼
Tag Alignment Plugin
  ├── fuzzy match（每个 alias → 数据库中 tag 表）
  ├── 汇总去重
  ├── 按 count 降序排序
  └── 返回 top 3
  │
  ▼
Agent（判断语义契合度 + 选择）
```

### 1.2 核心原则

- **不做语义推理**：Plugin 不判断 alias 和 tag 的语义关系，纯字符串匹配
- **不合成综合 score**：只返回 `{tag, count}`，count 最高的就是站点主流 tag
- **不做跨 token 分析**：每次请求独立处理一个 token
- **不限制数量**：固定返回 top 3，Agent 不需要的参数不暴露

---

## 二、Tag 索引结构

> 🚧 待后续对话补充。涉及：倒排索引设计、表结构、分站点存储策略、数据来源。

### 2.1 设计要点（占位）

- 倒排索引：alias → tag 列表
- count 字段：该 tag 在站点中的出现频次
- 分站点：每个站点独立索引（Pixiv、Danbooru、Gelbooru 等）

---

## 三、Fuzzy Matching 算法

> 🚧 待后续对话补充。涉及：匹配策略（前缀/子串/编辑距离）、中文/日文/英文的分词与匹配差异、性能考量。

### 3.1 设计要点（占位）

- 每个 alias 独立匹配
- 匹配结果汇总去重（同一个 tag 可能被多个 alias 匹配到）
- 按 count 降序排序
- Top 3 返回

---

## 四、Plugin 节点定义

### 4.1 Plugin 目录结构

```
plugins/tag_alignment/
├── plugin.py              # register() 入口
├── artifact_types.py      # ArtifactType 层次
├── nodes/
│   ├── source_nodes.py    # tag_query 入口节点
│   └── ...
├── services/
│   └── matching_service.py
└── repository/
    ├── tag_index.py       # 索引加载
    └── tag_repository.py  # 查询
```

### 4.2 节点：`tag_query`

**类型**：入口节点（`is_entry = true`，`input_count = 0`）

**功能**：接收一个 token + aliases + site，在 tag 数据库中查询匹配 tag，返回 top 3 候选（按 count 降序）。

**Node 协议声明**：

```python
class TagQueryNode(Node):
    name = "tag_query"
    plugin = "tag_alignment"
    description = "Query tag candidates by token and aliases, return top 3 by count"

    input_specs = {}

    output_spec = OutputSpec(
        key="tag_candidates",
        artifact_type=TagCandidateSet,
        description="Top 3 matching tags ordered by count DESC"
    )

    parameter_specs = {
        "token":    ParameterSpec("token", str, required=True, description="Original semantic token"),
        "aliases":  ParameterSpec("aliases", list, required=True, description="Alias list for fuzzy matching"),
        "site":     ParameterSpec("site", str, required=True, description="Target site identifier"),
    }
```

### 4.3 Agent 调用方式（Graph API）

Agent 通过 Gateway SDK 逐 token 调用：

```python
from gateway import Graph

g = Graph(plugin="tag_alignment")

result = g.tag_query(
    token="双马尾",
    aliases=["双马尾", "twintails", "twin tails", "ツインテール"],
    site="pixiv"
)

g.output(result)
final = g.execute()
```

---

## 五、Plugin API 协议

### 5.1 请求

```
{token: string, aliases: string[], site: string}
```

### 5.2 响应

```json
{
  "token": "双马尾",
  "candidates": [
    {"tag": "ツインテール", "count": 320000},
    {"tag": "twintails",   "count": 180000},
    {"tag": "twin_tails",  "count": 95000}
  ]
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `token` | string | 原始查询 token，回传用于 Agent 关联 |
| `candidates` | array | 候选 tag 列表，按 count 降序，最多 3 条 |
| `candidates[].tag` | string | 站点真实 tag 字符串 |
| `candidates[].count` | int | 该 tag 在站点的出现频次 |

**规则**：
- 固定按 count 降序，不做综合评分
- 固定返回 top 3
- 匹配不到时返回空 `candidates: []`

### 5.3 Agent 如何消费

Agent 收到 candidates 后：
1. 自行判断每个 candidate 与原始 term 是否语义契合
2. 排除概念不符的候选
3. 在契合的候选中选 count 最高的

---

## 六、ArtifactType 定义

```python
# artifact_types.py

from core.protocol.artifact import ArtifactType

class TagCandidate(ArtifactType):
    """单个候选 tag"""
    pass

class TagCandidateSet(ArtifactType):
    """一个 token 的候选 tag 集合。
    包含 token 和 top 3 candidates，按 count 降序。
    """
    pass
```

---

> **下一份文档**：[03-Tag与URL转换](./03-Tag与URL转换.md) — OR 展开算法、平面 tag 组生成、站点 URL 适配
