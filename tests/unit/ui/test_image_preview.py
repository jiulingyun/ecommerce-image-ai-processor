"""ImagePreview 组件单元测试."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PyQt6.QtWidgets import QApplication

from src.models.image_task import ImageTask
from src.ui.widgets.image_preview import ImagePreview


@pytest.fixture(scope="module")
def app():
    """创建 Qt 应用实例."""
    application = QApplication.instance()
    if not application:
        application = QApplication([])
    yield application


@pytest.fixture
def preview(app):
    """创建 ImagePreview 实例."""
    widget = ImagePreview()
    yield widget
    widget.close()


@pytest.fixture
def test_image_bg():
    """创建测试背景图片文件."""
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
def test_image_prod():
    """创建测试商品图片文件."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
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
            0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
            0x00, 0xFB, 0xD5, 0x00, 0x00, 0x00, 0x00, 0xFF,
            0xD9
        ])
        f.write(jpg_data)
        f.flush()
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def sample_task(test_image_bg, test_image_prod):
    """创建示例任务."""
    return ImageTask(
        background_path=str(test_image_bg),
        product_path=str(test_image_prod),
    )


class TestImagePreviewInit:
    """测试 ImagePreview 初始化."""

    def test_init_default(self, app):
        """测试默认初始化."""
        widget = ImagePreview()
        assert widget.current_task is None
        assert widget.is_showing_background is True
        widget.close()

    def test_has_image_label(self, preview):
        """测试图片标签存在."""
        assert hasattr(preview, "_image_label")

    def test_has_switch_buttons(self, preview):
        """测试切换按钮存在."""
        assert hasattr(preview, "_bg_radio")
        assert hasattr(preview, "_prod_radio")

    def test_switch_buttons_hidden_initially(self, preview):
        """测试切换按钮初始隐藏."""
        assert not preview._switch_container.isVisible()


class TestImagePreviewProperties:
    """测试 ImagePreview 属性."""

    def test_current_task_none_initially(self, preview):
        """测试初始任务为空."""
        assert preview.current_task is None

    def test_is_showing_background_true_initially(self, preview):
        """测试初始显示背景图."""
        assert preview.is_showing_background is True


class TestImagePreviewSetTask:
    """测试设置任务."""

    def test_set_task(self, preview, sample_task):
        """测试设置任务."""
        preview.set_task(sample_task)
        assert preview.current_task is not None
        assert preview.current_task.id == sample_task.id

    def test_set_task_shows_switch_buttons(self, preview, sample_task):
        """测试设置任务后显示切换按钮."""
        preview.set_task(sample_task)
        # 检查 switch_container 的显示状态
        # isVisibleTo 检查组件相对于父组件是否可见，
        # 或者检查 isHidden() 为 False
        assert not preview._switch_container.isHidden()

    def test_set_task_shows_background_by_default(self, preview, sample_task):
        """测试设置任务默认显示背景图."""
        preview.set_task(sample_task)
        assert preview.is_showing_background
        assert preview._bg_radio.isChecked()

    def test_set_task_none_clears(self, preview, sample_task):
        """测试设置 None 清空预览."""
        preview.set_task(sample_task)
        preview.set_task(None)
        assert preview.current_task is None


class TestImagePreviewClear:
    """测试清空预览."""

    def test_clear(self, preview, sample_task):
        """测试清空."""
        preview.set_task(sample_task)
        assert preview.current_task is not None

        preview.clear()
        assert preview.current_task is None

    def test_clear_hides_switch_buttons(self, preview, sample_task):
        """测试清空后隐藏切换按钮."""
        preview.set_task(sample_task)
        preview.clear()
        assert not preview._switch_container.isVisible()


class TestImagePreviewSwitch:
    """测试图片切换."""

    def test_switch_to_product(self, preview, sample_task):
        """测试切换到商品图."""
        preview.set_task(sample_task)
        preview.switch_to_product()
        assert not preview.is_showing_background

    def test_switch_to_background(self, preview, sample_task):
        """测试切换到背景图."""
        preview.set_task(sample_task)
        preview.switch_to_product()
        preview.switch_to_background()
        assert preview.is_showing_background

    def test_switch_updates_radio_button(self, preview, sample_task):
        """测试切换更新单选按钮."""
        preview.set_task(sample_task)
        preview.switch_to_product()
        assert preview._prod_radio.isChecked()

    def test_image_changed_signal(self, preview, sample_task):
        """测试图片切换信号."""
        preview.set_task(sample_task)

        signal_handler = MagicMock()
        preview.image_changed.connect(signal_handler)

        preview.switch_to_product()

        signal_handler.assert_called()

    def test_switch_without_task_does_nothing(self, preview):
        """测试无任务时切换无效."""
        preview.switch_to_product()
        assert preview.is_showing_background  # 保持默认值


class TestImagePreviewRadioButtons:
    """测试单选按钮切换."""

    def test_bg_radio_checked_initially(self, preview, sample_task):
        """测试背景图单选按钮初始选中."""
        preview.set_task(sample_task)
        assert preview._bg_radio.isChecked()

    def test_clicking_prod_radio_switches(self, preview, sample_task):
        """测试点击商品图单选按钮切换."""
        preview.set_task(sample_task)
        preview._prod_radio.setChecked(True)
        assert not preview.is_showing_background

    def test_clicking_bg_radio_switches_back(self, preview, sample_task):
        """测试点击背景图单选按钮切换回来."""
        preview.set_task(sample_task)
        preview._prod_radio.setChecked(True)
        preview._bg_radio.setChecked(True)
        assert preview.is_showing_background


class TestImagePreviewInfoDisplay:
    """测试信息显示."""

    def test_has_info_label(self, preview):
        """测试信息标签存在."""
        assert hasattr(preview, "_info_label")

    def test_has_empty_label(self, preview):
        """测试空状态标签存在."""
        assert hasattr(preview, "_empty_label")
