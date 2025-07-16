# danmaku_models.py
import time
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QPixmap

# 导入Config类仅用于类型注解，避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from config_loader import Config


class DanmakuData:
    """
    存储从XML文件解析出的原始、静态的弹幕数据。
    这是一个纯数据类，在程序运行期间其属性不会改变。
    """
    def __init__(self, start_time: float, mode: int, text: str, color: QColor):
        self.start_time = start_time
        self.mode = mode
        self.text = text
        self.color = color

class ActiveDanmaku:
    def __init__(self):
        self.text: str = ""
        self.color: QColor = QColor()
        self.mode: int = 0
        self.width: int = 0
        self.position: QPointF = QPointF()
        self.speed: float = 0
        self.disappear_time: float = 0.0
        # 【新增】用于缓存渲染好的弹幕图片
        self.pixmap_cache: QPixmap | None = None

    def init(self, data: DanmakuData, y_pos: float, width: int, config: 'Config'):
        self.text = data.text
        self.color = data.color
        self.mode = data.mode
        self.width = width
        # 【新增】重置缓存
        self.pixmap_cache = None
        
        screen_width = config.screen_geometry.width()

        if self.mode == 1:
            self.position = QPointF(screen_width, y_pos)
            self.speed = config.scroll_speed
            self.disappear_time = float('inf')
        else:
            self.position = QPointF((screen_width - width) / 2, y_pos)
            self.speed = 0
            current_time = time.monotonic()
            self.disappear_time = current_time + (config.fixed_duration_ms / 1000)

    def is_active(self, current_time: float, delta_time: float) -> bool:
        """
        判断弹幕在当前帧是否仍然处于活动状态，并更新其位置。

        Args:
            current_time (float): 当前时间戳 (来自 time.monotonic())。
            delta_time (float): 距离上一帧的时间差（秒）。

        Returns:
            bool: 如果弹幕仍然活动（可见），返回True，否则返回False。
        """
        if self.mode == 1:
            self.position.setX(self.position.x() - self.speed * delta_time)
            # 如果弹幕的右边缘仍在屏幕左侧之外，则为活动状态
            return self.position.x() + self.width > 0
        else:
            return current_time < self.disappear_time