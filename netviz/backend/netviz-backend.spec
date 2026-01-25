# -*- mode: python ; coding: utf-8 -*-
"""
NetViz 后端 PyInstaller 打包配置
"""

import sys
from pathlib import Path

block_cipher = None

# 项目根目录
backend_dir = Path(SPECPATH)

# 收集所有需要的数据文件
datas = [
    # app 模块
    (str(backend_dir / 'app'), 'app'),
]

# 隐藏导入
hiddenimports = [
    # FastAPI 和 Starlette
    'fastapi',
    'starlette',
    'starlette.responses',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',
    'starlette.staticfiles',
    
    # Uvicorn
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    
    # SQLAlchemy
    'sqlalchemy',
    'sqlalchemy.ext.asyncio',
    'aiosqlite',
    
    # Pydantic
    'pydantic',
    'pydantic_settings',
    
    # Scapy
    'scapy',
    'scapy.all',
    'scapy.layers',
    'scapy.layers.inet',
    'scapy.layers.inet6',
    'scapy.layers.dns',
    'scapy.layers.http',
    'scapy.layers.l2',
    'scapy.arch.windows',
    
    # 其他
    'httpx',
    'aiofiles',
    'multipart',
    'python_multipart',
    
    # 日志
    'logging.handlers',
]

a = Analysis(
    ['run_server.py'],
    pathex=[str(backend_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='netviz-backend-x86_64-pc-windows-msvc',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 保持控制台以便查看日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
