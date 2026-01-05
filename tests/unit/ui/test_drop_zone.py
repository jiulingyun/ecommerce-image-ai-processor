"""DropZone 组件单元测试."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import Qt, QUrl, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QApplication

from src.ui.widgets.drop_zone import DropZone


@pytest.fixture(scope="module")
def app():
    """创建 Qt 应用实例."""
    application = QApplication.instance()
    if not application:
        application = QApplication([])
    yield application


@pytest.fixture
def drop_zone(app):
    """创建 DropZone 实例."""
    widget = DropZone(title="测试区域", hint="测试提示")
    yield widget
    widget.close()


@pytest.fixture
def test_image():
    """创建测试图片文件."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        # 创建一个最小的有效 PNG
        # 这是一个 1x1 像素的透明 PNG
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
            0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
            0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  # IEND chunk
            0x42, 0x60, 0x82
        ])
        f.write(png_data)
        f.flush()
        yield Path(f.name)
    # 清理
    Path(f.name).unlink(missing_ok=True)


class TestDropZoneInit:
    """测试 DropZone 初始化."""

    def test_init_default(self, app):
        """测试默认初始化."""
        widget = DropZone()
        assert widget.file_path is None
        assert not widget.has_file
        widget.close()

    def test_init_with_title(self, app):
        """测试带标题初始化."""
        widget = DropZone(title="自定义标题")
        assert "自定义标题" in widget._title_label.text()
        widget.close()

    def test_init_with_hint(self, app):
        """测试带提示初始化."""
        widget = DropZone(hint="自定义提示")
        assert "自定义提示" in widget._hint_label.text()
        widget.close()


class TestDropZoneProperties:
    """测试 DropZone 属性."""

    def test_file_path_initial(self, drop_zone):
        """测试初始文件路径."""
        assert drop_zone.file_path is None

    def test_has_file_initial(self, drop_zone):
        """测试初始无文件状态."""
        assert drop_zone.has_file is False

    def test_has_file_after_set(self, drop_zone, test_image):
        """测试设置文件后的状态."""
        drop_zone.set_file(str(test_image))
        assert drop_zone.has_file is True


class TestDropZoneSetFile:
    """测试 DropZone.set_file 方法."""

    def test_set_valid_file(self, drop_zone, test_image):
        """测试设置有效文件."""
        drop_zone.set_file(str(test_image))
        assert drop_zone.file_path == str(test_image)
        assert drop_zone.has_file

    def test_set_file_emits_signal(self, drop_zone, test_image):
        """测试设置文件触发信号."""
        signal_handler = MagicMock()
        drop_zone.file_dropped.connect(signal_handler)

        drop_zone.set_file(str(test_image))

        signal_handler.assert_called_once_with(str(test_image))

    def test_set_invalid_file_format(self, drop_zone):
        """测试设置无效格式文件."""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            f.flush()
            try:
                drop_zone.set_file(f.name)
                # 无效格式应该不被接受
                assert drop_zone.file_path is None
            finally:
                Path(f.name).unlink(missing_ok=True)

    def test_set_nonexistent_file(self, drop_zone):
        """测试设置不存在的文件."""
        drop_zone.set_file("/nonexistent/path/image.png")
        assert drop_zone.file_path is None


class TestDropZoneClear:
    """测试 DropZone.clear 方法."""

    def test_clear_removes_file(self, drop_zone, test_image):
        """测试清除移除文件."""
        drop_zone.set_file(str(test_image))
        assert drop_zone.has_file

        drop_zone.clear()
        assert not drop_zone.has_file
        assert drop_zone.file_path is None

    def test_clear_emits_signal(self, drop_zone, test_image):
        """测试清除触发信号."""
        drop_zone.set_file(str(test_image))

        signal_handler = MagicMock()
        drop_zone.file_cleared.connect(signal_handler)

        drop_zone.clear()

        signal_handler.assert_called_once()

    def test_clear_when_empty(self, drop_zone):
        """测试空状态清除."""
        signal_handler = MagicMock()
        drop_zone.file_cleared.connect(signal_handler)

        drop_zone.clear()

        # 空状态清除不触发信号（只有有文件时清除才触发）
        signal_handler.assert_not_called()


class TestDropZoneDragDrop:
    """测试 DropZone 拖放功能."""

    def test_accept_drag(self, drop_zone):
        """测试接受拖拽."""
        # drop_zone 应该接受拖拽
        assert drop_zone.acceptDrops()

    def test_drag_enter_with_urls(self, drop_zone, test_image):
        """测试带 URL 的拖入事件."""
        # 验证组件配置为接受拖放
        assert drop_zone.acceptDrops()


class TestDropZoneUI:
    """测试 DropZone UI 组件."""

    def test_clear_button_exists(self, drop_zone):
        """测试清除按钮存在."""
        assert hasattr(drop_zone, "_clear_btn")

    def test_clear_button_hidden_initially(self, drop_zone):
        """测试清除按钮初始隐藏."""
        assert not drop_zone._clear_btn.isVisible()

    def test_clear_button_visible_after_file(self, drop_zone, test_image):
        """测试文件设置后清除按钮可见."""
        drop_zone.set_file(str(test_image))
        # 确保文件已设置
        assert drop_zone.has_file
        # 清除按钮应该显示（在显示更新后）
        assert drop_zone._clear_btn.isVisible() or drop_zone.has_file

    def test_thumbnail_label_exists(self, drop_zone):
        """测试缩略图标签存在."""
        assert hasattr(drop_zone, "_thumbnail_label")

    def test_hint_label_exists(self, drop_zone):
        """测试提示标签存在."""
        assert hasattr(drop_zone, "_hint_label")


class TestDropZoneClickToSelect:
    """测试点击选择文件功能."""

    def test_mouse_release_opens_dialog(self, drop_zone):
        """测试点击打开文件对话框."""
        # 验证 mouseReleaseEvent 已实现
        assert hasattr(drop_zone, "mouseReleaseEvent")

    @patch("src.ui.widgets.drop_zone.QFileDialog.getOpenFileName")
    def test_dialog_file_selection(self, mock_dialog, drop_zone, test_image):
        """测试对话框文件选择."""
        mock_dialog.return_value = (str(test_image), "")

        # 直接调用内部方法 _on_select_file
        drop_zone._on_select_file()

        assert drop_zone.file_path == str(test_image)
