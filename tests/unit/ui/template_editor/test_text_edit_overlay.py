"""文字编辑覆盖层单元测试."""

import pytest

from src.models.template_config import TextLayer, TextAlign
from src.ui.widgets.template_editor.layer_items import TextLayerItem
from src.ui.widgets.template_editor.text_edit_overlay import (
    TextEditWidget,
    TextEditOverlay,
)


# ===================
# TextEditWidget 测试
# ===================


class TestTextEditWidget:
    """测试文字编辑组件."""

    def test_should_create_widget(self, app):
        """应能创建组件."""
        widget = TextEditWidget()
        assert widget is not None

    def test_should_setup_from_layer(self, app):
        """应能从图层设置样式."""
        widget = TextEditWidget()
        layer = TextLayer(
            content="Hello",
            font_size=24,
            bold=True,
        )
        widget.setup_from_layer(layer)
        assert widget.toPlainText() == "Hello"
        assert widget.font().pointSize() == 24
        assert widget.font().bold() is True

    def test_should_have_signals(self, app):
        """应有信号."""
        widget = TextEditWidget()
        assert hasattr(widget, "editing_finished")
        assert hasattr(widget, "editing_cancelled")


# ===================
# TextEditOverlay 测试
# ===================


class TestTextEditOverlay:
    """测试文字编辑覆盖层."""

    def test_should_create_overlay(self, app):
        """应能创建覆盖层."""
        overlay = TextEditOverlay()
        assert overlay is not None
        assert overlay.isVisible() is False

    def test_should_not_be_editing_initially(self, app):
        """初始应不在编辑状态."""
        overlay = TextEditOverlay()
        assert overlay.is_editing is False
        assert overlay.layer_id is None

    def test_should_start_editing(self, app):
        """应能开始编辑."""
        overlay = TextEditOverlay()
        layer = TextLayer(content="Test")
        item = TextLayerItem(layer)

        overlay.start_editing(item)

        assert overlay.is_editing is True
        assert overlay.layer_id == layer.id
        assert overlay.isVisible() is True

    def test_should_finish_editing(self, app):
        """应能完成编辑."""
        overlay = TextEditOverlay()
        layer = TextLayer(content="Test")
        item = TextLayerItem(layer)

        overlay.start_editing(item)
        content = overlay.finish_editing()

        assert overlay.is_editing is False
        assert overlay.isVisible() is False
        assert content == "Test"

    def test_should_cancel_editing(self, app):
        """应能取消编辑."""
        overlay = TextEditOverlay()
        layer = TextLayer(content="Test")
        item = TextLayerItem(layer)

        overlay.start_editing(item)
        overlay.cancel_editing()

        assert overlay.is_editing is False
        assert overlay.isVisible() is False

    def test_should_have_signals(self, app):
        """应有信号."""
        overlay = TextEditOverlay()
        assert hasattr(overlay, "editing_finished")
        assert hasattr(overlay, "editing_cancelled")


# ===================
# 信号测试
# ===================


class TestTextEditOverlaySignals:
    """测试信号发射."""

    def test_should_emit_finished_signal(self, app):
        """完成编辑时应发出信号."""
        overlay = TextEditOverlay()
        layer = TextLayer(content="Test")
        item = TextLayerItem(layer)
        signal_received = []

        def on_finished(layer_id, content):
            signal_received.append((layer_id, content))

        overlay.editing_finished.connect(on_finished)
        overlay.start_editing(item)
        # 模拟编辑器内部触发完成
        overlay._on_editing_finished("New Content")

        assert len(signal_received) == 1
        assert signal_received[0][0] == layer.id
        assert signal_received[0][1] == "New Content"

    def test_should_emit_cancelled_signal(self, app):
        """取消编辑时应发出信号."""
        overlay = TextEditOverlay()
        layer = TextLayer(content="Test")
        item = TextLayerItem(layer)
        signal_received = []

        def on_cancelled(layer_id):
            signal_received.append(layer_id)

        overlay.editing_cancelled.connect(on_cancelled)
        overlay.start_editing(item)
        # 模拟编辑器内部触发取消
        overlay._on_editing_cancelled()

        assert len(signal_received) == 1
        assert signal_received[0] == layer.id
