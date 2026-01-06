"""模板与图层数据模型.

提供可视化模板编辑系统的数据模型，支持多图层（文字、形状、图片）管理。

Features:
    - 图层元素基类与子类（文字、形状、图片）
    - 模板配置管理
    - JSON序列化/反序列化
    - 图层层级管理
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ===================
# 类型别名
# ===================

RGBColor = tuple[int, int, int]
RGBAColor = tuple[int, int, int, int]
Position = tuple[int, int]
Size = tuple[int, int]


# ===================
# 常量定义
# ===================

# 默认图层属性
DEFAULT_LAYER_OPACITY = 100
DEFAULT_LAYER_ROTATION = 0.0
DEFAULT_LAYER_Z_INDEX = 0

# 文字图层默认值
DEFAULT_TEXT_CONTENT = "文字"
DEFAULT_TEXT_FONT_SIZE = 24
DEFAULT_TEXT_FONT_FAMILY = None  # 使用系统默认字体
DEFAULT_TEXT_COLOR: RGBColor = (0, 0, 0)
DEFAULT_TEXT_BACKGROUND_COLOR: RGBColor = (255, 255, 255)
DEFAULT_TEXT_BACKGROUND_PADDING = 8

# 形状图层默认值
DEFAULT_SHAPE_FILL_COLOR: RGBColor = (200, 200, 200)
DEFAULT_SHAPE_STROKE_COLOR: RGBColor = (100, 100, 100)
DEFAULT_SHAPE_STROKE_WIDTH = 1
DEFAULT_SHAPE_CORNER_RADIUS = 0

# 图片图层默认值
DEFAULT_IMAGE_FIT_MODE = "contain"

# 模板默认值
DEFAULT_CANVAS_SIZE: Size = (800, 800)


# ===================
# 枚举定义
# ===================


class LayerType(str, Enum):
    """图层类型枚举."""

    TEXT = "text"  # 文字图层
    RECTANGLE = "rectangle"  # 矩形图层
    ELLIPSE = "ellipse"  # 椭圆/圆形图层
    IMAGE = "image"  # 图片图层


class TextAlign(str, Enum):
    """文字对齐方式."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class ImageFitMode(str, Enum):
    """图片适应模式."""

    CONTAIN = "contain"  # 保持比例，完整显示
    COVER = "cover"  # 保持比例，填满区域
    STRETCH = "stretch"  # 拉伸填满


# 图层类型中文名称
LAYER_TYPE_NAMES: dict[LayerType, str] = {
    LayerType.TEXT: "文字",
    LayerType.RECTANGLE: "矩形",
    LayerType.ELLIPSE: "椭圆",
    LayerType.IMAGE: "图片",
}


# ===================
# 辅助函数
# ===================


def generate_layer_id() -> str:
    """生成唯一的图层ID.

    Returns:
        8位UUID字符串
    """
    return uuid.uuid4().hex[:8]


def validate_rgb_color(color: RGBColor) -> RGBColor:
    """验证RGB颜色值.

    Args:
        color: RGB颜色元组

    Returns:
        验证后的颜色元组

    Raises:
        ValueError: 颜色值不在有效范围内
    """
    if len(color) != 3:
        raise ValueError(f"RGB颜色必须包含3个值，实际: {len(color)}")
    for i, v in enumerate(color):
        if not 0 <= v <= 255:
            raise ValueError(f"颜色值必须在0-255之间，索引{i}的值: {v}")
    return color


def validate_rgba_color(color: RGBAColor) -> RGBAColor:
    """验证RGBA颜色值.

    Args:
        color: RGBA颜色元组

    Returns:
        验证后的颜色元组

    Raises:
        ValueError: 颜色值不在有效范围内
    """
    if len(color) != 4:
        raise ValueError(f"RGBA颜色必须包含4个值，实际: {len(color)}")
    for i, v in enumerate(color):
        if not 0 <= v <= 255:
            raise ValueError(f"颜色值必须在0-255之间，索引{i}的值: {v}")
    return color


# ===================
# 图层基类
# ===================


class LayerElement(BaseModel):
    """图层元素基类.

    所有图层类型的基类，定义通用属性。

    Attributes:
        id: 图层唯一标识符
        name: 图层名称（用于图层面板显示）
        type: 图层类型
        x: X坐标（像素）
        y: Y坐标（像素）
        width: 宽度（像素）
        height: 高度（像素）
        rotation: 旋转角度（度，顺时针）
        opacity: 不透明度（0-100）
        z_index: 层级索引（数值越大越靠前）
        visible: 是否可见
        locked: 是否锁定（锁定后不可编辑）

    Example:
        >>> # 通常不直接实例化，而是使用子类
        >>> layer = TextLayer(name="标题", x=100, y=50)
    """

    id: str = Field(default_factory=generate_layer_id, description="图层唯一ID")
    name: str = Field(default="图层", max_length=50, description="图层名称")
    type: LayerType = Field(description="图层类型")

    # 位置和尺寸
    x: int = Field(default=0, ge=0, description="X坐标")
    y: int = Field(default=0, ge=0, description="Y坐标")
    width: int = Field(default=100, ge=1, description="宽度")
    height: int = Field(default=100, ge=1, description="高度")

    # 变换属性
    rotation: float = Field(
        default=DEFAULT_LAYER_ROTATION,
        ge=-360,
        le=360,
        description="旋转角度",
    )
    opacity: int = Field(
        default=DEFAULT_LAYER_OPACITY,
        ge=0,
        le=100,
        description="不透明度",
    )

    # 层级和状态
    z_index: int = Field(default=DEFAULT_LAYER_Z_INDEX, description="层级索引")
    visible: bool = Field(default=True, description="是否可见")
    locked: bool = Field(default=False, description="是否锁定")

    model_config = ConfigDict(use_enum_values=False)  # 保留枚举对象

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        """获取图层边界框.

        Returns:
            (left, top, right, bottom) 边界元组
        """
        return (self.x, self.y, self.x + self.width, self.y + self.height)

    @property
    def center(self) -> Position:
        """获取图层中心点.

        Returns:
            (cx, cy) 中心点坐标
        """
        return (self.x + self.width // 2, self.y + self.height // 2)

    def move_to(self, x: int, y: int) -> None:
        """移动图层到指定位置.

        Args:
            x: 新的X坐标
            y: 新的Y坐标
        """
        self.x = max(0, x)
        self.y = max(0, y)

    def move_by(self, dx: int, dy: int) -> None:
        """相对移动图层.

        Args:
            dx: X方向偏移
            dy: Y方向偏移
        """
        self.x = max(0, self.x + dx)
        self.y = max(0, self.y + dy)

    def resize(self, width: int, height: int) -> None:
        """调整图层尺寸.

        Args:
            width: 新宽度
            height: 新高度
        """
        self.width = max(1, width)
        self.height = max(1, height)

    def clone(self) -> "LayerElement":
        """克隆图层.

        Returns:
            新的图层实例，具有新的ID
        """
        data = self.model_dump()
        data["id"] = generate_layer_id()
        data["name"] = f"{self.name}_副本"
        return self.__class__(**data)


# ===================
# 文字图层
# ===================


class TextLayer(LayerElement):
    """文字图层.

    支持富文本样式、背景和描边效果。

    Attributes:
        content: 文字内容
        font_family: 字体名称
        font_size: 字体大小
        font_color: 字体颜色
        bold: 是否粗体
        italic: 是否斜体
        underline: 是否下划线
        align: 文字对齐方式
        line_height: 行高倍数
        background_enabled: 是否启用背景
        background_color: 背景颜色
        background_opacity: 背景不透明度
        background_padding: 背景内边距
        stroke_enabled: 是否启用描边
        stroke_color: 描边颜色
        stroke_width: 描边宽度

    Example:
        >>> layer = TextLayer(
        ...     name="标题",
        ...     content="促销活动",
        ...     font_size=36,
        ...     font_color=(255, 0, 0),
        ...     bold=True,
        ... )
        >>> layer.type
        <LayerType.TEXT: 'text'>
    """

    type: Literal[LayerType.TEXT] = Field(default=LayerType.TEXT, description="图层类型")

    # 文字内容
    content: str = Field(
        default=DEFAULT_TEXT_CONTENT,
        max_length=1000,
        description="文字内容",
    )

    # 字体样式
    font_family: Optional[str] = Field(
        default=DEFAULT_TEXT_FONT_FAMILY,
        description="字体名称",
    )
    font_size: int = Field(
        default=DEFAULT_TEXT_FONT_SIZE,
        ge=8,
        le=200,
        description="字体大小",
    )
    font_color: RGBColor = Field(
        default=DEFAULT_TEXT_COLOR,
        description="字体颜色",
    )

    # 字体效果
    bold: bool = Field(default=False, description="粗体")
    italic: bool = Field(default=False, description="斜体")
    underline: bool = Field(default=False, description="下划线")

    # 排版
    align: TextAlign = Field(default=TextAlign.LEFT, description="对齐方式")
    line_height: float = Field(
        default=1.2,
        ge=0.5,
        le=3.0,
        description="行高倍数",
    )
    word_wrap: bool = Field(default=True, description="自动换行")

    # 背景
    background_enabled: bool = Field(default=False, description="启用背景")
    background_color: RGBColor = Field(
        default=DEFAULT_TEXT_BACKGROUND_COLOR,
        description="背景颜色",
    )
    background_opacity: int = Field(
        default=100,
        ge=0,
        le=100,
        description="背景不透明度",
    )
    background_padding: int = Field(
        default=DEFAULT_TEXT_BACKGROUND_PADDING,
        ge=0,
        le=50,
        description="背景内边距",
    )

    # 描边
    stroke_enabled: bool = Field(default=False, description="启用描边")
    stroke_color: RGBColor = Field(
        default=(255, 255, 255),
        description="描边颜色",
    )
    stroke_width: int = Field(
        default=1,
        ge=1,
        le=10,
        description="描边宽度",
    )

    @field_validator("font_color", "background_color", "stroke_color")
    @classmethod
    def validate_color(cls, v: RGBColor) -> RGBColor:
        """验证颜色值."""
        return validate_rgb_color(v)

    @classmethod
    def create(
        cls,
        content: str,
        x: int = 0,
        y: int = 0,
        font_size: int = DEFAULT_TEXT_FONT_SIZE,
        font_color: RGBColor = DEFAULT_TEXT_COLOR,
        name: Optional[str] = None,
    ) -> "TextLayer":
        """快速创建文字图层.

        Args:
            content: 文字内容
            x: X坐标
            y: Y坐标
            font_size: 字体大小
            font_color: 字体颜色
            name: 图层名称

        Returns:
            TextLayer实例
        """
        return cls(
            name=name or f"文字_{content[:4]}",
            content=content,
            x=x,
            y=y,
            font_size=font_size,
            font_color=font_color,
            # 初始宽高会在实际渲染时根据文字计算
            width=len(content) * font_size,
            height=int(font_size * 1.5),
        )

    @classmethod
    def create_label(
        cls,
        content: str,
        x: int = 0,
        y: int = 0,
        font_color: RGBColor = (255, 255, 255),
        background_color: RGBColor = (255, 0, 0),
    ) -> "TextLayer":
        """创建带背景的标签文字.

        Args:
            content: 文字内容
            x: X坐标
            y: Y坐标
            font_color: 字体颜色
            background_color: 背景颜色

        Returns:
            TextLayer实例
        """
        layer = cls.create(content, x, y, font_color=font_color)
        layer.name = f"标签_{content[:4]}"
        layer.background_enabled = True
        layer.background_color = background_color
        layer.background_opacity = 100
        return layer


# ===================
# 形状图层
# ===================


class ShapeLayer(LayerElement):
    """形状图层（矩形或椭圆）.

    支持填充、描边和圆角效果。

    Attributes:
        fill_enabled: 是否启用填充
        fill_color: 填充颜色
        fill_opacity: 填充不透明度
        stroke_enabled: 是否启用描边
        stroke_color: 描边颜色
        stroke_width: 描边宽度
        corner_radius: 圆角半径（仅矩形有效）

    Example:
        >>> rect = ShapeLayer(
        ...     type=LayerType.RECTANGLE,
        ...     name="背景框",
        ...     width=200,
        ...     height=100,
        ...     fill_color=(255, 200, 200),
        ...     corner_radius=10,
        ... )
    """

    type: Literal[LayerType.RECTANGLE, LayerType.ELLIPSE] = Field(
        default=LayerType.RECTANGLE,
        description="形状类型",
    )

    # 填充
    fill_enabled: bool = Field(default=True, description="启用填充")
    fill_color: RGBColor = Field(
        default=DEFAULT_SHAPE_FILL_COLOR,
        description="填充颜色",
    )
    fill_opacity: int = Field(
        default=100,
        ge=0,
        le=100,
        description="填充不透明度",
    )

    # 描边
    stroke_enabled: bool = Field(default=False, description="启用描边")
    stroke_color: RGBColor = Field(
        default=DEFAULT_SHAPE_STROKE_COLOR,
        description="描边颜色",
    )
    stroke_width: int = Field(
        default=DEFAULT_SHAPE_STROKE_WIDTH,
        ge=0,
        le=20,
        description="描边宽度",
    )

    # 圆角（仅矩形）
    corner_radius: int = Field(
        default=DEFAULT_SHAPE_CORNER_RADIUS,
        ge=0,
        le=100,
        description="圆角半径",
    )

    @field_validator("fill_color", "stroke_color")
    @classmethod
    def validate_color(cls, v: RGBColor) -> RGBColor:
        """验证颜色值."""
        return validate_rgb_color(v)

    @property
    def is_rectangle(self) -> bool:
        """是否为矩形."""
        return self.type == LayerType.RECTANGLE

    @property
    def is_ellipse(self) -> bool:
        """是否为椭圆."""
        return self.type == LayerType.ELLIPSE

    @classmethod
    def create_rectangle(
        cls,
        x: int = 0,
        y: int = 0,
        width: int = 100,
        height: int = 100,
        fill_color: RGBColor = DEFAULT_SHAPE_FILL_COLOR,
        corner_radius: int = 0,
        name: Optional[str] = None,
    ) -> "ShapeLayer":
        """创建矩形图层.

        Args:
            x: X坐标
            y: Y坐标
            width: 宽度
            height: 高度
            fill_color: 填充颜色
            corner_radius: 圆角半径
            name: 图层名称

        Returns:
            ShapeLayer实例
        """
        return cls(
            type=LayerType.RECTANGLE,
            name=name or "矩形",
            x=x,
            y=y,
            width=width,
            height=height,
            fill_color=fill_color,
            corner_radius=corner_radius,
        )

    @classmethod
    def create_ellipse(
        cls,
        x: int = 0,
        y: int = 0,
        width: int = 100,
        height: int = 100,
        fill_color: RGBColor = DEFAULT_SHAPE_FILL_COLOR,
        name: Optional[str] = None,
    ) -> "ShapeLayer":
        """创建椭圆图层.

        Args:
            x: X坐标
            y: Y坐标
            width: 宽度
            height: 高度
            fill_color: 填充颜色
            name: 图层名称

        Returns:
            ShapeLayer实例
        """
        return cls(
            type=LayerType.ELLIPSE,
            name=name or "椭圆",
            x=x,
            y=y,
            width=width,
            height=height,
            fill_color=fill_color,
        )


# ===================
# 图片图层
# ===================


class ImageLayer(LayerElement):
    """图片图层.

    支持从本地导入图片，提供多种适应模式。

    Attributes:
        image_path: 图片文件路径
        fit_mode: 图片适应模式
        preserve_aspect_ratio: 是否保持宽高比

    Example:
        >>> layer = ImageLayer(
        ...     name="Logo",
        ...     image_path="/path/to/logo.png",
        ...     fit_mode=ImageFitMode.CONTAIN,
        ... )
    """

    type: Literal[LayerType.IMAGE] = Field(default=LayerType.IMAGE, description="图层类型")

    # 图片属性
    image_path: str = Field(default="", description="图片文件路径")
    fit_mode: ImageFitMode = Field(
        default=ImageFitMode.CONTAIN,
        description="适应模式",
    )
    preserve_aspect_ratio: bool = Field(
        default=True,
        description="保持宽高比",
    )

    @property
    def has_image(self) -> bool:
        """是否已设置图片."""
        return bool(self.image_path)

    @classmethod
    def create(
        cls,
        image_path: str,
        x: int = 0,
        y: int = 0,
        width: int = 100,
        height: int = 100,
        name: Optional[str] = None,
    ) -> "ImageLayer":
        """创建图片图层.

        Args:
            image_path: 图片路径
            x: X坐标
            y: Y坐标
            width: 宽度
            height: 高度
            name: 图层名称

        Returns:
            ImageLayer实例
        """
        import os

        default_name = os.path.basename(image_path) if image_path else "图片"
        return cls(
            name=name or default_name,
            image_path=image_path,
            x=x,
            y=y,
            width=width,
            height=height,
        )


# ===================
# 图层联合类型
# ===================

# 用于类型检查的联合类型
AnyLayer = Union[TextLayer, ShapeLayer, ImageLayer]


# ===================
# 模板配置
# ===================


class TemplateConfig(BaseModel):
    """模板配置.

    管理画布和图层集合，支持序列化和反序列化。

    Attributes:
        id: 模板唯一ID
        name: 模板名称
        description: 模板描述
        canvas_width: 画布宽度
        canvas_height: 画布高度
        background_color: 画布背景色
        layers: 图层列表
        is_preset: 是否为预设模板
        version: 模板版本号

    Example:
        >>> template = TemplateConfig(name="促销模板")
        >>> text = TextLayer.create("促销", x=100, y=50)
        >>> template.add_layer(text)
        >>> template.layer_count
        1
    """

    id: str = Field(default_factory=generate_layer_id, description="模板唯一ID")
    name: str = Field(default="未命名模板", max_length=100, description="模板名称")
    description: str = Field(default="", max_length=500, description="模板描述")

    # 画布属性
    canvas_width: int = Field(
        default=DEFAULT_CANVAS_SIZE[0],
        ge=100,
        le=4096,
        description="画布宽度",
    )
    canvas_height: int = Field(
        default=DEFAULT_CANVAS_SIZE[1],
        ge=100,
        le=4096,
        description="画布高度",
    )
    background_color: RGBColor = Field(
        default=(255, 255, 255),
        description="画布背景色",
    )

    # 图层列表（使用list存储，支持多种图层类型）
    layers: list[dict[str, Any]] = Field(default_factory=list, description="图层数据列表")

    # 元数据
    is_preset: bool = Field(default=False, description="是否为预设模板")
    version: str = Field(default="1.0", description="模板版本")

    @field_validator("background_color")
    @classmethod
    def validate_bg_color(cls, v: RGBColor) -> RGBColor:
        """验证背景色."""
        return validate_rgb_color(v)

    @property
    def canvas_size(self) -> Size:
        """获取画布尺寸."""
        return (self.canvas_width, self.canvas_height)

    @property
    def layer_count(self) -> int:
        """获取图层数量."""
        return len(self.layers)

    def get_layers(self) -> list[AnyLayer]:
        """获取所有图层对象.

        Returns:
            图层对象列表
        """
        result: list[AnyLayer] = []
        for layer_data in self.layers:
            layer = self._deserialize_layer(layer_data)
            if layer:
                result.append(layer)
        return result

    def get_layer_by_id(self, layer_id: str) -> Optional[AnyLayer]:
        """根据ID获取图层.

        Args:
            layer_id: 图层ID

        Returns:
            图层对象，不存在返回None
        """
        for layer_data in self.layers:
            if layer_data.get("id") == layer_id:
                return self._deserialize_layer(layer_data)
        return None

    def add_layer(self, layer: AnyLayer) -> None:
        """添加图层.

        Args:
            layer: 图层对象
        """
        # 自动设置z_index为最大值+1
        if self.layers:
            max_z = max(l.get("z_index", 0) for l in self.layers)
            layer.z_index = max_z + 1

        self.layers.append(layer.model_dump())

    def remove_layer(self, layer_id: str) -> bool:
        """删除图层.

        Args:
            layer_id: 图层ID

        Returns:
            是否删除成功
        """
        for i, layer_data in enumerate(self.layers):
            if layer_data.get("id") == layer_id:
                self.layers.pop(i)
                return True
        return False

    def update_layer(self, layer: AnyLayer) -> bool:
        """更新图层.

        Args:
            layer: 更新后的图层对象

        Returns:
            是否更新成功
        """
        for i, layer_data in enumerate(self.layers):
            if layer_data.get("id") == layer.id:
                self.layers[i] = layer.model_dump()
                return True
        return False

    def move_layer(self, layer_id: str, new_z_index: int) -> bool:
        """移动图层层级.

        Args:
            layer_id: 图层ID
            new_z_index: 新的层级索引

        Returns:
            是否移动成功
        """
        for layer_data in self.layers:
            if layer_data.get("id") == layer_id:
                layer_data["z_index"] = new_z_index
                return True
        return False

    def get_layers_sorted(self) -> list[AnyLayer]:
        """获取按z_index排序的图层列表.

        Returns:
            排序后的图层列表（z_index从小到大）
        """
        layers = self.get_layers()
        return sorted(layers, key=lambda l: l.z_index)

    def clear_layers(self) -> None:
        """清空所有图层."""
        self.layers.clear()

    def _deserialize_layer(self, data: dict[str, Any]) -> Optional[AnyLayer]:
        """反序列化图层数据.

        Args:
            data: 图层字典数据

        Returns:
            图层对象，失败返回None
        """
        layer_type = data.get("type")
        if not layer_type:
            return None

        try:
            if layer_type == LayerType.TEXT or layer_type == "text":
                return TextLayer(**data)
            elif layer_type in (LayerType.RECTANGLE, LayerType.ELLIPSE, "rectangle", "ellipse"):
                return ShapeLayer(**data)
            elif layer_type == LayerType.IMAGE or layer_type == "image":
                return ImageLayer(**data)
        except Exception:
            return None

        return None

    @classmethod
    def create(
        cls,
        name: str,
        width: int = DEFAULT_CANVAS_SIZE[0],
        height: int = DEFAULT_CANVAS_SIZE[1],
        description: str = "",
    ) -> "TemplateConfig":
        """创建模板.

        Args:
            name: 模板名称
            width: 画布宽度
            height: 画布高度
            description: 描述

        Returns:
            TemplateConfig实例
        """
        return cls(
            name=name,
            canvas_width=width,
            canvas_height=height,
            description=description,
        )

    def to_json(self, indent: int = 2) -> str:
        """序列化为JSON字符串.

        Args:
            indent: 缩进空格数

        Returns:
            JSON字符串
        """
        import json

        return json.dumps(self.model_dump(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "TemplateConfig":
        """从JSON字符串反序列化.

        Args:
            json_str: JSON字符串

        Returns:
            TemplateConfig实例
        """
        import json

        data = json.loads(json_str)
        return cls(**data)

    @classmethod
    def from_file(cls, file_path: str) -> "TemplateConfig":
        """从文件加载模板.

        Args:
            file_path: 文件路径

        Returns:
            TemplateConfig实例
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return cls.from_json(f.read())

    def save_to_file(self, file_path: str) -> None:
        """保存模板到文件.

        Args:
            file_path: 文件路径
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
