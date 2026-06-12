"""BCL 指令解析器 —— 将业务指令字符串解析为管道定义"""

import re
from typing import Any

from .exceptions import InvalidDSLException


class PipelineNode:
    """解析后的单个管道节点"""

    def __init__(self, name: str, params: dict[str, str] | None = None):
        self.name = name
        self.params = params or {}

    def __repr__(self) -> str:
        return f"PipelineNode(name={self.name!r}, params={self.params})"


class Pipeline:
    """解析后的完整管道"""

    def __init__(self, plugin: str, nodes: list[PipelineNode] | None = None):
        self.plugin = plugin
        self.nodes = nodes or []

    def __repr__(self) -> str:
        return f"Pipeline(plugin={self.plugin!r}, nodes={self.nodes})"

    def to_dict(self) -> dict:
        return {
            "plugin": self.plugin,
            "nodes": [
                {"name": n.name, "params": n.params}
                for n in self.nodes
            ],
        }


def parse_bcl(bcl_string: str) -> Pipeline:
    """解析 BCL 指令字符串并返回 Pipeline 对象

    格式:
        <plugin>/<node_name>&<param1>=<value1>&<param2>=<value2>
        > <node_name>&<param1>=<value1>
        > <node_name>()

    Args:
        bcl_string: 业务指令字符串

    Returns:
        Pipeline: 解析后的管道对象

    Raises:
        InvalidDSLException: DSL 语法错误
    """
    if not bcl_string or not bcl_string.strip():
        raise InvalidDSLException("指令字符串不能为空")

    # 按行分割，支持 \n 和 \r\n
    lines = [line.strip() for line in bcl_string.strip().split("\n") if line.strip()]

    if not lines:
        raise InvalidDSLException("指令字符串无有效内容")

    # 解析第一行: <plugin>/<node_name>&params
    first_line = lines[0]
    # 移除开头的 ">" 如果存在
    first_line = re.sub(r"^>\s*", "", first_line)

    plugin, node_name, params = _parse_node_line(first_line)
    if not plugin:
        raise InvalidDSLException(f"无法解析插件名: {first_line}")
    if not node_name:
        raise InvalidDSLException(f"无法解析节点名: {first_line}")

    nodes: list[PipelineNode] = [PipelineNode(name=node_name, params=params)]

    # 解析后续行
    for line in lines[1:]:
        # 移除开头的 ">" 和空白
        line = re.sub(r"^>\s*", "", line)
        _plugin, node_name, params = _parse_node_line(line)
        if not node_name:
            raise InvalidDSLException(f"无法解析节点名: {line}")
        nodes.append(PipelineNode(name=node_name, params=params))

    return Pipeline(plugin=plugin, nodes=nodes)


def _parse_node_line(line: str) -> tuple[str, str, dict[str, str]]:
    """解析单个节点行，返回 (plugin, node_name, params)

    格式: [plugin/]node_name&key1=value1&key2=value2
          或 [plugin/]node_name()
    """
    plugin = ""
    node_name = ""
    params: dict[str, str] = {}

    # 检查是否包含 plugin/ 前缀
    if "/" in line:
        # 找到第一个 "/"，但不要匹配参数中的 "/"
        # 先看 "&" 之前的部分
        amp_pos = line.find("&")
        paren_pos = line.find("(")
        if amp_pos == -1 and paren_pos == -1:
            # 纯 "plugin/node_name" 格式
            prefix = line
        elif amp_pos >= 0 and paren_pos >= 0:
            prefix = line[: min(amp_pos, paren_pos)]
        elif amp_pos >= 0:
            prefix = line[:amp_pos]
        else:
            prefix = line[:paren_pos]

        if "/" in prefix:
            parts = prefix.split("/", 1)
            plugin = parts[0].strip()
            remaining = parts[1].strip() + line[len(prefix):]
        else:
            remaining = line
    else:
        remaining = line

    # 解析 node_name 和 params
    # 格式: node_name(...) 或 node_name&key=value&...
    paren_match = re.match(r"^([^(&\s]+)\s*\((.*)\)(.*)", remaining)
    amp_match = re.match(r"^([^(&\s]+)(&.*)?", remaining)
    bare_match = re.match(r"^([^(&)\s]+)$", remaining)

    if paren_match:
        node_name = paren_match.group(1).strip()
        paren_params = paren_match.group(2).strip()
        # 解析括号内参数 key=value, key=value
        if paren_params:
            params = _parse_params(paren_params)
        # 括号后可能还有 & 参数
        after = paren_match.group(3).strip()
        if after and after.startswith("&"):
            params.update(_parse_params(after[1:]))
    elif amp_match:
        node_name = amp_match.group(1).strip()
        if amp_match.group(2):
            params = _parse_params(amp_match.group(2)[1:])  # 去掉开头的 &
    elif bare_match:
        node_name = bare_match.group(1).strip()
    else:
        raise InvalidDSLException(f"无法解析节点行: {line}")

    # 如果没有显式 plugin，从 node_name 中无法提取
    return plugin, node_name, params


def _parse_params(params_str: str) -> dict[str, str]:
    """解析参数字符串 key1=value1&key2=value2 为字典

    值可以包含特殊字符（如 <, >, =, /），但不包含 &。
    支持引号包裹的值。
    """
    if not params_str:
        return {}

    params: dict[str, str] = {}
    # 按 & 分割，但要注意值中可能不包含 &
    pairs = params_str.split("&")
    for pair in pairs:
        if "=" not in pair:
            # 可能是布尔标志，如 flag
            params[pair.strip()] = "true"
            continue
        key, value = pair.split("=", 1)
        key = key.strip()
        value = value.strip()
        # 移除可能的引号包裹
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]
        params[key] = value

    return params
