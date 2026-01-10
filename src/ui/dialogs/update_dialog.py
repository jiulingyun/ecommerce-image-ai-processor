"""更新提示对话框.

显示版本更新信息，支持跳转到下载页面。
"""

from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.utils.constants import APP_NAME, APP_VERSION
from src.utils.logger import setup_logger

if TYPE_CHECKING:
    from src.services.version_checker import VersionInfo

logger = setup_logger(__name__)


class UpdateDialog(QDialog):
    """更新提示对话框.

    显示新版本信息，提供跳转到下载页面的功能。
    """

    def __init__(
        self,
        version_info: "VersionInfo",
        parent: QWidget | None = None,
    ) -> None:
        """初始化更新对话框.

        Args:
            version_info: 新版本信息
            parent: 父窗口
        """
        super().__init__(parent)
        self._version_info = version_info
        self._setup_ui()

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setWindowTitle("发现新版本")
        self.setMinimumWidth(450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题
        title_label = QLabel(f"🎉 {APP_NAME} 有新版本可用！")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # 版本信息
        version_layout = QHBoxLayout()
        version_layout.setSpacing(24)

        current_version_widget = self._create_version_widget(
            "当前版本", APP_VERSION
        )
        latest_version_widget = self._create_version_widget(
            "最新版本", self._version_info.version
        )

        version_layout.addWidget(current_version_widget)
        version_layout.addWidget(latest_version_widget)
        version_layout.addStretch()

        layout.addLayout(version_layout)

        # 发布说明
        if self._version_info.release_notes:
            notes_label = QLabel("更新内容：")
            notes_label.setStyleSheet("font-weight: bold; margin-top: 8px;")
            layout.addWidget(notes_label)

            notes_text = QTextEdit()
            notes_text.setPlainText(self._version_info.release_notes)
            notes_text.setReadOnly(True)
            notes_text.setMaximumHeight(150)
            layout.addWidget(notes_text)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        # 稍后提醒按钮
        later_button = QPushButton("稍后提醒")
        later_button.clicked.connect(self.reject)
        button_layout.addWidget(later_button)

        button_layout.addStretch()

        # 前往下载按钮
        download_button = QPushButton("前往下载")
        download_button.setDefault(True)
        download_button.setStyleSheet(
            """
            QPushButton {
                background-color: #0066cc;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
            """
        )
        download_button.clicked.connect(self._on_download_clicked)
        button_layout.addWidget(download_button)

        layout.addLayout(button_layout)

    def _create_version_widget(self, label: str, version: str) -> QWidget:
        """创建版本显示组件.

        Args:
            label: 标签文字
            version: 版本号

        Returns:
            版本显示组件
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #666;")
        layout.addWidget(label_widget)

        version_label = QLabel(version)
        version_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(version_label)

        return widget

    def _on_download_clicked(self) -> None:
        """处理下载按钮点击."""
        url = self._version_info.release_url
        logger.info(f"打开下载页面: {url}")
        webbrowser.open(url)
        self.accept()
