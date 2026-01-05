"""任务列表组件.

显示已添加的任务列表，每项显示背景图和商品图缩略图。

Features:
    - 显示任务列表
    - 双缩略图显示（背景图+商品图）
    - 支持选中和删除
    - 任务状态显示
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.models.image_task import ImageTask, TaskStatus
from src.utils.constants import MAX_QUEUE_SIZE
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 列表项缩略图大小
LIST_THUMBNAIL_SIZE = (60, 60)


class TaskListItem(QFrame):
    """任务列表项组件.

    显示单个任务的信息，包括双缩略图和任务状态。
    """

    delete_clicked = pyqtSignal(str)  # task_id

    def __init__(
        self,
        task: ImageTask,
        index: int = 0,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化任务列表项.

        Args:
            task: 任务对象
            index: 序号（从1开始）
            parent: 父组件
        """
        super().__init__(parent)
        self._task = task
        self._index = index
        self._setup_ui()
    @property
    def task(self) -> ImageTask:
        """任务对象."""
        return self._task

    @property
    def task_id(self) -> str:
        """任务 ID."""
        return self._task.id

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setProperty("card", True)
        # 覆盖全局 card 样式中的 padding，由 layout margins 完全控制布局
        # 必须重写背景和边框，否则可能被部分覆盖
        self.setStyleSheet("""
            TaskListItem[card="true"] {
                padding: 0px;
                background-color: #ffffff;
                border: 1px solid #e8e8e8;
                border-radius: 8px;
            }
        """)
        self.setFixedHeight(80)

        layout = QHBoxLayout(self)
        # 上下边距设为 10px，配合 60px 图片和 80px 总高度，实现精确的物理居中
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 序号角标
        if self._index > 0:
            index_label = QLabel(str(self._index))
            index_label.setFixedSize(24, 24)
            index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            index_label.setStyleSheet("""
                background-color: #1890ff;
                color: white;
                font-size: 12px;
                font-weight: bold;
                border-radius: 12px;
            """)
            layout.addWidget(index_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # 背景图缩略图
        self._bg_thumbnail = QLabel()
        self._bg_thumbnail.setFixedSize(LIST_THUMBNAIL_SIZE[0], LIST_THUMBNAIL_SIZE[1])
        self._bg_thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bg_thumbnail.setStyleSheet("""
            background-color: #f5f5f5;
            border: 1px solid #e8e8e8;
            border-radius: 4px;
        """)
        self._load_thumbnail(self._bg_thumbnail, self._task.background_path)
        layout.addWidget(self._bg_thumbnail, 0, Qt.AlignmentFlag.AlignVCenter)

        # 加号
        plus_label = QLabel("+")
        plus_label.setStyleSheet("color: #999; font-size: 16px; font-weight: bold;")
        plus_label.setFixedWidth(20)
        plus_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(plus_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # 商品图缩略图
        self._prod_thumbnail = QLabel()
        self._prod_thumbnail.setFixedSize(LIST_THUMBNAIL_SIZE[0], LIST_THUMBNAIL_SIZE[1])
        self._prod_thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._prod_thumbnail.setStyleSheet("""
            background-color: #f5f5f5;
            border: 1px solid #e8e8e8;
            border-radius: 4px;
        """)
        self._load_thumbnail(self._prod_thumbnail, self._task.product_path)
        layout.addWidget(self._prod_thumbnail, 0, Qt.AlignmentFlag.AlignVCenter)

        # 任务信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.addStretch()  # 顶部弹簧

        # 文件名
        bg_name = Path(self._task.background_path).name
        prod_name = Path(self._task.product_path).name
        name_label = QLabel(f"{bg_name[:15]}...")
        name_label.setStyleSheet("font-size: 13px; color: #333; font-weight: 500;")
        name_label.setToolTip(f"背景: {bg_name}\n商品: {prod_name}")
        info_layout.addWidget(name_label)

        # 状态
        self._status_label = QLabel()
        info_layout.addWidget(self._status_label)

        # 进度条（处理时显示）
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #f0f0f0;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #1890ff;
                border-radius: 2px;
            }
        """)
        self._progress_bar.setVisible(False)
        info_layout.addWidget(self._progress_bar)

        self._update_status_display()
        
        info_layout.addStretch()  # 底部弹簧
        layout.addLayout(info_layout, 1)

        # 删除按钮
        self._delete_btn = QPushButton("×")
        self._delete_btn.setFixedSize(24, 24)
        self._delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #999;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #ff4d4f;
            }
        """)
        self._delete_btn.setToolTip("删除任务")
        self._delete_btn.clicked.connect(self._on_delete)
        layout.addWidget(self._delete_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def _load_thumbnail(self, label: QLabel, file_path: str) -> None:
        """加载缩略图.

        Args:
            label: 目标标签
            file_path: 文件路径
        """
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    LIST_THUMBNAIL_SIZE[0] - 4,
                    LIST_THUMBNAIL_SIZE[1] - 4,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                label.setPixmap(scaled)
            else:
                label.setText("!")
        except Exception as e:
            logger.error(f"加载缩略图失败: {e}")
            label.setText("!")

    def _update_status_display(self) -> None:
        """更新状态显示."""
        status_config = {
            TaskStatus.PENDING: ("待处理", "#faad14"),
            TaskStatus.PROCESSING: ("处理中...", "#1890ff"),
            TaskStatus.COMPLETED: ("已完成", "#52c41a"),
            TaskStatus.FAILED: ("失败", "#ff4d4f"),
            TaskStatus.CANCELLED: ("已取消", "#999"),
        }

        text, color = status_config.get(
            self._task.status, ("未知", "#999")
        )

        is_processing = self._task.status == TaskStatus.PROCESSING
        if is_processing:
            text = f"处理中 {self._task.progress}%"

        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"font-size: 10px; color: {color};")

        # 更新进度条
        self._progress_bar.setVisible(is_processing)
        if is_processing:
            self._progress_bar.setValue(self._task.progress)

    def update_task(self, task: ImageTask) -> None:
        """更新任务状态.

        Args:
            task: 更新后的任务
        """
        self._task = task
        self._update_status_display()

    def _on_delete(self) -> None:
        """删除按钮点击."""
        self.delete_clicked.emit(self._task.id)


class TaskListWidget(QFrame):
    """任务列表组件.

    显示所有已添加的任务列表。

    Signals:
        task_selected: 任务选中信号，参数为 ImageTask
        task_deleted: 任务删除信号，参数为 task_id
    """

    task_selected = pyqtSignal(object)  # ImageTask
    task_deleted = pyqtSignal(str)  # task_id

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化任务列表组件.

        Args:
            parent: 父组件
        """
        super().__init__(parent)

        self._tasks: dict[str, ImageTask] = {}
        self._items: dict[str, TaskListItem] = {}

        self._setup_ui()

    # ========================
    # 属性
    # ========================

    @property
    def task_count(self) -> int:
        """任务数量."""
        return len(self._tasks)

    @property
    def tasks(self) -> List[ImageTask]:
        """所有任务列表."""
        return list(self._tasks.values())

    # ========================
    # 初始化
    # ========================

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setProperty("panel", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 标题行
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("处理队列")
        title_label.setProperty("heading", True)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        self._count_label = QLabel(f"0/{MAX_QUEUE_SIZE}")
        self._count_label.setProperty("hint", True)
        header_layout.addWidget(self._count_label)

        layout.addLayout(header_layout)

        # 列表区域
        self._list_widget = QListWidget()
        self._list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 4px;
                border: none;
            }
            QListWidget::item:selected {
                background-color: #e6f7ff;
                border-radius: 4px;
            }
        """)
        self._list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list_widget, 1)

        # 空状态提示
        self._empty_label = QLabel("暂无任务\n请在上方配对图片后添加")
        self._empty_label.setProperty("hint", True)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty_label)

        self._update_empty_state()

    # ========================
    # 公共方法
    # ========================

    def add_task(self, task: ImageTask) -> bool:
        """添加任务.

        Args:
            task: 任务对象

        Returns:
            是否添加成功
        """
        if task.id in self._tasks:
            logger.warning(f"任务已存在: {task.id}")
            return False

        if len(self._tasks) >= MAX_QUEUE_SIZE:
            logger.warning("队列已满")
            return False

        # 创建列表项（序号从1开始）
        index = len(self._tasks) + 1
        item_widget = TaskListItem(task, index=index)
        item_widget.delete_clicked.connect(self._on_delete_clicked)

        # 添加到列表
        list_item = QListWidgetItem()
        list_item.setSizeHint(QSize(0, 88))
        list_item.setData(Qt.ItemDataRole.UserRole, task.id)
        self._list_widget.addItem(list_item)
        self._list_widget.setItemWidget(list_item, item_widget)

        # 记录
        self._tasks[task.id] = task
        self._items[task.id] = item_widget

        self._update_count()
        self._update_empty_state()

        logger.debug(f"添加任务到列表: {task.id}")
        return True

    def remove_task(self, task_id: str) -> bool:
        """删除任务.

        Args:
            task_id: 任务 ID

        Returns:
            是否删除成功
        """
        if task_id not in self._tasks:
            return False

        # 找到列表项并删除
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == task_id:
                self._list_widget.takeItem(i)
                break

        # 清理记录
        del self._tasks[task_id]
        del self._items[task_id]

        # 删除后刷新序号
        self._refresh_indices()

        self._update_count()
        self._update_empty_state()

        logger.debug(f"删除任务: {task_id}")
        return True

    def update_task(self, task: ImageTask) -> None:
        """更新任务状态.

        Args:
            task: 更新后的任务
        """
        if task.id in self._tasks:
            self._tasks[task.id] = task
            if task.id in self._items:
                self._items[task.id].update_task(task)

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """更新任务状态.

        Args:
            task_id: 任务 ID
            status: 新状态
        """
        if task_id in self._tasks:
            self._tasks[task_id].status = status
            if task_id in self._items:
                self._items[task_id].update_task(self._tasks[task_id])

    def clear_all(self) -> None:
        """清空所有任务."""
        self._list_widget.clear()
        self._tasks.clear()
        self._items.clear()
        self._update_count()
        self._update_empty_state()

    def get_task(self, task_id: str) -> Optional[ImageTask]:
        """获取任务.

        Args:
            task_id: 任务 ID

        Returns:
            任务对象，不存在返回 None
        """
        return self._tasks.get(task_id)

    def get_selected_task(self) -> Optional[ImageTask]:
        """获取当前选中的任务.

        Returns:
            选中的任务，无选中返回 None
        """
        current_item = self._list_widget.currentItem()
        if current_item:
            task_id = current_item.data(Qt.ItemDataRole.UserRole)
            return self._tasks.get(task_id)
        return None

    # ========================
    # 私有方法
    # ========================

    def _update_count(self) -> None:
        """更新计数显示."""
        self._count_label.setText(f"{len(self._tasks)}/{MAX_QUEUE_SIZE}")

    def _update_empty_state(self) -> None:
        """更新空状态显示."""
        is_empty = len(self._tasks) == 0
        self._empty_label.setVisible(is_empty)
        self._list_widget.setVisible(not is_empty)

    def _refresh_indices(self) -> None:
        """刷新所有任务的序号显示."""
        # 需要重建列表项以更新序号
        tasks_backup = list(self._tasks.values())
        self._list_widget.clear()
        self._items.clear()

        for idx, task in enumerate(tasks_backup, 1):
            item_widget = TaskListItem(task, index=idx)
            item_widget.delete_clicked.connect(self._on_delete_clicked)

            list_item = QListWidgetItem()
            list_item.setSizeHint(QSize(0, 88))
            list_item.setData(Qt.ItemDataRole.UserRole, task.id)
            self._list_widget.addItem(list_item)
            self._list_widget.setItemWidget(list_item, item_widget)

            self._items[task.id] = item_widget

    # ========================
    # 槽函数
    # ========================

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """列表项点击."""
        task_id = item.data(Qt.ItemDataRole.UserRole)
        task = self._tasks.get(task_id)
        if task:
            self.task_selected.emit(task)

    def _on_delete_clicked(self, task_id: str) -> None:
        """删除按钮点击."""
        self.task_deleted.emit(task_id)
