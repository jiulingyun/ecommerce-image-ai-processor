"""性能工具模块单元测试."""

import gc
import time
from pathlib import Path

import pytest
from PIL import Image

from src.utils.performance import (
    CacheStats,
    ImageCache,
    LargeImageHandler,
    MemoryInfo,
    MemoryMonitor,
    PerformanceMetrics,
    PerformanceTracker,
    cleanup_all,
    format_size,
    get_image_cache,
    get_memory_monitor,
    get_performance_tracker,
    memory_efficient,
    timed,
)


class TestPerformanceMetrics:
    """PerformanceMetrics 测试."""

    def test_default_values(self):
        """测试默认值."""
        metrics = PerformanceMetrics(operation="test")
        assert metrics.operation == "test"
        assert metrics.start_time == 0.0
        assert metrics.end_time == 0.0
        assert metrics.duration_ms == 0.0
        assert metrics.success is True
        assert metrics.error is None

    def test_metrics_with_values(self):
        """测试设置值."""
        metrics = PerformanceMetrics(
            operation="load_image",
            start_time=1000.0,
            end_time=1001.5,
            duration_ms=1500.0,
            memory_before=1000000,
            memory_after=2000000,
            memory_delta=1000000,
            success=True,
        )
        assert metrics.operation == "load_image"
        assert metrics.duration_ms == 1500.0
        assert metrics.memory_delta == 1000000


class TestCacheStats:
    """CacheStats 测试."""

    def test_default_values(self):
        """测试默认值."""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.current_size == 0
        assert stats.max_size == 0
        assert stats.item_count == 0

    def test_hit_rate(self):
        """测试命中率计算."""
        stats = CacheStats(hits=7, misses=3)
        assert stats.hit_rate == 70.0

    def test_hit_rate_zero_total(self):
        """测试总数为零时的命中率."""
        stats = CacheStats(hits=0, misses=0)
        assert stats.hit_rate == 0.0

    def test_usage_percent(self):
        """测试使用率计算."""
        stats = CacheStats(current_size=500, max_size=1000)
        assert stats.usage_percent == 50.0


class TestMemoryInfo:
    """MemoryInfo 测试."""

    def test_default_values(self):
        """测试默认值."""
        info = MemoryInfo()
        assert info.total == 0
        assert info.available == 0
        assert info.used == 0
        assert info.percent == 0.0
        assert info.process_memory == 0

    def test_is_low(self):
        """测试内存不足检测."""
        info = MemoryInfo(percent=85.0)
        assert info.is_low is True

        info_ok = MemoryInfo(percent=50.0)
        assert info_ok.is_low is False

    def test_is_critical(self):
        """测试内存临界检测."""
        info = MemoryInfo(percent=95.0)
        assert info.is_critical is True

        info_ok = MemoryInfo(percent=85.0)
        assert info_ok.is_critical is False


class TestImageCache:
    """ImageCache 测试."""

    @pytest.fixture
    def cache(self):
        """创建测试缓存."""
        return ImageCache(max_size_mb=10, max_items=5)

    @pytest.fixture
    def sample_image(self):
        """创建测试图片."""
        return Image.new("RGB", (100, 100), color="red")

    def test_init(self, cache):
        """测试初始化."""
        assert cache._max_size_bytes == 10 * 1024 * 1024
        assert cache._max_items == 5

    def test_put_and_get(self, cache, sample_image):
        """测试添加和获取."""
        cache.put("test.jpg", sample_image)
        result = cache.get("test.jpg")

        assert result is not None
        assert result.size == sample_image.size

    def test_get_miss(self, cache):
        """测试缓存未命中."""
        result = cache.get("nonexistent.jpg")
        assert result is None

    def test_hit_miss_count(self, cache, sample_image):
        """测试命中/未命中计数."""
        cache.put("test.jpg", sample_image)

        cache.get("test.jpg")  # hit
        cache.get("test.jpg")  # hit
        cache.get("missing.jpg")  # miss

        stats = cache.get_stats()
        assert stats.hits == 2
        assert stats.misses == 1

    def test_lru_eviction(self, cache, sample_image):
        """测试 LRU 淘汰."""
        # 添加超过限制的项
        for i in range(6):
            img = Image.new("RGB", (100, 100), color="blue")
            cache.put(f"image{i}.jpg", img)

        stats = cache.get_stats()
        assert stats.item_count <= 5

    def test_clear(self, cache, sample_image):
        """测试清空缓存."""
        cache.put("test.jpg", sample_image)
        cache.clear()

        stats = cache.get_stats()
        assert stats.item_count == 0
        assert stats.current_size == 0

    def test_invalidate(self, cache, sample_image):
        """测试失效缓存项."""
        cache.put("test.jpg", sample_image)
        result = cache.invalidate("test.jpg")

        assert result is True
        assert cache.get("test.jpg") is None

    def test_invalidate_nonexistent(self, cache):
        """测试失效不存在的项."""
        result = cache.invalidate("nonexistent.jpg")
        assert result is False

    def test_get_stats(self, cache, sample_image):
        """测试获取统计信息."""
        cache.put("test.jpg", sample_image)

        stats = cache.get_stats()
        assert isinstance(stats, CacheStats)
        assert stats.item_count == 1
        assert stats.current_size > 0


class TestMemoryMonitor:
    """MemoryMonitor 测试."""

    @pytest.fixture
    def monitor(self):
        """创建测试监控器."""
        return MemoryMonitor()

    def test_get_memory_info(self, monitor):
        """测试获取内存信息."""
        info = monitor.get_memory_info()

        assert isinstance(info, MemoryInfo)
        assert info.process_memory >= 0

    def test_check_memory(self, monitor):
        """测试检查内存."""
        is_ok, message = monitor.check_memory()

        assert isinstance(is_ok, bool)
        assert isinstance(message, str)

    def test_register_cleanup_callback(self, monitor):
        """测试注册清理回调."""
        called = []

        def callback():
            called.append(True)

        monitor.register_cleanup_callback(callback)
        monitor.cleanup()

        assert len(called) == 1

    def test_cleanup(self, monitor):
        """测试清理."""
        freed = monitor.cleanup()
        assert isinstance(freed, int)
        assert freed >= 0


class TestLargeImageHandler:
    """LargeImageHandler 测试."""

    @pytest.fixture
    def handler(self):
        """创建测试处理器."""
        return LargeImageHandler(max_pixels=10000, chunk_height=50)

    @pytest.fixture
    def small_image_path(self, tmp_path):
        """创建小图片."""
        path = tmp_path / "small.png"
        img = Image.new("RGB", (50, 50), color="green")
        img.save(path)
        return path

    @pytest.fixture
    def large_image_path(self, tmp_path):
        """创建大图片."""
        path = tmp_path / "large.png"
        img = Image.new("RGB", (200, 200), color="blue")
        img.save(path)
        return path

    def test_should_chunk_small(self, handler, small_image_path):
        """测试小图片不需要分块."""
        assert handler.should_chunk(small_image_path) is False

    def test_should_chunk_large(self, handler, large_image_path):
        """测试大图片需要分块."""
        assert handler.should_chunk(large_image_path) is True

    def test_get_image_info(self, handler, small_image_path):
        """测试获取图片信息."""
        info = handler.get_image_info(small_image_path)

        assert "size" in info
        assert "mode" in info
        assert "pixels" in info
        assert "needs_chunking" in info

    def test_load_chunks(self, handler, large_image_path):
        """测试分块加载."""
        chunks = handler.load_chunks(large_image_path)

        assert len(chunks) > 0
        for chunk, box in chunks:
            assert isinstance(chunk, Image.Image)
            assert len(box) == 4

    def test_process_large_image_small(self, handler, small_image_path, tmp_path):
        """测试处理小图片（不分块）."""
        output_path = tmp_path / "output.png"

        def processor(img):
            return img.convert("L")

        result = handler.process_large_image(
            small_image_path, processor, output_path
        )

        assert result.mode == "L"
        assert output_path.exists()

    def test_process_large_image_chunked(self, handler, large_image_path, tmp_path):
        """测试处理大图片（分块）."""
        output_path = tmp_path / "output_large.png"

        def processor(img):
            return img

        result = handler.process_large_image(
            large_image_path, processor, output_path
        )

        assert result is not None
        assert output_path.exists()


class TestPerformanceTracker:
    """PerformanceTracker 测试."""

    @pytest.fixture
    def tracker(self):
        """创建测试追踪器."""
        return PerformanceTracker(max_history=10)

    def test_track_success(self, tracker):
        """测试追踪成功操作."""
        with tracker.track("test_op"):
            time.sleep(0.01)

        stats = tracker.get_stats("test_op")
        assert stats["count"] == 1
        assert stats["success_rate"] == 100.0
        assert stats["avg_duration_ms"] > 0

    def test_track_failure(self, tracker):
        """测试追踪失败操作."""
        with pytest.raises(ValueError):
            with tracker.track("failing_op"):
                raise ValueError("test error")

        stats = tracker.get_stats("failing_op")
        assert stats["count"] == 1
        assert stats["success_rate"] == 0.0

    def test_get_stats_empty(self, tracker):
        """测试空统计."""
        stats = tracker.get_stats()
        assert stats["count"] == 0
        assert stats["avg_duration_ms"] == 0

    def test_get_recent(self, tracker):
        """测试获取最近记录."""
        for i in range(5):
            with tracker.track(f"op_{i}"):
                pass

        recent = tracker.get_recent(3)
        assert len(recent) == 3

    def test_clear(self, tracker):
        """测试清空记录."""
        with tracker.track("test"):
            pass

        tracker.clear()
        stats = tracker.get_stats()
        assert stats["count"] == 0

    def test_max_history(self, tracker):
        """测试最大历史限制."""
        for i in range(15):
            with tracker.track(f"op_{i}"):
                pass

        stats = tracker.get_stats()
        assert stats["count"] <= 10


class TestDecorators:
    """装饰器测试."""

    def test_timed_decorator(self):
        """测试计时装饰器."""

        @timed
        def slow_func():
            time.sleep(0.01)
            return "done"

        result = slow_func()
        assert result == "done"

    def test_memory_efficient_decorator(self):
        """测试内存优化装饰器."""

        @memory_efficient(cleanup_after=True)
        def allocate_func():
            data = [0] * 1000
            return len(data)

        result = allocate_func()
        assert result == 1000


class TestGlobalFunctions:
    """全局函数测试."""

    def test_get_image_cache(self):
        """测试获取图片缓存."""
        cache = get_image_cache()
        assert isinstance(cache, ImageCache)

        # 再次获取应该是同一实例
        cache2 = get_image_cache()
        assert cache is cache2

    def test_get_memory_monitor(self):
        """测试获取内存监控器."""
        monitor = get_memory_monitor()
        assert isinstance(monitor, MemoryMonitor)

    def test_get_performance_tracker(self):
        """测试获取性能追踪器."""
        tracker = get_performance_tracker()
        assert isinstance(tracker, PerformanceTracker)

    def test_cleanup_all(self):
        """测试清理所有."""
        # 应该不会抛出异常
        cleanup_all()

    def test_format_size(self):
        """测试格式化大小."""
        assert "B" in format_size(100)
        assert "KB" in format_size(1500)
        assert "MB" in format_size(2 * 1024 * 1024)
        assert "GB" in format_size(3 * 1024 * 1024 * 1024)
