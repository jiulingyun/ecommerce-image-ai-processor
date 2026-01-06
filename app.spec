# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# 读取版本信息
VERSION = Path('VERSION').read_text().strip()

# 应用名称
app_name = '电商图片AI处理工具'

# 图标路径配置
icon_dir = Path('resources/icons')
if sys.platform == 'darwin':
    icon_path = icon_dir / 'icon.icns' if (icon_dir / 'icon.icns').exists() else None
elif sys.platform == 'win32':
    icon_path = icon_dir / 'icon.ico' if (icon_dir / 'icon.ico').exists() else None
else:  # Linux
    icon_path = icon_dir / 'icon.png' if (icon_dir / 'icon.png').exists() else None

# 数据文件
datas = [
    ('src/ui/resources', 'src/ui/resources'),  # UI 资源文件
    ('VERSION', '.'),  # 版本文件
]

# 隐藏导入（确保所有依赖被包含）
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PIL._tkinter_finder',
    'keyring.backends',
    'keyring.backends.macOS',  # macOS
    'keyring.backends.Windows',  # Windows
    'keyring.backends.SecretService',  # Linux
]

# 排除的模块（减小打包体积）
excludes = [
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'pytest',
    'tkinter',
]

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)

# macOS 应用包配置
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name=f'{app_name}.app',
        icon=str(icon_path) if icon_path and icon_path.suffix == '.icns' else None,
        bundle_identifier='io.jiuling.ecommerce-image-processor',
        version=VERSION,
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': VERSION,
            'CFBundleVersion': VERSION,
        },
    )
