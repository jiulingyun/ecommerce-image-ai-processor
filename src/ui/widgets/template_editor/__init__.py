"""模板编辑器组件模块.

提供可视化模板编辑功能，包括画布视图、图层管理、属性编辑等。

Components:
    - TemplateCanvas: 画布视图组件
    - LayerGraphicsItem: 图层图形项基类
    - TextLayerItem: 文字图层图形项
    - ShapeLayerItem: 形状图层图形项
    - ImageLayerItem: 图片图层图形项
    - TextEditOverlay: 文字编辑覆盖层
    - LayerPanel: 图层管理面板
    - EditorToolbar: 编辑器工具栏
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
from src.ui.widgets.template_editor.layer_panel import (
    LayerPanel,
    LayerListWidget,
    LayerItemWidget,
)
from src.ui.widgets.template_editor.property_panel import (
    PropertyPanel,
    ColorButton,
    LabeledSpinBox,
    LabeledSlider,
    TransformEditor,
    TextPropertyEditor,
    ShapePropertyEditor,
    ImagePropertyEditor,
    CanvasPropertyEditor,
)
from src.ui.widgets.template_editor.template_list import (
    TemplateListWidget,
    TemplateListItem,
)
from src.ui.widgets.template_editor.editor_toolbar import (
    EditorToolbar,
    AlignmentType,
    DistributeType,
    AlignmentManager,
    ClipboardManager,
    ContextMenuManager,
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
    "LayerPanel",
    "LayerListWidget",
    "LayerItemWidget",
    "PropertyPanel",
    "ColorButton",
    "LabeledSpinBox",
    "LabeledSlider",
    "TransformEditor",
    "TextPropertyEditor",
    "ShapePropertyEditor",
    "ImagePropertyEditor",
    "CanvasPropertyEditor",
    "TemplateListWidget",
    "TemplateListItem",
    "EditorToolbar",
    "AlignmentType",
    "DistributeType",
    "AlignmentManager",
    "ClipboardManager",
    "ContextMenuManager",
]
