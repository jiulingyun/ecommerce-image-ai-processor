"""图片配对面板组件.

提供双区域布局，用于配对选择背景图和商品图。

Features:
    - 左右双区域布局
    - 背景图拖入区
    - 商品图拖入区
    - 添加任务按钮
    - 配对完整性验证
"""

from __future__ import annotations

from typing import Optional, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.drop_zone import DropZone
from src.utils.constants import MAX_QUEUE_SIZE
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ImagePairPanel(QFrame):
    """图片配对面板.

    提供主图和商品图的配对选择界面。
    支持单图模式（仅主图）和双图模式（主图 + 商品图）。

    Signals:
        task_added: 任务添加信号，参数为 (background_path, product_path)
                    product_path 可能为空字符串表示单图模式
        pair_changed: 配对状态变化信号

    Example:
        >>> panel = ImagePairPanel()
        >>> panel.task_added.connect(on_task_added)
    """

    task_added = pyqtSignal(str, str)  # background_path, product_path (可为空)
    pair_changed = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化图片配对面板.

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
    def background_path(self) -> Optional[str]:
        """背景图路径."""
        return self._bg_drop_zone.file_path

    @property
    def product_path(self) -> Optional[str]:
        """商品图路径."""
        return self._prod_drop_zone.file_path

    @property
    def has_main_image(self) -> bool:
        """是否有主图（最低要求）."""
        return self._bg_drop_zone.has_file

    @property
    def is_pair_complete(self) -> bool:
        """配对是否完整（双图模式）."""
        return self._bg_drop_zone.has_file and self._prod_drop_zone.has_file

    @property
    def is_single_image_mode(self) -> bool:
        """是否为单图模式（仅有主图，无商品图）."""
        return self._bg_drop_zone.has_file and not self._prod_drop_zone.has_file

    @property
    def can_add_task(self) -> bool:
        """是否可以添加任务（有主图即可）."""
        return (
            self.has_main_image
            and self._current_queue_count < MAX_QUEUE_SIZE
        )

    # ========================
    # 初始化
    # ========================

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setProperty("panel", True)
        
        # 设置焦点策略，使面板可以接收键盘事件
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
        hint_label = QLabel("添加主图即可创建任务，商品图可选（用于 AI 合成）")
        hint_label.setProperty("hint", True)
        layout.addWidget(hint_label)

        # 双区域容器
        drop_zones_container = QFrame()
        drop_zones_layout = QHBoxLayout(drop_zones_container)
        drop_zones_layout.setContentsMargins(0, 0, 0, 0)
        drop_zones_layout.setSpacing(16)

        # 主图拖入区（必填）
        self._bg_drop_zone = DropZone(
            title="主图/场景图",
            hint="拖拽图片到此处\n或点击选择\n\n(必填，模特图、场景图等)",
        )
        drop_zones_layout.addWidget(self._bg_drop_zone)

        # 中间箭头/加号
        arrow_label = QLabel("+")
        arrow_label.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #999;
        """)
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow_label.setFixedWidth(40)
        drop_zones_layout.addWidget(arrow_label)

        # 商品图拖入区（可选）
        self._prod_drop_zone = DropZone(
            title="商品图（可选）",
            hint="拖拽商品图到此处\n或点击选择\n\n(可选，用于 AI 合成)",
        )
        drop_zones_layout.addWidget(self._prod_drop_zone)

        layout.addWidget(drop_zones_container, 1)

        # 底部按钮区域
        button_container = QFrame()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(12)

        # 弹性空间
        button_layout.addStretch()

        # 清空配对按钮
        self._clear_pair_btn = QPushButton("清空配对")
        self._clear_pair_btn.setProperty("secondary", True)
        self._clear_pair_btn.clicked.connect(self.clear_pair)
        button_layout.addWidget(self._clear_pair_btn)

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
        
        # 队列状态
        self._queue_status_label = QLabel(f"队列: 0/{MAX_QUEUE_SIZE}")
        self._queue_status_label.setProperty("hint", True)
        status_layout.addWidget(self._queue_status_label)
        
        layout.addWidget(status_container)

    def _connect_signals(self) -> None:
        """连接信号."""
        # 监听拖入区状态变化
        self._bg_drop_zone.file_dropped.connect(self._on_pair_changed)
        self._bg_drop_zone.file_cleared.connect(self._on_pair_changed)
        self._prod_drop_zone.file_dropped.connect(self._on_pair_changed)
        self._prod_drop_zone.file_cleared.connect(self._on_pair_changed)
        
        # 监听拖入区文件添加，如果配对完成则聚焦到添加按钮
        self._bg_drop_zone.file_dropped.connect(self._on_file_added)
        self._prod_drop_zone.file_dropped.connect(self._on_file_added)

    # ========================
    # 公共方法
    # ========================

    def clear_pair(self, force: bool = False) -> None:
        """清空当前配对.
        
        Args:
            force: 强制清除，忽略固定状态
        """
        self._bg_drop_zone.clear(force)
        self._prod_drop_zone.clear(force)
        self._update_button_state()

    def set_queue_count(self, count: int) -> None:
        """设置当前队列数量.

        Args:
            count: 队列数量
        """
        self._current_queue_count = count
        self._queue_status_label.setText(f"队列: {count}/{MAX_QUEUE_SIZE}")
        self._update_button_state()

    def get_pair(self) -> Tuple[Optional[str], Optional[str]]:
        """获取当前配对.

        Returns:
            (background_path, product_path)
        """
        return (self.background_path, self.product_path)

    def set_enabled(self, enabled: bool) -> None:
        """设置面板启用状态.

        Args:
            enabled: 是否启用
        """
        self._bg_drop_zone.setEnabled(enabled)
        self._prod_drop_zone.setEnabled(enabled)
        self._clear_pair_btn.setEnabled(enabled)
        if enabled:
            self._update_button_state()
        else:
            self._add_task_btn.setEnabled(False)

    # ========================
    # 私有方法
    # ========================

    def _update_button_state(self) -> None:
        """更新按钮状态."""
        # 添加按钮：有主图且队列未满
        can_add = self.can_add_task
        self._add_task_btn.setEnabled(can_add)

        # 清空按钮：有任意一个已选择
        has_any = self._bg_drop_zone.has_file or self._prod_drop_zone.has_file
        self._clear_pair_btn.setEnabled(has_any)

        # 更新添加按钮提示
        if not self.has_main_image:
            self._add_task_btn.setToolTip("请先选择主图")
        elif self._current_queue_count >= MAX_QUEUE_SIZE:
            self._add_task_btn.setToolTip(f"队列已满（最多{MAX_QUEUE_SIZE}个任务）")
        elif self.is_single_image_mode:
            self._add_task_btn.setToolTip("单图模式：将对主图进行处理")
        else:
            self._add_task_btn.setToolTip("双图模式：将商品合成到主图")

    # ========================
    # 事件处理
    # ========================
    
    def keyPressEvent(self, event) -> None:
        """键盘事件处理."""
        from PyQt6.QtCore import Qt as QtCore
        
        # 回车键添加任务
        if event.key() in (QtCore.Key.Key_Return, QtCore.Key.Key_Enter):
            if self.can_add_task:
                self._on_add_task()
                event.accept()
                return
        
        super().keyPressEvent(event)

    # ========================
    # 槽函数
    # ========================
    
    def _on_file_added(self) -> None:
        """文件添加后的处理."""
        # 如果可以添加任务，聚焦到添加按钮以便快捷键操作
        if self.can_add_task:
            self._add_task_btn.setFocus()

    def _on_pair_changed(self) -> None:
        """配对状态变化."""
        self._update_button_state()
        self.pair_changed.emit()

    def _on_add_task(self) -> None:
        """添加任务按钮点击."""
        if not self.has_main_image:
            QMessageBox.warning(
                self,
                "缺少主图",
                "请先选择主图。",
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

        bg_path = self.background_path
        prod_path = self.product_path or ""  # 单图模式时为空字符串

        if bg_path:
            self.task_added.emit(bg_path, prod_path)
            if prod_path:
                logger.info(f"添加双图任务: {bg_path} + {prod_path}")
            else:
                logger.info(f"添加单图任务: {bg_path}")

            # 清空配对，准备下一个（尊重固定状态）
            self.clear_pair()
            
            # 如果有图片被固定，自动聚焦到未固定的输入框
            if self._bg_drop_zone.is_pinned and not self._prod_drop_zone.has_file:
                self._prod_drop_zone.setFocus()
            elif self._prod_drop_zone.is_pinned and not self._bg_drop_zone.has_file:
                self._bg_drop_zone.setFocus()
