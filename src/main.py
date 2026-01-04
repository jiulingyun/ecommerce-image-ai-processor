"""电商图片批量AI合成与处理桌面工具 - 应用入口."""

from __future__ import annotations

import sys
from pathlib import Path

# 确保 src 目录在 Python 路径中
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


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
