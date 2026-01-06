"""应用常量定义."""

from pathlib import Path

# ===================
# 应用信息
# ===================
APP_NAME = "电商图片批量AI合成与处理桌面工具"
APP_VERSION = "1.0.2-preview"
APP_AUTHOR = "Yang"
APP_URL = "https://jiuling.io"

# ===================
# 路径常量
# ===================
# 应用数据目录
APP_DATA_DIR = Path.home() / ".ecommerce-image-processor"

# 数据库文件路径
DATABASE_PATH = APP_DATA_DIR / "data.db"

# 日志目录
LOG_DIR = APP_DATA_DIR / "logs"

# 临时文件目录
TEMP_DIR = APP_DATA_DIR / "temp"

# ===================
# 图片处理常量
# ===================
# 最大队列大小
MAX_QUEUE_SIZE = 10

# 默认输出尺寸
DEFAULT_OUTPUT_WIDTH = 800
DEFAULT_OUTPUT_HEIGHT = 800
DEFAULT_OUTPUT_SIZE = (DEFAULT_OUTPUT_WIDTH, DEFAULT_OUTPUT_HEIGHT)

# 默认输出质量 (1-100)
DEFAULT_OUTPUT_QUALITY = 85

# 支持的图片格式
SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}

# 最大图片文件大小 (50MB)
MAX_IMAGE_FILE_SIZE = 50 * 1024 * 1024

# ===================
# 边框设置
# ===================
MIN_BORDER_WIDTH = 1
MAX_BORDER_WIDTH = 20
DEFAULT_BORDER_WIDTH = 2
DEFAULT_BORDER_COLOR = (0, 0, 0)  # 黑色

# ===================
# 背景设置
# ===================
DEFAULT_BACKGROUND_COLOR = (255, 255, 255)  # 白色

# ===================
# 文字设置
# ===================
DEFAULT_TEXT_POSITION = (10, 10)
DEFAULT_TEXT_FONT_SIZE = 14
DEFAULT_TEXT_COLOR = (0, 0, 0)  # 黑色

# ===================
# API 设置
# ===================
DEFAULT_API_BASE = "https://api.openai.com/v1"
API_TIMEOUT = 60  # 秒
API_MAX_RETRIES = 3
API_RETRY_DELAY = 1  # 秒

# ===================
# UI 设置
# ===================
WINDOW_MIN_WIDTH = 1024
WINDOW_MIN_HEIGHT = 768
THUMBNAIL_SIZE = (150, 150)
PREVIEW_SIZE = (400, 400)

# ===================
# 任务状态
# ===================
class TaskStatus:
    """任务状态常量."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
