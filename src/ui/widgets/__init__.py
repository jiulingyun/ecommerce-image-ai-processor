"""UI 组件模块."""

from src.ui.widgets.ai_config_panel import AIConfigPanel
from src.ui.widgets.drop_zone import DropZone
from src.ui.widgets.image_pair_panel import ImagePairPanel
from src.ui.widgets.image_preview import ImagePreview
from src.ui.widgets.output_config_panel import OutputConfigPanel
from src.ui.widgets.process_config_panel import ProcessConfigPanel
from src.ui.widgets.prompt_config_panel import PromptConfigPanel
from src.ui.widgets.queue_progress_panel import QueueProgressPanel
from src.ui.widgets.template_config_panel import TemplateConfigPanel
from src.ui.widgets.task_list_widget import TaskListWidget, TaskListItem
from src.ui.widgets.toast_notification import (
    ToastNotification,
    ToastManager,
    ToastType,
    get_toast_manager,
    show_toast,
    show_success,
    show_warning,
    show_error,
    show_info,
)
from src.ui.widgets.template_editor import (
    TemplateCanvas,
    LayerGraphicsItem,
    TextLayerItem,
    ShapeLayerItem,
    ImageLayerItem,
    create_layer_item,
)

__all__ = [
    "AIConfigPanel",
    "DropZone",
    "ImagePairPanel",
    "ImagePreview",
    "OutputConfigPanel",
    "ProcessConfigPanel",
    "PromptConfigPanel",
    "QueueProgressPanel",
    "TemplateConfigPanel",
    "TaskListWidget",
    "TaskListItem",
    "ToastNotification",
    "ToastManager",
    "ToastType",
    "get_toast_manager",
    "show_toast",
    "show_success",
    "show_warning",
    "show_error",
    "show_info",
    # 模板编辑器
    "TemplateCanvas",
    "LayerGraphicsItem",
    "TextLayerItem",
    "ShapeLayerItem",
    "ImageLayerItem",
    "create_layer_item",
]
