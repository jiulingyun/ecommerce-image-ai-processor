"""主窗口模块."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from src.utils.constants import (
    APP_NAME,
    APP_VERSION,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class MainWindow(QMainWindow):
    """应用主窗口.

    提供应用的主要用户界面。

    TODO: 后续任务中实现完整功能
    """

    def __init__(self) -> None:
        """初始化主窗口."""
        super().__init__()
        self._setup_window()
        self._setup_ui()
        logger.debug("主窗口初始化完成")

    def _setup_window(self) -> None:
        """设置窗口属性."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # 窗口居中
        self.resize(1280, 800)

    def _setup_ui(self) -> None:
        """设置用户界面.

        TODO: 在后续任务中实现完整UI
        """
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 布局
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 占位标签
        placeholder = QLabel("电商图片批量AI合成与处理桌面工具\n\n界面开发中...")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #666;
            }
        """)
        layout.addWidget(placeholder)

    def closeEvent(self, event) -> None:
        """窗口关闭事件."""
        logger.info("主窗口关闭")
        event.accept()
