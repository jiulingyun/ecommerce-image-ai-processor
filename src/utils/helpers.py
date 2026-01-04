"""辅助函数模块.

提供各种通用辅助函数。
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def generate_uuid() -> str:
    """生成 UUID.

    Returns:
        UUID 字符串
    """
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """生成短 ID.

    Args:
        length: ID 长度

    Returns:
        短 ID 字符串
    """
    return uuid.uuid4().hex[:length]


def calculate_file_hash(file_path: Path, algorithm: str = "md5") -> str:
    """计算文件哈希值.

    Args:
        file_path: 文件路径
        algorithm: 哈希算法 (md5, sha256)

    Returns:
        哈希值字符串
    """
    hash_func = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小.

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        格式化后的大小字符串
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    """格式化时间间隔.

    Args:
        seconds: 秒数

    Returns:
        格式化后的时间字符串
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def get_timestamp() -> str:
    """获取当前时间戳字符串.

    Returns:
        格式化的时间戳
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_datetime_str(dt: Optional[datetime] = None) -> str:
    """获取日期时间字符串.

    Args:
        dt: 日期时间对象，默认为当前时间

    Returns:
        格式化的日期时间字符串
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def clamp(value: float, min_val: float, max_val: float) -> float:
    """限制值在指定范围内.

    Args:
        value: 原始值
        min_val: 最小值
        max_val: 最大值

    Returns:
        限制后的值
    """
    return max(min_val, min(max_val, value))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """RGB 转十六进制颜色.

    Args:
        r: 红色值 (0-255)
        g: 绿色值 (0-255)
        b: 蓝色值 (0-255)

    Returns:
        十六进制颜色字符串
    """
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """十六进制颜色转 RGB.

    Args:
        hex_color: 十六进制颜色字符串

    Returns:
        RGB 元组
    """
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """截断字符串.

    Args:
        s: 原始字符串
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的字符串
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def safe_filename(filename: str) -> str:
    """生成安全的文件名.

    移除或替换不安全的字符。

    Args:
        filename: 原始文件名

    Returns:
        安全的文件名
    """
    # 不安全字符
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, "_")
    return filename.strip()


def merge_dicts(base: dict, override: dict) -> dict:
    """深度合并字典.

    Args:
        base: 基础字典
        override: 覆盖字典

    Returns:
        合并后的字典
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result
