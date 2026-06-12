# Business Composition Language (BCL)

## 设计目标

BCL 是业务编排语言。

BCL 负责描述：

* 调用哪些能力
* 能力之间的依赖关系
* 最终输出什么

BCL 不负责：

* 执行
* 调度
* 并发控制

这些由 Runtime 完成。

---

# 设计原则

## 原则一

一种概念只允许一种语法。

---

## 原则二

所有节点调用形式一致。

---

## 原则三

所有依赖通过变量引用表达。

---

## 原则四

不支持流程控制语句。

禁止：

if

while

for

switch

lambda

---

BCL 不是通用编程语言。

BCL 是业务编排语言。

---

# 顶层结构

import 插件

节点调用

输出声明

组成一个完整程序。

---

# 导入插件

示例：

import amazon

导入后：

当前上下文进入 amazon 业务域。

后续能力自动从 amazon 插件中解析。

---

# 节点调用

统一语法：

result = node(
input1,
input2,
param=value
)

示例：

products = keyword_search(
keyword="halloween"
)

---

# 输入引用

引用上游结果：

sales = sales_analysis(
products
)

其中：

products

为上游节点输出。

---

# 多输入

market = market_score(
sales,
reviews,
prices
)

表示：

market_score

依赖：

sales

reviews

prices

---

# 参数

参数必须显式命名。

正确：

keyword="halloween"

错误：

"halloween"

---

# 输出声明

output market

表示：

market

为最终输出结果。

---

多个输出：

output market

output chart

output report

---

# 示例

import amazon

products = keyword_search(
keyword="halloween garland"
)

sales = sales_analysis(
products
)

reviews = review_analysis(
products
)

market = market_score(
sales,
reviews
)

chart = chart_output(
market
)

report = report_output(
market
)

output report

output chart

---

# AST

上述代码转换为：

KeywordSearchNode

SalesAnalysisNode

ReviewAnalysisNode

MarketScoreNode

ChartOutputNode

ReportOutputNode

并建立依赖关系。

---

# DAG 构建

products
├── sales
└── reviews

sales
reviews
└── market

market
├── chart
└── report

---

# 未来扩展

预留语法：

alias

const

metadata

cache

但当前版本不实现。

优先保持语言极简。

---

# Version 1.0 核心语法

仅保留：

import

变量赋值

节点调用

output

四种语法。

其余全部禁止。

保证：

简单

稳定

可预测

易于 Agent 生成
