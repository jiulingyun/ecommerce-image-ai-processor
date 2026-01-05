"""图层图形项组件.

将数据模型中的图层映射为 QGraphicsItem，用于画布显示和交互。

Classes:
    - LayerGraphicsItem: 图层图形项基类
    - TextLayerItem: 文字图层图形项
    - ShapeLayerItem: 形状图层图形项
    - ImageLayerItem: 图片图层图形项
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QPainterPath,
    QPixmap,
    QCursor,
)
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsObject,
    QStyleOptionGraphicsItem,
    QWidget,
    QGraphicsSceneMouseEvent,
    QGraphicsSceneHoverEvent,
)

from src.models.template_config import (
    LayerType,
    TextLayer,
    ShapeLayer,
    ImageLayer,
    AnyLayer,
    TextAlign,
)
from src.utils.logger import setup_logger

if TYPE_CHECKING:
    from src.ui.widgets.template_editor.canvas import TemplateCanvas

logger = setup_logger(__name__)


# ===================
# 常量定义
# ===================

# 控制点大小
HANDLE_SIZE = 8
HANDLE_HALF = HANDLE_SIZE // 2

# 选中框样式
SELECTION_COLOR = QColor(24, 144, 255)  # #1890ff
SELECTION_WIDTH = 2

# 控制点样式
HANDLE_FILL_COLOR = QColor(255, 255, 255)
HANDLE_BORDER_COLOR = QColor(24, 144, 255)

# 最小尺寸
MIN_SIZE = 10


class HandlePosition(Enum):
    """控制点位置枚举."""

    TOP_LEFT = auto()
    TOP_CENTER = auto()
    TOP_RIGHT = auto()
    MIDDLE_LEFT = auto()
    MIDDLE_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_CENTER = auto()
    BOTTOM_RIGHT = auto()


# 控制点光标映射
HANDLE_CURSORS = {
    HandlePosition.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    HandlePosition.TOP_CENTER: Qt.CursorShape.SizeVerCursor,
    HandlePosition.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    HandlePosition.MIDDLE_LEFT: Qt.CursorShape.SizeHorCursor,
    HandlePosition.MIDDLE_RIGHT: Qt.CursorShape.SizeHorCursor,
    HandlePosition.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
    HandlePosition.BOTTOM_CENTER: Qt.CursorShape.SizeVerCursor,
    HandlePosition.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
}


# ===================
# 信号发射器
# ===================


class LayerSignals(QObject):
    """图层信号发射器.

    由于 QGraphicsItem 不能直接继承 QObject，使用组合模式。
    """

    # 图层被选中
    selected = pyqtSignal(str)  # layer_id
    # 图层被取消选中
    deselected = pyqtSignal(str)  # layer_id
    # 图层位置改变
    position_changed = pyqtSignal(str, int, int)  # layer_id, x, y
    # 图层尺寸改变
    size_changed = pyqtSignal(str, int, int)  # layer_id, width, height
    # 图层属性改变
    layer_changed = pyqtSignal(str)  # layer_id
    # 开始编辑文字
    edit_started = pyqtSignal(str)  # layer_id
    # 结束编辑文字
    edit_finished = pyqtSignal(str, str)  # layer_id, new_content


# ===================
# 图层图形项基类
# ===================


class LayerGraphicsItem(QGraphicsItem):
    """图层图形项基类.

    所有图层类型的图形项基类，提供选中、移动、调整大小等基础功能。

    Attributes:
        layer: 关联的图层数据模型
        signals: 信号发射器

    Features:
        - 选中状态显示（边框和控制点）
        - 鼠标拖拽移动
        - 拖拽控制点调整大小
        - 数据模型同步
    """

    def __init__(
        self,
        layer: AnyLayer,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        """初始化图层图形项.

        Args:
            layer: 图层数据模型
            parent: 父图形项
        """
        super().__init__(parent)

        self._layer = layer
        self.signals = LayerSignals()

        # 拖拽状态
        self._is_resizing = False
        self._resize_handle: Optional[HandlePosition] = None
        self._drag_start_pos: Optional[QPointF] = None
        self._drag_start_rect: Optional[QRectF] = None

        # 设置标志
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not layer.locked)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

        # 设置位置
        self.setPos(layer.x, layer.y)
        self.setZValue(layer.z_index)

        # 设置可见性和透明度
        self.setVisible(layer.visible)
        self.setOpacity(layer.opacity / 100.0)

    # ========================
    # 属性
    # ========================

    @property
    def layer(self) -> AnyLayer:
        """获取关联的图层数据."""
        return self._layer

    @property
    def layer_id(self) -> str:
        """获取图层ID."""
        return self._layer.id

    @property
    def layer_type(self) -> LayerType:
        """获取图层类型."""
        return self._layer.type

    @property
    def is_locked(self) -> bool:
        """是否锁定."""
        return self._layer.locked

    # ========================
    # QGraphicsItem 接口
    # ========================

    def boundingRect(self) -> QRectF:
        """返回边界矩形.

        包含选中时的控制点区域。
        """
        margin = HANDLE_SIZE if self.isSelected() else 0
        return QRectF(
            -margin,
            -margin,
            self._layer.width + margin * 2,
            self._layer.height + margin * 2,
        )

    def shape(self) -> QPainterPath:
        """返回形状路径（用于碰撞检测）."""
        path = QPainterPath()
        path.addRect(QRectF(0, 0, self._layer.width, self._layer.height))
        return path

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        """绘制图形项.

        子类需要重写此方法绘制具体内容。
        """
        # 绘制选中状态
        if self.isSelected():
            self._paint_selection(painter)

    def _paint_selection(self, painter: QPainter) -> None:
        """绘制选中状态（边框和控制点）."""
        painter.save()

        # 绘制选中边框
        pen = QPen(SELECTION_COLOR, SELECTION_WIDTH)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(0, 0, self._layer.width, self._layer.height))

        # 如果未锁定，绘制控制点
        if not self.is_locked:
            self._paint_handles(painter)

        painter.restore()

    def _paint_handles(self, painter: QPainter) -> None:
        """绘制控制点."""
        painter.setPen(QPen(HANDLE_BORDER_COLOR, 1))
        painter.setBrush(QBrush(HANDLE_FILL_COLOR))

        for handle_pos in HandlePosition:
            rect = self._get_handle_rect(handle_pos)
            painter.drawRect(rect)

    def _get_handle_rect(self, handle: HandlePosition) -> QRectF:
        """获取控制点矩形."""
        w, h = self._layer.width, self._layer.height

        positions = {
            HandlePosition.TOP_LEFT: (0, 0),
            HandlePosition.TOP_CENTER: (w / 2, 0),
            HandlePosition.TOP_RIGHT: (w, 0),
            HandlePosition.MIDDLE_LEFT: (0, h / 2),
            HandlePosition.MIDDLE_RIGHT: (w, h / 2),
            HandlePosition.BOTTOM_LEFT: (0, h),
            HandlePosition.BOTTOM_CENTER: (w / 2, h),
            HandlePosition.BOTTOM_RIGHT: (w, h),
        }

        x, y = positions[handle]
        return QRectF(x - HANDLE_HALF, y - HANDLE_HALF, HANDLE_SIZE, HANDLE_SIZE)

    def _handle_at_pos(self, pos: QPointF) -> Optional[HandlePosition]:
        """检测位置处的控制点."""
        if not self.isSelected() or self.is_locked:
            return None

        for handle in HandlePosition:
            if self._get_handle_rect(handle).contains(pos):
                return handle
        return None

    # ========================
    # 鼠标事件
    # ========================

    def hoverMoveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """鼠标悬停移动事件."""
        handle = self._handle_at_pos(event.pos())
        if handle:
            self.setCursor(QCursor(HANDLE_CURSORS[handle]))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """鼠标按下事件."""
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self._handle_at_pos(event.pos())
            if handle and not self.is_locked:
                # 开始调整大小
                self._is_resizing = True
                self._resize_handle = handle
                self._drag_start_pos = event.scenePos()
                self._drag_start_rect = QRectF(
                    self.pos().x(),
                    self.pos().y(),
                    self._layer.width,
                    self._layer.height,
                )
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """鼠标移动事件."""
        if self._is_resizing and self._resize_handle:
            self._do_resize(event.scenePos())
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """鼠标释放事件."""
        if self._is_resizing:
            self._is_resizing = False
            self._resize_handle = None
            self._drag_start_pos = None
            self._drag_start_rect = None
            # 发送尺寸变更信号
            self.signals.size_changed.emit(
                self.layer_id,
                self._layer.width,
                self._layer.height,
            )
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _do_resize(self, scene_pos: QPointF) -> None:
        """执行调整大小."""
        if not self._drag_start_pos or not self._drag_start_rect or not self._resize_handle:
            return

        delta = scene_pos - self._drag_start_pos
        rect = self._drag_start_rect
        handle = self._resize_handle

        new_x = rect.x()
        new_y = rect.y()
        new_w = rect.width()
        new_h = rect.height()

        # 根据控制点位置计算新尺寸
        if handle in (HandlePosition.TOP_LEFT, HandlePosition.MIDDLE_LEFT, HandlePosition.BOTTOM_LEFT):
            new_x = rect.x() + delta.x()
            new_w = rect.width() - delta.x()
        if handle in (HandlePosition.TOP_RIGHT, HandlePosition.MIDDLE_RIGHT, HandlePosition.BOTTOM_RIGHT):
            new_w = rect.width() + delta.x()
        if handle in (HandlePosition.TOP_LEFT, HandlePosition.TOP_CENTER, HandlePosition.TOP_RIGHT):
            new_y = rect.y() + delta.y()
            new_h = rect.height() - delta.y()
        if handle in (HandlePosition.BOTTOM_LEFT, HandlePosition.BOTTOM_CENTER, HandlePosition.BOTTOM_RIGHT):
            new_h = rect.height() + delta.y()

        # 确保最小尺寸
        if new_w < MIN_SIZE:
            if handle in (HandlePosition.TOP_LEFT, HandlePosition.MIDDLE_LEFT, HandlePosition.BOTTOM_LEFT):
                new_x = rect.x() + rect.width() - MIN_SIZE
            new_w = MIN_SIZE
        if new_h < MIN_SIZE:
            if handle in (HandlePosition.TOP_LEFT, HandlePosition.TOP_CENTER, HandlePosition.TOP_RIGHT):
                new_y = rect.y() + rect.height() - MIN_SIZE
            new_h = MIN_SIZE

        # 更新位置和尺寸
        self.prepareGeometryChange()
        self.setPos(new_x, new_y)
        self._layer.x = int(new_x)
        self._layer.y = int(new_y)
        self._layer.width = int(new_w)
        self._layer.height = int(new_h)
        self.update()

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        """图形项变化事件."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # 位置改变，更新数据模型
            pos = value
            self._layer.x = int(pos.x())
            self._layer.y = int(pos.y())
            self.signals.position_changed.emit(
                self.layer_id,
                self._layer.x,
                self._layer.y,
            )

        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if value:
                self.signals.selected.emit(self.layer_id)
            else:
                self.signals.deselected.emit(self.layer_id)

        return super().itemChange(change, value)

    # ========================
    # 公共方法
    # ========================

    def update_from_layer(self) -> None:
        """从数据模型更新显示."""
        self.prepareGeometryChange()
        self.setPos(self._layer.x, self._layer.y)
        self.setZValue(self._layer.z_index)
        self.setVisible(self._layer.visible)
        self.setOpacity(self._layer.opacity / 100.0)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not self._layer.locked)
        self.update()

    def sync_to_layer(self) -> None:
        """同步位置到数据模型."""
        pos = self.pos()
        self._layer.x = int(pos.x())
        self._layer.y = int(pos.y())


# ===================
# 文字图层图形项
# ===================


class TextLayerItem(LayerGraphicsItem):
    """文字图层图形项.

    渲染文字内容，支持字体样式、背景和描边效果。
    支持双击进入编辑模式和自动换行。
    """

    def __init__(
        self,
        layer: TextLayer,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        """初始化文字图层图形项."""
        super().__init__(layer, parent)
        self._text_layer = layer
        self._is_editing = False

    @property
    def text_layer(self) -> TextLayer:
        """获取文字图层数据."""
        return self._text_layer

    @property
    def is_editing(self) -> bool:
        """是否处于编辑模式."""
        return self._is_editing

    def start_editing(self) -> None:
        """开始编辑模式."""
        if self._is_editing or self.is_locked:
            return
        self._is_editing = True
        self.signals.edit_started.emit(self.layer_id)
        self.update()

    def finish_editing(self, new_content: str) -> None:
        """结束编辑模式.

        Args:
            new_content: 新的文字内容
        """
        if not self._is_editing:
            return
        self._is_editing = False
        self._text_layer.content = new_content
        self.signals.edit_finished.emit(self.layer_id, new_content)
        self.signals.layer_changed.emit(self.layer_id)
        self.update()

    def cancel_editing(self) -> None:
        """取消编辑模式（不保存更改）."""
        if not self._is_editing:
            return
        self._is_editing = False
        self.update()

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """双击进入编辑模式."""
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.start_editing()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _build_font(self) -> QFont:
        """根据图层属性构建字体."""
        layer = self._text_layer
        font = QFont()
        if layer.font_family:
            font.setFamily(layer.font_family)
        font.setPointSize(layer.font_size)
        font.setBold(layer.bold)
        font.setItalic(layer.italic)
        font.setUnderline(layer.underline)
        return font

    def _get_alignment_flags(self) -> Qt.AlignmentFlag:
        """获取对齐标志."""
        layer = self._text_layer
        align_map = {
            TextAlign.LEFT: Qt.AlignmentFlag.AlignLeft,
            TextAlign.CENTER: Qt.AlignmentFlag.AlignHCenter,
            TextAlign.RIGHT: Qt.AlignmentFlag.AlignRight,
        }
        alignment = align_map.get(layer.align, Qt.AlignmentFlag.AlignLeft)
        # 支持自动换行
        alignment |= Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap
        return alignment

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        """绘制文字图层."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        layer = self._text_layer
        rect = QRectF(0, 0, layer.width, layer.height)

        # 绘制背景
        if layer.background_enabled:
            bg_color = QColor(*layer.background_color)
            bg_color.setAlpha(int(layer.background_opacity * 255 / 100))
            painter.fillRect(rect, bg_color)

        # 设置字体
        font = self._build_font()
        painter.setFont(font)

        # 计算文字区域
        text_rect = rect.adjusted(
            layer.background_padding,
            layer.background_padding,
            -layer.background_padding,
            -layer.background_padding,
        )

        # 获取对齐标志
        alignment = self._get_alignment_flags()

        # 绘制描边
        if layer.stroke_enabled and layer.stroke_width > 0:
            self._draw_text_stroke(painter, font, text_rect, alignment)

        # 绘制文字
        text_color = QColor(*layer.font_color)
        painter.setPen(text_color)
        painter.drawText(text_rect, int(alignment), layer.content)

        # 编辑模式时显示边框指示
        if self._is_editing:
            painter.setPen(QPen(SELECTION_COLOR, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

        painter.restore()

        # 绘制选中状态
        if not self._is_editing:
            super().paint(painter, option, widget)

    def _draw_text_stroke(self, painter: QPainter, font: QFont, text_rect: QRectF, alignment: int) -> None:
        """绘制文字描边.

        使用偏移绘制多次实现描边效果（比 QPainterPath 更好支持换行）。
        """
        layer = self._text_layer
        stroke_color = QColor(*layer.stroke_color)
        stroke_width = layer.stroke_width
        painter.setPen(stroke_color)

        # 在四个方向偏移绘制描边
        offsets = [
            (-stroke_width, 0),
            (stroke_width, 0),
            (0, -stroke_width),
            (0, stroke_width),
            (-stroke_width, -stroke_width),
            (stroke_width, -stroke_width),
            (-stroke_width, stroke_width),
            (stroke_width, stroke_width),
        ]

        for dx, dy in offsets:
            offset_rect = text_rect.translated(dx, dy)
            painter.drawText(offset_rect, alignment, layer.content)


# ===================
# 形状图层图形项
# ===================


class ShapeLayerItem(LayerGraphicsItem):
    """形状图层图形项.

    渲染矩形或椭圆，支持填充和描边效果。

    Features:
        - 矩形/椭圆绘制
        - 填充色和透明度
        - 描边（颜色、宽度）
        - 圆角矩形
        - 拖拽调整大小和位置
    """

    def __init__(
        self,
        layer: ShapeLayer,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        """初始化形状图层图形项."""
        super().__init__(layer, parent)
        self._shape_layer = layer

    @property
    def shape_layer(self) -> ShapeLayer:
        """获取形状图层数据."""
        return self._shape_layer

    @property
    def is_rectangle(self) -> bool:
        """是否为矩形."""
        return self._shape_layer.type == LayerType.RECTANGLE

    @property
    def is_ellipse(self) -> bool:
        """是否为椭圆."""
        return self._shape_layer.type == LayerType.ELLIPSE

    def set_fill_color(self, color: tuple, opacity: int = 100) -> None:
        """设置填充色.

        Args:
            color: RGB 颜色元组
            opacity: 透明度 (0-100)
        """
        self._shape_layer.fill_color = color
        self._shape_layer.fill_opacity = opacity
        self._shape_layer.fill_enabled = True
        self.update()
        self.signals.layer_changed.emit(self.layer_id)

    def set_stroke(self, color: tuple, width: int = 1) -> None:
        """设置描边.

        Args:
            color: RGB 颜色元组
            width: 描边宽度
        """
        self._shape_layer.stroke_color = color
        self._shape_layer.stroke_width = width
        self._shape_layer.stroke_enabled = True
        self.update()
        self.signals.layer_changed.emit(self.layer_id)

    def set_corner_radius(self, radius: int) -> None:
        """设置圆角半径（仅矩形有效）.

        Args:
            radius: 圆角半径
        """
        self._shape_layer.corner_radius = radius
        self.update()
        self.signals.layer_changed.emit(self.layer_id)

    def disable_fill(self) -> None:
        """禁用填充."""
        self._shape_layer.fill_enabled = False
        self.update()
        self.signals.layer_changed.emit(self.layer_id)

    def disable_stroke(self) -> None:
        """禁用描边."""
        self._shape_layer.stroke_enabled = False
        self.update()
        self.signals.layer_changed.emit(self.layer_id)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        """绘制形状图层."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        layer = self._shape_layer
        rect = QRectF(0, 0, layer.width, layer.height)

        # 设置填充
        if layer.fill_enabled:
            fill_color = QColor(*layer.fill_color)
            fill_color.setAlpha(int(layer.fill_opacity * 255 / 100))
            painter.setBrush(QBrush(fill_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        # 设置描边
        if layer.stroke_enabled and layer.stroke_width > 0:
            stroke_color = QColor(*layer.stroke_color)
            painter.setPen(QPen(stroke_color, layer.stroke_width))
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        # 绘制形状
        if layer.type == LayerType.RECTANGLE:
            if layer.corner_radius > 0:
                painter.drawRoundedRect(rect, layer.corner_radius, layer.corner_radius)
            else:
                painter.drawRect(rect)
        else:  # ELLIPSE
            painter.drawEllipse(rect)

        painter.restore()

        # 绘制选中状态
        super().paint(painter, option, widget)


# ===================
# 图片图层图形项
# ===================


class ImageLayerItem(LayerGraphicsItem):
    """图片图层图形项.

    加载并显示图片，支持多种适应模式。

    Features:
        - 从本地加载图片
        - 支持 contain/cover/stretch 适应模式
        - 透明度设置
        - 拖拽调整大小和位置
        - 图片预览
    """

    def __init__(
        self,
        layer: ImageLayer,
        parent: Optional[QGraphicsItem] = None,
    ) -> None:
        """初始化图片图层图形项."""
        super().__init__(layer, parent)
        self._image_layer = layer
        self._pixmap: Optional[QPixmap] = None
        self._load_image()

    @property
    def image_layer(self) -> ImageLayer:
        """获取图片图层数据."""
        return self._image_layer

    @property
    def has_image(self) -> bool:
        """是否已加载图片."""
        return self._pixmap is not None and not self._pixmap.isNull()

    @property
    def image_size(self) -> tuple:
        """获取原始图片尺寸.

        Returns:
            (width, height) 或 (0, 0) 如果无图片
        """
        if self._pixmap and not self._pixmap.isNull():
            return (self._pixmap.width(), self._pixmap.height())
        return (0, 0)

    def set_image(self, path: str) -> bool:
        """设置图片路径.

        Args:
            path: 图片文件路径

        Returns:
            是否加载成功
        """
        self._image_layer.image_path = path
        self._load_image()
        self.update()
        self.signals.layer_changed.emit(self.layer_id)
        return self.has_image

    def set_fit_mode(self, mode: str) -> None:
        """设置图片适应模式.

        Args:
            mode: 'contain', 'cover', or 'stretch'
        """
        from src.models.template_config import ImageFitMode
        mode_map = {
            'contain': ImageFitMode.CONTAIN,
            'cover': ImageFitMode.COVER,
            'stretch': ImageFitMode.STRETCH,
        }
        if mode in mode_map:
            self._image_layer.fit_mode = mode_map[mode]
            self.update()
            self.signals.layer_changed.emit(self.layer_id)

    def fit_to_image(self) -> None:
        """调整图层尺寸以适应图片原始尺寸."""
        if self.has_image:
            w, h = self.image_size
            self.prepareGeometryChange()
            self._image_layer.width = w
            self._image_layer.height = h
            self.update()
            self.signals.size_changed.emit(self.layer_id, w, h)
            self.signals.layer_changed.emit(self.layer_id)

    def _load_image(self) -> None:
        """加载图片."""
        if self._image_layer.image_path:
            pixmap = QPixmap(self._image_layer.image_path)
            if not pixmap.isNull():
                self._pixmap = pixmap
            else:
                self._pixmap = None
                logger.warning(f"无法加载图片: {self._image_layer.image_path}")
        else:
            self._pixmap = None

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        """绘制图片图层."""
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        layer = self._image_layer
        rect = QRectF(0, 0, layer.width, layer.height)

        if self._pixmap and not self._pixmap.isNull():
            # 根据适应模式绘制图片
            from src.models.template_config import ImageFitMode

            if layer.fit_mode == ImageFitMode.STRETCH:
                # 拉伸填满
                painter.drawPixmap(rect.toRect(), self._pixmap)
            elif layer.fit_mode == ImageFitMode.COVER:
                # 覆盖模式，保持比例裁剪
                scaled = self._pixmap.scaled(
                    int(rect.width()),
                    int(rect.height()),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                # 居中裁剪
                x = (scaled.width() - rect.width()) / 2
                y = (scaled.height() - rect.height()) / 2
                painter.drawPixmap(
                    rect.toRect(),
                    scaled,
                    QRectF(x, y, rect.width(), rect.height()).toRect(),
                )
            else:  # CONTAIN
                # 包含模式，保持比例
                scaled = self._pixmap.scaled(
                    int(rect.width()),
                    int(rect.height()),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                # 居中绘制
                x = (rect.width() - scaled.width()) / 2
                y = (rect.height() - scaled.height()) / 2
                painter.drawPixmap(int(x), int(y), scaled)
        else:
            # 绘制占位符
            painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(240, 240, 240)))
            painter.drawRect(rect)

            # 绘制叉号
            painter.setPen(QPen(QColor(180, 180, 180), 2))
            painter.drawLine(rect.topLeft(), rect.bottomRight())
            painter.drawLine(rect.topRight(), rect.bottomLeft())

            # 绘制提示文字
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "无图片")

        painter.restore()

        # 绘制选中状态
        super().paint(painter, option, widget)

    def reload_image(self) -> None:
        """重新加载图片."""
        self._load_image()
        self.update()


# ===================
# 工厂函数
# ===================


def create_layer_item(
    layer: AnyLayer,
    parent: Optional[QGraphicsItem] = None,
) -> LayerGraphicsItem:
    """根据图层类型创建对应的图形项.

    Args:
        layer: 图层数据模型
        parent: 父图形项

    Returns:
        对应类型的图形项实例
    """
    if isinstance(layer, TextLayer):
        return TextLayerItem(layer, parent)
    elif isinstance(layer, ShapeLayer):
        return ShapeLayerItem(layer, parent)
    elif isinstance(layer, ImageLayer):
        return ImageLayerItem(layer, parent)
    else:
        raise ValueError(f"不支持的图层类型: {type(layer)}")
