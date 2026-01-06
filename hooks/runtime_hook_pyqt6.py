# PyInstaller runtime hook for PyQt6
# 在应用启动时设置 Qt 库路径

import os
import sys
from pathlib import Path

# 获取应用的基础路径
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的路径
    bundle_dir = Path(sys._MEIPASS)
    
    # 设置 Qt 插件路径
    qt_plugin_path = bundle_dir / 'PyQt6' / 'Qt6' / 'plugins'
    if qt_plugin_path.exists():
        os.environ['QT_PLUGIN_PATH'] = str(qt_plugin_path)
    
    # 在 macOS 上，设置库路径
    if sys.platform == 'darwin':
        # 设置 Qt 库路径
        qt_lib_path = bundle_dir / 'PyQt6' / 'Qt6' / 'lib'
        if qt_lib_path.exists():
            os.environ['DYLD_LIBRARY_PATH'] = str(qt_lib_path)
        
        # 设置 Qt 框架路径
        frameworks_path = bundle_dir / 'PyQt6' / 'Qt6' / 'lib'
        if frameworks_path.exists():
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(qt_plugin_path / 'platforms')
