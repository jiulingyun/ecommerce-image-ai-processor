"""模板渲染引擎.

将模板中的图层元素渲染到图片上。

Features:
    - 按 z_index 顺序渲染图层
    - 文字渲染支持背景和描边
    - 形状渲染支持填充和边框
    - 图片图层合成
"""

from __future__ import annotations

import os
from typing import Optional, TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from src.models.template_config import (
    TemplateConfig,
    AnyLayer,
    TextLayer,
    ShapeLayer,
    ImageLayer,
    LayerType,
    TextAlign,
    ImageFitMode,
)
from src.utils.logger import setup_logger

if TYPE_CHECKING:
    pass

logger = setup_logger(__name__)


# ===================
# 常量定义
# ===================

# 默认字体
DEFAULT_FONT_NAME = "Arial"
DEFAULT_FONT_SIZE = 24

# 字体搜索路径
FONT_SEARCH_PATHS = [
    "/System/Library/Fonts/",
    "/System/Library/Fonts/Supplemental/",
    "/Library/Fonts/",
    "~/Library/Fonts/",
    "C:/Windows/Fonts/",
    "/usr/share/fonts/",
    "/usr/share/fonts/truetype/",
]

# 中文字体回退列表（macOS/Windows/Linux 常见中文字体）
CHINESE_FONT_FALLBACKS = [
    # macOS
    "PingFang SC.ttc",
    "PingFang.ttc",
    "STHeiti Light.ttc",
    "STHeiti Medium.ttc",
    "Hiragino Sans GB.ttc",
    "Songti.ttc",
    "Heiti.ttc",
    # Windows
    "msyh.ttc",  # 微软雅黑
    "simsun.ttc",  # 宋体
    "simhei.ttf",  # 黑体
    # Linux
    "wqy-microhei.ttc",
    "wqy-zenhei.ttc",
    "NotoSansCJK-Regular.ttc",
    "NotoSansSC-Regular.otf",
]


# ===================
# 字体管理
# ===================


def _has_chinese_characters(text: str) -> bool:
    """检查文本是否包含中文字符.

    Args:
        text: 要检查的文本

    Returns:
        是否包含中文
    """
    for char in text:
        if '\u4e00' <= char <= '\u9fff' or '\u3400' <= char <= '\u4dbf':
            return True
    return False


def _find_chinese_font(font_size: int) -> Optional[ImageFont.FreeTypeFont]:
    """查找中文字体.

    Args:
        font_size: 字体大小

    Returns:
        找到的字体，未找到返回 None
    """
    for search_path in FONT_SEARCH_PATHS:
        expanded_path = os.path.expanduser(search_path)
        if not os.path.exists(expanded_path):
            continue

        for font_name in CHINESE_FONT_FALLBACKS:
            font_path = os.path.join(expanded_path, font_name)
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, font_size)
                except (OSError, IOError):
                    continue

    return None


def find_font(
    font_family: Optional[str],
    font_size: int,
    bold: bool = False,
    italic: bool = False,
    text_content: Optional[str] = None,
) -> ImageFont.FreeTypeFont:
    """查找字体.

    Args:
        font_family: 字体名称
        font_size: 字体大小
        bold: 是否粗体
        italic: 是否斜体
        text_content: 要渲染的文本（用于检测是否需要中文字体）

    Returns:
        ImageFont 对象
    """
    # 检查是否需要中文字体
    needs_chinese = text_content and _has_chinese_characters(text_content)

    # 如果没有指定字体，根据内容选择默认字体
    if not font_family:
        if needs_chinese:
            chinese_font = _find_chinese_font(font_size)
            if chinese_font:
                return chinese_font
        try:
            return ImageFont.truetype("Arial", font_size)
        except (OSError, IOError):
            return ImageFont.load_default()

    # 尝试直接加载指定字体
    try:
        return ImageFont.truetype(font_family, font_size)
    except (OSError, IOError):
        pass

    # 尝试在常用路径中查找
    font_variants = [
        font_family,
        f"{font_family}.ttf",
        f"{font_family}.otf",
        f"{font_family}.ttc",
    ]

    # 添加粗体/斜体变体
    if bold and italic:
        font_variants.extend([
            f"{font_family}-BoldItalic.ttf",
            f"{font_family} Bold Italic.ttf",
        ])
    elif bold:
        font_variants.extend([
            f"{font_family}-Bold.ttf",
            f"{font_family} Bold.ttf",
        ])
    elif italic:
        font_variants.extend([
            f"{font_family}-Italic.ttf",
            f"{font_family} Italic.ttf",
        ])

    for search_path in FONT_SEARCH_PATHS:
        expanded_path = os.path.expanduser(search_path)
        if not os.path.exists(expanded_path):
            continue

        for variant in font_variants:
            font_path = os.path.join(expanded_path, variant)
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, font_size)
                except (OSError, IOError):
                    continue

    # 如果指定的字体找不到，且需要中文，尝试中文字体回退
    if needs_chinese:
        chinese_font = _find_chinese_font(font_size)
        if chinese_font:
            logger.warning(f"字体 '{font_family}' 未找到，使用中文字体回退")
            return chinese_font

    # 回退到默认字体
    logger.warning(f"字体 '{font_family}' 未找到，使用默认字体")
    try:
        return ImageFont.truetype("Arial", font_size)
    except (OSError, IOError):
        return ImageFont.load_default()


# ===================
# 模板渲染器
# ===================


class TemplateRenderer:
    """模板渲染器.

    将模板中的图层元素渲染到图片上。

    Example:
        >>> renderer = TemplateRenderer()
        >>> template = TemplateConfig.create("测试")
        >>> template.add_layer(TextLayer.create("Hello"))
        >>> result = renderer.render(image, template)
    """

    def __init__(self) -> None:
        """初始化渲染器."""
        pass

    def render(
        self,
        image: Image.Image,
        template: TemplateConfig,
        skip_invisible: bool = True,
    ) -> Image.Image:
        """渲染模板到图片.

        注意：如果图片尺寸与模板画布尺寸不一致，图层坐标和尺寸会按比例缩放。

        Args:
            image: 原始图片
            template: 模板配置
            skip_invisible: 是否跳过不可见图层

        Returns:
            渲染后的图片
        """
        # 确保图片是 RGBA 模式
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # 创建工作副本
        result = image.copy()

        # 计算缩放比例（图片尺寸 vs 模板画布尺寸）
        scale_x = image.width / template.canvas_width
        scale_y = image.height / template.canvas_height
        
        logger.debug(f"渲染模板: 图片尺寸={image.size}, 画布尺寸=({template.canvas_width}, {template.canvas_height}), 缩放=({scale_x:.2f}, {scale_y:.2f})")

        # 获取按 z_index 排序的图层
        layers = template.get_layers_sorted()

        # 渲染每个图层
        for layer in layers:
            if skip_invisible and not layer.visible:
                continue

            try:
                result = self._render_layer(result, layer, scale_x, scale_y)
            except Exception as e:
                logger.error(f"渲染图层失败: {layer.id}, 错误: {e}")

        return result

    def render_to_size(
        self,
        image: Image.Image,
        template: TemplateConfig,
        target_size: Optional[tuple[int, int]] = None,
    ) -> Image.Image:
        """渲染模板到指定尺寸.

        Args:
            image: 原始图片
            template: 模板配置
            target_size: 目标尺寸，默认使用模板画布尺寸

        Returns:
            渲染后的图片
        """
        # 确定目标尺寸
        if target_size is None:
            target_size = (template.canvas_width, template.canvas_height)

        # 创建画布
        canvas = Image.new("RGBA", target_size, (*template.background_color, 255))

        # 缩放原图适应画布
        img_ratio = image.width / image.height
        canvas_ratio = target_size[0] / target_size[1]

        if img_ratio > canvas_ratio:
            # 图片更宽，按宽度缩放
            new_width = target_size[0]
            new_height = int(new_width / img_ratio)
        else:
            # 图片更高，按高度缩放
            new_height = target_size[1]
            new_width = int(new_height * img_ratio)

        # 缩放图片
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 居中放置
        x = (target_size[0] - new_width) // 2
        y = (target_size[1] - new_height) // 2

        # 确保 resized 是 RGBA
        if resized.mode != "RGBA":
            resized = resized.convert("RGBA")

        canvas.paste(resized, (x, y), resized)

        # 渲染模板图层
        return self.render(canvas, template)

    def _render_layer(
        self,
        image: Image.Image,
        layer: AnyLayer,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> Image.Image:
        """渲染单个图层.

        Args:
            image: 当前图片
            layer: 图层数据
            scale_x: X轴缩放比例
            scale_y: Y轴缩放比例

        Returns:
            渲染后的图片
        """
        if isinstance(layer, TextLayer):
            return self._render_text_layer(image, layer, scale_x, scale_y)
        elif isinstance(layer, ShapeLayer):
            return self._render_shape_layer(image, layer, scale_x, scale_y)
        elif isinstance(layer, ImageLayer):
            return self._render_image_layer(image, layer, scale_x, scale_y)
        else:
            logger.warning(f"未知图层类型: {type(layer)}")
            return image

    def _render_text_layer(
        self,
        image: Image.Image,
        layer: TextLayer,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> Image.Image:
        """渲染文字图层.

        Args:
            image: 当前图片
            layer: 文字图层
            scale_x: X轴缩放比例
            scale_y: Y轴缩放比例

        Returns:
            渲染后的图片
        """
        if not layer.content:
            return image

        # 计算缩放后的字体大小（使用平均缩放比例）
        avg_scale = (scale_x + scale_y) / 2
        scaled_font_size = max(1, int(layer.font_size * avg_scale))

        # 获取字体（传递文本内容以便检测是否需要中文字体）
        font = find_font(
            layer.font_family,
            scaled_font_size,
            layer.bold,
            layer.italic,
            text_content=layer.content,
        )

        # 创建临时图像绘制文字
        temp = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(temp)

        # 处理多行文本
        lines = layer.content.split('\n') if '\n' in layer.content else [layer.content]
        
        # 计算行高
        line_height_px = int(scaled_font_size * layer.line_height)
        
        # 计算每行的宽度和总高度
        line_widths = []
        line_heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line or ' ', font=font)
            line_widths.append(bbox[2] - bbox[0])
            line_heights.append(bbox[3] - bbox[1])
        
        text_width = max(line_widths) if line_widths else 0
        total_height = sum(line_heights) + line_height_px * (len(lines) - 1) if lines else 0

        # 缩放后的位置
        base_x = int(layer.x * scale_x)
        base_y = int(layer.y * scale_y)

        # 绘制背景
        if layer.background_enabled:
            padding = int(layer.background_padding * avg_scale)
            bg_color = (*layer.background_color, int(layer.background_opacity * 2.55))
            draw.rectangle(
                [
                    base_x - padding,
                    base_y - padding,
                    base_x + text_width + padding,
                    base_y + total_height + padding,
                ],
                fill=bg_color,
            )

        # 绘制文字（逐行绘制）
        text_color = (*layer.font_color, int(layer.opacity * 2.55))
        scaled_stroke_width = max(1, int(layer.stroke_width * avg_scale)) if layer.stroke_enabled else 0
        
        current_y = base_y
        for i, line in enumerate(lines):
            if not line:
                current_y += line_height_px
                continue
            
            # 计算当前行的 X 位置（根据对齐方式）
            line_width = line_widths[i]
            if layer.align == TextAlign.CENTER:
                x = base_x + (text_width - line_width) // 2
            elif layer.align == TextAlign.RIGHT:
                x = base_x + text_width - line_width
            else:  # LEFT
                x = base_x
            
            # 绘制描边
            if layer.stroke_enabled:
                stroke_color = (*layer.stroke_color, 255)
                for dx in range(-scaled_stroke_width, scaled_stroke_width + 1):
                    for dy in range(-scaled_stroke_width, scaled_stroke_width + 1):
                        if dx != 0 or dy != 0:
                            draw.text(
                                (x + dx, current_y + dy),
                                line,
                                font=font,
                                fill=stroke_color,
                            )
            
            # 绘制文字
            draw.text((x, current_y), line, font=font, fill=text_color)
            
            # 移动到下一行
            current_y += line_heights[i] + line_height_px

        # 合成
        image = Image.alpha_composite(image, temp)

        return image

    def _render_shape_layer(
        self,
        image: Image.Image,
        layer: ShapeLayer,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> Image.Image:
        """渲染形状图层.

        Args:
            image: 当前图片
            layer: 形状图层
            scale_x: X轴缩放比例
            scale_y: Y轴缩放比例

        Returns:
            渲染后的图片
        """
        # 创建临时图像
        temp = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(temp)

        # 缩放后的位置和尺寸
        x1 = int(layer.x * scale_x)
        y1 = int(layer.y * scale_y)
        x2 = int((layer.x + layer.width) * scale_x)
        y2 = int((layer.y + layer.height) * scale_y)

        # 准备颜色
        fill_color = None
        if layer.fill_enabled:
            fill_color = (*layer.fill_color, int(layer.fill_opacity * 2.55))

        outline_color = None
        outline_width = 0
        if layer.stroke_enabled:
            outline_color = (*layer.stroke_color, 255)
            # 缩放边框宽度
            avg_scale = (scale_x + scale_y) / 2
            outline_width = max(1, int(layer.stroke_width * avg_scale))

        # 缩放圆角半径
        avg_scale = (scale_x + scale_y) / 2
        scaled_radius = int(layer.corner_radius * avg_scale)

        # 绘制形状
        if layer.is_rectangle:
            if scaled_radius > 0:
                # 圆角矩形
                self._draw_rounded_rectangle(
                    draw,
                    (x1, y1, x2, y2),
                    scaled_radius,
                    fill_color,
                    outline_color,
                    outline_width,
                )
            else:
                draw.rectangle(
                    (x1, y1, x2, y2),
                    fill=fill_color,
                    outline=outline_color,
                    width=outline_width,
                )
        elif layer.is_ellipse:
            draw.ellipse(
                (x1, y1, x2, y2),
                fill=fill_color,
                outline=outline_color,
                width=outline_width,
            )

        # 应用透明度
        if layer.opacity < 100:
            alpha = temp.split()[3]
            alpha = alpha.point(lambda p: int(p * layer.opacity / 100))
            temp.putalpha(alpha)

        # 合成
        image = Image.alpha_composite(image, temp)

        return image

    def _draw_rounded_rectangle(
        self,
        draw: ImageDraw.ImageDraw,
        bbox: tuple,
        radius: int,
        fill: Optional[tuple],
        outline: Optional[tuple],
        width: int,
    ) -> None:
        """绘制圆角矩形.

        Args:
            draw: ImageDraw 对象
            bbox: 边界框 (x1, y1, x2, y2)
            radius: 圆角半径
            fill: 填充颜色
            outline: 边框颜色
            width: 边框宽度
        """
        x1, y1, x2, y2 = bbox

        # 限制圆角半径
        max_radius = min((x2 - x1) // 2, (y2 - y1) // 2)
        radius = min(radius, max_radius)

        # 使用 rounded_rectangle（PIL 9.0+）
        try:
            draw.rounded_rectangle(bbox, radius, fill=fill, outline=outline, width=width)
        except AttributeError:
            # 兼容旧版本 PIL
            if fill:
                draw.rectangle((x1 + radius, y1, x2 - radius, y2), fill=fill)
                draw.rectangle((x1, y1 + radius, x2, y2 - radius), fill=fill)
                draw.pieslice((x1, y1, x1 + 2 * radius, y1 + 2 * radius), 180, 270, fill=fill)
                draw.pieslice((x2 - 2 * radius, y1, x2, y1 + 2 * radius), 270, 360, fill=fill)
                draw.pieslice((x1, y2 - 2 * radius, x1 + 2 * radius, y2), 90, 180, fill=fill)
                draw.pieslice((x2 - 2 * radius, y2 - 2 * radius, x2, y2), 0, 90, fill=fill)

            if outline and width > 0:
                draw.arc((x1, y1, x1 + 2 * radius, y1 + 2 * radius), 180, 270, fill=outline, width=width)
                draw.arc((x2 - 2 * radius, y1, x2, y1 + 2 * radius), 270, 360, fill=outline, width=width)
                draw.arc((x1, y2 - 2 * radius, x1 + 2 * radius, y2), 90, 180, fill=outline, width=width)
                draw.arc((x2 - 2 * radius, y2 - 2 * radius, x2, y2), 0, 90, fill=outline, width=width)
                draw.line((x1 + radius, y1, x2 - radius, y1), fill=outline, width=width)
                draw.line((x1 + radius, y2, x2 - radius, y2), fill=outline, width=width)
                draw.line((x1, y1 + radius, x1, y2 - radius), fill=outline, width=width)
                draw.line((x2, y1 + radius, x2, y2 - radius), fill=outline, width=width)

    def _render_image_layer(
        self,
        image: Image.Image,
        layer: ImageLayer,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
    ) -> Image.Image:
        """渲染图片图层.

        Args:
            image: 当前图片
            layer: 图片图层
            scale_x: X轴缩放比例
            scale_y: Y轴缩放比例

        Returns:
            渲染后的图片
        """
        if not layer.image_path or not os.path.exists(layer.image_path):
            return image

        try:
            # 加载图片
            overlay = Image.open(layer.image_path)
            if overlay.mode != "RGBA":
                overlay = overlay.convert("RGBA")

            # 缩放后的目标尺寸
            scaled_width = int(layer.width * scale_x)
            scaled_height = int(layer.height * scale_y)
            target_size = (scaled_width, scaled_height)
            overlay = self._fit_image(overlay, target_size, layer.fit_mode, layer.preserve_aspect_ratio)

            # 应用透明度
            if layer.opacity < 100:
                alpha = overlay.split()[3]
                alpha = alpha.point(lambda p: int(p * layer.opacity / 100))
                overlay.putalpha(alpha)

            # 创建临时画布
            temp = Image.new("RGBA", image.size, (0, 0, 0, 0))

            # 缩放后的粘贴位置
            paste_x = int(layer.x * scale_x)
            paste_y = int(layer.y * scale_y)
            # 确保在画布范围内
            paste_x = max(0, min(paste_x, image.width - 1))
            paste_y = max(0, min(paste_y, image.height - 1))

            temp.paste(overlay, (paste_x, paste_y), overlay)

            # 合成
            image = Image.alpha_composite(image, temp)

        except Exception as e:
            logger.error(f"渲染图片图层失败: {e}")

        return image

    def _fit_image(
        self,
        image: Image.Image,
        target_size: tuple[int, int],
        fit_mode: ImageFitMode,
        preserve_ratio: bool,
    ) -> Image.Image:
        """根据适应模式调整图片大小.

        Args:
            image: 原图片
            target_size: 目标尺寸
            fit_mode: 适应模式
            preserve_ratio: 是否保持比例

        Returns:
            调整后的图片
        """
        target_w, target_h = target_size

        if fit_mode == ImageFitMode.STRETCH or not preserve_ratio:
            # 拉伸
            return image.resize((target_w, target_h), Image.Resampling.LANCZOS)

        img_w, img_h = image.size
        img_ratio = img_w / img_h
        target_ratio = target_w / target_h

        if fit_mode == ImageFitMode.CONTAIN:
            # 包含：图片完全显示在目标区域内
            if img_ratio > target_ratio:
                new_w = target_w
                new_h = int(new_w / img_ratio)
            else:
                new_h = target_h
                new_w = int(new_h * img_ratio)

            resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 居中放置
            result = Image.new("RGBA", target_size, (0, 0, 0, 0))
            x = (target_w - new_w) // 2
            y = (target_h - new_h) // 2
            result.paste(resized, (x, y), resized)
            return result

        elif fit_mode == ImageFitMode.COVER:
            # 覆盖：填满目标区域，可能裁剪
            if img_ratio > target_ratio:
                new_h = target_h
                new_w = int(new_h * img_ratio)
            else:
                new_w = target_w
                new_h = int(new_w / img_ratio)

            resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 居中裁剪
            x = (new_w - target_w) // 2
            y = (new_h - target_h) // 2
            return resized.crop((x, y, x + target_w, y + target_h))

        return image


# ===================
# 便捷函数
# ===================


def render_template(
    image: Image.Image,
    template: TemplateConfig,
) -> Image.Image:
    """渲染模板到图片（便捷函数）.

    Args:
        image: 原始图片
        template: 模板配置

    Returns:
        渲染后的图片
    """
    renderer = TemplateRenderer()
    return renderer.render(image, template)


def render_template_to_canvas(
    image: Image.Image,
    template: TemplateConfig,
    target_size: Optional[tuple[int, int]] = None,
) -> Image.Image:
    """渲染模板到画布（便捷函数）.

    Args:
        image: 原始图片
        template: 模板配置
        target_size: 目标尺寸

    Returns:
        渲染后的图片
    """
    renderer = TemplateRenderer()
    return renderer.render_to_size(image, template, target_size)
