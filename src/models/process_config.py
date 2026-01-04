"""处理配置模型."""

import json
from typing import Optional

from pydantic import BaseModel, Field, field_validator

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


class BackgroundConfig(BaseModel):
    """背景配置."""

    color: RGBColor = Field(
        default=DEFAULT_BACKGROUND_COLOR,
        description="背景颜色 RGB",
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
