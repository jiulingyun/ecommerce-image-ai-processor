"""处理配置模型."""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import ClassVar, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from src.utils.constants import (
    DEFAULT_BACKGROUND_COLOR,
    DEFAULT_BORDER_COLOR,
    DEFAULT_BORDER_WIDTH,
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_OUTPUT_SIZE,
    DEFAULT_TEXT_COLOR,
    DEFAULT_TEXT_FONT_SIZE,
    DEFAULT_TEXT_POSITION,
    MAX_BORDER_WIDTH,
    MIN_BORDER_WIDTH,
)

# 类型别名
RGBColor = tuple[int, int, int]
Position = tuple[int, int]
Size = tuple[int, int]


class PresetColor(str, Enum):
    """预设背景颜色枚举."""

    WHITE = "white"  # 白色 #FFFFFF
    BLACK = "black"  # 黑色 #000000
    LIGHT_GRAY = "light_gray"  # 浅灰 #F5F5F5
    GRAY = "gray"  # 灰色 #E0E0E0
    CREAM = "cream"  # 米色 #FFF8E7
    LIGHT_BLUE = "light_blue"  # 浅蓝 #E3F2FD
    LIGHT_PINK = "light_pink"  # 浅粉 #FCE4EC
    LIGHT_GREEN = "light_green"  # 浅绿 #E8F5E9
    TRANSPARENT = "transparent"  # 透明（仅用于标识，实际不应用背景）
    CUSTOM = "custom"  # 自定义颜色


# 预设颜色对应的 RGB 值
PRESET_COLOR_VALUES: dict[PresetColor, RGBColor] = {
    PresetColor.WHITE: (255, 255, 255),
    PresetColor.BLACK: (0, 0, 0),
    PresetColor.LIGHT_GRAY: (245, 245, 245),
    PresetColor.GRAY: (224, 224, 224),
    PresetColor.CREAM: (255, 248, 231),
    PresetColor.LIGHT_BLUE: (227, 242, 253),
    PresetColor.LIGHT_PINK: (252, 228, 236),
    PresetColor.LIGHT_GREEN: (232, 245, 233),
    PresetColor.TRANSPARENT: (0, 0, 0),  # 占位，不实际使用
    PresetColor.CUSTOM: (255, 255, 255),  # 占位，使用 color 字段
}


def hex_to_rgb(hex_color: str) -> RGBColor:
    """将 HEX 颜色转换为 RGB.

    Args:
        hex_color: HEX 颜色字符串，如 "#FFFFFF" 或 "FFFFFF"

    Returns:
        RGB 颜色元组

    Raises:
        ValueError: 无效的 HEX 颜色格式
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6 or not re.match(r"^[0-9A-Fa-f]{6}$", hex_color):
        raise ValueError(f"无效的 HEX 颜色格式: {hex_color}")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore


def rgb_to_hex(rgb: RGBColor) -> str:
    """将 RGB 颜色转换为 HEX.

    Args:
        rgb: RGB 颜色元组

    Returns:
        HEX 颜色字符串，如 "#FFFFFF"
    """
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def validate_rgb_color(color: RGBColor) -> RGBColor:
    """验证 RGB 颜色值.

    Args:
        color: RGB 颜色元组

    Returns:
        验证后的 RGB 颜色元组

    Raises:
        ValueError: 颜色值无效
    """
    if len(color) != 3:
        raise ValueError("颜色必须是 RGB 三元组")
    for c in color:
        if not isinstance(c, int) or not 0 <= c <= 255:
            raise ValueError(f"颜色值必须是 0-255 范围内的整数: {c}")
    return color


class BackgroundConfig(BaseModel):
    """背景配置.

    支持纯色背景添加，提供颜色选择器和 RGB 数值输入。

    Attributes:
        enabled: 是否启用背景添加
        preset: 预设颜色选择
        color: 自定义 RGB 颜色值
        hex_color: HEX 颜色字符串（可选，用于 UI 输入）

    Example:
        >>> config = BackgroundConfig(preset=PresetColor.WHITE)
        >>> config.get_effective_color()
        (255, 255, 255)
        >>>
        >>> config = BackgroundConfig(preset=PresetColor.CUSTOM, color=(200, 100, 50))
        >>> config.get_effective_color()
        (200, 100, 50)
        >>>
        >>> config = BackgroundConfig.from_hex("#FF5733")
        >>> config.get_effective_color()
        (255, 87, 51)
    """

    # 预设颜色列表（供 UI 使用）
    PRESET_COLORS: ClassVar[dict[PresetColor, RGBColor]] = PRESET_COLOR_VALUES

    enabled: bool = Field(
        default=True,
        description="是否启用背景添加",
    )
    preset: PresetColor = Field(
        default=PresetColor.WHITE,
        description="预设颜色选择",
    )
    color: RGBColor = Field(
        default=DEFAULT_BACKGROUND_COLOR,
        description="自定义背景颜色 RGB",
    )
    hex_color: Optional[str] = Field(
        default=None,
        description="HEX 颜色字符串（可选）",
    )

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: RGBColor) -> RGBColor:
        """验证颜色值."""
        return validate_rgb_color(v)

    @field_validator("hex_color")
    @classmethod
    def validate_hex_color(cls, v: Optional[str]) -> Optional[str]:
        """验证 HEX 颜色格式."""
        if v is not None:
            # 尝试转换以验证格式
            hex_to_rgb(v)
        return v

    @model_validator(mode="after")
    def sync_hex_and_rgb(self) -> "BackgroundConfig":
        """同步 HEX 和 RGB 颜色值."""
        if self.hex_color is not None and self.preset == PresetColor.CUSTOM:
            # 如果提供了 hex_color 且是自定义模式，同步到 color
            object.__setattr__(self, "color", hex_to_rgb(self.hex_color))
        return self

    def get_effective_color(self) -> RGBColor:
        """获取实际生效的颜色值.

        根据 preset 设置返回对应的颜色值。

        Returns:
            RGB 颜色元组
        """
        if self.preset == PresetColor.CUSTOM:
            return self.color
        return PRESET_COLOR_VALUES.get(self.preset, DEFAULT_BACKGROUND_COLOR)

    def get_hex_color(self) -> str:
        """获取 HEX 格式的颜色值.

        Returns:
            HEX 颜色字符串
        """
        return rgb_to_hex(self.get_effective_color())

    def is_transparent(self) -> bool:
        """检查是否为透明背景.

        Returns:
            是否透明
        """
        return self.preset == PresetColor.TRANSPARENT

    @classmethod
    def from_hex(cls, hex_color: str, enabled: bool = True) -> "BackgroundConfig":
        """从 HEX 颜色创建配置.

        Args:
            hex_color: HEX 颜色字符串
            enabled: 是否启用

        Returns:
            BackgroundConfig 实例
        """
        rgb = hex_to_rgb(hex_color)
        return cls(
            enabled=enabled,
            preset=PresetColor.CUSTOM,
            color=rgb,
            hex_color=hex_color,
        )

    @classmethod
    def from_rgb(cls, r: int, g: int, b: int, enabled: bool = True) -> "BackgroundConfig":
        """从 RGB 值创建配置.

        Args:
            r: 红色值 (0-255)
            g: 绿色值 (0-255)
            b: 蓝色值 (0-255)
            enabled: 是否启用

        Returns:
            BackgroundConfig 实例
        """
        color = (r, g, b)
        validate_rgb_color(color)
        return cls(
            enabled=enabled,
            preset=PresetColor.CUSTOM,
            color=color,
        )

    @classmethod
    def from_preset(cls, preset: PresetColor, enabled: bool = True) -> "BackgroundConfig":
        """从预设颜色创建配置.

        Args:
            preset: 预设颜色
            enabled: 是否启用

        Returns:
            BackgroundConfig 实例
        """
        return cls(enabled=enabled, preset=preset)

    @classmethod
    def get_preset_colors(cls) -> list[dict]:
        """获取所有预设颜色列表（供 UI 使用）.

        Returns:
            预设颜色信息列表
        """
        return [
            {
                "name": preset.value,
                "preset": preset,
                "rgb": PRESET_COLOR_VALUES[preset],
                "hex": rgb_to_hex(PRESET_COLOR_VALUES[preset]),
            }
            for preset in PresetColor
            if preset not in (PresetColor.TRANSPARENT, PresetColor.CUSTOM)
        ]


class BorderConfig(BaseModel):
    """边框配置."""

    enabled: bool = Field(default=False, description="是否启用边框")
    width: int = Field(
        default=DEFAULT_BORDER_WIDTH,
        ge=MIN_BORDER_WIDTH,
        le=MAX_BORDER_WIDTH,
        description="边框宽度 (像素)",
    )
    color: RGBColor = Field(
        default=DEFAULT_BORDER_COLOR,
        description="边框颜色 RGB",
    )

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: RGBColor) -> RGBColor:
        """验证颜色值."""
        if len(v) != 3:
            raise ValueError("颜色必须是 RGB 三元组")
        for c in v:
            if not 0 <= c <= 255:
                raise ValueError(f"颜色值必须在 0-255 范围内: {c}")
        return v


class TextConfig(BaseModel):
    """文字配置."""

    enabled: bool = Field(default=False, description="是否启用文字")
    content: str = Field(default="", max_length=200, description="文字内容")
    position: Position = Field(
        default=DEFAULT_TEXT_POSITION,
        description="文字位置 (x, y)",
    )
    font_size: int = Field(
        default=DEFAULT_TEXT_FONT_SIZE,
        ge=8,
        le=72,
        description="字体大小",
    )
    color: RGBColor = Field(
        default=DEFAULT_TEXT_COLOR,
        description="文字颜色 RGB",
    )

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: RGBColor) -> RGBColor:
        """验证颜色值."""
        if len(v) != 3:
            raise ValueError("颜色必须是 RGB 三元组")
        for c in v:
            if not 0 <= c <= 255:
                raise ValueError(f"颜色值必须在 0-255 范围内: {c}")
        return v


class OutputConfig(BaseModel):
    """输出配置."""

    size: Size = Field(
        default=DEFAULT_OUTPUT_SIZE,
        description="输出尺寸 (宽, 高)",
    )
    quality: int = Field(
        default=DEFAULT_OUTPUT_QUALITY,
        ge=1,
        le=100,
        description="输出质量 (1-100)",
    )

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: Size) -> Size:
        """验证尺寸值."""
        if len(v) != 2:
            raise ValueError("尺寸必须是 (宽, 高) 二元组")
        for s in v:
            if not 100 <= s <= 4096:
                raise ValueError(f"尺寸必须在 100-4096 范围内: {s}")
        return v


class ProcessConfig(BaseModel):
    """图片处理配置.

    包含背景、边框、文字和输出的完整配置。

    Example:
        >>> config = ProcessConfig()
        >>> config.border.enabled = True
        >>> config.border.width = 5
        >>> json_str = config.to_json()
    """

    background: BackgroundConfig = Field(default_factory=BackgroundConfig)
    border: BorderConfig = Field(default_factory=BorderConfig)
    text: TextConfig = Field(default_factory=TextConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    def to_json(self) -> str:
        """转换为 JSON 字符串."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "ProcessConfig":
        """从 JSON 字符串创建配置.

        Args:
            json_str: JSON 字符串

        Returns:
            ProcessConfig 实例
        """
        data = json.loads(json_str)
        return cls.model_validate(data)

    def to_dict(self) -> dict:
        """转换为字典."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "ProcessConfig":
        """从字典创建配置."""
        return cls.model_validate(data)
