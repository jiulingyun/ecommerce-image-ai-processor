"""性能监控和内存管理工具模块.

提供图片处理的性能优化功能，包括：
- 图片缓存管理
- 内存使用监控
- 大图片分块处理
- 性能统计

Features:
    - LRU 图片缓存
    - 内存使用监控与自动清理
    - 大图片分块加载
    - 处理时间统计
"""

from __future__ import annotations

import gc
import os
import sys
import time
import threading
import weakref
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Union

from PIL import Image

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# 类型变量
T = TypeVar("T")

# 默认配置
DEFAULT_CACHE_SIZE_MB = 256  # 默认缓存大小 256MB
DEFAULT_MAX_IMAGE_PIXELS = 50_000_000  # 最大图片像素数 (50 百万)
DEFAULT_MEMORY_WARNING_THRESHOLD = 0.8  # 内存警告阈值 (80%)
DEFAULT_MEMORY_CRITICAL_THRESHOLD = 0.9  # 内存临界阈值 (90%)
CHUNK_SIZE = 1024 * 1024  # 分块大小 1MB


@dataclass
class PerformanceMetrics:
    """性能指标数据类.

    Attributes:
        operation: 操作名称
        start_time: 开始时间
        end_time: 结束时间
        duration_ms: 持续时间（毫秒）
        memory_before: 操作前内存使用（字节）
        memory_after: 操作后内存使用（字节）
        memory_delta: 内存变化（字节）
        success: 是否成功
        error: 错误信息
    """

    operation: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    memory_before: int = 0
    memory_after: int = 0
    memory_delta: int = 0
    success: bool = True
    error: Optional[str] = None


@dataclass
class CacheStats:
    """缓存统计信息.

    Attributes:
        hits: 命中次数
        misses: 未命中次数
        current_size: 当前缓存大小（字节）
        max_size: 最大缓存大小（字节）
        item_count: 缓存项数量
    """

    hits: int = 0
    misses: int = 0
    current_size: int = 0
    max_size: int = 0
    item_count: int = 0

    @property
    def hit_rate(self) -> float:
        """缓存命中率."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    @property
    def usage_percent(self) -> float:
        """缓存使用率."""
        return (self.current_size / self.max_size * 100) if self.max_size > 0 else 0.0


@dataclass
class MemoryInfo:
    """内存信息.

    Attributes:
        total: 总内存（字节）
        available: 可用内存（字节）
        used: 已用内存（字节）
        percent: 使用百分比
        process_memory: 当前进程内存（字节）
    """

    total: int = 0
    available: int = 0
    used: int = 0
    percent: float = 0.0
    process_memory: int = 0

    @property
    def is_low(self) -> bool:
        """内存是否不足."""
        return self.percent >= DEFAULT_MEMORY_WARNING_THRESHOLD * 100

    @property
    def is_critical(self) -> bool:
        """内存是否临界."""
        return self.percent >= DEFAULT_MEMORY_CRITICAL_THRESHOLD * 100


class ImageCache:
    """图片 LRU 缓存.

    使用 LRU (最近最少使用) 策略管理图片缓存，
    支持基于内存大小的自动淘汰。

    Attributes:
        max_size_bytes: 最大缓存大小（字节）
        max_items: 最大缓存项数量

    Example:
        >>> cache = ImageCache(max_size_mb=128)
        >>> cache.put("image1.jpg", image)
        >>> cached_image = cache.get("image1.jpg")
        >>> stats = cache.get_stats()
    """

    def __init__(
        self,
        max_size_mb: int = DEFAULT_CACHE_SIZE_MB,
        max_items: int = 100,
    ) -> None:
        """初始化缓存.

        Args:
            max_size_mb: 最大缓存大小（MB）
            max_items: 最大缓存项数量
        """
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._max_items = max_items
        self._cache: OrderedDict[str, tuple[Image.Image, int]] = OrderedDict()
        self._current_size = 0
        self._hits = 0
        self._misses = 0
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Image.Image]:
        """获取缓存的图片.

        Args:
            key: 缓存键（通常是文件路径）

        Returns:
            缓存的图片，如果不存在返回 None
        """
        with self._lock:
            if key in self._cache:
                # 移到末尾（最近使用）
                self._cache.move_to_end(key)
                self._hits += 1
                image, _ = self._cache[key]
                # 返回副本以避免意外修改
                return image.copy()
            self._misses += 1
            return None

    def put(self, key: str, image: Image.Image) -> None:
        """添加图片到缓存.

        Args:
            key: 缓存键
            image: 要缓存的图片
        """
        with self._lock:
            # 估算图片内存大小
            image_size = self._estimate_image_size(image)

            # 如果单个图片超过最大缓存大小，不缓存
            if image_size > self._max_size_bytes:
                logger.debug(f"图片太大，不缓存: {key} ({image_size} bytes)")
                return

            # 如果已存在，先移除
            if key in self._cache:
                self._remove(key)

            # 清理空间
            while (
                self._current_size + image_size > self._max_size_bytes
                or len(self._cache) >= self._max_items
            ):
                if not self._cache:
                    break
                # 移除最老的项
                oldest_key = next(iter(self._cache))
                self._remove(oldest_key)

            # 添加到缓存
            self._cache[key] = (image.copy(), image_size)
            self._current_size += image_size

    def _remove(self, key: str) -> None:
        """移除缓存项."""
        if key in self._cache:
            _, size = self._cache.pop(key)
            self._current_size -= size

    def clear(self) -> None:
        """清空缓存."""
        with self._lock:
            self._cache.clear()
            self._current_size = 0

    def invalidate(self, key: str) -> bool:
        """使缓存项失效.

        Args:
            key: 缓存键

        Returns:
            是否成功移除
        """
        with self._lock:
            if key in self._cache:
                self._remove(key)
                return True
            return False

    def get_stats(self) -> CacheStats:
        """获取缓存统计信息."""
        with self._lock:
            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                current_size=self._current_size,
                max_size=self._max_size_bytes,
                item_count=len(self._cache),
            )

    def _estimate_image_size(self, image: Image.Image) -> int:
        """估算图片内存大小."""
        # 基于像素数和模式估算
        width, height = image.size
        pixels = width * height

        # 根据模式确定每像素字节数
        mode_bytes = {
            "1": 0.125,  # 1位黑白
            "L": 1,  # 8位灰度
            "P": 1,  # 8位调色板
            "RGB": 3,  # 24位真彩色
            "RGBA": 4,  # 32位带透明
            "CMYK": 4,  # 32位 CMYK
            "YCbCr": 3,  # 24位
            "LAB": 3,  # 24位
            "HSV": 3,  # 24位
            "I": 4,  # 32位整数
            "F": 4,  # 32位浮点
        }
        bytes_per_pixel = mode_bytes.get(image.mode, 4)

        return int(pixels * bytes_per_pixel)


class MemoryMonitor:
    """内存使用监控器.

    监控应用程序内存使用情况，提供自动清理和警告机制。

    Example:
        >>> monitor = MemoryMonitor()
        >>> info = monitor.get_memory_info()
        >>> if info.is_critical:
        ...     monitor.cleanup()
    """

    def __init__(
        self,
        warning_threshold: float = DEFAULT_MEMORY_WARNING_THRESHOLD,
        critical_threshold: float = DEFAULT_MEMORY_CRITICAL_THRESHOLD,
    ) -> None:
        """初始化监控器.

        Args:
            warning_threshold: 警告阈值（0-1）
            critical_threshold: 临界阈值（0-1）
        """
        self._warning_threshold = warning_threshold
        self._critical_threshold = critical_threshold
        self._cleanup_callbacks: list[Callable[[], None]] = []

    def get_memory_info(self) -> MemoryInfo:
        """获取当前内存信息."""
        try:
            import psutil

            vm = psutil.virtual_memory()
            process = psutil.Process(os.getpid())

            return MemoryInfo(
                total=vm.total,
                available=vm.available,
                used=vm.used,
                percent=vm.percent,
                process_memory=process.memory_info().rss,
            )
        except ImportError:
            # psutil 不可用，使用基本方法
            return self._get_basic_memory_info()

    def _get_basic_memory_info(self) -> MemoryInfo:
        """获取基本内存信息（不依赖 psutil）."""
        # 获取进程内存
        process_memory = 0
        try:
            if sys.platform == "darwin":
                # macOS
                import subprocess

                pid = os.getpid()
                result = subprocess.run(
                    ["ps", "-o", "rss=", "-p", str(pid)],
                    capture_output=True,
                    text=True,
                )
                process_memory = int(result.stdout.strip()) * 1024
            elif sys.platform.startswith("linux"):
                # Linux
                with open(f"/proc/{os.getpid()}/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            process_memory = int(line.split()[1]) * 1024
                            break
        except Exception:
            pass

        return MemoryInfo(
            total=0,
            available=0,
            used=0,
            percent=0.0,
            process_memory=process_memory,
        )

    def check_memory(self) -> tuple[bool, str]:
        """检查内存状态.

        Returns:
            (is_ok, message) 元组
        """
        info = self.get_memory_info()

        if info.is_critical:
            return False, f"内存使用临界: {info.percent:.1f}%"
        elif info.is_low:
            return True, f"内存使用警告: {info.percent:.1f}%"
        else:
            return True, f"内存使用正常: {info.percent:.1f}%"

    def register_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """注册清理回调函数.

        Args:
            callback: 清理时调用的函数
        """
        self._cleanup_callbacks.append(callback)

    def cleanup(self) -> int:
        """执行内存清理.

        Returns:
            释放的内存大小（字节）
        """
        info_before = self.get_memory_info()

        # 调用注册的清理回调
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                logger.warning(f"清理回调执行失败: {e}")

        # 强制垃圾回收
        gc.collect()

        info_after = self.get_memory_info()
        freed = info_before.process_memory - info_after.process_memory

        logger.info(f"内存清理完成，释放: {freed / 1024 / 1024:.2f} MB")
        return max(0, freed)

    def auto_cleanup_if_needed(self) -> bool:
        """如果需要则自动清理.

        Returns:
            是否执行了清理
        """
        info = self.get_memory_info()
        if info.is_critical:
            logger.warning("内存使用临界，执行自动清理")
            self.cleanup()
            return True
        return False


class LargeImageHandler:
    """大图片处理器.

    处理超大图片时使用分块加载，避免内存溢出。

    Example:
        >>> handler = LargeImageHandler()
        >>> # 检查是否需要分块处理
        >>> if handler.should_chunk(image_path):
        ...     for chunk in handler.load_chunks(image_path):
        ...         process(chunk)
    """

    def __init__(
        self,
        max_pixels: int = DEFAULT_MAX_IMAGE_PIXELS,
        chunk_height: int = 1000,
    ) -> None:
        """初始化处理器.

        Args:
            max_pixels: 最大像素数
            chunk_height: 分块高度
        """
        self._max_pixels = max_pixels
        self._chunk_height = chunk_height

    def should_chunk(self, image_or_path: Union[Image.Image, Path, str]) -> bool:
        """判断是否需要分块处理.

        Args:
            image_or_path: 图片对象或路径

        Returns:
            是否需要分块
        """
        if isinstance(image_or_path, Image.Image):
            width, height = image_or_path.size
        else:
            with Image.open(image_or_path) as img:
                width, height = img.size

        return width * height > self._max_pixels

    def get_image_info(self, path: Union[Path, str]) -> dict:
        """获取图片信息（不加载完整图片）.

        Args:
            path: 图片路径

        Returns:
            图片信息字典
        """
        with Image.open(path) as img:
            return {
                "size": img.size,
                "mode": img.mode,
                "format": img.format,
                "pixels": img.size[0] * img.size[1],
                "needs_chunking": self.should_chunk(img),
            }

    def load_chunks(
        self, path: Union[Path, str]
    ) -> list[tuple[Image.Image, tuple[int, int, int, int]]]:
        """分块加载图片.

        Args:
            path: 图片路径

        Yields:
            (chunk_image, (left, top, right, bottom)) 元组
        """
        chunks = []
        with Image.open(path) as img:
            width, height = img.size

            for top in range(0, height, self._chunk_height):
                bottom = min(top + self._chunk_height, height)
                box = (0, top, width, bottom)
                chunk = img.crop(box).copy()
                chunks.append((chunk, box))

        return chunks

    def process_large_image(
        self,
        path: Union[Path, str],
        processor: Callable[[Image.Image], Image.Image],
        output_path: Optional[Union[Path, str]] = None,
    ) -> Image.Image:
        """处理大图片.

        如果图片较小，直接处理；否则分块处理后合并。

        Args:
            path: 输入图片路径
            processor: 处理函数
            output_path: 输出路径

        Returns:
            处理后的图片
        """
        if not self.should_chunk(path):
            # 小图片直接处理
            with Image.open(path) as img:
                img.load()
                result = processor(img)
                if output_path:
                    result.save(output_path)
                return result

        # 大图片分块处理
        logger.info(f"大图片分块处理: {path}")

        with Image.open(path) as img:
            width, height = img.size
            mode = img.mode

        # 创建结果图片
        result = Image.new(mode, (width, height))

        for chunk, (left, top, right, bottom) in self.load_chunks(path):
            processed_chunk = processor(chunk)
            result.paste(processed_chunk, (left, top))
            # 释放内存
            del chunk
            del processed_chunk
            gc.collect()

        if output_path:
            result.save(output_path)

        return result


class PerformanceTracker:
    """性能追踪器.

    追踪和统计操作性能，用于性能分析和优化。

    Example:
        >>> tracker = PerformanceTracker()
        >>> with tracker.track("load_image"):
        ...     image = load_image(path)
        >>> stats = tracker.get_stats()
    """

    def __init__(self, max_history: int = 1000) -> None:
        """初始化追踪器.

        Args:
            max_history: 最大历史记录数
        """
        self._max_history = max_history
        self._history: list[PerformanceMetrics] = []
        self._lock = threading.Lock()
        self._memory_monitor = MemoryMonitor()

    @contextmanager
    def track(self, operation: str):
        """追踪操作性能.

        Args:
            operation: 操作名称

        Yields:
            PerformanceMetrics 对象
        """
        metrics = PerformanceMetrics(operation=operation)
        metrics.start_time = time.time()
        metrics.memory_before = self._memory_monitor.get_memory_info().process_memory

        try:
            yield metrics
            metrics.success = True
        except Exception as e:
            metrics.success = False
            metrics.error = str(e)
            raise
        finally:
            metrics.end_time = time.time()
            metrics.duration_ms = (metrics.end_time - metrics.start_time) * 1000
            metrics.memory_after = self._memory_monitor.get_memory_info().process_memory
            metrics.memory_delta = metrics.memory_after - metrics.memory_before

            self._record(metrics)

    def _record(self, metrics: PerformanceMetrics) -> None:
        """记录性能指标."""
        with self._lock:
            self._history.append(metrics)
            # 保持历史记录在限制内
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

    def get_stats(
        self, operation: Optional[str] = None
    ) -> dict[str, Any]:
        """获取性能统计.

        Args:
            operation: 操作名称过滤

        Returns:
            统计信息字典
        """
        with self._lock:
            history = self._history
            if operation:
                history = [m for m in history if m.operation == operation]

            if not history:
                return {
                    "count": 0,
                    "avg_duration_ms": 0,
                    "min_duration_ms": 0,
                    "max_duration_ms": 0,
                    "total_duration_ms": 0,
                    "success_rate": 0,
                    "avg_memory_delta": 0,
                }

            durations = [m.duration_ms for m in history]
            memory_deltas = [m.memory_delta for m in history]
            successes = sum(1 for m in history if m.success)

            return {
                "count": len(history),
                "avg_duration_ms": sum(durations) / len(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "total_duration_ms": sum(durations),
                "success_rate": successes / len(history) * 100,
                "avg_memory_delta": sum(memory_deltas) / len(memory_deltas),
            }

    def get_recent(self, count: int = 10) -> list[PerformanceMetrics]:
        """获取最近的性能记录.

        Args:
            count: 记录数量

        Returns:
            性能记录列表
        """
        with self._lock:
            return list(reversed(self._history[-count:]))

    def clear(self) -> None:
        """清空历史记录."""
        with self._lock:
            self._history.clear()


def timed(func: Callable[..., T]) -> Callable[..., T]:
    """计时装饰器.

    用于追踪函数执行时间。

    Example:
        >>> @timed
        ... def slow_function():
        ...     time.sleep(1)
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        start = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed = (time.time() - start) * 1000
            logger.debug(f"{func.__name__} 执行时间: {elapsed:.2f}ms")

    return wrapper


def memory_efficient(
    cleanup_after: bool = True,
    max_memory_mb: Optional[int] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """内存优化装饰器.

    确保函数执行后进行内存清理。

    Args:
        cleanup_after: 执行后是否清理
        max_memory_mb: 最大内存限制（MB）

    Example:
        >>> @memory_efficient(cleanup_after=True)
        ... def process_images(images):
        ...     for img in images:
        ...         process(img)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            monitor = MemoryMonitor()

            # 检查内存限制
            if max_memory_mb:
                info = monitor.get_memory_info()
                if info.process_memory > max_memory_mb * 1024 * 1024:
                    logger.warning(f"内存使用超过限制，执行清理")
                    gc.collect()

            try:
                return func(*args, **kwargs)
            finally:
                if cleanup_after:
                    gc.collect()

        return wrapper

    return decorator


# 全局实例
_image_cache: Optional[ImageCache] = None
_memory_monitor: Optional[MemoryMonitor] = None
_performance_tracker: Optional[PerformanceTracker] = None


def get_image_cache(max_size_mb: int = DEFAULT_CACHE_SIZE_MB) -> ImageCache:
    """获取图片缓存单例."""
    global _image_cache
    if _image_cache is None:
        _image_cache = ImageCache(max_size_mb=max_size_mb)
    return _image_cache


def get_memory_monitor() -> MemoryMonitor:
    """获取内存监控器单例."""
    global _memory_monitor
    if _memory_monitor is None:
        _memory_monitor = MemoryMonitor()
    return _memory_monitor


def get_performance_tracker() -> PerformanceTracker:
    """获取性能追踪器单例."""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
    return _performance_tracker


def cleanup_all() -> None:
    """清理所有缓存和执行垃圾回收."""
    global _image_cache

    if _image_cache is not None:
        _image_cache.clear()

    gc.collect()
    logger.info("已清理所有缓存")


def format_size(size_bytes: int) -> str:
    """格式化字节大小为可读字符串."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"
