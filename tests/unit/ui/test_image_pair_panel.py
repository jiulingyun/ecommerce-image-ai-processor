"""ImagePairPanel 组件单元测试."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PyQt6.QtWidgets import QApplication

from src.ui.widgets.image_pair_panel import ImagePairPanel
from src.utils.constants import MAX_QUEUE_SIZE


@pytest.fixture(scope="module")
def app():
    """创建 Qt 应用实例."""
    application = QApplication.instance()
    if not application:
        application = QApplication([])
    yield application


@pytest.fixture
def panel(app):
    """创建 ImagePairPanel 实例."""
    widget = ImagePairPanel()
    yield widget
    widget.close()


@pytest.fixture
def test_image():
    """创建测试图片文件."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
            0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
            0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
            0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
            0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
            0x42, 0x60, 0x82
        ])
        f.write(png_data)
        f.flush()
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def test_image_2():
    """创建第二个测试图片文件."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        # 最小的有效 JPEG
        jpg_data = bytes([
            0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
            0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
            0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
            0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
            0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
            0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
            0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D,
            0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
            0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
            0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
            0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34,
            0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
            0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4,
            0x00, 0x1F, 0x00, 0x00, 0x01, 0x05, 0x01, 0x01,
            0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04,
            0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0xFF,
            0xC4, 0x00, 0xB5, 0x10, 0x00, 0x02, 0x01, 0x03,
            0x03, 0x02, 0x04, 0x03, 0x05, 0x05, 0x04, 0x04,
            0x00, 0x00, 0x01, 0x7D, 0x01, 0x02, 0x03, 0x00,
            0x04, 0x11, 0x05, 0x12, 0x21, 0x31, 0x41, 0x06,
            0x13, 0x51, 0x61, 0x07, 0x22, 0x71, 0x14, 0x32,
            0x81, 0x91, 0xA1, 0x08, 0x23, 0x42, 0xB1, 0xC1,
            0x15, 0x52, 0xD1, 0xF0, 0x24, 0x33, 0x62, 0x72,
            0x82, 0x09, 0x0A, 0x16, 0x17, 0x18, 0x19, 0x1A,
            0x25, 0x26, 0x27, 0x28, 0x29, 0x2A, 0x34, 0x35,
            0x36, 0x37, 0x38, 0x39, 0x3A, 0x43, 0x44, 0x45,
            0x46, 0x47, 0x48, 0x49, 0x4A, 0x53, 0x54, 0x55,
            0x56, 0x57, 0x58, 0x59, 0x5A, 0x63, 0x64, 0x65,
            0x66, 0x67, 0x68, 0x69, 0x6A, 0x73, 0x74, 0x75,
            0x76, 0x77, 0x78, 0x79, 0x7A, 0x83, 0x84, 0x85,
            0x86, 0x87, 0x88, 0x89, 0x8A, 0x92, 0x93, 0x94,
            0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0xA2, 0xA3,
            0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xB2,
            0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA,
            0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9,
            0xCA, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8,
            0xD9, 0xDA, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6,
            0xE7, 0xE8, 0xE9, 0xEA, 0xF1, 0xF2, 0xF3, 0xF4,
            0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF, 0xDA,
            0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00,
            0xFB, 0xD5, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xD9
        ])
        f.write(jpg_data)
        f.flush()
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


class TestImagePairPanelInit:
    """测试 ImagePairPanel 初始化."""

    def test_init_default(self, app):
        """测试默认初始化."""
        widget = ImagePairPanel()
        assert widget.background_path is None
        assert widget.product_path is None
        assert not widget.is_pair_complete
        widget.close()

    def test_has_drop_zones(self, panel):
        """测试拖入区存在."""
        assert hasattr(panel, "_bg_drop_zone")
        assert hasattr(panel, "_prod_drop_zone")

    def test_has_add_button(self, panel):
        """测试添加按钮存在."""
        assert hasattr(panel, "_add_task_btn")

    def test_add_button_disabled_initially(self, panel):
        """测试添加按钮初始禁用."""
        assert not panel._add_task_btn.isEnabled()


class TestImagePairPanelProperties:
    """测试 ImagePairPanel 属性."""

    def test_background_path_none_initially(self, panel):
        """测试初始背景图路径为空."""
        assert panel.background_path is None

    def test_product_path_none_initially(self, panel):
        """测试初始商品图路径为空."""
        assert panel.product_path is None

    def test_is_pair_complete_false_initially(self, panel):
        """测试初始配对不完整."""
        assert not panel.is_pair_complete

    def test_can_add_task_false_initially(self, panel):
        """测试初始不能添加任务."""
        assert not panel.can_add_task


class TestImagePairPanelPairComplete:
    """测试配对完整性."""

    def test_pair_incomplete_with_only_background(self, panel, test_image):
        """测试只有背景图时配对不完整."""
        panel._bg_drop_zone.set_file(str(test_image))
        assert not panel.is_pair_complete

    def test_pair_incomplete_with_only_product(self, panel, test_image):
        """测试只有商品图时配对不完整."""
        panel._prod_drop_zone.set_file(str(test_image))
        assert not panel.is_pair_complete

    def test_pair_complete_with_both(self, panel, test_image, test_image_2):
        """测试两张图都有时配对完整."""
        panel._bg_drop_zone.set_file(str(test_image))
        panel._prod_drop_zone.set_file(str(test_image_2))
        assert panel.is_pair_complete

    def test_add_button_enabled_when_complete(self, panel, test_image, test_image_2):
        """测试配对完整时添加按钮启用."""
        panel._bg_drop_zone.set_file(str(test_image))
        panel._prod_drop_zone.set_file(str(test_image_2))
        assert panel._add_task_btn.isEnabled()


class TestImagePairPanelTaskAdd:
    """测试任务添加."""

    def test_task_added_signal(self, panel, test_image, test_image_2):
        """测试添加任务信号."""
        signal_handler = MagicMock()
        panel.task_added.connect(signal_handler)

        panel._bg_drop_zone.set_file(str(test_image))
        panel._prod_drop_zone.set_file(str(test_image_2))
        panel._on_add_task()

        signal_handler.assert_called_once_with(str(test_image), str(test_image_2))

    def test_pair_cleared_after_add(self, panel, test_image, test_image_2):
        """测试添加后配对被清除."""
        panel._bg_drop_zone.set_file(str(test_image))
        panel._prod_drop_zone.set_file(str(test_image_2))
        panel._on_add_task()

        assert not panel.is_pair_complete
        assert panel.background_path is None
        assert panel.product_path is None


class TestImagePairPanelClear:
    """测试清空配对."""

    def test_clear_pair(self, panel, test_image, test_image_2):
        """测试清空配对."""
        panel._bg_drop_zone.set_file(str(test_image))
        panel._prod_drop_zone.set_file(str(test_image_2))
        assert panel.is_pair_complete

        panel.clear_pair()

        assert not panel.is_pair_complete
        assert panel.background_path is None
        assert panel.product_path is None


class TestImagePairPanelQueueCount:
    """测试队列计数."""

    def test_set_queue_count(self, panel):
        """测试设置队列计数."""
        panel.set_queue_count(5)
        assert panel._current_queue_count == 5

    def test_queue_status_label_updated(self, panel):
        """测试队列状态标签更新."""
        panel.set_queue_count(3)
        assert "3" in panel._queue_status_label.text()

    def test_can_add_task_false_when_queue_full(self, panel, test_image, test_image_2):
        """测试队列满时不能添加任务."""
        panel.set_queue_count(MAX_QUEUE_SIZE)
        panel._bg_drop_zone.set_file(str(test_image))
        panel._prod_drop_zone.set_file(str(test_image_2))
        assert not panel.can_add_task


class TestImagePairPanelSignals:
    """测试信号."""

    def test_pair_changed_signal_on_background_drop(self, panel, test_image):
        """测试背景图拖入时触发配对变化信号."""
        signal_handler = MagicMock()
        panel.pair_changed.connect(signal_handler)

        panel._bg_drop_zone.set_file(str(test_image))

        signal_handler.assert_called()

    def test_pair_changed_signal_on_product_drop(self, panel, test_image):
        """测试商品图拖入时触发配对变化信号."""
        signal_handler = MagicMock()
        panel.pair_changed.connect(signal_handler)

        panel._prod_drop_zone.set_file(str(test_image))

        signal_handler.assert_called()

    def test_pair_changed_signal_on_clear(self, panel, test_image):
        """测试清除时触发配对变化信号."""
        panel._bg_drop_zone.set_file(str(test_image))

        signal_handler = MagicMock()
        panel.pair_changed.connect(signal_handler)

        panel._bg_drop_zone.clear()

        signal_handler.assert_called()
