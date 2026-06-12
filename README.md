# Business Capability Gateway

## 项目简介

**Business Capability Gateway（业务能力网关）** 是一个面向 AI Agent 的轻量级协议网关。
它不执行任何业务逻辑，只负责插件发现与加载、请求解析与路由、管道构建与执行、结果标准化返回。
所有复杂业务能力都封装在插件内部，网关本身对业务一无所知。

## 核心理念

- 网关负责协议
- 插件负责业务
- 数据库负责存储

**Agent 永远不能接触原始数据。**
所有数据查询、过滤、分析、评分都在插件内部处理，Agent 只能拿到最终业务结果。

## 主要功能

- 插件自动发现与加载
- BCL（Business Command Language）指令解析
- 节点注册与能力发现
- 管道合法性校验与执行
- 统一成功/失败响应格式

## 目录结构

```
businessCapabilityGateway/
├── api/                       # HTTP 接口层
├── core/                      # 网关核心模块
├── docs/                      # 项目说明与开发规范
├── plugins/                   # 插件目录
├── tests/                     # 测试
├── main.py                    # 应用入口
├── requirements.txt           # 依赖
└── README.md                  # 项目说明
```

## 关键组件

- `core/dsl_parser.py`：BCL 指令解析器
- `core/node_registry.py`：节点注册中心
- `core/pipeline_executor.py`：管道执行器
- `core/plugin_loader.py`：插件加载器
- `core/execution_context.py`：执行上下文
- `core/response.py`：统一响应封装
- `core/exceptions.py`：网关异常定义
- `core/logger.py`：日志模块

## BCL 语法

BCL 是 Agent 与网关之间的唯一协议，格式示例：

```text
amazon/关键词搜索&keyword=halloween garland
> 数据过滤&review_lt=100&price_gte=20
> 市场分析()
```

- 第一行指定插件与第一个节点
- `>` 表示管道中节点链路
- 每个节点后面可跟参数列表

## 管道规则

合法管道示例：

- `Source → Transform → Transform → Sink`
- `Source → Sink`

非法管道示例：

- `Sink → Transform`
- `Transform` 无前置 `Source`
- `Source → Source`

## API 说明

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

```http
POST /execute
Content-Type: text/plain

amazon/关键词搜索&keyword=halloween garland
> 数据过滤&review_lt=100&price_gte=20
> 市场分析()
```

成功返回：

```json
{
  "success": true,
  "data": { ... },
  "message": ""
}
```

失败返回：

```json
{
  "success": false,
  "error": {
    "code": "INVALID_DSL",
    "message": "..."
  }
}
```

## 常见错误码

- `INVALID_DSL`：DSL 语法错误
- `PLUGIN_NOT_FOUND`：插件不存在
- `NODE_NOT_FOUND`：节点不存在
- `INVALID_PARAMS`：参数校验失败
- `INVALID_PIPELINE`：管道结构非法
- `RESULT_TOO_LARGE`：返回结果超大
- `EXECUTION_TIMEOUT`：执行超时
- `INTERNAL_ERROR`：内部错误

## 插件开发指南

- 插件由 `plugins/<plugin_name>/plugin.py` 注册节点
- 插件只暴露 `Node`，不直接暴露 Repository、Service 等内部实现
- Node 必须无状态，每次执行独立
- 插件内部应遵循：Node -> Service -> Repository
- 新增插件时不需要修改网关核心代码

## 运行方式

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 启动服务：

```bash
python main.py
```

## 备注

此项目面向未来扩展，支持新增插件而不改网关核心，遵循“Open for Extension, Closed for Modification”的设计原则。
