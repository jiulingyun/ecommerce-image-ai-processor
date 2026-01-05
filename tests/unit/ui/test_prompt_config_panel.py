"""PromptConfigPanel 组件单元测试."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PyQt6.QtWidgets import QApplication

from src.models.process_config import (
    AIPromptConfig,
    PositionHint,
    PromptTemplate,
    PROMPT_TEMPLATE_CONTENT,
)
from src.ui.widgets.prompt_config_panel import PromptConfigPanel


@pytest.fixture(scope="module")
def app():
    """创建 Qt 应用实例."""
    application = QApplication.instance()
    if not application:
        application = QApplication([])
    yield application


@pytest.fixture
def panel(app):
    """创建 PromptConfigPanel 实例."""
    widget = PromptConfigPanel()
    yield widget
    widget.close()


class TestPromptConfigPanelInit:
    """测试 PromptConfigPanel 初始化."""

    def test_init_default(self, app):
        """测试默认初始化."""
        widget = PromptConfigPanel()
        
        # 验证默认值
        assert widget._template_combo.currentData() == PromptTemplate.STANDARD_COMPOSITE.value
        assert widget._position_combo.currentData() == PositionHint.AUTO.value
        
        widget.close()

    def test_init_components(self, panel):
        """测试组件初始化."""
        # 验证 UI 组件存在
        assert panel._template_combo is not None
        assert panel._prompt_edit is not None
        assert panel._position_combo is not None
        assert panel._reset_btn is not None
        assert panel._apply_btn is not None

    def test_init_template_options(self, panel):
        """测试模板选项."""
        # 验证所有模板都在下拉框中
        assert panel._template_combo.count() == len(PromptTemplate)


class TestPromptConfigPanelTemplateSelection:
    """测试模板选择功能."""

    def test_change_template(self, panel):
        """测试切换模板."""
        # 切换到 LOGO_OVERLAY
        logo_index = panel._template_combo.findData(PromptTemplate.LOGO_OVERLAY.value)
        panel._template_combo.setCurrentIndex(logo_index)
        
        # 验证提示词文本更新
        prompt_text = panel._prompt_edit.toPlainText()
        assert prompt_text == PROMPT_TEMPLATE_CONTENT[PromptTemplate.LOGO_OVERLAY]

    def test_change_to_custom_template(self, panel):
        """测试切换到自定义模板."""
        # 切换到自定义
        custom_index = panel._template_combo.findData(PromptTemplate.CUSTOM.value)
        panel._template_combo.setCurrentIndex(custom_index)
        
        # 验证模板说明更新
        assert "自定义" in panel._template_desc.text()

    def test_template_preserves_user_edits(self, panel):
        """测试用户编辑后切换模板."""
        # 先输入自定义内容
        panel._prompt_edit.setPlainText("用户自定义的内容")
        
        # 切换模板会覆盖
        logo_index = panel._template_combo.findData(PromptTemplate.LOGO_OVERLAY.value)
        panel._template_combo.setCurrentIndex(logo_index)
        
        # 应该被模板内容覆盖
        assert panel._prompt_edit.toPlainText() == PROMPT_TEMPLATE_CONTENT[PromptTemplate.LOGO_OVERLAY]


class TestPromptConfigPanelPromptEdit:
    """测试提示词编辑功能."""

    def test_edit_prompt(self, panel):
        """测试编辑提示词."""
        test_prompt = "这是测试提示词"
        panel._prompt_edit.setPlainText(test_prompt)
        
        assert panel._prompt_edit.toPlainText() == test_prompt

    def test_char_count_update(self, panel):
        """测试字数统计更新."""
        panel._prompt_edit.setPlainText("12345")
        
        # 验证字数统计
        assert "5/1000" in panel._char_count_label.text()

    def test_char_count_warning(self, panel):
        """测试字数超限警告."""
        # 输入超过1000字符
        long_text = "a" * 1001
        panel._prompt_edit.setPlainText(long_text)
        
        # 应该显示红色警告
        style = panel._char_count_label.styleSheet()
        assert "#ff4d4f" in style


class TestPromptConfigPanelPositionSelection:
    """测试位置选择功能."""

    def test_position_options(self, panel):
        """测试位置选项."""
        # 验证所有位置都在下拉框中
        assert panel._position_combo.count() == len(PositionHint)

    def test_change_position(self, panel):
        """测试切换位置."""
        # 切换到居中
        center_index = panel._position_combo.findData(PositionHint.CENTER.value)
        panel._position_combo.setCurrentIndex(center_index)
        
        assert panel._position_combo.currentData() == PositionHint.CENTER.value


class TestPromptConfigPanelConfigManagement:
    """测试配置管理功能."""

    def test_get_config_default(self, panel):
        """测试获取默认配置."""
        config = panel.get_config()
        
        assert isinstance(config, AIPromptConfig)
        assert config.template == PromptTemplate.STANDARD_COMPOSITE
        assert config.position_hint == PositionHint.AUTO

    def test_get_config_after_edit(self, panel):
        """测试编辑后获取配置."""
        # 设置为自定义模板
        custom_index = panel._template_combo.findData(PromptTemplate.CUSTOM.value)
        panel._template_combo.setCurrentIndex(custom_index)
        
        # 输入自定义内容
        panel._prompt_edit.setPlainText("我的自定义提示词")
        
        # 设置位置
        center_index = panel._position_combo.findData(PositionHint.CENTER.value)
        panel._position_combo.setCurrentIndex(center_index)
        
        config = panel.get_config()
        
        assert config.template == PromptTemplate.CUSTOM
        assert config.position_hint == PositionHint.CENTER

    def test_set_config(self, panel):
        """测试设置配置."""
        config = AIPromptConfig(
            template=PromptTemplate.BACKGROUND_REPLACE,
            position_hint=PositionHint.LEFT,
        )
        
        panel.set_config(config)
        
        assert panel._template_combo.currentData() == PromptTemplate.BACKGROUND_REPLACE.value
        assert panel._position_combo.currentData() == PositionHint.LEFT.value

    def test_set_custom_config(self, panel):
        """测试设置自定义配置."""
        config = AIPromptConfig.custom("自定义测试内容", PositionHint.RIGHT)
        
        panel.set_config(config)
        
        assert panel._template_combo.currentData() == PromptTemplate.CUSTOM.value
        assert panel._prompt_edit.toPlainText() == "自定义测试内容"
        assert panel._position_combo.currentData() == PositionHint.RIGHT.value

    def test_get_effective_prompt(self, panel):
        """测试获取生效提示词."""
        prompt = panel.get_effective_prompt()
        
        # 默认应该是标准合成模板
        assert prompt == PROMPT_TEMPLATE_CONTENT[PromptTemplate.STANDARD_COMPOSITE]


class TestPromptConfigPanelButtons:
    """测试按钮功能."""

    def test_reset_button(self, panel):
        """测试重置按钮."""
        # 先修改提示词
        panel._prompt_edit.setPlainText("被修改的内容")
        
        # 点击重置
        panel._on_reset_clicked()
        
        # 应该恢复为模板内容
        assert panel._prompt_edit.toPlainText() == PROMPT_TEMPLATE_CONTENT[PromptTemplate.STANDARD_COMPOSITE]

    def test_apply_button_emits_signal(self, panel):
        """测试应用按钮发送信号."""
        signal_handler = MagicMock()
        panel.config_changed.connect(signal_handler)
        
        panel._on_apply_clicked()
        
        signal_handler.assert_called_once()
        # 验证参数是 AIPromptConfig
        args = signal_handler.call_args[0]
        assert isinstance(args[0], AIPromptConfig)


class TestPromptConfigPanelEdgeCases:
    """测试边界情况."""

    def test_empty_prompt_fallback(self, panel):
        """测试空提示词回退."""
        # 切换到自定义模板
        custom_index = panel._template_combo.findData(PromptTemplate.CUSTOM.value)
        panel._template_combo.setCurrentIndex(custom_index)
        
        # 清空内容
        panel._prompt_edit.setPlainText("")
        
        # 获取配置
        config = panel.get_config()
        effective = config.get_effective_prompt()
        
        # 应该回退到默认模板
        assert effective == PROMPT_TEMPLATE_CONTENT[PromptTemplate.STANDARD_COMPOSITE]

    def test_rapid_template_changes(self, panel):
        """测试快速切换模板."""
        for template in PromptTemplate:
            index = panel._template_combo.findData(template.value)
            panel._template_combo.setCurrentIndex(index)
        
        # 最终应该停留在最后一个
        assert panel._template_combo.currentData() == PromptTemplate.CUSTOM.value
