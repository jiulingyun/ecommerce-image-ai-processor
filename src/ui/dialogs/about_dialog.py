"""关于对话框.

显示应用信息，支持检测更新功能。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.services.version_checker import VersionChecker, VersionInfo
from src.ui.dialogs.update_dialog import UpdateDialog
from src.utils.constants import (
    APP_AUTHOR,
    APP_NAME,
    APP_URL,
    APP_VERSION,
    GITHUB_RELEASES_URL,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class AboutDialog(QDialog):
    """关于对话框.

    显示应用名称、版本、作者等信息，提供检测更新功能。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """初始化关于对话框.

        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self._version_checker: Optional[VersionChecker] = None
        self._check_button: Optional[QPushButton] = None
        self._status_label: Optional[QLabel] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setWindowTitle(f"关于 {APP_NAME}")
        self.setFixedWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 应用图标和名称
        title_label = QLabel(f"<h2>{APP_NAME}</h2>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 版本信息
        version_label = QLabel(f"版本: {APP_VERSION}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #666;")
        layout.addWidget(version_label)

        # 分隔线
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #e0e0e0;")
        layout.addWidget(separator)

        # 应用描述
        desc_label = QLabel(
            "一款基于 AI 的电商图片批量处理工具。\n"
            "支持背景去除、商品合成、边框添加等功能。"
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # 作者信息
        author_label = QLabel(f"作者: {APP_AUTHOR}")
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(author_label)

        # 官网链接
        website_label = QLabel(
            f'官网: <a href="{APP_URL}">{APP_URL}</a>'
        )
        website_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        website_label.setOpenExternalLinks(True)
        layout.addWidget(website_label)

        # 检测更新状态
        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #666; font-size: 12px;")
        self._status_label.hide()
        layout.addWidget(self._status_label)

        layout.addSpacing(8)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        # 检测更新按钮
        self._check_button = QPushButton("检测更新")
        self._check_button.clicked.connect(self._on_check_update)
        button_layout.addWidget(self._check_button)

        button_layout.addStretch()

        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _on_check_update(self) -> None:
        """检测更新按钮点击处理."""
        if self._version_checker and self._version_checker.isRunning():
            return

        # 更新 UI 状态
        if self._check_button:
            self._check_button.setEnabled(False)
            self._check_button.setText("检测中...")

        if self._status_label:
            self._status_label.setText("正在检测更新...")
            self._status_label.setStyleSheet("color: #666; font-size: 12px;")
            self._status_label.show()

        logger.info("用户手动触发版本检测")

        # 启动版本检测
        self._version_checker = VersionChecker(self)
        self._version_checker.update_available.connect(self._on_update_available)
        self._version_checker.check_finished.connect(self._on_check_finished)
        self._version_checker.check_failed.connect(self._on_check_failed)
        self._version_checker.start()

    def _on_update_available(self, version_info: VersionInfo) -> None:
        """发现新版本处理.

        Args:
            version_info: 新版本信息
        """
        # 显示更新对话框
        dialog = UpdateDialog(version_info, self)
        dialog.exec()

    def _on_check_finished(self, has_update: bool) -> None:
        """检测完成处理.

        Args:
            has_update: 是否有更新
        """
        # 恢复按钮状态
        if self._check_button:
            self._check_button.setEnabled(True)
            self._check_button.setText("检测更新")

        # 更新状态文字
        if self._status_label:
            if not has_update:
                self._status_label.setText("✓ 当前已是最新版本")
                self._status_label.setStyleSheet(
                    "color: #28a745; font-size: 12px;"
                )
            self._status_label.show()

    def _on_check_failed(self, error_msg: str) -> None:
        """检测失败处理.

        Args:
            error_msg: 错误信息
        """
        # 恢复按钮状态
        if self._check_button:
            self._check_button.setEnabled(True)
            self._check_button.setText("检测更新")

        # 显示错误信息
        if self._status_label:
            self._status_label.setText("检测失败，请检查网络连接")
            self._status_label.setStyleSheet(
                "color: #dc3545; font-size: 12px;"
            )
            self._status_label.show()

        logger.warning(f"版本检测失败: {error_msg}")

    def closeEvent(self, event) -> None:
        """关闭事件处理."""
        # 停止正在进行的版本检测
        if self._version_checker and self._version_checker.isRunning():
            self._version_checker.quit()
            self._version_checker.wait(1000)

        super().closeEvent(event)
