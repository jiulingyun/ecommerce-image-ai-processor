"""文件工具函数模块.

提供文件和目录操作的工具函数。
"""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional, Set

from src.utils.constants import SUPPORTED_IMAGE_FORMATS, TEMP_DIR
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def ensure_directory(path: Path) -> Path:
    """确保目录存在.

    Args:
        path: 目录路径

    Returns:
        目录路径
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_extension(path: Path | str) -> str:
    """获取文件扩展名（小写）.

    Args:
        path: 文件路径

    Returns:
        小写扩展名（含点号）
    """
    return Path(path).suffix.lower()


def is_image_file(path: Path | str) -> bool:
    """检查是否为支持的图片文件.

    Args:
        path: 文件路径

    Returns:
        是否为图片文件
    """
    ext = get_file_extension(path)
    return ext in SUPPORTED_IMAGE_FORMATS


def get_file_size(path: Path | str) -> int:
    """获取文件大小（字节）.

    Args:
        path: 文件路径

    Returns:
        文件大小
    """
    return Path(path).stat().st_size


def list_image_files(
    directory: Path | str,
    recursive: bool = False,
) -> List[Path]:
    """列出目录中的图片文件.

    Args:
        directory: 目录路径
        recursive: 是否递归搜索

    Returns:
        图片文件路径列表
    """
    directory = Path(directory)
    if not directory.is_dir():
        return []

    files = []
    pattern = "**/*" if recursive else "*"

    for path in directory.glob(pattern):
        if path.is_file() and is_image_file(path):
            files.append(path)

    return sorted(files)


def generate_output_filename(
    input_path: Path | str,
    suffix: str = "_processed",
    output_dir: Optional[Path] = None,
    extension: Optional[str] = None,
) -> Path:
    """生成输出文件名.

    Args:
        input_path: 输入文件路径
        suffix: 文件名后缀
        output_dir: 输出目录
        extension: 输出扩展名

    Returns:
        输出文件路径
    """
    input_path = Path(input_path)
    stem = input_path.stem
    ext = extension or input_path.suffix

    output_name = f"{stem}{suffix}{ext}"

    if output_dir:
        return output_dir / output_name
    return input_path.parent / output_name


def create_temp_file(
    suffix: str = "",
    prefix: str = "img_",
    directory: Optional[Path] = None,
) -> Path:
    """创建临时文件.

    Args:
        suffix: 文件后缀
        prefix: 文件前缀
        directory: 临时目录

    Returns:
        临时文件路径
    """
    temp_dir = directory or ensure_directory(TEMP_DIR)
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=temp_dir)
    os.close(fd)
    return Path(path)


@contextmanager
def temp_file_context(
    suffix: str = "",
    prefix: str = "img_",
    delete: bool = True,
) -> Generator[Path, None, None]:
    """临时文件上下文管理器.

    自动清理临时文件。

    Args:
        suffix: 文件后缀
        prefix: 文件前缀
        delete: 是否在退出时删除

    Yields:
        临时文件路径
    """
    temp_path = create_temp_file(suffix=suffix, prefix=prefix)
    try:
        yield temp_path
    finally:
        if delete and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as e:
                logger.warning(f"删除临时文件失败: {temp_path}, {e}")


@contextmanager
def temp_directory_context(
    prefix: str = "img_",
    delete: bool = True,
) -> Generator[Path, None, None]:
    """临时目录上下文管理器.

    自动清理临时目录。

    Args:
        prefix: 目录前缀
        delete: 是否在退出时删除

    Yields:
        临时目录路径
    """
    temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=TEMP_DIR))
    try:
        yield temp_dir
    finally:
        if delete and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"删除临时目录失败: {temp_dir}, {e}")


def cleanup_temp_files(max_age_hours: int = 24) -> int:
    """清理过期的临时文件.

    Args:
        max_age_hours: 最大保留时间（小时）

    Returns:
        删除的文件数量
    """
    import time

    if not TEMP_DIR.exists():
        return 0

    deleted = 0
    now = time.time()
    max_age_seconds = max_age_hours * 3600

    for path in TEMP_DIR.iterdir():
        try:
            if now - path.stat().st_mtime > max_age_seconds:
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    shutil.rmtree(path)
                deleted += 1
        except Exception as e:
            logger.warning(f"清理临时文件失败: {path}, {e}")

    if deleted > 0:
        logger.info(f"清理了 {deleted} 个过期临时文件")

    return deleted


def copy_file(src: Path | str, dst: Path | str) -> Path:
    """复制文件.

    Args:
        src: 源文件路径
        dst: 目标文件路径

    Returns:
        目标文件路径
    """
    src = Path(src)
    dst = Path(dst)
    ensure_directory(dst.parent)
    shutil.copy2(src, dst)
    return dst


def move_file(src: Path | str, dst: Path | str) -> Path:
    """移动文件.

    Args:
        src: 源文件路径
        dst: 目标文件路径

    Returns:
        目标文件路径
    """
    src = Path(src)
    dst = Path(dst)
    ensure_directory(dst.parent)
    shutil.move(str(src), str(dst))
    return dst


def safe_delete(path: Path | str) -> bool:
    """安全删除文件或目录.

    Args:
        path: 文件或目录路径

    Returns:
        是否删除成功
    """
    path = Path(path)
    try:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        return True
    except Exception as e:
        logger.warning(f"删除失败: {path}, {e}")
        return False
