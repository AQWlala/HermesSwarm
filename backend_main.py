"""HermesSwarm后端入口点 - 供PyInstaller打包

启动FastAPI + uvicorn服务器，支持环境变量配置API密钥
"""
import os
import sys


def main():
    os.environ.setdefault("DEEPSEEK_API_KEY", os.environ.get("DEEPSEEK_API_KEY", ""))

    import uvicorn
    from src.core.api import app

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8765"))

    print(f"HermesSwarm backend starting on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        import pathlib
        os.chdir(pathlib.Path(sys.executable).parent)
    main()