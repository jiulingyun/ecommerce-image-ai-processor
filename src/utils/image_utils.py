"""图片工具函数模块.

提供图片读取、保存、格式转换等工具函数。
"""

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
