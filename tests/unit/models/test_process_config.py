"""处理配置模型单元测试."""

from __future__ import annotations

import pytest

from src.models.process_config import (
    AIPromptConfig,
    BackgroundConfig,
    BorderConfig,
    BorderStyle,
    BORDER_STYLE_NAMES,
    OutputConfig,
    OutputFormat,
    PositionHint,
    POSITION_HINT_NAMES,
    PresetColor,
    PRESET_COLOR_VALUES,
    ProcessConfig,
    PromptTemplate,
    PROMPT_TEMPLATE_CONTENT,
    PROMPT_TEMPLATE_NAMES,
    QualityPreset,
    QUALITY_PRESET_VALUES,
    ResizeMode,
    TextAlign,
    TextConfig,
    TextPosition,
    TEXT_POSITION_NAMES,
    hex_to_rgb,
    rgb_to_hex,
    validate_rgb_color,
)


# ===================
# 颜色转换函数测试
# ===================
class TestHexToRgb:
    """测试 HEX 转 RGB 函数."""

    def test_hex_to_rgb_with_hash(self) -> None:
        """测试带 # 前缀的 HEX 颜色."""
        assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
        assert hex_to_rgb("#000000") == (0, 0, 0)
        assert hex_to_rgb("#FF5733") == (255, 87, 51)

    def test_hex_to_rgb_without_hash(self) -> None:
        """测试不带 # 前缀的 HEX 颜色."""
        assert hex_to_rgb("FFFFFF") == (255, 255, 255)
        assert hex_to_rgb("000000") == (0, 0, 0)

    def test_hex_to_rgb_lowercase(self) -> None:
        """测试小写 HEX 颜色."""
        assert hex_to_rgb("#ffffff") == (255, 255, 255)
        assert hex_to_rgb("#ff5733") == (255, 87, 51)

    def test_hex_to_rgb_short_format(self) -> None:
        """测试缩写格式 HEX 颜色."""
        assert hex_to_rgb("#FFF") == (255, 255, 255)
        assert hex_to_rgb("#000") == (0, 0, 0)
        assert hex_to_rgb("#F00") == (255, 0, 0)

    def test_hex_to_rgb_invalid(self) -> None:
        """测试无效的 HEX 颜色."""
        with pytest.raises(ValueError):
            hex_to_rgb("#GGGGGG")
        with pytest.raises(ValueError):
            hex_to_rgb("#12345")
        with pytest.raises(ValueError):
            hex_to_rgb("invalid")


class TestRgbToHex:
    """测试 RGB 转 HEX 函数."""

    def test_rgb_to_hex(self) -> None:
        """测试基本转换."""
        assert rgb_to_hex((255, 255, 255)) == "#FFFFFF"
        assert rgb_to_hex((0, 0, 0)) == "#000000"
        assert rgb_to_hex((255, 87, 51)) == "#FF5733"

    def test_rgb_to_hex_single_digit(self) -> None:
        """测试单位数值转换（应补零）."""
        assert rgb_to_hex((0, 0, 0)) == "#000000"
        assert rgb_to_hex((15, 15, 15)) == "#0F0F0F"


class TestValidateRgbColor:
    """测试 RGB 颜色验证函数."""

    def test_validate_valid_color(self) -> None:
        """测试有效颜色."""
        assert validate_rgb_color((255, 255, 255)) == (255, 255, 255)
        assert validate_rgb_color((0, 0, 0)) == (0, 0, 0)
        assert validate_rgb_color((128, 128, 128)) == (128, 128, 128)

    def test_validate_invalid_length(self) -> None:
        """测试无效长度."""
        with pytest.raises(ValueError, match="RGB 三元组"):
            validate_rgb_color((255, 255))  # type: ignore
        with pytest.raises(ValueError, match="RGB 三元组"):
            validate_rgb_color((255, 255, 255, 255))  # type: ignore

    def test_validate_out_of_range(self) -> None:
        """测试超出范围的值."""
        with pytest.raises(ValueError, match="0-255"):
            validate_rgb_color((256, 0, 0))
        with pytest.raises(ValueError, match="0-255"):
            validate_rgb_color((0, -1, 0))


# ===================
# BackgroundConfig 测试
# ===================
class TestBackgroundConfig:
    """测试 BackgroundConfig 模型."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = BackgroundConfig()
        assert config.enabled is True
        assert config.preset == PresetColor.WHITE
        assert config.color == (255, 255, 255)

    def test_from_preset(self) -> None:
        """测试从预设颜色创建."""
        config = BackgroundConfig.from_preset(PresetColor.LIGHT_GRAY)
        assert config.preset == PresetColor.LIGHT_GRAY
        assert config.get_effective_color() == (245, 245, 245)

    def test_from_hex(self) -> None:
        """测试从 HEX 颜色创建."""
        config = BackgroundConfig.from_hex("#FF5733")
        assert config.preset == PresetColor.CUSTOM
        assert config.get_effective_color() == (255, 87, 51)
        assert config.hex_color == "#FF5733"

    def test_from_rgb(self) -> None:
        """测试从 RGB 值创建."""
        config = BackgroundConfig.from_rgb(200, 100, 50)
        assert config.preset == PresetColor.CUSTOM
        assert config.get_effective_color() == (200, 100, 50)

    def test_get_effective_color_preset(self) -> None:
        """测试预设颜色的生效颜色."""
        config = BackgroundConfig(preset=PresetColor.LIGHT_BLUE)
        assert config.get_effective_color() == PRESET_COLOR_VALUES[PresetColor.LIGHT_BLUE]

    def test_get_effective_color_custom(self) -> None:
        """测试自定义颜色的生效颜色."""
        config = BackgroundConfig(
            preset=PresetColor.CUSTOM,
            color=(123, 45, 67),
        )
        assert config.get_effective_color() == (123, 45, 67)

    def test_get_hex_color(self) -> None:
        """测试获取 HEX 格式颜色."""
        config = BackgroundConfig.from_rgb(255, 128, 64)
        assert config.get_hex_color() == "#FF8040"

    def test_is_transparent(self) -> None:
        """测试透明背景检测."""
        config = BackgroundConfig(preset=PresetColor.TRANSPARENT)
        assert config.is_transparent() is True

        config = BackgroundConfig(preset=PresetColor.WHITE)
        assert config.is_transparent() is False

    def test_enabled_disabled(self) -> None:
        """测试启用/禁用状态."""
        config = BackgroundConfig(enabled=False)
        assert config.enabled is False

        config = BackgroundConfig(enabled=True)
        assert config.enabled is True

    def test_get_preset_colors(self) -> None:
        """测试获取预设颜色列表."""
        colors = BackgroundConfig.get_preset_colors()
        
        assert len(colors) > 0
        # 不应包含 TRANSPARENT 和 CUSTOM
        names = [c["name"] for c in colors]
        assert "transparent" not in names
        assert "custom" not in names
        
        # 应包含常见颜色
        assert "white" in names
        assert "black" in names
        assert "light_gray" in names

    def test_preset_colors_structure(self) -> None:
        """测试预设颜色结构."""
        colors = BackgroundConfig.get_preset_colors()
        
        for color in colors:
            assert "name" in color
            assert "preset" in color
            assert "rgb" in color
            assert "hex" in color
            assert isinstance(color["rgb"], tuple)
            assert len(color["rgb"]) == 3
            assert color["hex"].startswith("#")

    def test_color_validation(self) -> None:
        """测试颜色验证."""
        # 有效颜色
        config = BackgroundConfig(color=(100, 100, 100))
        assert config.color == (100, 100, 100)

        # 无效颜色
        with pytest.raises(ValueError):
            BackgroundConfig(color=(256, 0, 0))

    def test_hex_color_sync(self) -> None:
        """测试 HEX 颜色同步到 RGB."""
        config = BackgroundConfig(
            preset=PresetColor.CUSTOM,
            hex_color="#FF5733",
        )
        assert config.color == (255, 87, 51)

    def test_serialization(self) -> None:
        """测试序列化."""
        config = BackgroundConfig.from_hex("#F5F5F5")
        data = config.model_dump()
        
        assert "enabled" in data
        assert "preset" in data
        assert "color" in data
        
        # 反序列化
        restored = BackgroundConfig.model_validate(data)
        assert restored.get_effective_color() == config.get_effective_color()


class TestPresetColor:
    """测试 PresetColor 枚举."""

    def test_preset_color_values(self) -> None:
        """测试预设颜色枚举值."""
        assert PresetColor.WHITE.value == "white"
        assert PresetColor.BLACK.value == "black"
        assert PresetColor.TRANSPARENT.value == "transparent"
        assert PresetColor.CUSTOM.value == "custom"

    def test_all_presets_have_rgb_values(self) -> None:
        """测试所有预设颜色都有对应的 RGB 值."""
        for preset in PresetColor:
            assert preset in PRESET_COLOR_VALUES


# ===================
# BorderStyle 测试
# ===================
class TestBorderStyle:
    """测试 BorderStyle 枚举."""

    def test_border_style_values(self) -> None:
        """测试边框样式枚举值."""
        assert BorderStyle.SOLID.value == "solid"
        assert BorderStyle.DASHED.value == "dashed"
        assert BorderStyle.DOTTED.value == "dotted"
        assert BorderStyle.DOUBLE.value == "double"
        assert BorderStyle.GROOVE.value == "groove"
        assert BorderStyle.RIDGE.value == "ridge"
        assert BorderStyle.INSET.value == "inset"
        assert BorderStyle.OUTSET.value == "outset"

    def test_all_styles_have_names(self) -> None:
        """测试所有边框样式都有中文名称."""
        for style in BorderStyle:
            assert style in BORDER_STYLE_NAMES
            assert isinstance(BORDER_STYLE_NAMES[style], str)


# ===================
# BorderConfig 测试
# ===================
class TestBorderConfig:
    """测试 BorderConfig 模型."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = BorderConfig()
        assert config.enabled is False
        assert config.width == 2  # DEFAULT_BORDER_WIDTH
        assert config.color == (0, 0, 0)  # DEFAULT_BORDER_COLOR
        assert config.style == BorderStyle.SOLID

    def test_enabled_config(self) -> None:
        """测试启用边框."""
        config = BorderConfig(enabled=True, width=5)
        assert config.enabled is True
        assert config.width == 5

    def test_width_validation(self) -> None:
        """测试宽度验证."""
        # 有效宽度
        config = BorderConfig(width=1)
        assert config.width == 1
        config = BorderConfig(width=20)
        assert config.width == 20

        # 无效宽度
        with pytest.raises(ValueError):
            BorderConfig(width=0)
        with pytest.raises(ValueError):
            BorderConfig(width=21)

    def test_from_hex(self) -> None:
        """测试从 HEX 颜色创建."""
        config = BorderConfig.from_hex("#FF0000", width=5, style=BorderStyle.DASHED)
        assert config.enabled is True
        assert config.width == 5
        assert config.get_effective_color() == (255, 0, 0)
        assert config.style == BorderStyle.DASHED

    def test_from_rgb(self) -> None:
        """测试从 RGB 值创建."""
        config = BorderConfig.from_rgb(0, 128, 255, width=10, style=BorderStyle.DOTTED)
        assert config.enabled is True
        assert config.width == 10
        assert config.get_effective_color() == (0, 128, 255)
        assert config.style == BorderStyle.DOTTED

    def test_get_hex_color(self) -> None:
        """测试获取 HEX 格式颜色."""
        config = BorderConfig.from_rgb(255, 128, 64)
        assert config.get_hex_color() == "#FF8040"

    def test_style_selection(self) -> None:
        """测试边框样式选择."""
        for style in BorderStyle:
            config = BorderConfig(style=style)
            assert config.style == style

    def test_get_available_styles(self) -> None:
        """测试获取可用样式列表."""
        styles = BorderConfig.get_available_styles()
        assert len(styles) == len(BorderStyle)

        for style_info in styles:
            assert "value" in style_info
            assert "style" in style_info
            assert "name" in style_info
            assert isinstance(style_info["style"], BorderStyle)

    def test_serialization(self) -> None:
        """测试序列化."""
        config = BorderConfig.from_hex("#00FF00", width=8, style=BorderStyle.DOUBLE)
        data = config.model_dump()

        assert "enabled" in data
        assert "width" in data
        assert "color" in data
        assert "style" in data

        # 反序列化
        restored = BorderConfig.model_validate(data)
        assert restored.width == config.width
        assert restored.get_effective_color() == config.get_effective_color()
        assert restored.style == config.style


# ===================
# TextPosition 测试
# ===================
class TestTextPosition:
    """测试 TextPosition 枚举."""

    def test_text_position_values(self) -> None:
        """测试文字位置枚举值."""
        assert TextPosition.TOP_LEFT.value == "top_left"
        assert TextPosition.TOP_CENTER.value == "top_center"
        assert TextPosition.TOP_RIGHT.value == "top_right"
        assert TextPosition.CENTER_LEFT.value == "center_left"
        assert TextPosition.CENTER.value == "center"
        assert TextPosition.CENTER_RIGHT.value == "center_right"
        assert TextPosition.BOTTOM_LEFT.value == "bottom_left"
        assert TextPosition.BOTTOM_CENTER.value == "bottom_center"
        assert TextPosition.BOTTOM_RIGHT.value == "bottom_right"
        assert TextPosition.CUSTOM.value == "custom"

    def test_all_positions_have_names(self) -> None:
        """测试所有位置都有中文名称."""
        for position in TextPosition:
            assert position in TEXT_POSITION_NAMES
            assert isinstance(TEXT_POSITION_NAMES[position], str)


class TestTextAlign:
    """测试 TextAlign 枚举."""

    def test_text_align_values(self) -> None:
        """测试文字对齐枚举值."""
        assert TextAlign.LEFT.value == "left"
        assert TextAlign.CENTER.value == "center"
        assert TextAlign.RIGHT.value == "right"


# ===================
# TextConfig 测试
# ===================
class TestTextConfig:
    """测试 TextConfig 模型."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = TextConfig()
        assert config.enabled is False
        assert config.content == ""
        assert config.font_size == 14
        assert config.color == (0, 0, 0)
        assert config.opacity == 100
        assert config.preset_position == TextPosition.BOTTOM_RIGHT
        assert config.align == TextAlign.LEFT

    def test_enabled_config(self) -> None:
        """测试启用文字."""
        config = TextConfig(enabled=True, content="测试水印")
        assert config.enabled is True
        assert config.content == "测试水印"

    def test_from_hex(self) -> None:
        """测试从 HEX 颜色创建."""
        config = TextConfig.from_hex(
            "#FF5733",
            content="水印",
            font_size=24,
            preset_position=TextPosition.TOP_LEFT,
        )
        assert config.enabled is True
        assert config.content == "水印"
        assert config.font_size == 24
        assert config.get_effective_color() == (255, 87, 51)
        assert config.preset_position == TextPosition.TOP_LEFT

    def test_get_effective_color(self) -> None:
        """测试获取有效颜色."""
        config = TextConfig(color=(128, 64, 32))
        assert config.get_effective_color() == (128, 64, 32)

        # 测试 HEX 颜色同步
        config = TextConfig(hex_color="#FF0000")
        assert config.get_effective_color() == (255, 0, 0)

    def test_font_size_validation(self) -> None:
        """测试字体大小验证."""
        # 有效大小
        config = TextConfig(font_size=8)
        assert config.font_size == 8
        config = TextConfig(font_size=200)
        assert config.font_size == 200

        # 无效大小
        with pytest.raises(ValueError):
            TextConfig(font_size=7)
        with pytest.raises(ValueError):
            TextConfig(font_size=201)

    def test_opacity_validation(self) -> None:
        """测试不透明度验证."""
        # 有效不透明度
        config = TextConfig(opacity=0)
        assert config.opacity == 0
        config = TextConfig(opacity=100)
        assert config.opacity == 100

        # 无效不透明度
        with pytest.raises(ValueError):
            TextConfig(opacity=-1)
        with pytest.raises(ValueError):
            TextConfig(opacity=101)

    def test_background_config(self) -> None:
        """测试背景配置."""
        config = TextConfig(
            background_enabled=True,
            background_color=(255, 255, 0),
            background_opacity=80,
            background_padding=10,
        )
        assert config.background_enabled is True
        assert config.background_color == (255, 255, 0)
        assert config.background_opacity == 80
        assert config.background_padding == 10

    def test_stroke_config(self) -> None:
        """测试描边配置."""
        config = TextConfig(
            stroke_enabled=True,
            stroke_color=(255, 255, 255),
            stroke_width=3,
        )
        assert config.stroke_enabled is True
        assert config.stroke_color == (255, 255, 255)
        assert config.stroke_width == 3

    def test_create_watermark(self) -> None:
        """测试创建水印配置."""
        config = TextConfig.create_watermark(
            content="版权所有",
            opacity=50,
            color=(128, 128, 128),
        )
        assert config.content == "版权所有"
        assert config.opacity == 50
        assert config.get_effective_color() == (128, 128, 128)
        assert config.preset_position == TextPosition.BOTTOM_RIGHT

    def test_create_label(self) -> None:
        """测试创建标签配置."""
        config = TextConfig.create_label(
            content="热卖",
            position=TextPosition.TOP_LEFT,
        )
        assert config.content == "热卖"
        assert config.background_enabled is True
        assert config.preset_position == TextPosition.TOP_LEFT

    def test_get_effective_position_preset(self) -> None:
        """测试获取预设位置."""
        config = TextConfig(preset_position=TextPosition.TOP_CENTER)
        pos = config.get_effective_position((400, 300), (100, 20))
        # 顶部居中: x = (400-100)//2 = 150
        assert pos[0] == 150
        assert pos[1] == 10  # 默认 margin

    def test_get_effective_position_custom(self) -> None:
        """测试获取自定义位置."""
        config = TextConfig(
            preset_position=TextPosition.CUSTOM,
            custom_position=(50, 100),
        )
        pos = config.get_effective_position((400, 300), (100, 20))
        assert pos == (50, 100)

    def test_get_available_positions(self) -> None:
        """测试获取可用位置列表."""
        positions = TextConfig.get_available_positions()
        assert len(positions) == len(TextPosition) - 1  # 不包括 CUSTOM

        for pos_info in positions:
            assert "value" in pos_info
            assert "position" in pos_info
            assert "name" in pos_info
            assert isinstance(pos_info["position"], TextPosition)

    def test_get_available_aligns(self) -> None:
        """测试获取可用对齐方式列表."""
        aligns = TextConfig.get_available_aligns()
        assert len(aligns) == len(TextAlign)

        for align_info in aligns:
            assert "value" in align_info
            assert "align" in align_info
            assert "name" in align_info
            assert isinstance(align_info["align"], TextAlign)

    def test_serialization(self) -> None:
        """测试序列化."""
        config = TextConfig.from_hex(
            "#FF5733",
            content="水印测试",
            font_size=24,
            preset_position=TextPosition.TOP_LEFT,
        )
        data = config.model_dump()

        assert "enabled" in data
        assert "content" in data
        assert "font_size" in data
        assert "color" in data
        assert "preset_position" in data

        # 反序列化
        restored = TextConfig.model_validate(data)
        assert restored.content == config.content
        assert restored.font_size == config.font_size
        assert restored.get_effective_color() == config.get_effective_color()
        assert restored.preset_position == config.preset_position

    def test_layer_name_for_template(self) -> None:
        """测试模板系统的图层名称字段."""
        config = TextConfig(layer_name="watermark_layer")
        assert config.layer_name == "watermark_layer"

        config = TextConfig()
        assert config.layer_name is None


# ===================
# OutputFormat 测试
# ===================
class TestOutputFormat:
    """测试 OutputFormat 枚举."""

    def test_output_format_values(self) -> None:
        """测试输出格式枚举值."""
        assert OutputFormat.JPEG.value == "jpeg"
        assert OutputFormat.PNG.value == "png"
        assert OutputFormat.WEBP.value == "webp"


class TestQualityPreset:
    """测试 QualityPreset 枚举."""

    def test_quality_preset_values(self) -> None:
        """测试质量预设枚举值."""
        assert QualityPreset.LOW.value == "low"
        assert QualityPreset.MEDIUM.value == "medium"
        assert QualityPreset.HIGH.value == "high"
        assert QualityPreset.BEST.value == "best"
        assert QualityPreset.CUSTOM.value == "custom"

    def test_quality_preset_values_mapping(self) -> None:
        """测试质量预设对应的数值."""
        assert QUALITY_PRESET_VALUES[QualityPreset.LOW] == 60
        assert QUALITY_PRESET_VALUES[QualityPreset.MEDIUM] == 75
        assert QUALITY_PRESET_VALUES[QualityPreset.HIGH] == 85
        assert QUALITY_PRESET_VALUES[QualityPreset.BEST] == 95


class TestResizeMode:
    """测试 ResizeMode 枚举."""

    def test_resize_mode_values(self) -> None:
        """测试尺寸模式枚举值."""
        assert ResizeMode.FIT.value == "fit"
        assert ResizeMode.FILL.value == "fill"
        assert ResizeMode.STRETCH.value == "stretch"
        assert ResizeMode.NONE.value == "none"


# ===================
# OutputConfig 测试
# ===================
class TestOutputConfig:
    """测试 OutputConfig 模型."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = OutputConfig()
        assert config.format == OutputFormat.JPEG
        assert config.size == (800, 800)
        assert config.resize_mode == ResizeMode.FIT
        assert config.quality_preset == QualityPreset.HIGH
        assert config.optimize is True

    def test_get_effective_quality_preset(self) -> None:
        """测试从预设获取质量."""
        config = OutputConfig(quality_preset=QualityPreset.MEDIUM)
        assert config.get_effective_quality() == 75

        config = OutputConfig(quality_preset=QualityPreset.BEST)
        assert config.get_effective_quality() == 95

    def test_get_effective_quality_custom(self) -> None:
        """测试自定义质量."""
        config = OutputConfig(
            quality_preset=QualityPreset.CUSTOM,
            quality=70,
        )
        assert config.get_effective_quality() == 70

    def test_get_file_extension(self) -> None:
        """测试获取文件扩展名."""
        config = OutputConfig(format=OutputFormat.JPEG)
        assert config.get_file_extension() == ".jpg"

        config = OutputConfig(format=OutputFormat.PNG)
        assert config.get_file_extension() == ".png"

        config = OutputConfig(format=OutputFormat.WEBP)
        assert config.get_file_extension() == ".webp"

    def test_supports_quality(self) -> None:
        """测试格式是否支持质量设置."""
        config = OutputConfig(format=OutputFormat.JPEG)
        assert config.supports_quality() is True

        config = OutputConfig(format=OutputFormat.PNG)
        assert config.supports_quality() is False

        config = OutputConfig(format=OutputFormat.WEBP)
        assert config.supports_quality() is True

    def test_supports_transparency(self) -> None:
        """测试格式是否支持透明度."""
        config = OutputConfig(format=OutputFormat.JPEG)
        assert config.supports_transparency() is False

        config = OutputConfig(format=OutputFormat.PNG)
        assert config.supports_transparency() is True

        config = OutputConfig(format=OutputFormat.WEBP)
        assert config.supports_transparency() is True

    def test_size_validation(self) -> None:
        """测试尺寸验证."""
        # 有效尺寸
        config = OutputConfig(size=(800, 800))
        assert config.size == (800, 800)

        # 无效尺寸
        with pytest.raises(ValueError):
            OutputConfig(size=(50, 50))  # 太小
        with pytest.raises(ValueError):
            OutputConfig(size=(5000, 5000))  # 太大

    def test_for_ecommerce(self) -> None:
        """测试电商配置工厂方法."""
        config = OutputConfig.for_ecommerce()
        assert config.format == OutputFormat.JPEG
        assert config.size == (800, 800)
        assert config.resize_mode == ResizeMode.FIT
        assert config.get_effective_quality() == 85
        assert config.background_color == (255, 255, 255)

    def test_for_web(self) -> None:
        """测试网页配置工厂方法."""
        config = OutputConfig.for_web()
        assert config.format == OutputFormat.WEBP
        assert config.size == (1200, 1200)
        assert config.quality_preset == QualityPreset.HIGH

    def test_for_print(self) -> None:
        """测试打印配置工厂方法."""
        config = OutputConfig.for_print()
        assert config.format == OutputFormat.PNG
        assert config.size == (2400, 2400)
        assert config.quality_preset == QualityPreset.BEST
        assert config.optimize is False

    def test_get_available_formats(self) -> None:
        """测试获取可用格式列表."""
        formats = OutputConfig.get_available_formats()
        assert len(formats) == 3

        for fmt_info in formats:
            assert "value" in fmt_info
            assert "format" in fmt_info
            assert "name" in fmt_info
            assert isinstance(fmt_info["format"], OutputFormat)

    def test_get_quality_presets(self) -> None:
        """测试获取质量预设列表."""
        presets = OutputConfig.get_quality_presets()
        # 不包含 CUSTOM
        assert len(presets) == len(QualityPreset) - 1

        for preset_info in presets:
            assert "value" in preset_info
            assert "preset" in preset_info
            assert "name" in preset_info
            assert "quality" in preset_info

    def test_get_resize_modes(self) -> None:
        """测试获取尺寸模式列表."""
        modes = OutputConfig.get_resize_modes()
        assert len(modes) == len(ResizeMode)

        for mode_info in modes:
            assert "value" in mode_info
            assert "mode" in mode_info
            assert "name" in mode_info


# ===================
# AIPromptConfig 测试
# ===================
class TestAIPromptConfig:
    """测试 AIPromptConfig 模型."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = AIPromptConfig()
        assert config.template == PromptTemplate.STANDARD_COMPOSITE
        assert config.custom_prompt == ""
        assert config.position_hint == PositionHint.AUTO
        assert config.use_default is True

    def test_from_template(self) -> None:
        """测试从模板创建."""
        config = AIPromptConfig.from_template(PromptTemplate.LOGO_OVERLAY)
        assert config.template == PromptTemplate.LOGO_OVERLAY
        assert config.use_default is True

        config = AIPromptConfig.from_template(PromptTemplate.BACKGROUND_REPLACE)
        assert config.template == PromptTemplate.BACKGROUND_REPLACE

    def test_custom_prompt(self) -> None:
        """测试自定义提示词创建."""
        config = AIPromptConfig.custom("我的自定义提示词")
        assert config.template == PromptTemplate.CUSTOM
        assert config.custom_prompt == "我的自定义提示词"
        assert config.use_default is False

    def test_custom_with_position(self) -> None:
        """测试带位置的自定义提示词."""
        config = AIPromptConfig.custom("测试提示词", PositionHint.CENTER)
        assert config.position_hint == PositionHint.CENTER
        assert config.custom_prompt == "测试提示词"

    def test_get_effective_prompt_default(self) -> None:
        """测试默认模板的生效提示词."""
        config = AIPromptConfig()
        prompt = config.get_effective_prompt()
        assert prompt == PROMPT_TEMPLATE_CONTENT[PromptTemplate.STANDARD_COMPOSITE]

    def test_get_effective_prompt_template(self) -> None:
        """测试不同模板的生效提示词."""
        for template in PromptTemplate:
            if template == PromptTemplate.CUSTOM:
                continue
            config = AIPromptConfig.from_template(template)
            prompt = config.get_effective_prompt()
            assert prompt == PROMPT_TEMPLATE_CONTENT[template]

    def test_get_effective_prompt_custom(self) -> None:
        """测试自定义提示词的生效提示词."""
        config = AIPromptConfig.custom("我的提示词内容")
        assert config.get_effective_prompt() == "我的提示词内容"

    def test_get_effective_prompt_custom_empty(self) -> None:
        """测试空自定义提示词回退到默认."""
        config = AIPromptConfig(
            template=PromptTemplate.CUSTOM,
            custom_prompt="",
            use_default=False,
        )
        prompt = config.get_effective_prompt()
        # 应回退到默认模板
        assert prompt == PROMPT_TEMPLATE_CONTENT[PromptTemplate.STANDARD_COMPOSITE]

    def test_get_position_description(self) -> None:
        """测试位置描述."""
        config = AIPromptConfig(position_hint=PositionHint.AUTO)
        assert config.get_position_description() == "合适的"

        config = AIPromptConfig(position_hint=PositionHint.CENTER)
        assert config.get_position_description() == "居中"

        config = AIPromptConfig(position_hint=PositionHint.LEFT)
        assert config.get_position_description() == "偏左"

    def test_get_full_prompt_auto(self) -> None:
        """测试自动位置的完整提示词."""
        config = AIPromptConfig(position_hint=PositionHint.AUTO)
        full_prompt = config.get_full_prompt()
        # AUTO 位置不应添加额外位置说明
        assert full_prompt == config.get_effective_prompt()

    def test_get_full_prompt_with_position(self) -> None:
        """测试带位置的完整提示词."""
        config = AIPromptConfig(position_hint=PositionHint.CENTER)
        full_prompt = config.get_full_prompt()
        assert "位置要求" in full_prompt
        assert "居中" in full_prompt

    def test_get_available_templates(self) -> None:
        """测试获取可用模板列表."""
        templates = AIPromptConfig.get_available_templates()
        assert len(templates) == len(PromptTemplate)

        for template_info in templates:
            assert "value" in template_info
            assert "template" in template_info
            assert "name" in template_info
            assert "content" in template_info
            assert isinstance(template_info["template"], PromptTemplate)

    def test_get_available_positions(self) -> None:
        """测试获取可用位置列表."""
        positions = AIPromptConfig.get_available_positions()
        assert len(positions) == len(PositionHint)

        for pos_info in positions:
            assert "value" in pos_info
            assert "position" in pos_info
            assert "name" in pos_info
            assert isinstance(pos_info["position"], PositionHint)

    def test_prompt_template_names(self) -> None:
        """测试模板名称映射."""
        for template in PromptTemplate:
            assert template in PROMPT_TEMPLATE_NAMES
            assert PROMPT_TEMPLATE_NAMES[template]  # 非空

    def test_position_hint_names(self) -> None:
        """测试位置名称映射."""
        for pos in PositionHint:
            assert pos in POSITION_HINT_NAMES
            assert POSITION_HINT_NAMES[pos]  # 非空

    def test_prompt_max_length(self) -> None:
        """测试提示词最大长度限制."""
        # 应该能接受 1000 字符
        long_prompt = "a" * 1000
        config = AIPromptConfig(custom_prompt=long_prompt)
        assert len(config.custom_prompt) == 1000

        # 超过 1000 字符应该失败
        with pytest.raises(ValueError):
            AIPromptConfig(custom_prompt="a" * 1001)


# ===================
# ProcessConfig 集成测试
# ===================
class TestProcessConfigWithPrompt:
    """测试 ProcessConfig 中的 AIPromptConfig 集成."""

    def test_default_prompt_config(self) -> None:
        """测试默认提示词配置."""
        config = ProcessConfig()
        assert config.prompt is not None
        assert isinstance(config.prompt, AIPromptConfig)
        assert config.prompt.template == PromptTemplate.STANDARD_COMPOSITE

    def test_process_config_with_custom_prompt(self) -> None:
        """测试带自定义提示词的处理配置."""
        prompt_config = AIPromptConfig.custom("自定义合成提示词")
        config = ProcessConfig(prompt=prompt_config)
        
        assert config.prompt.custom_prompt == "自定义合成提示词"
        assert config.prompt.template == PromptTemplate.CUSTOM

    def test_process_config_to_json_with_prompt(self) -> None:
        """测试带提示词配置的 JSON 序列化."""
        config = ProcessConfig(
            prompt=AIPromptConfig.from_template(PromptTemplate.LOGO_OVERLAY)
        )
        json_str = config.to_json()
        
        # 从 JSON 恢复
        restored = ProcessConfig.from_json(json_str)
        assert restored.prompt.template == PromptTemplate.LOGO_OVERLAY

    def test_process_config_to_dict_with_prompt(self) -> None:
        """测试带提示词配置的字典序列化."""
        config = ProcessConfig(
            prompt=AIPromptConfig(position_hint=PositionHint.CENTER)
        )
        data = config.to_dict()
        
        assert "prompt" in data
        assert data["prompt"]["position_hint"] == "center"
