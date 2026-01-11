"""图片上传面板组件.

提供多图上传区域，支持创建处理任务。

Features:
    - 多图上传（1-3张）
    - 添加任务按钮
    - 队列状态显示
    - 快捷键支持
"""

from __future__ import annotations

from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.multi_image_drop_zone import MultiImageDropZone
from src.utils.constants import MAX_QUEUE_SIZE, MAX_TASK_IMAGES
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ImageUploadPanel(QFrame):
    """图片上传面板.

    提供多图上传界面，支持创建处理任务。
    
    处理模式：
    - 1张图片：单图模式，跳过AI合成，直接进入后期处理
    - 2-3张图片：多图合成模式，AI合成后进入后期处理

    Signals:
        task_added: 任务添加信号，参数为图片路径列表 list[str]
        images_changed: 图片变化信号

    Example:
        >>> panel = ImageUploadPanel()
        >>> panel.task_added.connect(on_task_added)
    """

    task_added = pyqtSignal(list)  # list[str] - 图片路径列表
    images_changed = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化图片上传面板.

        Args:
            parent: 父组件
        """
        super().__init__(parent)

        self._current_queue_count: int = 0

        self._setup_ui()
        self._connect_signals()

    # ========================
    # 属性
    # ========================

    @property
    def image_paths(self) -> List[str]:
        """图片路径列表."""
        return self._drop_zone.image_paths

    @property
    def image_count(self) -> int:
        """图片数量."""
        return self._drop_zone.image_count

    @property
    def has_images(self) -> bool:
        """是否有图片."""
        return self._drop_zone.has_images

    @property
    def is_single_image_mode(self) -> bool:
        """是否为单图模式."""
        return self._drop_zone.image_count == 1

    @property
    def is_multi_image_mode(self) -> bool:
        """是否为多图模式."""
        return self._drop_zone.image_count > 1

    @property
    def can_add_task(self) -> bool:
        """是否可以添加任务."""
        return (
            self.has_images
            and self._current_queue_count < MAX_QUEUE_SIZE
        )

    # ========================
    # 初始化
    # ========================

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setProperty("panel", True)
        
        # 设置焦点策略
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 标题
        title_label = QLabel("创建处理任务")
        title_label.setProperty("heading", True)
        layout.addWidget(title_label)

        # 说明
        hint_label = QLabel("添加1-3张图片，1张为单图处理，2张及以上为AI多图合成")
        hint_label.setProperty("hint", True)
        layout.addWidget(hint_label)

        # 多图上传区域
        self._drop_zone = MultiImageDropZone(max_images=MAX_TASK_IMAGES)
        layout.addWidget(self._drop_zone, 1)

        # 底部按钮区域
        button_container = QFrame()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(12)

        # 弹性空间
        button_layout.addStretch()

        # 添加任务按钮
        self._add_task_btn = QPushButton("添加到队列")
        self._add_task_btn.setProperty("success", True)
        self._add_task_btn.setEnabled(False)
        self._add_task_btn.clicked.connect(self._on_add_task)
        button_layout.addWidget(self._add_task_btn)

        layout.addWidget(button_container)

        # 队列状态和提示
        status_container = QFrame()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        # 快捷键提示
        shortcut_hint = QLabel("⏎ 回车键快速添加")
        shortcut_hint.setProperty("hint", True)
        status_layout.addWidget(shortcut_hint)
        
        status_layout.addStretch()
        
        # 处理模式提示
        self._mode_label = QLabel("")
        self._mode_label.setProperty("hint", True)
        status_layout.addWidget(self._mode_label)
        
        status_layout.addStretch()
        
        # 队列状态
        self._queue_status_label = QLabel(f"队列: 0/{MAX_QUEUE_SIZE}")
        self._queue_status_label.setProperty("hint", True)
        status_layout.addWidget(self._queue_status_label)
        
        layout.addWidget(status_container)

    def _connect_signals(self) -> None:
        """连接信号."""
        self._drop_zone.images_changed.connect(self._on_images_changed)

    # ========================
    # 公共方法
    # ========================

    def clear_images(self) -> None:
        """清空图片."""
        self._drop_zone.clear_all()
        self._update_button_state()

    def set_queue_count(self, count: int) -> None:
        """设置当前队列数量.

        Args:
            count: 队列数量
        """
        self._current_queue_count = count
        self._queue_status_label.setText(f"队列: {count}/{MAX_QUEUE_SIZE}")
        self._update_button_state()

    def set_enabled(self, enabled: bool) -> None:
        """设置面板启用状态.

        Args:
            enabled: 是否启用
        """
        self._drop_zone.setEnabled(enabled)
        if enabled:
            self._update_button_state()
        else:
            self._add_task_btn.setEnabled(False)

    # ========================
    # 私有方法
    # ========================

    def _update_button_state(self) -> None:
        """更新按钮状态."""
        can_add = self.can_add_task
        self._add_task_btn.setEnabled(can_add)

        # 更新模式提示
        if self.image_count == 0:
            self._mode_label.setText("")
        elif self.image_count == 1:
            self._mode_label.setText("📷 单图模式")
            self._mode_label.setStyleSheet("color: #1890ff;")
        else:
            self._mode_label.setText(f"🎨 {self.image_count}图合成模式")
            self._mode_label.setStyleSheet("color: #52c41a;")

        # 更新添加按钮提示
        if not self.has_images:
            self._add_task_btn.setToolTip("请先添加图片")
        elif self._current_queue_count >= MAX_QUEUE_SIZE:
            self._add_task_btn.setToolTip(f"队列已满（最多{MAX_QUEUE_SIZE}个任务）")
        elif self.is_single_image_mode:
            self._add_task_btn.setToolTip("单图模式：将对图片进行后期处理")
        else:
            self._add_task_btn.setToolTip(f"{self.image_count}图合成模式：AI合成后进行后期处理")

    # ========================
    # 事件处理
    # ========================
    
    def keyPressEvent(self, event) -> None:
        """键盘事件处理."""
        # 回车键添加任务
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.can_add_task:
                self._on_add_task()
                event.accept()
                return
        
        super().keyPressEvent(event)

    # ========================
    # 槽函数
    # ========================
    
    def _on_images_changed(self) -> None:
        """图片变化处理."""
        self._update_button_state()
        self.images_changed.emit()
        
        # 如果可以添加任务，聚焦到添加按钮
        if self.can_add_task:
            self._add_task_btn.setFocus()

    def _on_add_task(self) -> None:
        """添加任务按钮点击."""
        if not self.has_images:
            QMessageBox.warning(
                self,
                "缺少图片",
                "请先添加至少1张图片。",
            )
            return

        if self._current_queue_count >= MAX_QUEUE_SIZE:
            QMessageBox.warning(
                self,
                "队列已满",
                f"处理队列最多支持 {MAX_QUEUE_SIZE} 个任务。\n"
                "请先处理或删除现有任务。",
            )
            return

        # 获取图片路径列表
        image_paths = self.image_paths

        if image_paths:
            self.task_added.emit(image_paths)
            
            if len(image_paths) == 1:
                logger.info(f"添加单图任务: {image_paths[0]}")
            else:
                logger.info(f"添加{len(image_paths)}图合成任务: {image_paths}")

            # 清空图片，准备下一个任务
            self.clear_images()
