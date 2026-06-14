# 01 — 用户意图与 Agent 语义拆解

> **所属项目**：Business Capability Gateway + Tag Alignment + Gallery Pipeline
> **本文档定位**：Pipeline 第 1 阶段——从用户自然语言到结构化 IR，再经由 Plugin 候选检索，产出最终 tag IR
> **下游文档**：[02-Tag数据库实现](./02-Tag数据库实现.md) → [03-Tag与URL转换](./03-Tag与URL转换.md) → [04-gallery-dl与Hydrus转换](./04-gallery-dl与Hydrus转换.md)
> **最后更新**：2026-06-14

---

## 一、概述

### 1.1 文档定位

本文档定义 Pipeline 中 **Agent 负责的全部工作**，分两个阶段：

```
阶段 A：用户自然语言 → 中文 IR（约束代数）
阶段 B：中文 IR → Tag IR（经 Plugin 候选检索 + Agent 选择）
```

阶段 B 之后，产出的 Tag IR 直接交付 [03-Tag与URL转换](./03-Tag与URL转换.md) 处理。

```
┌──────────────┐     ┌──────────────────────┐     ┌───────────────────────┐     ┌──────────────────────┐
│  用户自然语言  │ ──→ │  Agent 语义解析 + IR  │ ──→ │  Tag Alignment Plugin │ ──→ │  Tag IR (最终输出)     │
│  (自由文本)    │     │  (阶段 A)             │     │  (候选检索，阶段 B)     │     │  → 交付 03-转换层      │
└──────────────┘     └──────────────────────┘     └───────────────────────┘     └──────────────────────┘
```

### 1.2 核心职责归属

| 职责 | 归属 | 说明 |
|------|------|------|
| 解析用户意图 | **Agent** | 唯一语义层 |
| 生成 IR（must/should/not） | **Agent** | 从自然语言识别 AND/OR/NOT 关系 |
| 生成 alias 集 | **Agent** | 自由扩展近义词/翻译/变体 |
| 候选 tag 检索 | **Plugin** | 纯字符串匹配，按 count 降序返回 top 3 |
| 最终 tag 选择 | **Agent** | 从候选中判断语义契合度，选 count 最高的匹配 tag |
| OR 展开 + URL 生成 | **转换层（03）** | Agent 不参与 |
| 执行 | **Gateway** | 无状态沙箱 |

### 1.3 关键原则

- **语义只存在于 Agent**：Tag DB 只做字符串匹配和 count 排序，不做语义推理。Agent 从候选中选择 tag 时自行判断语义是否契合。
- **Agent 不展开 OR**：IR 中的 `should` 保留 OR 组结构，展开（笛卡尔积）是转换层（03）的职责。
- **Plugin 不做综合评分**：Plugin 只返回 `{tag, count}`，不合成综合 score。count 高的就是站点主流 tag。Agent 结合 count 和语义契合度做选择。
- **NOT 是全局过滤器**：`not` 对每条展开结果都生效，不参与 Cartesian product。
- **IR 表达约束集合，不表达执行顺序**：`must`/`should`/`not` 是一组约束声明，顺序无关。

---

## 二、用户输入模型

### 2.1 输入形式

系统接受**自由格式自然语言文本**作为唯一入口。用户不需要学习任何查询语法。

**典型输入示例**：

```
"初音未来 双马尾 女仆装"
"summer beach swimsuit pink hair"
"風景 富士山 桜"
"cat girl maid blue eyes -r18"
"初音未来 双马尾 女仆装或和服 不要R18"
"博丽灵梦或者魔理沙 站姿或者坐姿 背景有烟花 不要白天"
```

### 2.2 输入特征

| 特征 | 说明 |
|------|------|
| 语言 | 支持中文、英文、日文等多语言混合 |
| 分隔 | 以空格或自然语义边界分隔 |
| AND（默认） | 并列概念之间隐含 AND |
| OR | 通过「或」「或者」「or」连接同一替换集合 |
| NOT | 通过「不要」「排除」「非」「not」「!」标记要排除的概念 |
| 歧义 | 用户表达可能存在歧义，Agent 需结合上下文消歧 |

### 2.3 边界

- 用户输入**不直接**包含站点信息——站点选择是 Agent 的决策
- 用户**不需要**知道目标站点的 tag 词汇表
- 用户**不需要**指定组合运算符——Agent 从自然语言中推断

---

## 三、阶段 A：自然语言 → 中文 IR

### 3.1 IR 格式定义

IR（Intermediate Representation）是 Agent 产出、转换层消费的稳定结构化格式。格式本身就是约束声明，不表达执行顺序。

```jsonc
{
  "must": [],      // string[]  — 强制 AND：所有 tag 必须同时满足
  "should": [],    // string[][] — OR 组：每个子数组是一个替换集合，组间 AND，组内 OR
  "not": []        // string[]  — 排除：每条结果均排除包含这些 tag 的内容
}
```

**字段语义**：

| 字段 | 类型 | 语义 | 转换层处理 |
|------|------|------|-----------|
| `must` | `string[]` | 强制 AND 约束，所有元素在每条结果中都必须出现 | 附加到每条展开结果 |
| `should` | `string[][]` | OR 约束集合。每个子数组是一个 OR 组（同一替换集合），组内元素互斥选择；组间 AND | Cartesian product 展开 |
| `not` | `string[]` | 全局排除约束，每条结果都要过滤 | NOT filter 应用于所有结果 |

### 3.2 从自然语言到 IR 的解析规则

Agent 解析自然语言时遵循以下规则：

#### AND（must）

连续并列的独立概念，默认 AND 关系，归入 `must`。

```
输入: "初音未来 双马尾 女仆装"
IR:   { "must": ["初音未来", "双马尾", "女仆装"], "should": [], "not": [] }
```

#### OR（should）

「或」「或者」「or」连接的项属于同一个 OR 组（互斥替换集合），归入 `should` 的一个子数组。

规则：
- 一个「或」连接的前后项属于同一 OR 组
- 连续的多个「或」链归入同一个 OR 组：`A或B或C` → `["A","B","C"]` 在一个组内
- `must` 项或 `not` 项会截断 OR 组的合并——OR 组只由连续的「或」链构成

```
输入: "女仆装或和服"
IR:   { "must": [], "should": [["女仆装", "和服"]], "not": [] }
```

```
输入: "初音未来 女仆装或和服"
IR:   { "must": ["初音未来"], "should": [["女仆装", "和服"]], "not": [] }
```

```
输入: "猫耳 女仆装或和服或水手服 双马尾"
IR:   { "must": ["猫耳", "双马尾"], "should": [["女仆装", "和服", "水手服"]], "not": [] }
```

#### NOT

「不要」「排除」「非」「not」「!」「没有」标记排除概念，归入 `not`。

NOT 是**全局过滤器**：不参与 Cartesian product，展开后在每条结果上统一应用。

```
输入: "不要R18"
IR:   { "must": [], "should": [], "not": ["R18"] }
```

NOT 不会卷入周围的 OR 组：

```
输入: "猫耳 不要R18 女仆装或和服"
IR:   { "must": ["猫耳"], "should": [["女仆装", "和服"]], "not": ["R18"] }
```

#### 多 OR 组

输入中包含多组 OR，每组独立成一个 `should` 子数组：

```
输入: "博丽灵梦或者魔理沙 站姿或者坐姿 背景有烟花 不要白天"
IR:
{
  "must": ["背景有烟花"],
  "should": [
    ["博丽灵梦", "魔理沙"],
    ["站姿", "坐姿"]
  ],
  "not": ["白天"]
}
```

**OR 组分裂规则（AND 截断）**：

```
输入: "初音未来 双马尾或短发 女仆装或和服 不要R18"
IR:
{
  "must": ["初音未来"],
  "should": [
    ["双马尾", "短发"],
    ["女仆装", "和服"]
  ],
  "not": ["R18"]
}
```

### 3.3 复杂示例

```
输入: "立绘 初音未来或镜音铃 双马尾或短发 女仆装和和服任选 不要R18 不要白天"
IR:
{
  "must": ["立绘"],
  "should": [
    ["初音未来", "镜音铃"],
    ["双马尾", "短发"],
    ["女仆装", "和服"]
  ],
  "not": ["R18", "白天"]
}
```

### 3.4 阶段 A 总结

Agent 的输出就是这份中文 IR。IR 不包含真正的 tag 字符串（那是阶段 B 的产物），保留用户的原始中文表达，为后续 alias 生成和 Plugin 检索保留完整的语义上下文。

---

## 四、阶段 B：中文 IR → Tag IR

阶段 B 将中文 IR 中的每个 term（`must`、`should` 各元素、`not` 各元素）替换为对应站点的实际 tag。

### 4.1 流程

```
中文 IR
  │
  ▼
Step 1: 提取所有 term（去重）
  ├── 遍历 must、should、not 中的所有 term
  └── 产出 term 清单
  │
  ▼
Step 2: 为每个 term 生成 alias 集
  ├── 翻译、同义词、变体
  └── 提升 Plugin 召回率
  │
  ▼
Step 3: 逐 term 调用 Plugin
  ├── 每个 term 独立发送至 Plugin
  ├── Plugin 返回 top 3 候选（按 count 降序）
  └── 不跨 term 检索
  │
  ▼
Step 4: Agent 逐 term 选择最终 tag
  ├── 从候选中判断语义契合度
  ├── 选 count 最高的语义匹配 tag
  └── 一词一选（即使 should 组里有多个 term，每个 term 独立选一个 tag）
  │
  ▼
Step 5: 组装 Tag IR
  └── 将选定的 tag 按原 IR 结构回填
```

### 4.2 Alias 生成

Agent 为每个 term 生成 alias 集，覆盖不同表达形式。alias 是**辅助召回工具**，不直接出现在最终 IR 中。

| 策略 | 说明 | 示例 |
|------|------|------|
| 翻译 | 中→英、中→日、英→中等 | "双马尾" → "twintails" |
| 同义词 | 语义等价的不同表达 | "女仆装" → "maid outfit", "maid uniform" |
| 缩写/全称 | 常见缩写展开 | "miku" ↔ "hatsune miku" |
| 变体 | 拼写变体、罗马字变体 | "初音ミク" → "hatsune miku" |

**约束**：
- alias 不能偏离原始语义（"cat" 不能 alias 成 "dog"）
- 不强制每个 term 都有 alias——简洁或罕见的 term 可以只有自身

### 4.3 Plugin 调用协议

Agent 向 Tag Alignment Plugin 发送单条查询：

**请求**：
```json
{
  "token": "双马尾",
  "aliases": ["双马尾", "twintails", "twin tails", "ツインテール"],
  "site": "pixiv"
}
```

**Plugin 响应**（按 count 降序，最多 3 条）：
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

> **重要**：Plugin 不返回综合 score。Agent 自行判断每个候选 tag 与原始 term 的语义契合度，然后选 count 最高的契合 tag。

详细 Plugin 实现见 [02-Tag数据库实现](./02-Tag数据库实现.md)。

### 4.4 Agent 选择逻辑

Plugin 返回 top 3 候选后，Agent 需要做最终选择。

**选择规则**：
1. 逐个判断候选 tag 是否与原始 term **语义契合**（Agent 用自身知识判断）
2. 排除概念不符的候选（如 alias "miku" 匹配到了 "Vocaloid"——上位概念，排除）
3. 在契合的候选中选 **count 最高**的
4. 如果 3 个候选都不契合，返回 count 最高的（作为 fallback）

**举例**：

```
term: "初音未来"
aliases: ["初音未来", "hatsune miku", "miku", "初音ミク"]

Plugin 返回:
  ┌─────────────────┬──────────┐
  │ tag             │ count    │
  ├─────────────────┼──────────┤
  │ Vocaloid        │ 2400000  │  → Agent判断：上位概念，不契合 ❌
  │ 初音ミク        │ 1200000  │  → 契合 ✅ 选 count 最高 = 1200000 ✅
  │ hatsune miku    │ 850000   │  → 契合，但count更低
  └─────────────────┴──────────┘

选择: "初音ミク"
```

**小众 tag 情况**（候选 count 都很小且接近）：Agent 难以凭 count 差距判断，需结合语义契合度仔细选择。极端情况下三选一均可接受。

### 4.5 一词选一

IR 中每个 term 独立选一个 tag。即使 `should` 组内有两个 term（代表同一维度两个互斥选项），每个 term 仍然各自独立选择一个 tag。

```
should: [["女仆装", "和服"]]
  → "女仆装" 独立检索，选 "メイド服"
  → "和服"   独立检索，选 "着物"
  → should 组变为: [["メイド服", "着物"]]
```

OR 组内的元素保持互斥关系，多选一是转换层展开时做的事。

### 4.6 组装 Tag IR

所有 term 替换完成后，按原 IR 结构回填，**保持 IR 结构不变**：

```
中文 IR:
{
  "must": ["初音未来", "双马尾"],
  "should": [["女仆装", "和服"]],
  "not": ["R18"]
}

Tag IR (Pixiv):
{
  "must": ["初音ミク", "ツインテール"],
  "should": [["メイド服", "着物"]],
  "not": ["R-18"]
}
```

---

## 五、Agent 最终输出

### 5.1 输出结构

Agent 完成阶段 A + B 后，产出 Tag IR 交付转换层：

```jsonc
{
  "pipeline_version": "1.0",
  "site": "pixiv",
  "tag_ir": {
    "must": ["初音ミク", "ツインテール"],
    "should": [["メイド服", "着物"]],
    "not": ["R-18"]
  },
  "meta": {
    "user_input": "初音未来 双马尾 女仆装或和服 不要R18"
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `pipeline_version` | string | Pipeline 版本号 |
| `site` | string | 目标站点标识 |
| `tag_ir` | object | Tag IR（`must`/`should`/`not`），所有 term 已替换为站点实际 tag |
| `tag_ir.must` | string[] | 强制 AND tag 列表 |
| `tag_ir.should` | string[][] | OR 组列表，每个子数组是互斥替换集合 |
| `tag_ir.not` | string[] | 排除 tag 列表 |
| `meta.user_input` | string | 原始用户输入（用于日志/调试） |

### 5.2 完整示例

**用户输入**：`"立绘 初音未来或镜音铃 双马尾或短发 女仆装和和服任选 不要R18 不要白天"`

**Agent 最终输出**（假设 Pixiv 站点）：

```json
{
  "pipeline_version": "1.0",
  "site": "pixiv",
  "tag_ir": {
    "must": ["立ち絵"],
    "should": [
      ["初音ミク", "鏡音リン"],
      ["ツインテール", "ショートヘア"],
      ["メイド服", "着物"]
    ],
    "not": ["R-18", "昼間"]
  },
  "meta": {
    "user_input": "立绘 初音未来或镜音铃 双马尾或短发 女仆装和和服任选 不要R18 不要白天"
  }
}
```

### 5.3 下游消费

转换层（[03-Tag与URL转换](./03-Tag与URL转换.md)）接收 `tag_ir` 后执行：

1. Cartesian product 展开 `should` 各组
2. 每条结果附加全部 `must` tag
3. 每条结果应用 `not` 过滤
4. 将平铺后的各组 tag 转为站点搜索 URL

详见 [03-Tag与URL转换](./03-Tag与URL转换.md)。

---

## 六、约束与边界

### 6.1 Agent 职责

| # | 职责 | 说明 |
|---|------|------|
| 1 | 解析用户自然语言意图 | 唯一语义层 |
| 2 | 识别 AND/OR/NOT 关系 | 生成 must/should/not 结构 |
| 3 | 确定目标站点 | 从用户输入或上下文推断 |
| 4 | 生成 alias 集 | 翻译/同义词/变体，提升召回率 |
| 5 | 调用 Plugin 检索候选 tag | 逐 term 独立检索 |
| 6 | 从候选中选择最终 tag | 判断语义契合度 + 选 count 最高 |
| 7 | 组装 Tag IR | 不展开 OR，保留 IR 结构 |

### 6.2 Agent 不做的事

| # | 不做的事 | 原因 |
|---|---------|------|
| 1 | 不展开 OR | 转换层（03）负责 |
| 2 | 不生成 URL | 转换层（03）负责 |
| 3 | 不直接查询 Tag 数据库 | 通过 Plugin API |
| 4 | 不修改候选数据 | Plugin 产出只读 |
| 5 | 不缓存用户历史 | 无状态原则 |
| 6 | 不跨站点一次性检索 | 单次请求针对一个站点 |

### 6.3 与上下游的接口

| 接口 | 输入方 | 数据 |
|------|--------|------|
| Agent → Plugin | [02-Tag数据库](./02-Tag数据库实现.md) | `{token, aliases[], site}` |
| Plugin → Agent | Agent | `{token, candidates: [{tag, count}]}` |
| Agent → 转换层 | [03-Tag与URL转换](./03-Tag与URL转换.md) | `{site, tag_ir: {must, should, not}}` |

### 6.4 错误处理

| 场景 | 处理方式 |
|------|---------|
| 用户输入无法解析 | Agent 返回错误，要求用户澄清 |
| 某 term 在 Plugin 中无候选 | 尝试放宽 alias 重试；仍无结果则标记该 term 为不可解析 |
| `should` 为空数组 | 等价于纯 AND 查询，无需展开 |
| `must` 和空 `should` | 只产出一条结果（仅 must + not） |
| `must` 和 `should` 均为空 | 错误——至少需要一个可检索的 term |

---

## 七、版本兼容

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.0 | 2026-06-14 | 推翻 v1.0 表达式树，改用 must/should/not IR；拆分阶段 A/B；移除综合 score，Plugin 只返回 tag+count |

---

> **下一份文档**：[02-Tag数据库实现](./02-Tag数据库实现.md) — Tag 索引结构、fuzzy matching 算法、Plugin 节点定义、API 协议
