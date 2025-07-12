# danmaku_models.py
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor
import time
import random

class DanmakuData:
    """存储从XML加载的原始弹幕信息。"""
    def __init__(self, start_time: float, mode: int, text: str, color: QColor):
        self.start_time = start_time
        self.mode = mode
        self.text = text
        self.color = color

class ActiveDanmaku:
    """存储屏幕上活动弹幕的实时状态。"""
    def __init__(self, text: str, color: QColor, mode: int, y_pos: float, width: int, config):
        self.text = text
        self.color = color
        self.mode = mode
        self.width = width
        
        screen_width = config.screen_geometry.width()

        if self.mode_is_scroll():
            self.position = QPointF(screen_width, y_pos)
            self.speed = config.scroll_speed * (1 + len(text) / 20)
        else: # 顶部或底部弹幕
            self.position = QPointF((screen_width - width) / 2, y_pos)
            self.speed = 0
            self.creation_time = time.monotonic()
            self.disappear_time = self.creation_time + (config.fixed_duration_ms / 1000)

    def mode_is_scroll(self) -> bool:
        return self.mode in [1, 2, 3]