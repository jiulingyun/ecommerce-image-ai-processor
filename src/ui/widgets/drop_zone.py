"""拖拽上传区域组件.

提供支持拖拽放置图片的区域，显示图片预览缩略图。

Features:
    - 拖拽放置图片文件
    - 点击选择文件
    - 显示图片缩略图预览
    - 清除已选图片
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QPainter, QColor
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.utils.constants import SUPPORTED_IMAGE_FORMATS, THUMBNAIL_SIZE
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DropZone(QFrame):
    """拖拽上传区域组件.

    支持拖拽放置图片文件或点击选择文件，显示图片缩略图预览。

    Signals:
        file_dropped: 文件放置信号，参数为文件路径
        file_cleared: 文件清除信号

    Attributes:
        title: 区域标题
        file_path: 当前选择的文件路径

    Example:
        >>> drop_zone = DropZone("背景图")
        >>> drop_zone.file_dropped.connect(on_file_selected)
    """

    file_dropped = pyqtSignal(str)  # 文件路径
    file_cleared = pyqtSignal()

    def __init__(
        self,
        title: str = "拖入图片",
        hint: str = "拖拽图片到此处\n或点击选择",
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化拖拽上传区域.

        Args:
            title: 区域标题
            hint: 提示文字
            parent: 父组件
        """
        super().__init__(parent)

        self._title = title
        self._hint = hint
        self._file_path: Optional[str] = None
        self._thumbnail_size = THUMBNAIL_SIZE
        self._is_pinned = False  # 图片是否固定

        self._setup_ui()
        self._setup_drag_drop()

    # ========================
    # 属性
    # ========================

    @property
    def title(self) -> str:
        """区域标题."""
        return self._title

    @property
    def file_path(self) -> Optional[str]:
        """当前选择的文件路径."""
        return self._file_path

    @property
    def has_file(self) -> bool:
        """是否已选择文件."""
        return self._file_path is not None
    
    @property
    def is_pinned(self) -> bool:
        """图片是否固定."""
        return self._is_pinned

    # ========================
    # 初始化
    # ========================

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setProperty("dropzone", True)
        self.setMinimumSize(180, 200)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 标题
        self._title_label = QLabel(self._title)
        self._title_label.setProperty("subheading", True)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_label)

        # 预览/提示区域
        self._preview_container = QFrame()
        self._preview_container.setProperty("card", True)
        preview_layout = QVBoxLayout(self._preview_container)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 缩略图标签
        self._thumbnail_label = QLabel()
        self._thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 使用 Expanding 策略填满容器，依靠 setAlignment 居中图片
        self._thumbnail_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        # 移除固定最小尺寸限制，避免布局问题
        # self._thumbnail_label.setMinimumSize(...) 
        
        # 添加到布局，给予伸缩因子 1
        preview_layout.addWidget(self._thumbnail_label, 1)

        # 提示标签
        self._hint_label = QLabel(self._hint)
        self._hint_label.setProperty("hint", True)
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setWordWrap(True)
        preview_layout.addWidget(self._hint_label)

        # 文件名标签
        self._filename_label = QLabel()
        self._filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._filename_label.setWordWrap(True)
        self._filename_label.setProperty("hint", True)
        self._filename_label.hide()
        preview_layout.addWidget(self._filename_label)

        layout.addWidget(self._preview_container, 1)

        # 底部按钮区域
        button_container = QFrame()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)

        # 按钮样式（覆盖全局 min-width）
        btn_style = "min-width: 60px; padding: 6px 8px;"

        # 选择按钮
        self._select_btn = QPushButton("选择文件")
        self._select_btn.setProperty("secondary", True)
        self._select_btn.setStyleSheet(btn_style)
        self._select_btn.clicked.connect(self._on_select_file)
        button_layout.addWidget(self._select_btn, 1)  # stretch=1 均分空间

        # 清除按钮
        self._clear_btn = QPushButton("清除")
        self._clear_btn.setProperty("danger", True)
        self._clear_btn.setStyleSheet(btn_style)
        self._clear_btn.clicked.connect(self.clear)
        self._clear_btn.hide()
        button_layout.addWidget(self._clear_btn, 1)  # stretch=1 均分空间

        layout.addWidget(button_container)
        
        # 固定复选框
        from PyQt6.QtWidgets import QCheckBox
        self._pin_checkbox = QCheckBox("📌 固定此图片（批量添加）")
        self._pin_checkbox.setToolTip("勾选后，此图片将保留不被清除，方便批量添加任务")
        self._pin_checkbox.setProperty("hint", True)
        self._pin_checkbox.hide()
        self._pin_checkbox.stateChanged.connect(self._on_pin_changed)
        layout.addWidget(self._pin_checkbox)

        # 更新初始状态
        self._update_display()

    def _setup_drag_drop(self) -> None:
        """设置拖拽功能."""
        self.setAcceptDrops(True)

    # ========================
    # 公共方法
    # ========================

    def set_file(self, file_path: str) -> bool:
        """设置文件.

        Args:
            file_path: 文件路径

        Returns:
            是否设置成功
        """
        if not self._validate_file(file_path):
            return False

        self._file_path = file_path
        self._update_display()
        self.file_dropped.emit(file_path)
        logger.debug(f"DropZone [{self._title}] 设置文件: {file_path}")
        return True

    def clear(self, force: bool = False) -> None:
        """清除当前文件.
        
        Args:
            force: 强制清除，忽略固定状态
        """
        # 如果图片被固定且不是强制清除，则不清除
        if self._is_pinned and not force:
            logger.debug(f"DropZone [{self._title}] 图片已固定，跳过清除")
            return
        
        if self._file_path:
            self._file_path = None
            self._is_pinned = False
            self._update_display()
            self.file_cleared.emit()
            logger.debug(f"DropZone [{self._title}] 清除文件")

    def get_file_path(self) -> Optional[str]:
        """获取当前文件路径.

        Returns:
            文件路径，未选择时返回 None
        """
        return self._file_path

    # ========================
    # 私有方法
    # ========================

    def _validate_file(self, file_path: str) -> bool:
        """验证文件.

        Args:
            file_path: 文件路径

        Returns:
            是否有效
        """
        path = Path(file_path)

        # 检查文件存在
        if not path.exists():
            logger.warning(f"文件不存在: {file_path}")
            return False

        # 检查文件格式
        if path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
            logger.warning(f"不支持的图片格式: {path.suffix}")
            return False

        return True

    def _update_display(self) -> None:
        """更新显示状态."""
        if self._file_path:
            # 显示缩略图
            self._load_thumbnail(self._file_path)
            self._hint_label.hide()
            self._filename_label.setText(Path(self._file_path).name)
            self._filename_label.show()
            self._clear_btn.show()
            self._pin_checkbox.show()  # 显示固定复选框
            self.setProperty("dropzone-filled", True)
        else:
            # 显示提示
            self._thumbnail_label.clear()
            self._thumbnail_label.setText("")
            self._hint_label.show()
            self._filename_label.hide()
            self._clear_btn.hide()
            self._pin_checkbox.hide()  # 隐藏固定复选框
            self.setProperty("dropzone-filled", False)
        
        # 更新固定复选框状态
        self._pin_checkbox.setChecked(self._is_pinned)

        # 刷新样式
        self.style().unpolish(self)
        self.style().polish(self)
    
    def _on_pin_changed(self, state: int) -> None:
        """固定状态变化."""
        from PyQt6.QtCore import Qt as QtCore
        self._is_pinned = (state == QtCore.CheckState.Checked.value)
        logger.debug(f"DropZone [{self._title}] 固定状态: {self._is_pinned}")

    def _load_thumbnail(self, file_path: str) -> None:
        """加载缩略图.

        Args:
            file_path: 文件路径
        """
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # 计算缩放尺寸（保持纵横比）
                # 使用 preview_container 的大小来计算，减去边距
                container_size = self._preview_container.size()
                target_w = max(100, container_size.width() - 20)
                target_h = max(100, container_size.height() - 40) # 留出文字空间
                
                # 限制最大尺寸
                target_w = min(target_w, 200)
                target_h = min(target_h, 200)

                scaled = pixmap.scaled(
                    target_w,
                    target_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._thumbnail_label.setPixmap(scaled)
            else:
                self._thumbnail_label.setText("加载失败")
        except Exception as e:
            logger.error(f"加载缩略图失败: {e}")
            self._thumbnail_label.setText("加载失败")

    def _get_file_from_mime(self, event) -> Optional[str]:
        """从拖拽事件获取文件路径.

        Args:
            event: 拖拽事件

        Returns:
            文件路径，无效时返回 None
        """
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if self._validate_file(file_path):
                    return file_path
        return None

    # ========================
    # 事件处理
    # ========================

    def _on_select_file(self) -> None:
        """选择文件按钮点击."""
        formats = " ".join(f"*{ext}" for ext in SUPPORTED_IMAGE_FORMATS)
        filter_str = f"图片文件 ({formats});;所有文件 (*.*)"

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"选择{self._title}",
            "",
            filter_str,
        )

        if file_path:
            self.set_file(file_path)

    def mousePressEvent(self, event) -> None:
        """鼠标点击事件."""
        if event.button() == Qt.MouseButton.LeftButton:
            # 点击区域也可以选择文件
            if not self._file_path:
                self._on_select_file()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """拖拽进入事件."""
        if self._get_file_from_mime(event):
            event.acceptProposedAction()
            self.setProperty("dropzone-hover", True)
            self.style().unpolish(self)
            self.style().polish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        """拖拽离开事件."""
        self.setProperty("dropzone-hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        """拖拽放置事件."""
        file_path = self._get_file_from_mime(event)
        if file_path:
            self.set_file(file_path)
            event.acceptProposedAction()

        self.setProperty("dropzone-hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
