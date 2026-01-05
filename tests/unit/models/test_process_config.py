"""处理配置模型单元测试."""

from __future__ import annotations

import pytest

from src.models.process_config import (
    BackgroundConfig,
    PresetColor,
    PRESET_COLOR_VALUES,
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
