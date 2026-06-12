#!/usr/bin/env python3
"""业务能力网关 (Business Capability Gateway)

用法:
    python main.py [start] [--host HOST] [--port PORT]
    python main.py stop

示例:
    python main.py                          # 以默认配置启动
    python main.py --port 9000              # 指定端口
    python main.py --host 0.0.0.0 --port 8765
    python main.py stop                     # 停止运行中的服务

Agent 使用流程:
    1. python main.py start                 # 启动服务
    2. curl http://localhost:8765/plugins   # 发现可用插件
    3. curl http://localhost:8765/plugins/amazon/actions  # 查看能力
    4. curl -X POST http://localhost:8765/execute \
       --data "amazon/关键词搜索&keyword=halloween garland
               > 数据过滤&review_lt=100
               > 市场分析()"               # 执行业务指令
    5. python main.py stop                  # 停止服务
"""

import argparse
import sys
import os

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def cmd_start(args):
    """启动网关服务"""
    from core.plugin_loader import discover_and_load_plugins
    from api.server import run_server

    print("正在加载插件...")
    loaded = discover_and_load_plugins()
    if loaded:
        print(f"已加载插件: {', '.join(loaded)}")
    else:
        print("警告: 未加载任何插件")

    print()
    run_server(host=args.host, port=args.port)


def cmd_stop(args):
    """停止网关服务"""
    from api.server import stop_server
    success = stop_server()
    sys.exit(0 if success else 1)


def cmd_status(args):
    """查看网关状态"""
    from api.server import PID_FILE
    import os
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = f.read().strip()
            print(f"网关服务运行中 (PID: {pid})")
        except Exception:
            print("网关服务状态未知")
    else:
        print("网关服务未运行")


def main():
    parser = argparse.ArgumentParser(
        description="业务能力网关 (Business Capability Gateway)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                             以默认配置启动
  python main.py --port 9000                 指定端口启动
  python main.py --host 0.0.0.0 --port 8765  监听所有接口
  python main.py stop                        停止服务
  python main.py status                      查看状态
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="指令")

    # start
    start_parser = subparsers.add_parser("start", help="启动网关服务")
    start_parser.add_argument("--host", default="127.0.0.1", help="监听地址 (默认: 127.0.0.1)")
    start_parser.add_argument("--port", type=int, default=8765, help="监听端口 (默认: 8765)")
    start_parser.set_defaults(func=cmd_start)

    # stop
    stop_parser = subparsers.add_parser("stop", help="停止运行中的网关服务")
    stop_parser.set_defaults(func=cmd_stop)

    # status
    status_parser = subparsers.add_parser("status", help="查看网关运行状态")
    status_parser.set_defaults(func=cmd_status)

    args = parser.parse_args()

    # 默认指令为 start
    if args.command is None:
        # 不传子命令时以默认配置启动
        cmd_start(argparse.Namespace(host="127.0.0.1", port=8765))
    else:
        args.func(args)


if __name__ == "__main__":
    main()
