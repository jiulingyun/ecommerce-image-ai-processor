"""多图上传区域组件.

支持拖拽多张图片上传，显示图片编号，支持拖拽排序。

Features:
    - 拖拽放置多张图片
    - 显示图片编号（图1、图2、图3）
    - 支持单独删除某张图片
    - 支持拖拽重新排序
    - 显示图片数量和限制提示
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QDrag, QMouseEvent
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)

from src.utils.constants import SUPPORTED_IMAGE_FORMATS, MAX_TASK_IMAGES
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 缩略图大小
THUMBNAIL_SIZE = (100, 100)


class ImageThumbnail(QFrame):
    """单个图片缩略图组件.
    
    显示单张图片的缩略图，带编号和删除按钮。
    支持拖拽排序。
    """
    
    delete_clicked = pyqtSignal(int)  # index
    drag_started = pyqtSignal(int)  # index
    
    def __init__(
        self,
        index: int,
        file_path: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化图片缩略图.
        
        Args:
            index: 图片索引（0-based）
            file_path: 图片文件路径
            parent: 父组件
        """
        super().__init__(parent)
        self._index = index
        self._file_path = file_path
        self._drag_start_position: Optional[QPoint] = None
        
        self._setup_ui()
        self._load_thumbnail()
    
    @property
    def index(self) -> int:
        """图片索引."""
        return self._index
    
    @index.setter
    def index(self, value: int) -> None:
        """设置图片索引."""
        self._index = value
        self._index_label.setText(f"图{value + 1}")
    
    @property
    def file_path(self) -> str:
        """文件路径."""
        return self._file_path
    
    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setProperty("imageThumbnail", True)
        self.setFixedSize(120, 150)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # 编号标签
        self._index_label = QLabel(f"图{self._index + 1}")
        self._index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._index_label.setStyleSheet("""
            background-color: #1890ff;
            color: white;
            font-size: 12px;
            font-weight: bold;
            border-radius: 4px;
            padding: 2px 8px;
        """)
        layout.addWidget(self._index_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 缩略图
        self._thumbnail_label = QLabel()
        self._thumbnail_label.setFixedSize(THUMBNAIL_SIZE[0], THUMBNAIL_SIZE[1])
        self._thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumbnail_label.setStyleSheet("""
            background-color: #f5f5f5;
            border: 1px solid #e8e8e8;
            border-radius: 4px;
        """)
        layout.addWidget(self._thumbnail_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 删除按钮
        self._delete_btn = QPushButton("X")
        self._delete_btn.setObjectName("deleteBtn")
        self._delete_btn.setFixedSize(22, 22)
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self._index))
        layout.addWidget(self._delete_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 整体样式（包含删除按钮）
        self.setStyleSheet("""
            ImageThumbnail {
                background-color: #fafafa;
                border: 1px solid #d9d9d9;
                border-radius: 8px;
            }
            ImageThumbnail:hover {
                border-color: #1890ff;
                background-color: #e6f7ff;
            }
            QPushButton#deleteBtn {
                background-color: #ff4d4f;
                color: white;
                font-size: 14px;
                font-weight: bold;
                font-family: Arial, Helvetica, sans-serif;
                border: none;
                border-radius: 11px;
                padding: 0px;
                margin: 0px;
            }
            QPushButton#deleteBtn:hover {
                background-color: #ff7875;
            }
        """)
    
    def _load_thumbnail(self) -> None:
        """加载缩略图."""
        try:
            pixmap = QPixmap(self._file_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    THUMBNAIL_SIZE[0] - 4,
                    THUMBNAIL_SIZE[1] - 4,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._thumbnail_label.setPixmap(scaled)
            else:
                self._thumbnail_label.setText("加载失败")
        except Exception as e:
            logger.error(f"加载缩略图失败: {e}")
            self._thumbnail_label.setText("加载失败")
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """鼠标按下事件."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_position = event.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动事件，触发拖拽."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_start_position is None:
            return
        
        # 检查是否超过拖拽阈值
        distance = (event.pos() - self._drag_start_position).manhattanLength()
        if distance < 10:
            return
        
        # 开始拖拽
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self._index))
        drag.setMimeData(mime_data)
        
        # 设置拖拽图像
        pixmap = self.grab()
        drag.setPixmap(pixmap.scaled(80, 100, Qt.AspectRatioMode.KeepAspectRatio))
        drag.setHotSpot(QPoint(40, 50))
        
        self.drag_started.emit(self._index)
        drag.exec(Qt.DropAction.MoveAction)
        
        self.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """鼠标释放事件."""
        self._drag_start_position = None
        super().mouseReleaseEvent(event)


class MultiImageDropZone(QFrame):
    """多图上传区域组件.
    
    支持拖拽多张图片上传，显示图片编号，支持拖拽排序。
    
    Signals:
        images_changed: 图片列表变化信号
        
    Attributes:
        image_paths: 当前图片路径列表
        image_count: 当前图片数量
    """
    
    images_changed = pyqtSignal()
    
    def __init__(
        self,
        max_images: int = MAX_TASK_IMAGES,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化多图上传区域.
        
        Args:
            max_images: 最大图片数量
            parent: 父组件
        """
        super().__init__(parent)
        
        self._max_images = max_images
        self._image_paths: List[str] = []
        self._thumbnails: List[ImageThumbnail] = []
        self._dragging_index: Optional[int] = None
        
        self._setup_ui()
        self._setup_drag_drop()
    
    @property
    def image_paths(self) -> List[str]:
        """图片路径列表."""
        return self._image_paths.copy()
    
    @property
    def image_count(self) -> int:
        """图片数量."""
        return len(self._image_paths)
    
    @property
    def has_images(self) -> bool:
        """是否有图片."""
        return len(self._image_paths) > 0
    
    @property
    def is_full(self) -> bool:
        """是否已满."""
        return len(self._image_paths) >= self._max_images
    
    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setProperty("multiImageDropZone", True)
        self.setMinimumHeight(200)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # 标题和数量提示
        header_layout = QHBoxLayout()
        
        title_label = QLabel("添加图片")
        title_label.setProperty("subheading", True)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self._count_label = QLabel(f"0/{self._max_images}")
        self._count_label.setProperty("hint", True)
        header_layout.addWidget(self._count_label)
        
        main_layout.addLayout(header_layout)
        
        # 图片展示区域（水平滚动）
        self._images_container = QFrame()
        self._images_container.setProperty("card", True)
        self._images_container.setAcceptDrops(True)
        
        self._images_layout = QHBoxLayout(self._images_container)
        self._images_layout.setContentsMargins(12, 12, 12, 12)
        self._images_layout.setSpacing(12)
        self._images_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # 空状态/添加提示
        self._empty_widget = QFrame()
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._hint_label = QLabel("拖拽图片到此处\n或点击下方按钮选择\n\n支持1-3张图片")
        self._hint_label.setProperty("hint", True)
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setStyleSheet("font-size: 14px; color: #999;")
        empty_layout.addWidget(self._hint_label)
        
        self._images_layout.addWidget(self._empty_widget)
        self._images_layout.addStretch()
        
        main_layout.addWidget(self._images_container, 1)
        
        # 底部按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        self._select_btn = QPushButton("选择图片")
        self._select_btn.setProperty("secondary", True)
        self._select_btn.clicked.connect(self._on_select_files)
        button_layout.addWidget(self._select_btn)
        
        self._clear_btn = QPushButton("清空全部")
        self._clear_btn.setProperty("danger", True)
        self._clear_btn.clicked.connect(self.clear_all)
        self._clear_btn.setEnabled(False)
        button_layout.addWidget(self._clear_btn)
        
        button_layout.addStretch()
        
        # 提示文字
        tip_label = QLabel("💡 拖拽图片可调整顺序，提示词中用「图1」「图2」「图3」引用")
        tip_label.setProperty("hint", True)
        button_layout.addWidget(tip_label)
        
        main_layout.addLayout(button_layout)
        
        # 整体样式
        self.setStyleSheet("""
            MultiImageDropZone {
                background-color: #fafafa;
                border: 2px dashed #d9d9d9;
                border-radius: 8px;
            }
            MultiImageDropZone[dropzone-hover="true"] {
                border-color: #1890ff;
                background-color: #e6f7ff;
            }
        """)
    
    def _setup_drag_drop(self) -> None:
        """设置拖拽功能."""
        self.setAcceptDrops(True)
        self._images_container.setAcceptDrops(True)
    
    def _update_display(self) -> None:
        """更新显示."""
        # 更新数量标签
        self._count_label.setText(f"{self.image_count}/{self._max_images}")
        
        # 更新空状态显示
        self._empty_widget.setVisible(self.image_count == 0)
        
        # 更新按钮状态
        self._clear_btn.setEnabled(self.image_count > 0)
        self._select_btn.setEnabled(not self.is_full)
        
        # 更新提示文字
        if self.is_full:
            self._hint_label.setText(f"已达到最大数量（{self._max_images}张）")
    
    def _rebuild_thumbnails(self) -> None:
        """重建缩略图列表."""
        # 清除旧的缩略图
        for thumb in self._thumbnails:
            thumb.deleteLater()
        self._thumbnails.clear()
        
        # 创建新的缩略图
        for i, path in enumerate(self._image_paths):
            thumb = ImageThumbnail(i, path, self)
            thumb.delete_clicked.connect(self._on_delete_image)
            thumb.drag_started.connect(self._on_drag_started)
            self._thumbnails.append(thumb)
            # 在 stretch 之前插入
            self._images_layout.insertWidget(i, thumb)
        
        self._update_display()
    
    def _update_thumbnail_indices(self) -> None:
        """更新缩略图索引."""
        for i, thumb in enumerate(self._thumbnails):
            thumb.index = i
    
    def add_images(self, file_paths: List[str]) -> int:
        """添加图片.
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            实际添加的图片数量
        """
        added = 0
        for path in file_paths:
            if self.is_full:
                break
            if self._validate_file(path) and path not in self._image_paths:
                self._image_paths.append(path)
                added += 1
        
        if added > 0:
            self._rebuild_thumbnails()
            self.images_changed.emit()
            logger.info(f"添加了 {added} 张图片")
        
        return added
    
    def remove_image(self, index: int) -> bool:
        """删除指定索引的图片.
        
        Args:
            index: 图片索引
            
        Returns:
            是否删除成功
        """
        if 0 <= index < len(self._image_paths):
            removed_path = self._image_paths.pop(index)
            self._rebuild_thumbnails()
            self.images_changed.emit()
            logger.info(f"删除图片: {removed_path}")
            return True
        return False
    
    def move_image(self, from_index: int, to_index: int) -> bool:
        """移动图片位置.
        
        Args:
            from_index: 源索引
            to_index: 目标索引
            
        Returns:
            是否移动成功
        """
        if from_index == to_index:
            return False
        if not (0 <= from_index < len(self._image_paths)):
            return False
        if not (0 <= to_index < len(self._image_paths)):
            return False
        
        # 移动图片
        path = self._image_paths.pop(from_index)
        self._image_paths.insert(to_index, path)
        
        self._rebuild_thumbnails()
        self.images_changed.emit()
        logger.info(f"移动图片: {from_index} -> {to_index}")
        return True
    
    def clear_all(self) -> None:
        """清空所有图片."""
        if self._image_paths:
            self._image_paths.clear()
            self._rebuild_thumbnails()
            self.images_changed.emit()
            logger.info("清空所有图片")
    
    def _validate_file(self, file_path: str) -> bool:
        """验证文件.
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否有效
        """
        path = Path(file_path)
        
        if not path.exists():
            logger.warning(f"文件不存在: {file_path}")
            return False
        
        if path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
            logger.warning(f"不支持的图片格式: {path.suffix}")
            return False
        
        return True
    
    def _get_files_from_mime(self, event) -> List[str]:
        """从拖拽事件获取文件路径列表.
        
        Args:
            event: 拖拽事件
            
        Returns:
            有效的文件路径列表
        """
        valid_files = []
        mime_data = event.mimeData()
        
        if mime_data.hasUrls():
            for url in mime_data.urls():
                file_path = url.toLocalFile()
                if self._validate_file(file_path):
                    valid_files.append(file_path)
        
        return valid_files
    
    def _on_select_files(self) -> None:
        """选择文件按钮点击."""
        if self.is_full:
            return
        
        formats = " ".join(f"*{ext}" for ext in SUPPORTED_IMAGE_FORMATS)
        filter_str = f"图片文件 ({formats});;所有文件 (*.*)"
        
        remaining = self._max_images - self.image_count
        
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            f"选择图片（还可添加 {remaining} 张）",
            "",
            filter_str,
        )
        
        if file_paths:
            self.add_images(file_paths[:remaining])
    
    def _on_delete_image(self, index: int) -> None:
        """删除图片."""
        self.remove_image(index)
    
    def _on_drag_started(self, index: int) -> None:
        """拖拽开始."""
        self._dragging_index = index
    
    def _calculate_drop_index(self, pos: QPoint) -> int:
        """计算放置位置索引.
        
        Args:
            pos: 鼠标位置（相对于 images_container）
            
        Returns:
            放置位置索引
        """
        if not self._thumbnails:
            return 0
        
        # 遍历缩略图，找到最近的位置
        for i, thumb in enumerate(self._thumbnails):
            thumb_pos = thumb.pos()
            thumb_center_x = thumb_pos.x() + thumb.width() // 2
            
            if pos.x() < thumb_center_x:
                return i
        
        return len(self._thumbnails)
    
    # 拖拽事件处理
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """拖拽进入事件."""
        mime_data = event.mimeData()
        
        # 检查是否是内部排序拖拽
        if mime_data.hasText() and mime_data.text().isdigit():
            event.acceptProposedAction()
            self.setProperty("dropzone-hover", True)
            self.style().unpolish(self)
            self.style().polish(self)
            return
        
        # 检查是否是外部文件拖入
        if self._get_files_from_mime(event) and not self.is_full:
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
        mime_data = event.mimeData()
        
        # 处理内部排序拖拽
        if mime_data.hasText() and mime_data.text().isdigit():
            from_index = int(mime_data.text())
            # 计算放置位置
            pos = self._images_container.mapFromParent(event.position().toPoint())
            to_index = self._calculate_drop_index(pos)
            
            # 调整索引（如果向后移动）
            if to_index > from_index:
                to_index -= 1
            
            self.move_image(from_index, to_index)
            event.acceptProposedAction()
        else:
            # 处理外部文件拖入
            file_paths = self._get_files_from_mime(event)
            if file_paths:
                remaining = self._max_images - self.image_count
                self.add_images(file_paths[:remaining])
                event.acceptProposedAction()
        
        self.setProperty("dropzone-hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self._dragging_index = None
