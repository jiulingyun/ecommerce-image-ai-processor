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


class BorderStyle(str, Enum):
    """边框样式枚举."""

    SOLID = "solid"  # 实线边框
    DASHED = "dashed"  # 虚线边框
    DOTTED = "dotted"  # 点线边框
    DOUBLE = "double"  # 双线边框
    GROOVE = "groove"  # 凹槽边框
    RIDGE = "ridge"  # 垂脊边框
    INSET = "inset"  # 内嵌边框
    OUTSET = "outset"  # 外凸边框


# 边框样式中文名称映射
BORDER_STYLE_NAMES: dict[BorderStyle, str] = {
    BorderStyle.SOLID: "实线",
    BorderStyle.DASHED: "虚线",
    BorderStyle.DOTTED: "点线",
    BorderStyle.DOUBLE: "双线",
    BorderStyle.GROOVE: "凹槽",
    BorderStyle.RIDGE: "垂脊",
    BorderStyle.INSET: "内嵌",
    BorderStyle.OUTSET: "外凸",
}


class BorderConfig(BaseModel):
    """边框配置.

    支持 1-20px 边框宽度调节，提供多种边框样式选择。

    Attributes:
        enabled: 是否启用边框
        width: 边框宽度 (1-20 像素)
        color: 边框颜色 RGB
        style: 边框样式
        hex_color: HEX 颜色字符串（可选）

    Example:
        >>> config = BorderConfig(enabled=True, width=5, style=BorderStyle.SOLID)
        >>> config.get_effective_color()
        (0, 0, 0)
        >>>
        >>> config = BorderConfig.from_hex("#FF0000", width=3)
        >>> config.get_effective_color()
        (255, 0, 0)
    """

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
    style: BorderStyle = Field(
        default=BorderStyle.SOLID,
        description="边框样式",
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
            hex_to_rgb(v)
        return v

    @model_validator(mode="after")
    def sync_hex_and_rgb(self) -> "BorderConfig":
        """同步 HEX 和 RGB 颜色值."""
        if self.hex_color is not None:
            object.__setattr__(self, "color", hex_to_rgb(self.hex_color))
        return self

    def get_effective_color(self) -> RGBColor:
        """获取实际生效的颜色值.

        Returns:
            RGB 颜色元组
        """
        return self.color

    def get_hex_color(self) -> str:
        """获取 HEX 格式的颜色值.

        Returns:
            HEX 颜色字符串
        """
        return rgb_to_hex(self.color)

    @classmethod
    def from_hex(
        cls,
        hex_color: str,
        width: int = DEFAULT_BORDER_WIDTH,
        style: BorderStyle = BorderStyle.SOLID,
        enabled: bool = True,
    ) -> "BorderConfig":
        """从 HEX 颜色创建配置.

        Args:
            hex_color: HEX 颜色字符串
            width: 边框宽度
            style: 边框样式
            enabled: 是否启用

        Returns:
            BorderConfig 实例
        """
        rgb = hex_to_rgb(hex_color)
        return cls(
            enabled=enabled,
            width=width,
            color=rgb,
            style=style,
            hex_color=hex_color,
        )

    @classmethod
    def from_rgb(
        cls,
        r: int,
        g: int,
        b: int,
        width: int = DEFAULT_BORDER_WIDTH,
        style: BorderStyle = BorderStyle.SOLID,
        enabled: bool = True,
    ) -> "BorderConfig":
        """从 RGB 值创建配置.

        Args:
            r: 红色值 (0-255)
            g: 绿色值 (0-255)
            b: 蓝色值 (0-255)
            width: 边框宽度
            style: 边框样式
            enabled: 是否启用

        Returns:
            BorderConfig 实例
        """
        color = (r, g, b)
        validate_rgb_color(color)
        return cls(
            enabled=enabled,
            width=width,
            color=color,
            style=style,
        )

    @classmethod
    def get_available_styles(cls) -> list[dict]:
        """获取所有可用的边框样式（供 UI 使用）.

        Returns:
            边框样式信息列表
        """
        return [
            {
                "value": style.value,
                "style": style,
                "name": BORDER_STYLE_NAMES[style],
            }
            for style in BorderStyle
        ]


class TextPosition(str, Enum):
    """文字位置枚举.

    预设位置，也可以使用自定义坐标。
    """

    TOP_LEFT = "top_left"  # 左上角
    TOP_CENTER = "top_center"  # 上方居中
    TOP_RIGHT = "top_right"  # 右上角
    CENTER_LEFT = "center_left"  # 左侧居中
    CENTER = "center"  # 居中
    CENTER_RIGHT = "center_right"  # 右侧居中
    BOTTOM_LEFT = "bottom_left"  # 左下角
    BOTTOM_CENTER = "bottom_center"  # 下方居中
    BOTTOM_RIGHT = "bottom_right"  # 右下角
    CUSTOM = "custom"  # 自定义位置


class TextAlign(str, Enum):
    """文字对齐方式."""

    LEFT = "left"  # 左对齐
    CENTER = "center"  # 居中
    RIGHT = "right"  # 右对齐


# 文字位置中文名称
TEXT_POSITION_NAMES: dict[TextPosition, str] = {
    TextPosition.TOP_LEFT: "左上角",
    TextPosition.TOP_CENTER: "上方居中",
    TextPosition.TOP_RIGHT: "右上角",
    TextPosition.CENTER_LEFT: "左侧居中",
    TextPosition.CENTER: "居中",
    TextPosition.CENTER_RIGHT: "右侧居中",
    TextPosition.BOTTOM_LEFT: "左下角",
    TextPosition.BOTTOM_CENTER: "下方居中",
    TextPosition.BOTTOM_RIGHT: "右下角",
    TextPosition.CUSTOM: "自定义",
}


class TextConfig(BaseModel):
    """文字配置.

    支持文字内容、字体、大小、颜色、位置、背景、描边等配置。
    设计为模板系统预留扩展能力。

    Attributes:
        enabled: 是否启用文字
        content: 文字内容
        preset_position: 预设位置
        custom_position: 自定义位置坐标 (x, y)
        margin: 边距（用于预设位置）
        align: 文字对齐方式
        font_family: 字体名称
        font_size: 字体大小
        color: 文字颜色
        background_enabled: 是否启用文字背景
        background_color: 文字背景颜色
        background_padding: 文字背景内边距
        stroke_enabled: 是否启用文字描边
        stroke_color: 描边颜色
        stroke_width: 描边宽度
        opacity: 不透明度 (0-100)
        layer_name: 图层名称（用于模板系统识别）

    Example:
        >>> config = TextConfig(
        ...     enabled=True,
        ...     content="水印文字",
        ...     preset_position=TextPosition.BOTTOM_RIGHT,
        ...     font_size=24,
        ... )
        >>> config.get_effective_position((800, 800))
        (750, 760)
    """

    # 基本配置
    enabled: bool = Field(default=False, description="是否启用文字")
    content: str = Field(default="", max_length=500, description="文字内容")

    # 位置配置
    preset_position: TextPosition = Field(
        default=TextPosition.BOTTOM_RIGHT,
        description="预设位置",
    )
    custom_position: Optional[Position] = Field(
        default=None,
        description="自定义位置坐标 (x, y)",
    )
    margin: int = Field(
        default=10,
        ge=0,
        le=100,
        description="边距（用于预设位置）",
    )
    align: TextAlign = Field(
        default=TextAlign.LEFT,
        description="文字对齐方式",
    )

    # 字体配置
    font_family: Optional[str] = Field(
        default=None,
        description="字体名称（None 表示使用默认字体）",
    )
    font_size: int = Field(
        default=DEFAULT_TEXT_FONT_SIZE,
        ge=8,
        le=200,
        description="字体大小",
    )
    bold: bool = Field(default=False, description="粗体")
    italic: bool = Field(default=False, description="斜体")

    # 颜色配置
    color: RGBColor = Field(
        default=DEFAULT_TEXT_COLOR,
        description="文字颜色 RGB",
    )
    hex_color: Optional[str] = Field(
        default=None,
        description="HEX 颜色字符串（可选）",
    )
    opacity: int = Field(
        default=100,
        ge=0,
        le=100,
        description="不透明度 (0-100)",
    )

    # 背景配置
    background_enabled: bool = Field(
        default=False,
        description="是否启用文字背景",
    )
    background_color: RGBColor = Field(
        default=(0, 0, 0),
        description="文字背景颜色 RGB",
    )
    background_opacity: int = Field(
        default=50,
        ge=0,
        le=100,
        description="背景不透明度 (0-100)",
    )
    background_padding: int = Field(
        default=5,
        ge=0,
        le=50,
        description="背景内边距",
    )

    # 描边配置
    stroke_enabled: bool = Field(
        default=False,
        description="是否启用文字描边",
    )
    stroke_color: RGBColor = Field(
        default=(255, 255, 255),
        description="描边颜色 RGB",
    )
    stroke_width: int = Field(
        default=1,
        ge=1,
        le=10,
        description="描边宽度",
    )

    # 模板系统预留字段
    layer_name: Optional[str] = Field(
        default=None,
        description="图层名称（用于模板系统识别）",
    )

    # 兼容旧版本的 position 字段
    position: Optional[Position] = Field(
        default=None,
        description="[已废弃] 使用 preset_position 或 custom_position",
    )

    @field_validator("color", "background_color", "stroke_color")
    @classmethod
    def validate_color(cls, v: RGBColor) -> RGBColor:
        """验证颜色值."""
        return validate_rgb_color(v)

    @field_validator("hex_color")
    @classmethod
    def validate_hex_color(cls, v: Optional[str]) -> Optional[str]:
        """验证 HEX 颜色格式."""
        if v is not None:
            hex_to_rgb(v)
        return v

    @model_validator(mode="after")
    def sync_hex_and_rgb(self) -> "TextConfig":
        """同步 HEX 和 RGB 颜色值."""
        if self.hex_color is not None:
            object.__setattr__(self, "color", hex_to_rgb(self.hex_color))
        # 兼容旧版 position 字段
        if self.position is not None and self.custom_position is None:
            object.__setattr__(self, "custom_position", self.position)
            object.__setattr__(self, "preset_position", TextPosition.CUSTOM)
        return self

    def get_effective_color(self) -> RGBColor:
        """获取实际生效的颜色值."""
        return self.color

    def get_hex_color(self) -> str:
        """获取 HEX 格式的颜色值."""
        return rgb_to_hex(self.color)

    def get_effective_position(
        self,
        image_size: tuple[int, int],
        text_size: tuple[int, int] = (0, 0),
    ) -> Position:
        """获取实际生效的位置坐标.

        根据预设位置和图片尺寸计算实际坐标。

        Args:
            image_size: 图片尺寸 (宽, 高)
            text_size: 文字尺寸 (宽, 高)，用于精确定位

        Returns:
            坐标元组 (x, y)
        """
        if self.preset_position == TextPosition.CUSTOM:
            if self.custom_position:
                return self.custom_position
            return DEFAULT_TEXT_POSITION

        img_w, img_h = image_size
        text_w, text_h = text_size
        margin = self.margin

        # 计算位置
        position_map = {
            TextPosition.TOP_LEFT: (margin, margin),
            TextPosition.TOP_CENTER: ((img_w - text_w) // 2, margin),
            TextPosition.TOP_RIGHT: (img_w - text_w - margin, margin),
            TextPosition.CENTER_LEFT: (margin, (img_h - text_h) // 2),
            TextPosition.CENTER: ((img_w - text_w) // 2, (img_h - text_h) // 2),
            TextPosition.CENTER_RIGHT: (img_w - text_w - margin, (img_h - text_h) // 2),
            TextPosition.BOTTOM_LEFT: (margin, img_h - text_h - margin),
            TextPosition.BOTTOM_CENTER: ((img_w - text_w) // 2, img_h - text_h - margin),
            TextPosition.BOTTOM_RIGHT: (img_w - text_w - margin, img_h - text_h - margin),
        }

        return position_map.get(self.preset_position, DEFAULT_TEXT_POSITION)

    @classmethod
    def from_hex(
        cls,
        hex_color: str,
        content: str = "",
        font_size: int = DEFAULT_TEXT_FONT_SIZE,
        preset_position: TextPosition = TextPosition.BOTTOM_RIGHT,
        enabled: bool = True,
    ) -> "TextConfig":
        """从 HEX 颜色创建配置."""
        rgb = hex_to_rgb(hex_color)
        return cls(
            enabled=enabled,
            content=content,
            color=rgb,
            hex_color=hex_color,
            font_size=font_size,
            preset_position=preset_position,
        )

    @classmethod
    def create_watermark(
        cls,
        content: str,
        position: TextPosition = TextPosition.BOTTOM_RIGHT,
        font_size: int = 16,
        color: RGBColor = (128, 128, 128),
        opacity: int = 50,
    ) -> "TextConfig":
        """创建水印配置."""
        return cls(
            enabled=True,
            content=content,
            preset_position=position,
            font_size=font_size,
            color=color,
            opacity=opacity,
            layer_name="watermark",
        )

    @classmethod
    def create_label(
        cls,
        content: str,
        position: TextPosition = TextPosition.TOP_LEFT,
        font_size: int = 14,
        color: RGBColor = (255, 255, 255),
        background_color: RGBColor = (255, 0, 0),
    ) -> "TextConfig":
        """创建标签配置（带背景的文字）."""
        return cls(
            enabled=True,
            content=content,
            preset_position=position,
            font_size=font_size,
            color=color,
            background_enabled=True,
            background_color=background_color,
            background_opacity=100,
            background_padding=5,
            layer_name="label",
        )

    @classmethod
    def get_available_positions(cls) -> list[dict]:
        """获取所有可用的位置（供 UI 使用）."""
        return [
            {
                "value": pos.value,
                "position": pos,
                "name": TEXT_POSITION_NAMES[pos],
            }
            for pos in TextPosition
            if pos != TextPosition.CUSTOM
        ]

    @classmethod
    def get_available_aligns(cls) -> list[dict]:
        """获取所有可用的对齐方式（供 UI 使用）."""
        align_names = {
            TextAlign.LEFT: "左对齐",
            TextAlign.CENTER: "居中",
            TextAlign.RIGHT: "右对齐",
        }
        return [
            {
                "value": align.value,
                "align": align,
                "name": align_names[align],
            }
            for align in TextAlign
        ]


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
