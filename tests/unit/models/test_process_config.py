"""处理配置模型单元测试."""

from __future__ import annotations

import pytest

from src.models.process_config import (
    BackgroundConfig,
    BorderConfig,
    BorderStyle,
    BORDER_STYLE_NAMES,
    PresetColor,
    PRESET_COLOR_VALUES,
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
