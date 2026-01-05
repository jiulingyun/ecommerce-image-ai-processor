"""图片预览组件.

显示任务的大图预览，支持背景图和商品图切换查看。

Features:
    - 大图预览显示
    - 背景图/商品图切换
    - 适应缩放
    - 显示图片信息
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QResizeEvent
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.models.image_task import ImageTask
from src.utils.constants import PREVIEW_SIZE
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ImagePreview(QFrame):
    """图片预览组件.

    显示选中任务的大图预览，支持切换查看背景图和商品图。

    Signals:
        image_changed: 预览图片切换信号

    Example:
        >>> preview = ImagePreview()
        >>> preview.set_task(task)
    """

    image_changed = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化图片预览组件.

        Args:
            parent: 父组件
        """
        super().__init__(parent)

        self._current_task: Optional[ImageTask] = None
        self._show_background: bool = True  # True=背景图, False=商品图
        self._original_pixmap: Optional[QPixmap] = None

        self._setup_ui()

    # ========================
    # 属性
    # ========================

    @property
    def current_task(self) -> Optional[ImageTask]:
        """当前显示的任务."""
        return self._current_task

    @property
    def is_showing_background(self) -> bool:
        """是否显示背景图."""
        return self._show_background

    # ========================
    # 初始化
    # ========================

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setProperty("previewPanel", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 标题和切换按钮
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("预览")
        title_label.setProperty("heading", True)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # 切换按钮组
        self._switch_container = QFrame()
        switch_layout = QHBoxLayout(self._switch_container)
        switch_layout.setContentsMargins(0, 0, 0, 0)
        switch_layout.setSpacing(8)

        self._bg_radio = QRadioButton("背景图")
        self._bg_radio.setChecked(True)
        self._bg_radio.toggled.connect(self._on_switch_image)
        switch_layout.addWidget(self._bg_radio)

        self._prod_radio = QRadioButton("商品图")
        self._prod_radio.toggled.connect(self._on_switch_image)
        switch_layout.addWidget(self._prod_radio)

        self._switch_container.hide()
        header_layout.addWidget(self._switch_container)

        layout.addLayout(header_layout)

        # 预览区域
        self._preview_container = QFrame()
        self._preview_container.setProperty("card", True)
        self._preview_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        preview_layout = QVBoxLayout(self._preview_container)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 图片标签
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        preview_layout.addWidget(self._image_label)

        layout.addWidget(self._preview_container, 1)

        # 图片信息
        self._info_label = QLabel()
        self._info_label.setProperty("hint", True)
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._info_label)

        # 空状态
        self._empty_label = QLabel("选择任务后\n在此预览图片")
        self._empty_label.setProperty("hint", True)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("font-size: 16px; color: #999;")

        # 初始显示空状态
        self._show_empty_state()

    # ========================
    # 公共方法
    # ========================

    def set_task(self, task: Optional[ImageTask]) -> None:
        """设置要预览的任务.

        Args:
            task: 任务对象，None 表示清空
        """
        self._current_task = task

        if task:
            self._show_background = True
            self._bg_radio.setChecked(True)
            self._switch_container.show()
            self._load_image()
        else:
            self._show_empty_state()

    def clear(self) -> None:
        """清空预览."""
        self.set_task(None)

    def switch_to_background(self) -> None:
        """切换到背景图."""
        if self._current_task and not self._show_background:
            self._show_background = True
            self._bg_radio.setChecked(True)
            self._load_image()

    def switch_to_product(self) -> None:
        """切换到商品图."""
        if self._current_task and self._show_background:
            self._show_background = False
            self._prod_radio.setChecked(True)
            self._load_image()

    # ========================
    # 私有方法
    # ========================

    def _show_empty_state(self) -> None:
        """显示空状态."""
        self._switch_container.hide()
        self._image_label.clear()
        self._image_label.setText("")
        self._info_label.clear()
        self._original_pixmap = None

        # 显示空状态文本
        self._image_label.setText("选择任务后\n在此预览图片")
        self._image_label.setStyleSheet("font-size: 16px; color: #999;")

    def _load_image(self) -> None:
        """加载当前图片."""
        if not self._current_task:
            return

        # 获取图片路径
        if self._show_background:
            image_path = self._current_task.background_path
            image_type = "背景图"
        else:
            image_path = self._current_task.product_path
            image_type = "商品图"

        # 加载图片
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                self._image_label.setText("加载失败")
                self._image_label.setStyleSheet("color: #ff4d4f;")
                self._info_label.clear()
                self._original_pixmap = None
                return

            self._original_pixmap = pixmap
            self._image_label.setStyleSheet("")

            # 缩放显示
            self._update_preview_size()

            # 显示图片信息
            file_name = Path(image_path).name
            width, height = pixmap.width(), pixmap.height()
            self._info_label.setText(
                f"{image_type}: {file_name}\n尺寸: {width} × {height}"
            )

            self.image_changed.emit()
            logger.debug(f"加载预览图: {image_path}")

        except Exception as e:
            logger.error(f"加载预览图失败: {e}")
            self._image_label.setText("加载失败")
            self._image_label.setStyleSheet("color: #ff4d4f;")
            self._info_label.clear()
            self._original_pixmap = None

    def _update_preview_size(self) -> None:
        """更新预览图片尺寸."""
        if not self._original_pixmap:
            return

        # 获取可用空间
        container_size = self._preview_container.size()
        available_width = container_size.width() - 20
        available_height = container_size.height() - 20

        if available_width <= 0 or available_height <= 0:
            return

        # 缩放图片
        scaled = self._original_pixmap.scaled(
            available_width,
            available_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)

    # ========================
    # 槽函数
    # ========================

    def _on_switch_image(self, checked: bool) -> None:
        """切换图片."""
        if not checked:
            return

        sender = self.sender()
        if sender == self._bg_radio:
            self._show_background = True
        elif sender == self._prod_radio:
            self._show_background = False

        if self._current_task:
            self._load_image()

    # ========================
    # 事件处理
    # ========================

    def resizeEvent(self, event: QResizeEvent) -> None:
        """窗口大小变化事件."""
        super().resizeEvent(event)
        # 延迟更新预览尺寸
        if self._original_pixmap:
            self._update_preview_size()
