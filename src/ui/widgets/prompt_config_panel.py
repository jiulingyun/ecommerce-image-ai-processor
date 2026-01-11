"""AI 合成配置面板组件."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.models.process_config import (
    AIPromptConfig,
    PositionHint,
    POSITION_HINT_NAMES,
    PromptTemplate,
    PROMPT_TEMPLATE_CONTENT,
    PROMPT_TEMPLATE_NAMES,
)
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class PromptConfigPanel(QFrame):
    """AI 合成配置面板.

    提供 AI 合成配置界面，包括提示词模板选择、自定义编辑和位置提示。

    Signals:
        config_changed: 配置变更信号，参数为 AIPromptConfig 对象
    """

    config_changed = pyqtSignal(object)  # AIPromptConfig

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化提示词配置面板."""
        super().__init__(parent)
        self._current_config = AIPromptConfig()
        self._is_updating = False  # 防止循环更新

        self._setup_ui()
        self._connect_signals()
        self._load_config(self._current_config)

    def _setup_ui(self) -> None:
        """设置 UI."""
        self.setProperty("configPanel", True)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 标题
        title_label = QLabel("AI 合成配置")
        title_label.setProperty("heading", True)
        layout.addWidget(title_label)

        # 1. 模板选择区域
        template_group = QGroupBox("提示词模板")
        template_layout = QVBoxLayout(template_group)
        template_layout.setSpacing(8)

        # 模板下拉框
        self._template_combo = QComboBox()
        for template in PromptTemplate:
            self._template_combo.addItem(
                PROMPT_TEMPLATE_NAMES[template],
                template.value,
            )
        template_layout.addWidget(self._template_combo)

        # 模板说明
        self._template_desc = QLabel()
        self._template_desc.setProperty("hint", True)
        self._template_desc.setWordWrap(True)
        # self._template_desc.setStyleSheet(
        #     "color: #666; font-size: 11px; padding: 4px 0;"
        # )
        template_layout.addWidget(self._template_desc)

        layout.addWidget(template_group)

        # 2. 提示词编辑区域
        prompt_group = QGroupBox("提示词内容")
        prompt_layout = QVBoxLayout(prompt_group)
        prompt_layout.setSpacing(8)

        # 提示词文本编辑框
        self._prompt_edit = QPlainTextEdit()
        self._prompt_edit.setPlaceholderText("输入自定义提示词，或选择模板自动填充...")
        self._prompt_edit.setFixedHeight(120)
        self._prompt_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        # self._prompt_edit.setStyleSheet(...) # Removed hardcoded style
        prompt_layout.addWidget(self._prompt_edit)

        # 字数统计
        self._char_count_label = QLabel("0/1000")
        self._char_count_label.setProperty("hint", True)
        # self._char_count_label.setStyleSheet("color: #999; font-size: 11px;")
        self._char_count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        prompt_layout.addWidget(self._char_count_label)

        layout.addWidget(prompt_group)

        # 3. 位置提示选择
        position_group = QGroupBox("位置提示")
        position_layout = QHBoxLayout(position_group)
        position_layout.setSpacing(8)

        position_label = QLabel("合成位置:")
        position_layout.addWidget(position_label)

        self._position_combo = QComboBox()
        for pos in PositionHint:
            self._position_combo.addItem(
                POSITION_HINT_NAMES[pos],
                pos.value,
            )
        self._position_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        position_layout.addWidget(self._position_combo)

        layout.addWidget(position_group)

        # 4. 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._reset_btn = QPushButton("重置为默认")
        self._reset_btn.setProperty("secondary", True)
        self._reset_btn.setToolTip("恢复为当前模板的默认提示词")
        btn_layout.addWidget(self._reset_btn)

        btn_layout.addStretch()

        self._apply_btn = QPushButton("应用配置")
        self._apply_btn.setProperty("success", True)
        btn_layout.addWidget(self._apply_btn)

        layout.addLayout(btn_layout)

    def _connect_signals(self) -> None:
        """连接信号."""
        self._template_combo.currentIndexChanged.connect(self._on_template_changed)
        self._prompt_edit.textChanged.connect(self._on_prompt_changed)
        self._position_combo.currentIndexChanged.connect(self._on_position_changed)
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        self._apply_btn.clicked.connect(self._on_apply_clicked)

    def _load_config(self, config: AIPromptConfig) -> None:
        """加载配置到 UI.

        Args:
            config: AI 提示词配置
        """
        self._is_updating = True
        try:
            # 设置模板
            template_index = self._template_combo.findData(config.template.value)
            if template_index >= 0:
                self._template_combo.setCurrentIndex(template_index)

            # 设置提示词内容
            if config.template == PromptTemplate.CUSTOM or not config.use_default:
                self._prompt_edit.setPlainText(config.custom_prompt)
            else:
                self._prompt_edit.setPlainText(
                    PROMPT_TEMPLATE_CONTENT.get(config.template, "")
                )

            # 设置位置
            pos_index = self._position_combo.findData(config.position_hint.value)
            if pos_index >= 0:
                self._position_combo.setCurrentIndex(pos_index)

            # 更新模板说明
            self._update_template_description()
            self._update_char_count()

        finally:
            self._is_updating = False

    def _update_template_description(self) -> None:
        """更新模板说明文字."""
        template_value = self._template_combo.currentData()
        if template_value:
            template = PromptTemplate(template_value)
            if template == PromptTemplate.CUSTOM:
                self._template_desc.setText("自定义模式：完全自行编写提示词内容")
            else:
                self._template_desc.setText(f"适用场景：{PROMPT_TEMPLATE_NAMES[template]}")

    def _update_char_count(self) -> None:
        """更新字数统计."""
        text = self._prompt_edit.toPlainText()
        count = len(text)
        
        self._char_count_label.setText(f"{count}/1000")
        self._char_count_label.setProperty("error", count > 1000)
        self._char_count_label.style().unpolish(self._char_count_label)
        self._char_count_label.style().polish(self._char_count_label)

    def _on_template_changed(self, index: int) -> None:
        """模板选择变更."""
        if self._is_updating:
            return

        template_value = self._template_combo.currentData()
        if template_value:
            template = PromptTemplate(template_value)
            # 如果不是自定义模板，自动填充模板内容
            if template != PromptTemplate.CUSTOM:
                self._is_updating = True
                self._prompt_edit.setPlainText(
                    PROMPT_TEMPLATE_CONTENT.get(template, "")
                )
                self._is_updating = False

            self._update_template_description()
            self._update_current_config()

    def _on_prompt_changed(self) -> None:
        """提示词内容变更."""
        self._update_char_count()

        if self._is_updating:
            return

        # 如果用户修改了内容，检查是否与模板内容一致
        current_text = self._prompt_edit.toPlainText()
        template_value = self._template_combo.currentData()

        if template_value:
            template = PromptTemplate(template_value)
            template_content = PROMPT_TEMPLATE_CONTENT.get(template, "")

            # 如果内容与模板不同，标记为已自定义
            if current_text != template_content and template != PromptTemplate.CUSTOM:
                # 用户已修改，切换到自定义模式
                pass  # 保持当前模板选择，但实际使用自定义内容

        self._update_current_config()

    def _on_position_changed(self, index: int) -> None:
        """位置选择变更."""
        if self._is_updating:
            return
        self._update_current_config()

    def _update_current_config(self) -> None:
        """更新当前配置对象."""
        template_value = self._template_combo.currentData()
        template = PromptTemplate(template_value) if template_value else PromptTemplate.STANDARD_COMPOSITE

        pos_value = self._position_combo.currentData()
        position = PositionHint(pos_value) if pos_value else PositionHint.AUTO

        current_text = self._prompt_edit.toPlainText()
        template_content = PROMPT_TEMPLATE_CONTENT.get(template, "")

        # 判断是否使用默认
        use_default = (
            template != PromptTemplate.CUSTOM
            and current_text == template_content
        )

        # 截断超长文本以避免验证错误（UI 层面已显示警告）
        custom_prompt = current_text if not use_default else ""
        if len(custom_prompt) > 1000:
            custom_prompt = custom_prompt[:1000]

        self._current_config = AIPromptConfig(
            template=template,
            custom_prompt=custom_prompt,
            position_hint=position,
            use_default=use_default,
        )

    def _on_reset_clicked(self) -> None:
        """重置按钮点击."""
        template_value = self._template_combo.currentData()
        if template_value:
            template = PromptTemplate(template_value)
            self._is_updating = True
            self._prompt_edit.setPlainText(
                PROMPT_TEMPLATE_CONTENT.get(template, "")
            )
            self._is_updating = False
            self._update_current_config()
            logger.info(f"提示词已重置为模板: {PROMPT_TEMPLATE_NAMES[template]}")

    def _on_apply_clicked(self) -> None:
        """应用按钮点击."""
        self._update_current_config()
        self.config_changed.emit(self._current_config)
        logger.info("提示词配置已应用")

    # ========================
    # 公共接口
    # ========================

    def get_config(self) -> AIPromptConfig:
        """获取当前配置.

        Returns:
            当前的 AI 提示词配置
        """
        self._update_current_config()
        return self._current_config

    def set_config(self, config: AIPromptConfig) -> None:
        """设置配置.

        Args:
            config: AI 提示词配置
        """
        self._current_config = config
        self._load_config(config)

    def get_effective_prompt(self) -> str:
        """获取实际生效的提示词.

        Returns:
            提示词字符串
        """
        self._update_current_config()
        return self._current_config.get_full_prompt()
