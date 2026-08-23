"""HermesSwarm CLI 入口"""

from __future__ import annotations

import sys


def main() -> None:
    """CLI主入口"""
    if len(sys.argv) < 2:
        print("HermesSwarm - 基因级融合的可视化智能体编排平台")
        print("用法: hermesswarm <command>")
        print("命令:")
        print("  serve    启动API服务器 (端口8765)")
        print("  init     初始化项目配置")
        return

    cmd = sys.argv[1]
    if cmd == "serve":
        from src.core.api import run_server
        run_server()
    elif cmd == "init":
        from src.core.config import FusionConfig
        config = FusionConfig()
        path = config.get_default_config_path()
        config.save_yaml(path)
        print(f"配置已初始化: {path}")
    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
