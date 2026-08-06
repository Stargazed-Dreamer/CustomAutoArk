"""集中常量定义模块

将原先散落在 tool.py、core/task.py 等文件中的硬编码常量集中到此模块，
便于统一管理和跨平台适配。

现有代码仍保留各自的常量定义以保证向后兼容，新代码应优先从此模块导入。
迁移现有代码时可逐步将各文件的常量替换为 `from core.constants import ...`。

## 常量分类
- 路径：图片目录、数据文件
- 屏幕区域：公招标签/干员名/历史记录/凭证的区域（百分比坐标）
- 设备：默认端口
- 数据：星级优先级
"""

import os

# ==================== 路径常量 ====================

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 模板图片目录
IMG_PATH = os.path.join(PROJECT_ROOT, "img")

# 默认数据记录文件
RECORD_PATH = "#record.txt"

# 默认配置文件
CONFIG_PATH = "config.yaml"

# 默认日志目录
LOG_DIR = "log"


# ==================== 屏幕区域常量（百分比坐标 x1, y1, x2, y2） ====================

# 公招标签区域
REGION_TAG = (0.30, 0.47, 0.66, 0.70)

# 干员名区域
REGION_AGENT = (0.45, 0.67, 0.87, 0.85)

# 历史记录区域
REGION_HISTORY = (0.44, 0.27, 0.71, 0.91)

# 源石/凭证区域
REGION_CERTIFICATE = (0.776, 0.363, 1.0, 0.9)


# ==================== 设备常量 ====================

# 默认模拟器端口（MuMu12）
DEFAULT_PORT = 7555

# 默认设备地址
DEFAULT_DEVICE_ADDR = "127.0.0.1:7555"


# ==================== 星级常量 ====================

# 星级优先级排序（5星最高，1星最低，0星为支援机械）
STAR_PRIORITY = ['5', '4', '0', '3', '2', '1']

# 排除的高星级（不参与"低等级tag锁定"分析）
STAR_EXCEPTION = ["5"]

# 六星干员的内部星级标识（data.py 中 star='5' 对应游戏内6星）
SIX_STAR_INTERNAL = '5'


# ==================== OCR 常量 ====================

# OCR 最大重试次数
OCR_MAX_RETRIES = 3

# 历史记录中相邻干员的垂直间距（基于1080p高度）
HISTORY_LINE_DELTA_1080P = 60

# 历史记录间距容差（像素）
HISTORY_LINE_TOLERANCE = 10
