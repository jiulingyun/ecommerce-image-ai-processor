"""文字编辑覆盖层组件.

在画布上显示文字编辑器，支持实时编辑文字图层内容。

Features:
    - 覆盖在文字图层上显示
    - 支持多行编辑和自动换行
    - 实时同步样式（字体、颜色、对齐）
    - 点击外部或按 Esc 退出编辑
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QFont,
    QColor,
    QPalette,
    QFocusEvent,
    QKeyEvent,
)
from PyQt6.QtWidgets import (
    QTextEdit,
    QGraphicsProxyWidget,
)

from src.models.template_config import TextAlign

if TYPE_CHECKING:
    from src.models.template_config import TextLayer
    from src.ui.widgets.template_editor.layer_items import TextLayerItem


class TextEditWidget(QTextEdit):
    """文字编辑组件.

    继承 QTextEdit，支持文字图层的内联编辑。
    """

    # 编辑完成信号
    editing_finished = pyqtSignal(str)  # new_content
    # 编辑取消信号
    editing_cancelled = pyqtSignal()

    def __init__(self, parent=None) -> None:
        """初始化文字编辑组件."""
        super().__init__(parent)

        # 设置基本属性
        self.setFrameStyle(0)  # 无边框
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 设置透明背景（由图层自己绘制背景）
        self.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)

    def setup_from_layer(self, layer: "TextLayer") -> None:
        """根据图层设置编辑器样式.

        Args:
            layer: 文字图层数据
        """
        # 设置字体
        font = QFont()
        if layer.font_family:
            font.setFamily(layer.font_family)
        font.setPointSize(layer.font_size)
        font.setBold(layer.bold)
        font.setItalic(layer.italic)
        font.setUnderline(layer.underline)
        self.setFont(font)

        # 设置文字颜色
        palette = self.palette()
        text_color = QColor(*layer.font_color)
        palette.setColor(QPalette.ColorRole.Text, text_color)
        self.setPalette(palette)

        # 设置对齐
        align_map = {
            TextAlign.LEFT: Qt.AlignmentFlag.AlignLeft,
            TextAlign.CENTER: Qt.AlignmentFlag.AlignCenter,
            TextAlign.RIGHT: Qt.AlignmentFlag.AlignRight,
        }
        alignment = align_map.get(layer.align, Qt.AlignmentFlag.AlignLeft)
        self.setAlignment(alignment)

        # 设置内容
        self.setPlainText(layer.content)

        # 全选文字便于编辑
        self.selectAll()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        """失去焦点时完成编辑."""
        # 发送编辑完成信号
        self.editing_finished.emit(self.toPlainText())
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """处理按键事件."""
        # Escape 取消编辑
        if event.key() == Qt.Key.Key_Escape:
            self.editing_cancelled.emit()
            event.accept()
            return

        # Ctrl+Enter 或 Shift+Enter 完成编辑
        if event.key() == Qt.Key.Key_Return and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
            or event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.editing_finished.emit(self.toPlainText())
            event.accept()
            return

        super().keyPressEvent(event)


class TextEditOverlay(QGraphicsProxyWidget):
    """文字编辑覆盖层.

    在画布上显示文字编辑器，覆盖在文字图层上。
    """

    # 编辑完成信号
    editing_finished = pyqtSignal(str, str)  # layer_id, new_content
    # 编辑取消信号
    editing_cancelled = pyqtSignal(str)  # layer_id

    def __init__(self, parent=None) -> None:
        """初始化覆盖层."""
        super().__init__(parent)

        self._layer_id: Optional[str] = None
        self._layer_item: Optional["TextLayerItem"] = None

        # 创建编辑器
        self._editor = TextEditWidget()
        self._editor.editing_finished.connect(self._on_editing_finished)
        self._editor.editing_cancelled.connect(self._on_editing_cancelled)
        self.setWidget(self._editor)

        # 初始隐藏
        self.hide()

    @property
    def layer_id(self) -> Optional[str]:
        """当前编辑的图层ID."""
        return self._layer_id

    @property
    def is_editing(self) -> bool:
        """是否正在编辑."""
        return self.isVisible() and self._layer_id is not None

    def start_editing(self, layer_item: "TextLayerItem") -> None:
        """开始编辑文字图层.

        Args:
            layer_item: 要编辑的文字图层项
        """
        self._layer_id = layer_item.layer_id
        self._layer_item = layer_item
        layer = layer_item.text_layer

        # 配置编辑器
        self._editor.setup_from_layer(layer)

        # 设置位置和大小（与图层对齐）
        padding = layer.background_padding
        rect = QRectF(
            padding,
            padding,
            layer.width - padding * 2,
            layer.height - padding * 2,
        )
        self.setGeometry(rect)

        # 设置位置到图层
        self.setPos(layer_item.pos() + QRectF(0, 0, padding, padding).topLeft())

        # 显示并获取焦点
        self.show()
        self._editor.setFocus(Qt.FocusReason.OtherFocusReason)

    def finish_editing(self) -> str:
        """完成编辑并返回新内容.

        Returns:
            新的文字内容
        """
        content = self._editor.toPlainText()
        self._cleanup()
        return content

    def cancel_editing(self) -> None:
        """取消编辑."""
        self._cleanup()

    def _cleanup(self) -> None:
        """清理编辑状态."""
        self.hide()
        self._layer_id = None
        self._layer_item = None

    def _on_editing_finished(self, content: str) -> None:
        """编辑完成处理."""
        if self._layer_id:
            layer_id = self._layer_id
            self._cleanup()
            self.editing_finished.emit(layer_id, content)

    def _on_editing_cancelled(self) -> None:
        """编辑取消处理."""
        if self._layer_id:
            layer_id = self._layer_id
            self._cleanup()
            self.editing_cancelled.emit(layer_id)

    def update_position(self) -> None:
        """更新覆盖层位置（当图层移动时调用）."""
        if self._layer_item:
            layer = self._layer_item.text_layer
            padding = layer.background_padding
            self.setPos(
                self._layer_item.pos().x() + padding,
                self._layer_item.pos().y() + padding,
            )
