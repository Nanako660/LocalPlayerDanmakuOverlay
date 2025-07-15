# danmaku_models.py (v2 - Object Pool Support)
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
        # ==================== 对象池优化 START ====================
        # 构造函数现在直接调用新的init方法。
        # 这样无论是首次创建还是后续重用，逻辑都保持一致。
        self.init(text, color, mode, y_pos, width, config)
        # ==================== 对象池优化 END ======================

    # ==================== 对象池优化 START ====================
    # 1. 添加 init 方法
    # 这个方法是对象池优化的核心。它允许我们重用一个已经存在的 ActiveDanmaku 对象，
    # 用新的数据重新初始化它，而不是销毁旧的、创建新的。
    def init(self, text: str, color: QColor, mode: int, y_pos: float, width: int, config):
        """重置并初始化一个弹幕对象的状态。"""
        self.text = text
        self.color = color
        self.mode = mode
        self.width = width
        
        screen_width = config.screen_geometry.width()

        if self.mode_is_scroll():
            # 重置滚动弹幕的起始位置和速度
            self.position = QPointF(screen_width, y_pos)
            self.speed = config.scroll_speed
            # 确保旧的计时属性被清除或设为无效值
            self.disappear_time = float('inf') 
        else: # 顶部或底部弹幕
            # 重置固定弹幕的起始位置和生命周期
            self.position = QPointF((screen_width - width) / 2, y_pos)
            self.speed = 0
            # creation_time 和 disappear_time 必须在每次重用时都重新计算
            self.creation_time = time.monotonic()
            self.disappear_time = self.creation_time + (config.fixed_duration_ms / 1000)
    # ==================== 对象池优化 END ======================

    def mode_is_scroll(self) -> bool:
        return self.mode in [1, 2, 3]