"""模板画布组件.

提供模板编辑的可视化画布，支持缩放、平移、网格显示和图层管理。

Features:
    - 画布缩放和平移
    - 背景网格显示
    - 图层添加、删除、选择
    - 多选和框选
    - 与数据模型同步
"""

from __future__ import annotations

from typing import Optional, List, Dict

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal, QLineF
from PyQt6.QtGui import (
    QPainter,
    QPen,
    QBrush,
    QColor,
    QWheelEvent,
    QMouseEvent,
    QKeyEvent,
    QTransform,
)
from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsRectItem,
    QRubberBand,
    QWidget,
)

from src.models.template_config import (
    TemplateConfig,
    AnyLayer,
    TextLayer,
    ShapeLayer,
    ImageLayer,
    LayerType,
)
from src.ui.widgets.template_editor.layer_items import (
    LayerGraphicsItem,
    TextLayerItem,
    create_layer_item,
)
from src.ui.widgets.template_editor.text_edit_overlay import TextEditOverlay
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


# ===================
# 常量定义
# ===================

# 缩放限制
MIN_ZOOM = 0.1
MAX_ZOOM = 5.0
ZOOM_STEP = 0.1

# 网格设置
GRID_SIZE = 20
GRID_COLOR = QColor(230, 230, 230)
GRID_MAJOR_COLOR = QColor(200, 200, 200)
GRID_MAJOR_INTERVAL = 5  # 每5个小格一条主线

# 画布边距（场景超出画布的区域）
CANVAS_MARGIN = 100

# 画布边框颜色
CANVAS_BORDER_COLOR = QColor(200, 200, 200)
CANVAS_SHADOW_COLOR = QColor(0, 0, 0, 30)


# ===================
# 画布场景
# ===================


class TemplateScene(QGraphicsScene):
    """模板编辑场景.

    管理画布区域和图层项。
    """

    def __init__(
        self,
        canvas_width: int,
        canvas_height: int,
        parent: Optional[QWidget] = None,
    ) -> None:
        """初始化场景.

        Args:
            canvas_width: 画布宽度
            canvas_height: 画布高度
            parent: 父组件
        """
        super().__init__(parent)

        self._canvas_width = canvas_width
        self._canvas_height = canvas_height
        self._background_color = QColor(255, 255, 255)
        self._show_grid = True

        # 设置场景大小（包含边距）
        self._update_scene_rect()

    @property
    def canvas_width(self) -> int:
        """画布宽度."""
        return self._canvas_width

    @property
    def canvas_height(self) -> int:
        """画布高度."""
        return self._canvas_height

    @property
    def canvas_rect(self) -> QRectF:
        """画布矩形区域."""
        return QRectF(0, 0, self._canvas_width, self._canvas_height)

    def set_canvas_size(self, width: int, height: int) -> None:
        """设置画布大小."""
        self._canvas_width = width
        self._canvas_height = height
        self._update_scene_rect()
        self.update()

    def set_background_color(self, color: tuple) -> None:
        """设置背景颜色."""
        self._background_color = QColor(*color)
        self.update()

    def set_show_grid(self, show: bool) -> None:
        """设置是否显示网格."""
        self._show_grid = show
        self.update()

    def _update_scene_rect(self) -> None:
        """更新场景矩形."""
        self.setSceneRect(
            -CANVAS_MARGIN,
            -CANVAS_MARGIN,
            self._canvas_width + CANVAS_MARGIN * 2,
            self._canvas_height + CANVAS_MARGIN * 2,
        )

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """绘制背景."""
        painter.save()

        # 绘制场景背景（画布外区域）
        painter.fillRect(rect, QColor(245, 245, 245))

        # 绘制画布阴影
        shadow_offset = 4
        shadow_rect = QRectF(
            shadow_offset,
            shadow_offset,
            self._canvas_width,
            self._canvas_height,
        )
        painter.fillRect(shadow_rect, CANVAS_SHADOW_COLOR)

        # 绘制画布背景
        canvas_rect = self.canvas_rect
        painter.fillRect(canvas_rect, self._background_color)

        # 绘制网格
        if self._show_grid:
            self._draw_grid(painter, canvas_rect)

        # 绘制画布边框
        painter.setPen(QPen(CANVAS_BORDER_COLOR, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(canvas_rect)

        painter.restore()

    def _draw_grid(self, painter: QPainter, rect: QRectF) -> None:
        """绘制网格."""
        left = int(rect.left())
        top = int(rect.top())
        right = int(rect.right())
        bottom = int(rect.bottom())

        # 绘制次网格线
        painter.setPen(QPen(GRID_COLOR, 0.5))
        for x in range(left, right + 1, GRID_SIZE):
            if (x - left) % (GRID_SIZE * GRID_MAJOR_INTERVAL) != 0:
                painter.drawLine(x, top, x, bottom)
        for y in range(top, bottom + 1, GRID_SIZE):
            if (y - top) % (GRID_SIZE * GRID_MAJOR_INTERVAL) != 0:
                painter.drawLine(left, y, right, y)

        # 绘制主网格线
        painter.setPen(QPen(GRID_MAJOR_COLOR, 0.5))
        for x in range(left, right + 1, GRID_SIZE * GRID_MAJOR_INTERVAL):
            painter.drawLine(x, top, x, bottom)
        for y in range(top, bottom + 1, GRID_SIZE * GRID_MAJOR_INTERVAL):
            painter.drawLine(left, y, right, y)


# ===================
# 画布视图
# ===================


class TemplateCanvas(QGraphicsView):
    """模板画布视图.

    提供模板编辑的可视化界面，支持缩放、平移、图层管理等功能。

    Signals:
        layer_selected: 图层被选中
        layer_deselected: 图层被取消选中
        layer_moved: 图层位置改变
        layer_resized: 图层尺寸改变
        selection_changed: 选择状态改变
        zoom_changed: 缩放比例改变

    Example:
        >>> canvas = TemplateCanvas()
        >>> template = TemplateConfig(name="测试模板")
        >>> canvas.set_template(template)
        >>> canvas.add_layer(TextLayer.create("Hello"))
    """

    # 信号定义
    layer_selected = pyqtSignal(str)  # layer_id
    layer_deselected = pyqtSignal(str)  # layer_id
    layer_moved = pyqtSignal(str, int, int)  # layer_id, x, y
    layer_resized = pyqtSignal(str, int, int)  # layer_id, width, height
    layer_content_changed = pyqtSignal(str, str)  # layer_id, new_content
    selection_changed = pyqtSignal(list)  # list[layer_id]
    zoom_changed = pyqtSignal(float)  # zoom_level

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化画布视图."""
        super().__init__(parent)

        # 模板和图层管理
        self._template: Optional[TemplateConfig] = None
        self._layer_items: Dict[str, LayerGraphicsItem] = {}

        # 交互状态
        self._is_panning = False
        self._pan_start_pos: Optional[QPointF] = None
        self._space_pressed = False
        self._zoom_level = 1.0

        # 框选
        self._rubber_band: Optional[QRubberBand] = None
        self._rubber_band_origin: Optional[QPointF] = None

        # 文字编辑覆盖层
        self._text_edit_overlay: Optional[TextEditOverlay] = None

        # 初始化UI
        self._setup_ui()
        self._setup_scene()
        self._setup_text_editor()

    # ========================
    # 初始化
    # ========================

    def _setup_ui(self) -> None:
        """设置UI属性."""
        # 渲染设置
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 视图设置
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        # 启用鼠标追踪
        self.setMouseTracking(True)

        # 设置背景
        self.setBackgroundBrush(QBrush(QColor(245, 245, 245)))

    def _setup_scene(self) -> None:
        """设置场景."""
        from src.models.template_config import DEFAULT_CANVAS_SIZE

        self._scene = TemplateScene(
            DEFAULT_CANVAS_SIZE[0],
            DEFAULT_CANVAS_SIZE[1],
        )
        self.setScene(self._scene)

        # 居中显示
        self.centerOn(self._scene.canvas_rect.center())

    def _setup_text_editor(self) -> None:
        """设置文字编辑器."""
        self._text_edit_overlay = TextEditOverlay()
        self._scene.addItem(self._text_edit_overlay)
        self._text_edit_overlay.setZValue(10000)  # 确保在最上层

        # 连接信号
        self._text_edit_overlay.editing_finished.connect(self._on_text_editing_finished)
        self._text_edit_overlay.editing_cancelled.connect(self._on_text_editing_cancelled)

    # ========================
    # 公共属性
    # ========================

    @property
    def template(self) -> Optional[TemplateConfig]:
        """当前模板."""
        return self._template

    @property
    def zoom_level(self) -> float:
        """当前缩放比例."""
        return self._zoom_level

    @property
    def selected_layers(self) -> List[str]:
        """获取选中的图层ID列表."""
        return [
            item.layer_id
            for item in self._layer_items.values()
            if item.isSelected()
        ]

    @property
    def show_grid(self) -> bool:
        """是否显示网格."""
        return self._scene._show_grid

    # ========================
    # 模板管理
    # ========================

    def set_template(self, template: Optional[TemplateConfig]) -> None:
        """设置模板.

        Args:
            template: 模板配置，None表示清空
        """
        # 清空现有图层
        self.clear_layers()

        self._template = template

        if template:
            # 更新画布大小
            self._scene.set_canvas_size(
                template.canvas_width,
                template.canvas_height,
            )
            self._scene.set_background_color(template.background_color)

            # 加载图层
            for layer in template.get_layers():
                self._add_layer_item(layer)

            # 居中显示
            self.fit_in_view()

    def clear_layers(self) -> None:
        """清空所有图层."""
        for item in self._layer_items.values():
            self._scene.removeItem(item)
        self._layer_items.clear()

    def refresh_from_template(self) -> None:
        """从模板刷新显示."""
        if not self._template:
            return

        # 更新画布
        self._scene.set_canvas_size(
            self._template.canvas_width,
            self._template.canvas_height,
        )
        self._scene.set_background_color(self._template.background_color)

        # 获取当前图层ID
        current_ids = set(self._layer_items.keys())
        template_ids = {l.id for l in self._template.get_layers()}

        # 删除不存在的图层项
        for layer_id in current_ids - template_ids:
            item = self._layer_items.pop(layer_id)
            self._scene.removeItem(item)

        # 添加新图层
        for layer in self._template.get_layers():
            if layer.id not in current_ids:
                self._add_layer_item(layer)
            else:
                # 更新现有图层
                self._layer_items[layer.id].update_from_layer()

    # ========================
    # 图层管理
    # ========================

    def add_layer(self, layer: AnyLayer) -> None:
        """添加图层.

        Args:
            layer: 图层数据模型
        """
        if not self._template:
            return

        # 添加到模板
        self._template.add_layer(layer)

        # 创建图形项
        self._add_layer_item(layer)

    def _add_layer_item(self, layer: AnyLayer) -> LayerGraphicsItem:
        """添加图层图形项."""
        item = create_layer_item(layer)

        # 连接信号
        item.signals.selected.connect(self._on_item_selected)
        item.signals.deselected.connect(self._on_item_deselected)
        item.signals.position_changed.connect(self._on_item_moved)
        item.signals.size_changed.connect(self._on_item_resized)

        # 文字图层额外连接编辑信号
        if isinstance(item, TextLayerItem):
            item.signals.edit_started.connect(self._on_text_edit_started)

        # 添加到场景
        self._scene.addItem(item)
        self._layer_items[layer.id] = item

        return item

    def remove_layer(self, layer_id: str) -> bool:
        """删除图层.

        Args:
            layer_id: 图层ID

        Returns:
            是否删除成功
        """
        if not self._template:
            return False

        # 从模板删除
        if not self._template.remove_layer(layer_id):
            return False

        # 从场景删除
        if layer_id in self._layer_items:
            item = self._layer_items.pop(layer_id)
            self._scene.removeItem(item)

        return True

    def get_layer_item(self, layer_id: str) -> Optional[LayerGraphicsItem]:
        """获取图层图形项.

        Args:
            layer_id: 图层ID

        Returns:
            图形项，不存在返回None
        """
        return self._layer_items.get(layer_id)

    def update_layer(self, layer_id: str) -> None:
        """更新图层显示.

        Args:
            layer_id: 图层ID
        """
        if layer_id in self._layer_items:
            self._layer_items[layer_id].update_from_layer()

    def select_layer(self, layer_id: str, clear_others: bool = True) -> None:
        """选中图层.

        Args:
            layer_id: 图层ID
            clear_others: 是否清除其他选中
        """
        if clear_others:
            self._scene.clearSelection()

        if layer_id in self._layer_items:
            self._layer_items[layer_id].setSelected(True)

    def deselect_all(self) -> None:
        """取消所有选中."""
        self._scene.clearSelection()

    # ========================
    # 视图控制
    # ========================

    def set_zoom(self, level: float) -> None:
        """设置缩放级别.

        Args:
            level: 缩放比例 (0.1 - 5.0)
        """
        level = max(MIN_ZOOM, min(MAX_ZOOM, level))
        if level != self._zoom_level:
            scale_factor = level / self._zoom_level
            self.scale(scale_factor, scale_factor)
            self._zoom_level = level
            self.zoom_changed.emit(self._zoom_level)

    def zoom_in(self) -> None:
        """放大."""
        self.set_zoom(self._zoom_level + ZOOM_STEP)

    def zoom_out(self) -> None:
        """缩小."""
        self.set_zoom(self._zoom_level - ZOOM_STEP)

    def zoom_reset(self) -> None:
        """重置缩放."""
        self.set_zoom(1.0)

    def fit_in_view(self) -> None:
        """适应视图大小."""
        self.fitInView(
            self._scene.canvas_rect,
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        # 更新缩放级别
        transform = self.transform()
        self._zoom_level = transform.m11()
        self.zoom_changed.emit(self._zoom_level)

    def set_show_grid(self, show: bool) -> None:
        """设置是否显示网格."""
        self._scene.set_show_grid(show)

    # ========================
    # 事件处理
    # ========================

    def wheelEvent(self, event: QWheelEvent) -> None:
        """鼠标滚轮事件 - 缩放."""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl + 滚轮缩放
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """鼠标按下事件."""
        # 中键或空格+左键开始平移
        if event.button() == Qt.MouseButton.MiddleButton or (
            self._space_pressed and event.button() == Qt.MouseButton.LeftButton
        ):
            self._is_panning = True
            self._pan_start_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动事件."""
        if self._is_panning and self._pan_start_pos:
            # 平移
            delta = event.position() - self._pan_start_pos
            self._pan_start_pos = event.position()
            self.horizontalScrollBar().setValue(
                int(self.horizontalScrollBar().value() - delta.x())
            )
            self.verticalScrollBar().setValue(
                int(self.verticalScrollBar().value() - delta.y())
            )
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """鼠标释放事件."""
        if self._is_panning:
            self._is_panning = False
            self._pan_start_pos = None
            if self._space_pressed:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        # 发送选择变更信号
        self.selection_changed.emit(self.selected_layers)

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """按键按下事件."""
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pressed = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return

        # Delete 键删除选中图层
        if event.key() == Qt.Key.Key_Delete:
            for layer_id in self.selected_layers:
                self.remove_layer(layer_id)
            event.accept()
            return

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        """按键释放事件."""
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_pressed = False
            if not self._is_panning:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        super().keyReleaseEvent(event)

    # ========================
    # 内部槽函数
    # ========================

    def _on_item_selected(self, layer_id: str) -> None:
        """图层被选中."""
        self.layer_selected.emit(layer_id)

    def _on_item_deselected(self, layer_id: str) -> None:
        """图层被取消选中."""
        self.layer_deselected.emit(layer_id)

    def _on_item_moved(self, layer_id: str, x: int, y: int) -> None:
        """图层位置改变."""
        # 更新模板数据
        if self._template:
            layer = self._template.get_layer_by_id(layer_id)
            if layer:
                layer.x = x
                layer.y = y
                self._template.update_layer(layer)

        self.layer_moved.emit(layer_id, x, y)

    def _on_item_resized(self, layer_id: str, width: int, height: int) -> None:
        """图层尺寸改变."""
        # 更新模板数据
        if self._template:
            layer = self._template.get_layer_by_id(layer_id)
            if layer:
                layer.width = width
                layer.height = height
                self._template.update_layer(layer)

        self.layer_resized.emit(layer_id, width, height)

    def _on_text_edit_started(self, layer_id: str) -> None:
        """文字图层开始编辑."""
        item = self._layer_items.get(layer_id)
        if item and isinstance(item, TextLayerItem) and self._text_edit_overlay:
            self._text_edit_overlay.start_editing(item)

    def _on_text_editing_finished(self, layer_id: str, new_content: str) -> None:
        """文字编辑完成."""
        item = self._layer_items.get(layer_id)
        if item and isinstance(item, TextLayerItem):
            item.finish_editing(new_content)

            # 更新模板数据
            if self._template:
                layer = self._template.get_layer_by_id(layer_id)
                if layer:
                    layer.content = new_content
                    self._template.update_layer(layer)

            self.layer_content_changed.emit(layer_id, new_content)

    def _on_text_editing_cancelled(self, layer_id: str) -> None:
        """文字编辑取消."""
        item = self._layer_items.get(layer_id)
        if item and isinstance(item, TextLayerItem):
            item.cancel_editing()
