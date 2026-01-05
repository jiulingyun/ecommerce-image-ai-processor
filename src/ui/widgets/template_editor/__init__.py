"""模板编辑器组件模块.

提供可视化模板编辑功能，包括画布视图、图层管理、属性编辑等。

Components:
    - TemplateCanvas: 画布视图组件
    - LayerGraphicsItem: 图层图形项基类
    - TextLayerItem: 文字图层图形项
    - ShapeLayerItem: 形状图层图形项
    - ImageLayerItem: 图片图层图形项
    - TextEditOverlay: 文字编辑覆盖层
"""

from src.ui.widgets.template_editor.canvas import TemplateCanvas
from src.ui.widgets.template_editor.layer_items import (
    LayerGraphicsItem,
    TextLayerItem,
    ShapeLayerItem,
    ImageLayerItem,
    create_layer_item,
)
from src.ui.widgets.template_editor.text_edit_overlay import (
    TextEditOverlay,
    TextEditWidget,
)

__all__ = [
    "TemplateCanvas",
    "LayerGraphicsItem",
    "TextLayerItem",
    "ShapeLayerItem",
    "ImageLayerItem",
    "create_layer_item",
    "TextEditOverlay",
    "TextEditWidget",
]
