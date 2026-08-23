"""HermesSwarm桌面应用入口点 - 单exe打包

启动FastAPI后端(含前端静态文件serve) + 自动打开浏览器
打包后为单个exe文件，不分前后端
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _get_frontend_dir() -> Path:
    """获取前端静态文件目录"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "frontend"
    return Path(__file__).parent / "src" / "ui" / "dist"


def _get_skills_dir() -> Path:
    """获取技能目录"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "skills"
    return Path(__file__).parent / "skills"


def main():
    os.environ.setdefault("DEEPSEEK_API_KEY", os.environ.get("DEEPSEEK_API_KEY", ""))

    frontend_dir = _get_frontend_dir()
    skills_dir = _get_skills_dir()

    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).parent)

    import uvicorn
    from src.core.api import app
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    if frontend_dir.exists():
        app.mount("/assets", StaticFiles(directory=frontend_dir / "assets"), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            file_path = frontend_dir / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(frontend_dir / "index.html")

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8765"))
    url = f"http://{host}:{port}"

    def open_browser():
        time.sleep(1.5)
        webbrowser.open(url)

    if not os.environ.get("HERMESSWARM_NO_BROWSER"):
        threading.Thread(target=open_browser, daemon=True).start()

    print(f"HermesSwarm starting at {url}")
    print(f"Frontend: {frontend_dir}")
    print(f"Skills: {skills_dir}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()