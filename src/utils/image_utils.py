"""图片工具函数模块.

提供图片读取、保存、格式转换等工具函数。
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Optional, Tuple, Union

from PIL import Image

from src.utils.constants import (
    DEFAULT_OUTPUT_QUALITY,
    DEFAULT_OUTPUT_SIZE,
    MAX_IMAGE_FILE_SIZE,
    SUPPORTED_IMAGE_FORMATS,
)
from src.utils.exceptions import (
    ImageCorruptedError,
    ImageNotFoundError,
    ImageTooLargeError,
    UnsupportedImageFormatError,
)
from src.utils.file_utils import get_file_extension, get_file_size
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def validate_image_file(path: Path | str) -> None:
    """验证图片文件.

    Args:
        path: 图片文件路径

    Raises:
        ImageNotFoundError: 文件不存在
        UnsupportedImageFormatError: 不支持的格式
        ImageTooLargeError: 文件过大
        ImageCorruptedError: 文件损坏
    """
    path = Path(path)

    # 检查文件存在
    if not path.exists():
        raise ImageNotFoundError(str(path))

    # 检查格式
    ext = get_file_extension(path)
    if ext not in SUPPORTED_IMAGE_FORMATS:
        raise UnsupportedImageFormatError(ext)

    # 检查大小
    size = get_file_size(path)
    if size > MAX_IMAGE_FILE_SIZE:
        raise ImageTooLargeError(size, MAX_IMAGE_FILE_SIZE)

    # 检查是否可读
    try:
        with Image.open(path) as img:
            img.verify()
    except Exception:
        raise ImageCorruptedError(str(path))


def load_image(path: Path | str) -> Image.Image:
    """加载图片.

    Args:
        path: 图片文件路径

    Returns:
        PIL Image 对象

    Raises:
        ImageNotFoundError: 文件不存在
        ImageCorruptedError: 文件损坏
    """
    path = Path(path)

    if not path.exists():
        raise ImageNotFoundError(str(path))

    try:
        img = Image.open(path)
        img.load()  # 强制加载到内存
        return img
    except Exception as e:
        logger.error(f"加载图片失败: {path}, {e}")
        raise ImageCorruptedError(str(path))


def save_image(
    image: Image.Image,
    path: Path | str,
    quality: int = DEFAULT_OUTPUT_QUALITY,
    optimize: bool = True,
) -> Path:
    """保存图片.

    Args:
        image: PIL Image 对象
        path: 保存路径
        quality: JPEG 质量 (1-100)
        optimize: 是否优化

    Returns:
        保存的文件路径
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # 确保是 RGB 模式（用于 JPEG）
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

    # 保存
    save_kwargs = {"optimize": optimize}
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        save_kwargs["quality"] = quality

    image.save(path, **save_kwargs)
    logger.debug(f"图片已保存: {path}")

    return path


def resize_image(
    image: Image.Image,
    size: Tuple[int, int],
    maintain_aspect: bool = True,
    resample: int = Image.Resampling.LANCZOS,
) -> Image.Image:
    """调整图片尺寸.

    Args:
        image: PIL Image 对象
        size: 目标尺寸 (宽, 高)
        maintain_aspect: 是否保持纵横比
        resample: 重采样方法

    Returns:
        调整后的图片
    """
    if maintain_aspect:
        image.thumbnail(size, resample)
        return image
    else:
        return image.resize(size, resample)


def fit_to_size(
    image: Image.Image,
    size: Tuple[int, int],
    background_color: Tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """将图片适配到指定尺寸.

    保持纵横比，用背景色填充空白区域。

    Args:
        image: PIL Image 对象
        size: 目标尺寸 (宽, 高)
        background_color: 背景颜色

    Returns:
        适配后的图片
    """
    target_w, target_h = size

    # 计算缩放比例
    img_w, img_h = image.size
    scale = min(target_w / img_w, target_h / img_h)

    # 缩放
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 创建背景并粘贴
    result = Image.new("RGB", size, background_color)
    offset_x = (target_w - new_w) // 2
    offset_y = (target_h - new_h) // 2

    # 处理透明通道
    if resized.mode == "RGBA":
        result.paste(resized, (offset_x, offset_y), resized)
    else:
        result.paste(resized, (offset_x, offset_y))

    return result


def convert_format(
    image: Image.Image,
    format: str,
    quality: int = DEFAULT_OUTPUT_QUALITY,
) -> bytes:
    """转换图片格式.

    Args:
        image: PIL Image 对象
        format: 目标格式 (JPEG, PNG, WEBP)
        quality: 质量

    Returns:
        图片字节数据
    """
    buffer = io.BytesIO()

    # 确保格式正确
    if format.upper() == "JPEG" and image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    save_kwargs = {}
    if format.upper() in ("JPEG", "WEBP"):
        save_kwargs["quality"] = quality

    image.save(buffer, format=format.upper(), **save_kwargs)
    return buffer.getvalue()


def image_to_base64(
    image: Image.Image,
    format: str = "PNG",
    quality: int = DEFAULT_OUTPUT_QUALITY,
) -> str:
    """图片转 Base64.

    Args:
        image: PIL Image 对象
        format: 图片格式
        quality: 质量

    Returns:
        Base64 字符串
    """
    data = convert_format(image, format, quality)
    return base64.b64encode(data).decode("utf-8")


def base64_to_image(base64_str: str) -> Image.Image:
    """Base64 转图片.

    Args:
        base64_str: Base64 字符串

    Returns:
        PIL Image 对象
    """
    # 移除可能的前缀
    if "," in base64_str:
        base64_str = base64_str.split(",")[1]

    data = base64.b64decode(base64_str)
    return Image.open(io.BytesIO(data))


def bytes_to_image(data: bytes) -> Image.Image:
    """字节数据转图片.

    Args:
        data: 图片字节数据

    Returns:
        PIL Image 对象
    """
    return Image.open(io.BytesIO(data))


def image_to_bytes(
    image: Image.Image,
    format: str = "PNG",
    quality: int = DEFAULT_OUTPUT_QUALITY,
) -> bytes:
    """图片转字节数据.

    Args:
        image: PIL Image 对象
        format: 图片格式
        quality: 质量

    Returns:
        图片字节数据
    """
    return convert_format(image, format, quality)


def get_image_info(path: Path | str) -> dict:
    """获取图片信息.

    Args:
        path: 图片文件路径

    Returns:
        图片信息字典
    """
    path = Path(path)
    with Image.open(path) as img:
        return {
            "path": str(path),
            "filename": path.name,
            "format": img.format,
            "mode": img.mode,
            "size": img.size,
            "width": img.width,
            "height": img.height,
            "file_size": get_file_size(path),
        }


def create_thumbnail(
    image: Image.Image,
    size: Tuple[int, int] = (150, 150),
) -> Image.Image:
    """创建缩略图.

    Args:
        image: PIL Image 对象
        size: 缩略图尺寸

    Returns:
        缩略图
    """
    thumb = image.copy()
    thumb.thumbnail(size, Image.Resampling.LANCZOS)
    return thumb


def has_transparency(image: Image.Image) -> bool:
    """检查图片是否有透明通道.

    Args:
        image: PIL Image 对象

    Returns:
        是否有透明通道
    """
    if image.mode == "RGBA":
        return True
    if image.mode == "P" and "transparency" in image.info:
        return True
    return False


def ensure_rgb(image: Image.Image) -> Image.Image:
    """确保图片为 RGB 模式.

    Args:
        image: PIL Image 对象

    Returns:
        RGB 模式的图片
    """
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def ensure_rgba(image: Image.Image) -> Image.Image:
    """确保图片为 RGBA 模式.

    Args:
        image: PIL Image 对象

    Returns:
        RGBA 模式的图片
    """
    if image.mode != "RGBA":
        return image.convert("RGBA")
    return image


def add_solid_background(
    image: Image.Image,
    color: Tuple[int, int, int],
    maintain_size: bool = True,
) -> Image.Image:
    """为图片添加纯色背景.

    将透明背景的图片合成到纯色背景上。

    Args:
        image: PIL Image 对象（通常是 RGBA 模式）
        color: RGB 背景颜色元组
        maintain_size: 是否保持原始尺寸

    Returns:
        添加背景后的 RGB 模式图片
    """
    # 确保是 RGBA 模式以处理透明度
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # 创建背景
    background = Image.new("RGB", image.size, color)

    # 使用 alpha 通道作为蒙版合成
    background.paste(image, (0, 0), image.split()[3])

    return background


def create_background_preview(
    color: Tuple[int, int, int],
    size: Tuple[int, int] = (100, 100),
    with_checkerboard: bool = False,
) -> Image.Image:
    """创建背景颜色预览图.

    生成一个小型预览图，用于 UI 颜色选择器显示。

    Args:
        color: RGB 背景颜色元组
        size: 预览图尺寸
        with_checkerboard: 是否在背景下显示棋盘格（用于透明色预览）

    Returns:
        预览图片
    """
    if with_checkerboard:
        # 创建棋盘格背景
        preview = _create_checkerboard(size)
        # 叠加半透明颜色层
        color_layer = Image.new("RGBA", size, (*color, 200))
        preview.paste(color_layer, (0, 0), color_layer)
        return preview.convert("RGB")
    else:
        return Image.new("RGB", size, color)


def _create_checkerboard(
    size: Tuple[int, int],
    cell_size: int = 10,
    color1: Tuple[int, int, int] = (200, 200, 200),
    color2: Tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """创建棋盘格背景.

    Args:
        size: 图片尺寸
        cell_size: 格子大小
        color1: 颜色1
        color2: 颜色2

    Returns:
        棋盘格图片
    """
    w, h = size
    img = Image.new("RGB", size, color1)

    for y in range(0, h, cell_size):
        for x in range(0, w, cell_size):
            if (x // cell_size + y // cell_size) % 2 == 0:
                for dy in range(min(cell_size, h - y)):
                    for dx in range(min(cell_size, w - x)):
                        img.putpixel((x + dx, y + dy), color2)

    return img


def composite_with_background(
    foreground: Image.Image,
    background_color: Tuple[int, int, int],
    target_size: Optional[Tuple[int, int]] = None,
    position: str = "center",
) -> Image.Image:
    """将前景图合成到纯色背景上.

    支持自动调整尺寸和位置。

    Args:
        foreground: 前景图片（应为 RGBA 模式）
        background_color: 背景颜色
        target_size: 目标尺寸，为 None 则使用前景图尺寸
        position: 位置 ("center", "top-left", "top-right", "bottom-left", "bottom-right")

    Returns:
        合成后的图片
    """
    foreground = ensure_rgba(foreground)

    if target_size is None:
        target_size = foreground.size

    # 创建背景
    result = Image.new("RGB", target_size, background_color)

    # 如果前景尺寸与目标不同，需要计算位置
    fg_w, fg_h = foreground.size
    bg_w, bg_h = target_size

    # 计算位置
    if position == "center":
        x = (bg_w - fg_w) // 2
        y = (bg_h - fg_h) // 2
    elif position == "top-left":
        x, y = 0, 0
    elif position == "top-right":
        x = bg_w - fg_w
        y = 0
    elif position == "bottom-left":
        x = 0
        y = bg_h - fg_h
    elif position == "bottom-right":
        x = bg_w - fg_w
        y = bg_h - fg_h
    else:
        x = (bg_w - fg_w) // 2
        y = (bg_h - fg_h) // 2

    # 合成
    result.paste(foreground, (x, y), foreground.split()[3])

    return result


def apply_background_with_padding(
    image: Image.Image,
    background_color: Tuple[int, int, int],
    padding: Union[int, Tuple[int, int, int, int]],
) -> Image.Image:
    """为图片添加带边距的纯色背景.

    Args:
        image: PIL Image 对象
        background_color: 背景颜色
        padding: 边距，可以是单个整数（四边相同）或元组 (上, 右, 下, 左)

    Returns:
        添加背景和边距后的图片
    """
    image = ensure_rgba(image)

    # 解析边距
    if isinstance(padding, int):
        top = right = bottom = left = padding
    else:
        top, right, bottom, left = padding

    # 计算新尺寸
    orig_w, orig_h = image.size
    new_w = orig_w + left + right
    new_h = orig_h + top + bottom

    # 创建背景
    result = Image.new("RGB", (new_w, new_h), background_color)

    # 粘贴原图
    result.paste(image, (left, top), image.split()[3])

    return result
