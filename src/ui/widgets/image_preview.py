"""图片预览组件.

显示任务的大图预览，支持背景图和商品图切换查看。

Features:
    - 大图预览显示
    - 背景图/商品图/处理结果切换
    - 适应缩放
    - 显示图片信息
    - 处理前后对比预览
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
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.models.image_task import ImageTask
from src.utils.constants import PREVIEW_SIZE
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PreviewMode:
    """预览模式常量."""

    BACKGROUND = "background"  # 背景图
    PRODUCT = "product"  # 商品图
    RESULT = "result"  # 处理结果


class ImagePreview(QFrame):
    """图片预览组件.

    显示选中任务的大图预览，支持切换查看背景图、商品图和处理结果。

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
        self._preview_mode: str = PreviewMode.BACKGROUND
        self._original_pixmap: Optional[QPixmap] = None
        self._result_pixmap: Optional[QPixmap] = None  # 处理结果图

        self._setup_ui()

    # ========================
    # 属性
    # ========================

    @property
    def current_task(self) -> Optional[ImageTask]:
        """当前显示的任务."""
        return self._current_task

    @property
    def preview_mode(self) -> str:
        """当前预览模式."""
        return self._preview_mode

    @property
    def is_showing_background(self) -> bool:
        """是否显示背景图."""
        return self._preview_mode == PreviewMode.BACKGROUND

    @property
    def has_result(self) -> bool:
        """是否有处理结果."""
        return self._result_pixmap is not None

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

        self._btn_group = QButtonGroup(self)

        self._bg_radio = QRadioButton("背景图")
        self._bg_radio.setChecked(True)
        self._bg_radio.toggled.connect(self._on_switch_image)
        self._btn_group.addButton(self._bg_radio)
        switch_layout.addWidget(self._bg_radio)

        self._prod_radio = QRadioButton("商品图")
        self._prod_radio.toggled.connect(self._on_switch_image)
        self._btn_group.addButton(self._prod_radio)
        switch_layout.addWidget(self._prod_radio)

        self._result_radio = QRadioButton("处理结果")
        self._result_radio.toggled.connect(self._on_switch_image)
        self._btn_group.addButton(self._result_radio)
        self._result_radio.hide()  # 默认隐藏，有结果时显示
        switch_layout.addWidget(self._result_radio)

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
        self._result_pixmap = None

        if task:
            self._preview_mode = PreviewMode.BACKGROUND
            self._bg_radio.setChecked(True)
            self._result_radio.hide()
            self._switch_container.show()

            # 如果任务有结果路径，加载结果
            if task.output_path:
                self._load_result_image(task.output_path)

            self._load_image()
        else:
            self._show_empty_state()

    def clear(self) -> None:
        """清空预览."""
        self.set_task(None)

    def set_result_image(self, image_path: str) -> None:
        """设置处理结果图片.

        Args:
            image_path: 结果图片路径
        """
        self._load_result_image(image_path)
        # 自动切换到结果显示
        if self._result_pixmap:
            self.switch_to_result()

    def switch_to_background(self) -> None:
        """切换到背景图."""
        if self._current_task and self._preview_mode != PreviewMode.BACKGROUND:
            self._preview_mode = PreviewMode.BACKGROUND
            self._bg_radio.setChecked(True)
            self._load_image()

    def switch_to_product(self) -> None:
        """切换到商品图."""
        if self._current_task and self._preview_mode != PreviewMode.PRODUCT:
            self._preview_mode = PreviewMode.PRODUCT
            self._prod_radio.setChecked(True)
            self._load_image()

    def switch_to_result(self) -> None:
        """切换到处理结果."""
        if self._result_pixmap and self._preview_mode != PreviewMode.RESULT:
            self._preview_mode = PreviewMode.RESULT
            self._result_radio.setChecked(True)
            self._show_result_image()

    # ========================
    # 私有方法
    # ========================

    def _show_empty_state(self) -> None:
        """显示空状态."""
        self._switch_container.hide()
        self._result_radio.hide()
        self._image_label.clear()
        self._image_label.setText("")
        self._info_label.clear()
        self._original_pixmap = None
        self._result_pixmap = None

        # 显示空状态文本
        self._image_label.setText("选择任务后\n在此预览图片")
        self._image_label.setStyleSheet("font-size: 16px; color: #999;")

    def _load_result_image(self, image_path: str) -> None:
        """加载处理结果图片."""
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self._result_pixmap = pixmap
                self._result_radio.show()
                logger.debug(f"加载处理结果: {image_path}")
            else:
                logger.warning(f"无法加载处理结果图: {image_path}")
        except Exception as e:
            logger.error(f"加载处理结果失败: {e}")

    def _load_image(self) -> None:
        """加载当前图片."""
        if not self._current_task:
            return

        # 处理结果单独显示
        if self._preview_mode == PreviewMode.RESULT:
            self._show_result_image()
            return

        # 获取图片路径
        if self._preview_mode == PreviewMode.BACKGROUND:
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

    def _show_result_image(self) -> None:
        """显示处理结果图片."""
        if not self._result_pixmap:
            return

        self._original_pixmap = self._result_pixmap
        self._image_label.setStyleSheet("")
        self._update_preview_size()

        # 显示图片信息
        width, height = self._result_pixmap.width(), self._result_pixmap.height()
        self._info_label.setText(f"处理结果\n尺寸: {width} × {height}")

        self.image_changed.emit()

    def _on_switch_image(self, checked: bool) -> None:
        """切换图片."""
        if not checked:
            return

        sender = self.sender()
        if sender == self._bg_radio:
            self._preview_mode = PreviewMode.BACKGROUND
        elif sender == self._prod_radio:
            self._preview_mode = PreviewMode.PRODUCT
        elif sender == self._result_radio:
            self._preview_mode = PreviewMode.RESULT

        if self._current_task or self._preview_mode == PreviewMode.RESULT:
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
