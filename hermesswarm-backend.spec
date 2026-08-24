# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['backend_main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['uvicorn.logging', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'src.core.api', 'src.core.engine', 'src.core.config', 'src.core.events', 'src.workflow.engine', 'src.workflow.state', 'src.agents.base', 'src.agents.specialist', 'src.agents.leader', 'src.agents.evolution', 'src.llm.adapter', 'src.tools.registry', 'src.skills.registry', 'src.memory.unified'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='hermesswarm-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
