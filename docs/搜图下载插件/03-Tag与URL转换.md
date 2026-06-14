# 03 — Tag 与 URL 转换

> **所属项目**：Business Capability Gateway + Tag Alignment + Gallery Pipeline
> **本文档定位**：Pipeline 第 3 阶段——接收 Tag IR，展开 OR 组，生成平铺 tag 组，转换为站点搜索 URL
> **上游文档**：[02-Tag数据库实现](./02-Tag数据库实现.md)
> **下游文档**：[04-gallery-dl与Hydrus转换](./04-gallery-dl与Hydrus转换.md)
> **最后更新**：2026-06-14

---

## 一、概述

### 1.1 文档定位

转换层接收 Agent 产出的 Tag IR `{must, should, not}`，执行三个步骤后输出平铺的 tag 组，每组对应一个搜索 URL。

```
Tag IR → OR 展开 → 平铺 tag 组 → 站点 URL 生成 → 搜索 URL 列表
```

### 1.2 核心职责

| 步骤 | 职责 | 说明 |
|------|------|------|
| 1. OR 展开 | Cartesian product over `should` groups | 将 OR 组展开为多组平面 tag |
| 2. 附加 must | 每组附加全部 `must` tag | AND 约束 |
| 3. 应用 not | 每组标记排除 tag | NOT 全局过滤 |
| 4. URL 生成 | 将每组平面 tag 转为站点搜索 URL | 站点特定适配 |

### 1.3 Agent 与本层的关系

- Agent **不展开** OR：Tag IR 保留 `should` 的 OR 组结构
- Agent **不关心** URL：URL 生成完全是本层的职责
- 本层**不参与语义**：输入 IR 中所有 tag 已经是站点的最终 tag 字符串

---

## 二、输入格式

### 2.1 Tag IR

转换层接收 [01-用户意图与Agent语义拆解](./01-用户意图与Agent语义拆解.md) 产出的 `tag_ir` 字段：

```json
{
  "must": ["初音ミク", "ツインテール"],
  "should": [["メイド服", "着物"]],
  "not": ["R-18"]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `must` | `string[]` | 强制 AND tag，每条结果必须全部包含 |
| `should` | `string[][]` | OR 组。每个子数组是一个互斥替换集合；组间 AND，组内 OR |
| `not` | `string[]` | 排除 tag，每条结果均过滤 |

> 注意：`should` 为空数组表示纯 AND 查询；`must` 为空是合法的（纯 OR 查询）；两者均为空是非法输入。

---

## 三、OR 展开算法

### 3.1 算法描述

```
输入: must = [m1, m2, ...], should = [[s1a, s1b, ...], [s2a, s2b, ...], ...], not = [n1, n2, ...]

Step 1: Cartesian product over should groups
  should = [[s1a, s1b], [s2a, s2b]]
  → [[s1a, s2a], [s1a, s2b], [s1b, s2a], [s1b, s2b]]

Step 2: 每组附加 must
  → [must + [s1a, s2a], must + [s1a, s2b], ...]

Step 3: 每组附加 not
  → 每条结果为 {and: [...], not: [...]}
```

### 3.2 展开实例

**输入**：
```json
{
  "must": ["立ち絵"],
  "should": [
    ["初音ミク", "鏡音リン"],
    ["ツインテール", "ショートヘア"],
    ["メイド服", "着物"]
  ],
  "not": ["R-18", "昼間"]
}
```

**展开**：`|should[0]| × |should[1]| × |should[2]| = 2 × 2 × 2 = 8 条`

```
组1: [立ち絵, 初音ミク, ツインテール, メイド服]  NOT [R-18, 昼間]
组2: [立ち絵, 初音ミク, ツインテール, 着物]      NOT [R-18, 昼間]
组3: [立ち絵, 初音ミク, ショートヘア, メイド服]  NOT [R-18, 昼間]
组4: [立ち絵, 初音ミク, ショートヘア, 着物]      NOT [R-18, 昼間]
组5: [立ち絵, 鏡音リン, ツインテール, メイド服]  NOT [R-18, 昼間]
组6: [立ち絵, 鏡音リン, ツインテール, 着物]      NOT [R-18, 昼間]
组7: [立ち絵, 鏡音リン, ショートヘア, メイド服]  NOT [R-18, 昼間]
组8: [立ち絵, 鏡音リン, ショートヘア, 着物]      NOT [R-18, 昼間]
```

### 3.3 简单例子

**无 OR**（纯 AND）：
```
输入: must=["A","B"], should=[], not=["C"]
展开: 1 条 → {and: ["A","B"], not: ["C"]}
```

**单 OR 组**：
```
输入: must=["A"], should=[["B","C"]], not=[]
展开: 2 条 → {and: ["A","B"]}, {and: ["A","C"]}
```

**纯 OR**（无 must）：
```
输入: must=[], should=[["A","B"],["C","D"]], not=[]
展开: 4 条 → {A,C}, {A,D}, {B,C}, {B,D}
```

### 3.4 展开输出格式

每条展开结果为一个平面 tag 组：

```jsonc
{
  "and": ["tag1", "tag2", ...],   // 全部 AND tag
  "not": ["tag3", ...]            // 排除 tag（可选，空则省略）
}
```

---

## 四、NOT 处理

### 4.1 语义

NOT 是**全局过滤器**：不参与 Cartesian product，展开后每条结果统一附带。

### 4.2 处理层级

NOT 的最终生效位置取决于目标站点的能力：

| 站点能力 | NOT 处理方式 |
|---------|-------------|
| 原生支持排除 tag | 在 URL 中编码为排除参数 |
| 不支持排除 | 下载层（04）客户端过滤，或本层标记 `not_supported` 向上游报错 |

### 4.3 错误处理

如果本层（转换层）或下游（下载层）当前未实现 NOT，收到含 `not` 的 IR 时应返回明确错误 `NOT_NOT_SUPPORTED`，而非静默忽略。

> 具体实现待后续对接。当前 NOT 在 Tag IR 中已预留位置。

---

## 五、URL 生成

> 🚧 待后续对话补充。涉及：各站点搜索 URL 格式适配（Pixiv、Danbooru、Gelbooru 等）、AND tag 如何编码（空格/加号/AND 关键字）、NOT tag 如何编码、分页参数。

### 5.1 设计要点（占位）

- 每个平铺 tag 组生成一个搜索 URL
- URL 格式取决于站点
- 上一步的展开结果 → URL 列表 → 传递给 [04-gallery-dl与Hydrus转换](./04-gallery-dl与Hydrus转换.md)

---

## 六、输出格式

转换层最终输出：

```jsonc
{
  "requests": [
    {
      "url": "https://www.pixiv.net/tags/初音ミク/artworks?s_mode=s_tag&word=ツインテール メイド服",
      "and": ["初音ミク", "ツインテール", "メイド服"],
      "not": ["R-18"]
    },
    {
      "url": "https://www.pixiv.net/tags/初音ミク/artworks?s_mode=s_tag&word=ツインテール 着物",
      "and": ["初音ミク", "ツインテール", "着物"],
      "not": ["R-18"]
    }
  ]
}
```

`requests[]` 中每条为一个独立下载任务，传递给 gallery-dl 执行。

---

## 七、边界条件

| 条件 | 处理 |
|------|------|
| `should` 为空 | 无 Cartesian 展开，只返回 1 条（must + not） |
| `must` 为空 | 合法，展开结果只含 should 的 Cartesian 组合 |
| `must` 和 `should` 均为空 | 非法输入，返回错误 |
| `not` 为空 | 正常，不附加 NOT 过滤 |
| 展开数量过大 | 设置上限（如最多 64 条），超出返回错误 |
| 某站点不支持 NOT | 返回 `NOT_NOT_SUPPORTED` |

---

> **下一份文档**：[04-gallery-dl与Hydrus转换](./04-gallery-dl与Hydrus转换.md) — gallery-dl 下载、metadata 解析、Hydrus 入库
