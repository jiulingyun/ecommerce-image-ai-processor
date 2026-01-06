# PyInstaller hook for PyQt6
# 确保 Qt 插件被正确包含

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# 收集 Qt 插件
datas = collect_data_files('PyQt6', includes=['Qt6/plugins/**/*'])
binaries = collect_dynamic_libs('PyQt6')
