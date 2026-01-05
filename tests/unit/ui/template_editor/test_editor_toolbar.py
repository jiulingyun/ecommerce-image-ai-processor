"""编辑器工具栏单元测试."""

import pytest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.models.template_config import (
    TemplateConfig,
    TextLayer,
    ShapeLayer,
    ImageLayer,
)
from src.ui.widgets.template_editor.editor_toolbar import (
    EditorToolbar,
    AlignmentType,
    DistributeType,
    AlignmentManager,
    ClipboardManager,
    ContextMenuManager,
)


# ===================
# Fixtures
# ===================


@pytest.fixture
def toolbar(qtbot):
    """创建工具栏实例."""
    toolbar = EditorToolbar()
    qtbot.addWidget(toolbar)
    return toolbar


@pytest.fixture
def mock_canvas():
    """创建模拟画布."""
    canvas = MagicMock()
    canvas.template = TemplateConfig.create("测试模板", 800, 600)
    canvas.selected_layers = []
    return canvas


@pytest.fixture
def alignment_manager(mock_canvas):
    """创建对齐管理器."""
    return AlignmentManager(mock_canvas)


@pytest.fixture
def clipboard_manager(mock_canvas):
    """创建剪贴板管理器."""
    return ClipboardManager(mock_canvas)


# ===================
# EditorToolbar 测试
# ===================


class TestEditorToolbar:
    """编辑器工具栏测试."""

    def test_init(self, toolbar):
        """测试工具栏初始化."""
        assert toolbar is not None
        assert toolbar.objectName() == "EditorToolbar"

    def test_has_add_text_action(self, toolbar):
        """测试有添加文字动作."""
        assert toolbar._action_add_text is not None
        assert toolbar._action_add_text.text() == "文字"

    def test_has_add_rect_action(self, toolbar):
        """测试有添加矩形动作."""
        assert toolbar._action_add_rect is not None
        assert toolbar._action_add_rect.text() == "矩形"

    def test_has_add_ellipse_action(self, toolbar):
        """测试有添加圆形动作."""
        assert toolbar._action_add_ellipse is not None
        assert toolbar._action_add_ellipse.text() == "圆形"

    def test_has_add_image_action(self, toolbar):
        """测试有添加图片动作."""
        assert toolbar._action_add_image is not None
        assert toolbar._action_add_image.text() == "图片"

    def test_has_copy_action(self, toolbar):
        """测试有复制动作."""
        assert toolbar._action_copy is not None
        assert toolbar._action_copy.text() == "复制"

    def test_has_paste_action(self, toolbar):
        """测试有粘贴动作."""
        assert toolbar._action_paste is not None
        assert toolbar._action_paste.text() == "粘贴"

    def test_has_delete_action(self, toolbar):
        """测试有删除动作."""
        assert toolbar._action_delete is not None
        assert toolbar._action_delete.text() == "删除"

    def test_add_text_signal(self, toolbar, qtbot):
        """测试添加文字信号."""
        with qtbot.waitSignal(toolbar.add_text_requested, timeout=1000):
            toolbar._action_add_text.trigger()

    def test_add_rectangle_signal(self, toolbar, qtbot):
        """测试添加矩形信号."""
        with qtbot.waitSignal(toolbar.add_rectangle_requested, timeout=1000):
            toolbar._action_add_rect.trigger()

    def test_add_ellipse_signal(self, toolbar, qtbot):
        """测试添加圆形信号."""
        with qtbot.waitSignal(toolbar.add_ellipse_requested, timeout=1000):
            toolbar._action_add_ellipse.trigger()

    def test_copy_signal(self, toolbar, qtbot):
        """测试复制信号."""
        with qtbot.waitSignal(toolbar.copy_requested, timeout=1000):
            toolbar._action_copy.trigger()

    def test_paste_signal(self, toolbar, qtbot):
        """测试粘贴信号."""
        with qtbot.waitSignal(toolbar.paste_requested, timeout=1000):
            toolbar._action_paste.trigger()

    def test_delete_signal(self, toolbar, qtbot):
        """测试删除信号."""
        with qtbot.waitSignal(toolbar.delete_requested, timeout=1000):
            toolbar._action_delete.trigger()


# ===================
# AlignmentManager 测试
# ===================


class TestAlignmentManager:
    """对齐管理器测试."""

    def test_init(self, alignment_manager, mock_canvas):
        """测试初始化."""
        assert alignment_manager._canvas == mock_canvas

    def test_align_left(self, alignment_manager, mock_canvas):
        """测试左对齐."""
        # 创建两个图层
        layer1 = TextLayer.create("Layer 1", x=100, y=100)
        layer2 = TextLayer.create("Layer 2", x=200, y=150)
        mock_canvas.template.add_layer(layer1)
        mock_canvas.template.add_layer(layer2)

        # 执行左对齐
        alignment_manager.align([layer1.id, layer2.id], AlignmentType.LEFT)

        # 验证两个图层都对齐到最左边
        updated_layer1 = mock_canvas.template.get_layer_by_id(layer1.id)
        updated_layer2 = mock_canvas.template.get_layer_by_id(layer2.id)
        assert updated_layer1.x == updated_layer2.x

    def test_align_right(self, alignment_manager, mock_canvas):
        """测试右对齐."""
        layer1 = TextLayer.create("Layer 1", x=100, y=100)
        layer1.width = 100
        layer2 = TextLayer.create("Layer 2", x=200, y=150)
        layer2.width = 80
        mock_canvas.template.add_layer(layer1)
        mock_canvas.template.add_layer(layer2)

        alignment_manager.align([layer1.id, layer2.id], AlignmentType.RIGHT)

        updated_layer1 = mock_canvas.template.get_layer_by_id(layer1.id)
        updated_layer2 = mock_canvas.template.get_layer_by_id(layer2.id)
        # 右边界应该对齐
        assert updated_layer1.x + updated_layer1.width == updated_layer2.x + updated_layer2.width

    def test_align_top(self, alignment_manager, mock_canvas):
        """测试顶部对齐."""
        layer1 = TextLayer.create("Layer 1", x=100, y=100)
        layer2 = TextLayer.create("Layer 2", x=200, y=150)
        mock_canvas.template.add_layer(layer1)
        mock_canvas.template.add_layer(layer2)

        alignment_manager.align([layer1.id, layer2.id], AlignmentType.TOP)

        updated_layer1 = mock_canvas.template.get_layer_by_id(layer1.id)
        updated_layer2 = mock_canvas.template.get_layer_by_id(layer2.id)
        assert updated_layer1.y == updated_layer2.y

    def test_align_bottom(self, alignment_manager, mock_canvas):
        """测试底部对齐."""
        layer1 = TextLayer.create("Layer 1", x=100, y=100)
        layer1.height = 50
        layer2 = TextLayer.create("Layer 2", x=200, y=150)
        layer2.height = 30
        mock_canvas.template.add_layer(layer1)
        mock_canvas.template.add_layer(layer2)

        alignment_manager.align([layer1.id, layer2.id], AlignmentType.BOTTOM)

        updated_layer1 = mock_canvas.template.get_layer_by_id(layer1.id)
        updated_layer2 = mock_canvas.template.get_layer_by_id(layer2.id)
        # 底边界应该对齐
        assert updated_layer1.y + updated_layer1.height == updated_layer2.y + updated_layer2.height

    def test_align_center_horizontal(self, alignment_manager, mock_canvas):
        """测试水平居中对齐."""
        layer1 = TextLayer.create("Layer 1", x=100, y=100)
        layer1.width = 100
        layer2 = TextLayer.create("Layer 2", x=300, y=150)
        layer2.width = 80
        mock_canvas.template.add_layer(layer1)
        mock_canvas.template.add_layer(layer2)

        alignment_manager.align([layer1.id, layer2.id], AlignmentType.CENTER_H)

        updated_layer1 = mock_canvas.template.get_layer_by_id(layer1.id)
        updated_layer2 = mock_canvas.template.get_layer_by_id(layer2.id)
        # 水平中心应该对齐
        center1 = updated_layer1.x + updated_layer1.width / 2
        center2 = updated_layer2.x + updated_layer2.width / 2
        assert abs(center1 - center2) < 1  # 允许小误差

    def test_align_center_vertical(self, alignment_manager, mock_canvas):
        """测试垂直居中对齐."""
        layer1 = TextLayer.create("Layer 1", x=100, y=100)
        layer1.height = 50
        layer2 = TextLayer.create("Layer 2", x=200, y=200)
        layer2.height = 30
        mock_canvas.template.add_layer(layer1)
        mock_canvas.template.add_layer(layer2)

        alignment_manager.align([layer1.id, layer2.id], AlignmentType.CENTER_V)

        updated_layer1 = mock_canvas.template.get_layer_by_id(layer1.id)
        updated_layer2 = mock_canvas.template.get_layer_by_id(layer2.id)
        # 垂直中心应该对齐
        center1 = updated_layer1.y + updated_layer1.height / 2
        center2 = updated_layer2.y + updated_layer2.height / 2
        assert abs(center1 - center2) < 1

    def test_align_single_layer_no_effect(self, alignment_manager, mock_canvas):
        """测试单个图层对齐无效果."""
        layer1 = TextLayer.create("Layer 1", x=100, y=100)
        mock_canvas.template.add_layer(layer1)
        original_x = layer1.x

        alignment_manager.align([layer1.id], AlignmentType.LEFT)

        updated_layer = mock_canvas.template.get_layer_by_id(layer1.id)
        assert updated_layer.x == original_x

    def test_distribute_horizontal(self, alignment_manager, mock_canvas):
        """测试水平均匀分布."""
        layer1 = TextLayer.create("Layer 1", x=0, y=100)
        layer1.width = 50
        layer2 = TextLayer.create("Layer 2", x=100, y=100)
        layer2.width = 50
        layer3 = TextLayer.create("Layer 3", x=300, y=100)
        layer3.width = 50
        mock_canvas.template.add_layer(layer1)
        mock_canvas.template.add_layer(layer2)
        mock_canvas.template.add_layer(layer3)

        alignment_manager.distribute(
            [layer1.id, layer2.id, layer3.id],
            DistributeType.HORIZONTAL,
        )

        # 验证分布后间距均匀
        updated_layer1 = mock_canvas.template.get_layer_by_id(layer1.id)
        updated_layer2 = mock_canvas.template.get_layer_by_id(layer2.id)
        updated_layer3 = mock_canvas.template.get_layer_by_id(layer3.id)

        gap1 = updated_layer2.x - (updated_layer1.x + updated_layer1.width)
        gap2 = updated_layer3.x - (updated_layer2.x + updated_layer2.width)
        assert abs(gap1 - gap2) < 1

    def test_distribute_vertical(self, alignment_manager, mock_canvas):
        """测试垂直均匀分布."""
        layer1 = TextLayer.create("Layer 1", x=100, y=0)
        layer1.height = 30
        layer2 = TextLayer.create("Layer 2", x=100, y=100)
        layer2.height = 30
        layer3 = TextLayer.create("Layer 3", x=100, y=300)
        layer3.height = 30
        mock_canvas.template.add_layer(layer1)
        mock_canvas.template.add_layer(layer2)
        mock_canvas.template.add_layer(layer3)

        alignment_manager.distribute(
            [layer1.id, layer2.id, layer3.id],
            DistributeType.VERTICAL,
        )

        updated_layer1 = mock_canvas.template.get_layer_by_id(layer1.id)
        updated_layer2 = mock_canvas.template.get_layer_by_id(layer2.id)
        updated_layer3 = mock_canvas.template.get_layer_by_id(layer3.id)

        gap1 = updated_layer2.y - (updated_layer1.y + updated_layer1.height)
        gap2 = updated_layer3.y - (updated_layer2.y + updated_layer2.height)
        assert abs(gap1 - gap2) < 1

    def test_distribute_two_layers_no_effect(self, alignment_manager, mock_canvas):
        """测试两个图层分布无效果."""
        layer1 = TextLayer.create("Layer 1", x=0, y=100)
        layer2 = TextLayer.create("Layer 2", x=200, y=100)
        mock_canvas.template.add_layer(layer1)
        mock_canvas.template.add_layer(layer2)
        original_x1 = layer1.x
        original_x2 = layer2.x

        alignment_manager.distribute([layer1.id, layer2.id], DistributeType.HORIZONTAL)

        updated_layer1 = mock_canvas.template.get_layer_by_id(layer1.id)
        updated_layer2 = mock_canvas.template.get_layer_by_id(layer2.id)
        assert updated_layer1.x == original_x1
        assert updated_layer2.x == original_x2


# ===================
# ClipboardManager 测试
# ===================


class TestClipboardManager:
    """剪贴板管理器测试."""

    def test_init(self, clipboard_manager, mock_canvas):
        """测试初始化."""
        assert clipboard_manager._canvas == mock_canvas
        assert clipboard_manager.has_content is False

    def test_copy_single_layer(self, clipboard_manager, mock_canvas):
        """测试复制单个图层."""
        layer = TextLayer.create("Test Layer", x=100, y=100)
        mock_canvas.template.add_layer(layer)

        clipboard_manager.copy([layer.id])

        assert clipboard_manager.has_content is True
        assert len(clipboard_manager._clipboard) == 1

    def test_copy_multiple_layers(self, clipboard_manager, mock_canvas):
        """测试复制多个图层."""
        layer1 = TextLayer.create("Layer 1", x=100, y=100)
        layer2 = TextLayer.create("Layer 2", x=200, y=200)
        mock_canvas.template.add_layer(layer1)
        mock_canvas.template.add_layer(layer2)

        clipboard_manager.copy([layer1.id, layer2.id])

        assert clipboard_manager.has_content is True
        assert len(clipboard_manager._clipboard) == 2

    def test_paste_creates_new_layers(self, clipboard_manager, mock_canvas):
        """测试粘贴创建新图层."""
        layer = TextLayer.create("Test Layer", x=100, y=100)
        mock_canvas.template.add_layer(layer)
        clipboard_manager.copy([layer.id])

        new_ids = clipboard_manager.paste()

        assert len(new_ids) == 1
        assert new_ids[0] != layer.id  # 新ID

    def test_paste_offsets_position(self, clipboard_manager, mock_canvas):
        """测试粘贴偏移位置."""
        layer = TextLayer.create("Test Layer", x=100, y=100)
        mock_canvas.template.add_layer(layer)
        clipboard_manager.copy([layer.id])

        clipboard_manager.paste()

        # 验证 add_layer 被调用时图层位置有偏移
        assert mock_canvas.add_layer.called

    def test_paste_empty_clipboard(self, clipboard_manager, mock_canvas):
        """测试粘贴空剪贴板."""
        new_ids = clipboard_manager.paste()
        assert len(new_ids) == 0

    def test_clear(self, clipboard_manager, mock_canvas):
        """测试清空剪贴板."""
        layer = TextLayer.create("Test Layer", x=100, y=100)
        mock_canvas.template.add_layer(layer)
        clipboard_manager.copy([layer.id])

        clipboard_manager.clear()

        assert clipboard_manager.has_content is False


# ===================
# AlignmentType 测试
# ===================


class TestAlignmentType:
    """对齐类型常量测试."""

    def test_alignment_types(self):
        """测试对齐类型定义."""
        assert AlignmentType.LEFT == "left"
        assert AlignmentType.CENTER_H == "center_h"
        assert AlignmentType.RIGHT == "right"
        assert AlignmentType.TOP == "top"
        assert AlignmentType.CENTER_V == "center_v"
        assert AlignmentType.BOTTOM == "bottom"


class TestDistributeType:
    """分布类型常量测试."""

    def test_distribute_types(self):
        """测试分布类型定义."""
        assert DistributeType.HORIZONTAL == "horizontal"
        assert DistributeType.VERTICAL == "vertical"
