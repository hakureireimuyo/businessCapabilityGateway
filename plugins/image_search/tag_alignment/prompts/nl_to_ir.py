"""
自然语言 → IR 转换规范

此模块定义将用户自然语言输入转换为 Tag IR（must/should/not）的完整规则。
Agent 是唯一语义层——本模块**不运行任何业务逻辑**，只提供：
  - IR 数据结构定义
  - 从自然语言到 IR 的转换规则
  - IR 有效性校验
  - 覆盖边界情况的示例集

Agent 在会话中读取本模块后，自行完成语义理解并生成 IR。
"""

from __future__ import annotations

# ============================================================
# 一、IR 数据结构定义
# ============================================================

# Tag IR 是一个三元组 {must, should, not}，表达搜索约束集合。
#
# Python 类型定义：
#
#   TagIR = {
#       "must":   list[str],      # 强制 AND —— 每条结果必须全部包含
#       "should": list[list[str]],# OR 组    —— 每个子数组是一个互斥替换集合
#       "not":    list[str],      # 排除    —— 全局过滤器
#   }
#
# 语义规则：
#  - must:  所有元素之间是 AND 关系
#  - should: 组间 AND，组内 OR（每组是多选一的替换集合）
#  - not:   全局排除，每条展开结果统一过滤

IR_KEY_MUST = "must"
IR_KEY_SHOULD = "should"
IR_KEY_NOT = "not"

IR_KEYS = frozenset({IR_KEY_MUST, IR_KEY_SHOULD, IR_KEY_NOT})


def ir_schema_description() -> str:
    """返回 Tag IR 的 schema 说明文本。Agent 可在提示中使用。"""
    return """
## Tag IR Schema

```json
{
  "must": ["tag1", "tag2"],          // AND — 每条结果必须全部包含
  "should": [["a", "b"], ["c"]],     // OR 组 — 组间 AND，组内 OR（多选一）
  "not": ["tag3"]                    // NOT — 全局排除过滤
}
```

- `must`   : string[]  — 强制 AND。所有元素在每条展开结果中都必须出现。
- `should` : string[][] — OR 组。每个子数组是一个「替换集合」，组内元素互斥选择。
  组之间是 AND 关系。空数组 `[]` 等价于无 OR。
- `not`    : string[]  — 排除条件。全局过滤器，应用于所有展开结果。
"""


def ir_field_description() -> str:
    """返回各字段语义的详细说明。"""
    return """
| 字段 | 类型 | 语义 | 转换层行为 |
|------|------|------|-----------|
| must | string[] | AND 约束 | 附加到每条展开结果 |
| should | string[][] | OR 约束（组间 AND，组内 OR） | Cartesian product 展开 |
| not | string[] | 全局排除 | 每条结果统一过滤 |
"""


# ============================================================
# 二、转换规则
# ============================================================

def conversion_rules() -> str:
    """返回 Agent 将自然语言转换为 IR 时必须遵循的完整规则。

    Agent 应在每次执行 NL→IR 转换前阅读此规则。
    """
    return """

## AND 规则 (→ must)

默认并列概念之间是 AND 关系，归入 `must`。

识别条件:
  - 以空格分隔的独立语义概念
  - 两个概念之间无 「或」「或者」「or」等 OR 关键词
  - 无 「不要」「排除」「非」「not」「!」等 NOT 关键词

示例:
  输入: "初音未来 双马尾"
  → {"must": ["初音未来", "双马尾"], "should": [], "not": []}

  输入: "1girl long_hair school_uniform"
  → {"must": ["1girl", "long_hair", "school_uniform"], "should": [], "not": []}

---

## OR 规则 (→ should)

OR 关键词「或」「或者」「or」连接的前后项属于同一个 OR 组（替换集合）。

识别条件:
  - 两个语义概念之间出现 OR 关键词
  - 连续的 OR 链归入同一个 OR 组: A或B或C → ["A","B","C"] 一个组

OR 组合并原则:
  - 只有连续的 "或" 链才属于同一组
  - 「AND 截断」: must 项 或 not 项的出现会结束当前 OR 组的合并
  - 多个独立的 OR 组各自成为 should 的一个子数组

示例:

  单 OR:
    输入: "女仆装或和服"
    → {"must": [], "should": [["女仆装", "和服"]], "not": []}

  AND + OR:
    输入: "初音未来 女仆装或和服"
    → {"must": ["初音未来"], "should": [["女仆装", "和服"]], "not": []}

  三连 OR:
    输入: "猫耳 女仆装或和服或水手服 双马尾"
    → {"must": ["猫耳", "双马尾"], "should": [["女仆装", "和服", "水手服"]], "not": []}

  多 OR 组 (AND 截断):
    输入: "初音未来 双马尾或短发 女仆装或和服"
    → {"must": ["初音未来"], "should": [["双马尾", "短发"], ["女仆装", "和服"]], "not": []}

  「或者」连续:
    输入: "博丽灵梦或者魔理沙"
    → {"must": [], "should": [["博丽灵梦", "魔理沙"]], "not": []}

  「或」与「或者」混合:
    输入: "灵梦或魔理沙或者早苗"
    → {"must": [], "should": [["灵梦", "魔理沙", "早苗"]], "not": []}

---

## NOT 规则 (→ not)

NOT 关键词「不要」「排除」「非」「not」「!」「没有」标记需要排除的概念。

识别条件:
  - 概念前/后出现 NOT 关键词
  - NOT 语义独立于 AND/OR，是全局过滤器
  - not 数组中的元素之间是 AND 关系（全部排除）

重要约束:
  - **NOT 不能独立存在**——must 和 should 不能同时为空
  - 用户只输入「不要R18」时，Agent 应要求用户补充至少一个正面搜索词
  - NOT 是"带搜索词的排除"，不是"全站反选"

NOT 与 OR 的关系:
  - NOT 不参与 OR 组的合并——遇到 NOT 关键词时，当前 OR 组被截断
  - NOT 项单独归入 not 数组
  - 示例:
      输入: "猫耳 不要R18 女仆装或和服"
      → {"must": ["猫耳"], "should": [["女仆装", "和服"]], "not": ["R18"]}

  单独 NOT:
    输入: "不要R18"
    → {"must": [], "should": [], "not": ["R18"]}

  NOT 截断 OR:
    输入: "猫耳 不要R18 女仆装或和服"
    → {"must": ["猫耳"], "should": [["女仆装", "和服"]], "not": ["R18"]}

  多 NOT:
    输入: "不要R18 不要白天"
    → {"must": [], "should": [], "not": ["R18", "白天"]}

  NOT + AND:
    输入: "初音未来 不要R18"
    → {"must": ["初音未来"], "should": [], "not": ["R18"]}

---

## 组合规则

AND、OR、NOT 混合时的解析策略:

1. **从左到右扫描**语义概念，逐个判断归属
2. **每遇到一个 OR 关键词**，将前后两个概念纳入同一个 OR 组
3. **每遇到 AND（默认分隔）**，如果当前有一个未闭合的 OR 组，则 OR 组闭合
4. **每遇到 NOT 关键词**，将关联的概念放入 not 数组，同时截断当前 OR 组
5. **扫描结束后**，所有不在 OR 组中的独立概念归入 must

关键: OR 组的闭合条件（AND 截断 / NOT 截断）仅由遇到的下一个非 OR 概念触发。

---

## must / should / not 的空值规则

| 字段 | 是否可以为空 | 含义 |
|------|------------|------|
| must=[] | 合法 | 无强制 AND 约束（仅靠 OR 组检索） |
| should=[] | 合法 | 无 OR，纯 AND 查询，展开为 1 条 |
| not=[] | 合法 | 无排除条件 |
| must=[] 且 should=[] | **非法** | 至少需要一个可检索的 term |
"""


# ============================================================
# 三、示例集
# ============================================================

def examples() -> list[dict]:
    """返回 (输入, IR, 说明) 的三元组列表。Agent 可将此作为参考。"""
    return [
        # ---- 纯 AND ----
        {
            "input": "初音未来 双马尾 女仆装",
            "ir": {
                "must": ["初音未来", "双马尾", "女仆装"],
                "should": [],
                "not": [],
            },
            "note": "纯 AND — 三个独立概念，默认空格分隔",
        },
        {
            "input": "1girl long_hair school_uniform",
            "ir": {
                "must": ["1girl", "long_hair", "school_uniform"],
                "should": [],
                "not": [],
            },
            "note": "英文 tag — 空格分隔的 AND",
        },

        # ---- 单 OR ----
        {
            "input": "女仆装或和服",
            "ir": {
                "must": [],
                "should": [["女仆装", "和服"]],
                "not": [],
            },
            "note": "单 OR 组 — 「或」连接两个互斥选项",
        },
        {
            "input": "博丽灵梦或者魔理沙",
            "ir": {
                "must": [],
                "should": [["博丽灵梦", "魔理沙"]],
                "not": [],
            },
            "note": "「或者」等价于「或」",
        },

        # ---- AND + 单 OR ----
        {
            "input": "初音未来 女仆装或和服",
            "ir": {
                "must": ["初音未来"],
                "should": [["女仆装", "和服"]],
                "not": [],
            },
            "note": "AND(must) + 单 OR 组",
        },
        {
            "input": "猫耳 女仆装或和服或水手服 双马尾",
            "ir": {
                "must": ["猫耳", "双马尾"],
                "should": [["女仆装", "和服", "水手服"]],
                "not": [],
            },
            "note": "AND 截断 OR 组 — 猫耳(AND) → OR组 → 双马尾(AND)闭合",
        },

        # ---- 多 OR 组 ----
        {
            "input": "博丽灵梦或者魔理沙 站姿或者坐姿 背景有烟花",
            "ir": {
                "must": ["背景有烟花"],
                "should": [["博丽灵梦", "魔理沙"], ["站姿", "坐姿"]],
                "not": [],
            },
            "note": "两个独立 OR 组，被 AND 截断",
        },
        {
            "input": "初音未来 双马尾或短发 女仆装或和服",
            "ir": {
                "must": ["初音未来"],
                "should": [["双马尾", "短发"], ["女仆装", "和服"]],
                "not": [],
            },
            "note": "多 OR 组 + AND must",
        },

        # ---- NOT ----
        {
            "input": "初音未来 不要R18",
            "ir": {
                "must": ["初音未来"],
                "should": [],
                "not": ["R18"],
            },
            "note": "AND + NOT — NOT 必须搭配至少一个正面搜索词",
        },
        {
            "input": "猫耳 不要R18 女仆装或和服",
            "ir": {
                "must": ["猫耳"],
                "should": [["女仆装", "和服"]],
                "not": ["R18"],
            },
            "note": "NOT 截断 OR — NOT 不影响后面的 OR 组独立解析",
        },

        # ---- 全组合 ----
        {
            "input": "初音未来 双马尾 女仆装或和服 不要R18",
            "ir": {
                "must": ["初音未来", "双马尾"],
                "should": [["女仆装", "和服"]],
                "not": ["R18"],
            },
            "note": "AND + OR + NOT 标准输入",
        },
        {
            "input": "立绘 初音未来或镜音铃 双马尾或短发 女仆装和和服任选 不要R18 不要白天",
            "ir": {
                "must": ["立绘"],
                "should": [
                    ["初音未来", "镜音铃"],
                    ["双马尾", "短发"],
                    ["女仆装", "和服"],
                ],
                "not": ["R18", "白天"],
            },
            "note": "复杂输入 — 1 must + 3 OR组 + 2 not",
        },
    ]


# ============================================================
# 四、IR 校验
# ============================================================

class IRError(Exception):
    """Tag IR 格式校验错误。"""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_ir(ir: dict) -> list[str]:
    """校验一个 IR 是否合法。返回错误列表，空列表 = 合法。

    校验规则：
    - 必须包含 must/should/not 三个键
    - must 必须是 list[str]
    - should 必须是 list[list[str]]，每个子数组至少 2 个元素
    - not 必须是 list[str]
    - must 和 should 不能同时为空
    - 无多余键
    """
    errors: list[str] = []

    # 1. 键检查
    keys = set(ir.keys())
    if keys != IR_KEYS:
        missing = IR_KEYS - keys
        extra = keys - IR_KEYS
        if missing:
            errors.append(f"缺少字段: {sorted(missing)}")
        if extra:
            errors.append(f"多余字段: {sorted(extra)}")

    must = ir.get(IR_KEY_MUST, [])
    should = ir.get(IR_KEY_SHOULD, [])
    not_tags = ir.get(IR_KEY_NOT, [])

    # 2. must: list[str]
    if not isinstance(must, list):
        errors.append(f"must 必须是 list，实际: {type(must).__name__}")
    else:
        for i, item in enumerate(must):
            if not isinstance(item, str):
                errors.append(f"must[{i}] 必须是 str，实际: {type(item).__name__}")
            elif not item.strip():
                errors.append(f"must[{i}] 不能为空字符串")

    # 3. should: list[list[str]]，每个子数组 >= 2 个元素
    if not isinstance(should, list):
        errors.append(f"should 必须是 list，实际: {type(should).__name__}")
    else:
        for i, group in enumerate(should):
            if not isinstance(group, list):
                errors.append(f"should[{i}] 必须是 list，实际: {type(group).__name__}")
                continue
            if len(group) < 2:
                errors.append(f"should[{i}] OR 组至少需要 2 个元素，实际: {len(group)}")
            for j, item in enumerate(group):
                if not isinstance(item, str):
                    errors.append(
                        f"should[{i}][{j}] 必须是 str，实际: {type(item).__name__}"
                    )
                elif not item.strip():
                    errors.append(f"should[{i}][{j}] 不能为空字符串")

    # 4. not: list[str]
    if not isinstance(not_tags, list):
        errors.append(f"not 必须是 list，实际: {type(not_tags).__name__}")
    else:
        for i, item in enumerate(not_tags):
            if not isinstance(item, str):
                errors.append(f"not[{i}] 必须是 str，实际: {type(item).__name__}")
            elif not item.strip():
                errors.append(f"not[{i}] 不能为空字符串")

    # 5. must 和 should 不能同时为空（至少有一个可检索 term）
    if isinstance(must, list) and isinstance(should, list):
        if not must and not should:
            errors.append("must 和 should 不能同时为空——至少需要一个可检索的 term")

    return errors


def check_ir(ir: dict) -> bool:
    """快捷校验：合法返回 True，非法返回 False。"""
    return len(validate_ir(ir)) == 0
