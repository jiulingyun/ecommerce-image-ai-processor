"""电商图片批量AI合成与处理桌面工具 - 应用入口."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 确保 src 目录在 Python 路径中
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# PyInstaller 打包后的 Qt 插件路径设置
if getattr(sys, 'frozen', False):
    # 获取打包后的资源路径
    bundle_dir = Path(sys._MEIPASS)
    
    # macOS 特定配置
    if sys.platform == 'darwin':
        # 设置 Qt 插件路径
        qt_plugin_path = bundle_dir / 'PyQt6' / 'Qt6' / 'plugins'
        if qt_plugin_path.exists():
            os.environ['QT_PLUGIN_PATH'] = str(qt_plugin_path)
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(qt_plugin_path / 'platforms')
        
        # 设置 Qt 库路径（对于 Qt 框架）
        qt_lib_path = bundle_dir
        if qt_lib_path.exists():
            # 将 Qt 框架路径添加到环境变量
            current_path = os.environ.get('DYLD_FRAMEWORK_PATH', '')
            os.environ['DYLD_FRAMEWORK_PATH'] = f"{qt_lib_path}:{current_path}" if current_path else str(qt_lib_path)


def main() -> int:
    """应用主入口函数.

    Returns:
        退出码，0 表示正常退出
    """
    from PyQt6.QtWidgets import QApplication

    from src.app import Application
    from src.utils.logger import setup_logger

    # 初始化日志
    logger = setup_logger(__name__)
    logger.info("启动电商图片批量AI合成与处理桌面工具")

    # 创建 Qt 应用
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("电商图片批量AI合成与处理桌面工具")
    qt_app.setApplicationVersion("1.0.0")
    qt_app.setOrganizationName("Yang")

    try:
        # 初始化应用
        app = Application()
        app.initialize()

        # 显示主窗口
        app.show_main_window()

        # 运行事件循环
        exit_code = qt_app.exec()

        # 清理资源
        app.cleanup()

        logger.info(f"应用正常退出，退出码: {exit_code}")
        return exit_code

    except Exception as e:
        logger.exception(f"应用运行时发生错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
