# debug_overlay.py
import time
import os
import psutil
from collections import deque
from PyQt6.QtGui import QPainter, QColor, QPen, QFont
from PyQt6.QtCore import Qt

class DebugOverlay:
    """一个独立的调试信息覆盖层。"""
    def __init__(self, parent_window, config, total_danmaku_count: int):
        self.parent = parent_window
        self.config = config
        self._paint_times = deque(maxlen=60)
        
        # 传入的静态信息
        self._total_count = total_danmaku_count
        
        # 需要在update_stats中更新的动态信息
        self._active_count = 0
        self._pool_free = 0
        
        # 需要内部定时更新的系统信息
        self._cpu_usage = 0.0
        self._mem_usage_mb = 0.0
        self._frame_count = 0
        
        self._font = QFont("Consolas", 12)
        
        # psutil 进程对象初始化
        try:
            self._proc = psutil.Process(os.getpid())
            self._proc.cpu_percent(interval=None) # 第一次调用以初始化
        except psutil.NoSuchProcess:
            self._proc = None

        # ... (pos_map 和 self._alignment 的代码无变化)
        pos_map = {
            'top_left': Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
            'top_right': Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
            'bottom_right': Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
            'bottom_left': Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft
        }
        self._alignment = pos_map.get(
            self.config.debug_info_position, 
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft
        )

    def update_stats(self, active_count: int, pool_free: int):
        """从外部（渲染器）更新与弹幕相关的统计数据。"""
        self._active_count = active_count
        self._pool_free = pool_free

    def _update_system_stats(self):
        """内部方法，用于更新CPU和内存等系统信息。"""
        if self._proc:
            self._cpu_usage = self._proc.cpu_percent(interval=None)
            self._mem_usage_mb = self._proc.memory_info().rss / (1024 * 1024)

    def paint(self, painter: QPainter):
        """执行实际的绘制操作。"""
        # 绘制红色边框
        painter.setPen(QPen(QColor("red"), 2))
        painter.drawRect(self.parent.rect().adjusted(1, 1, -1, -1))

        # --- 定时更新系统信息 ---
        # 每30帧（约0.5秒）更新一次CPU和内存，避免性能损耗
        self._frame_count += 1
        if self._frame_count >= 30:
            self._frame_count = 0
            self._update_system_stats()
            
        # 计算FPS
        now = time.monotonic()
        self._paint_times.append(now)
        if len(self._paint_times) > 1:
            elapsed = self._paint_times[-1] - self._paint_times[0]
            fps = (len(self._paint_times) - 1) / elapsed if elapsed > 0 else 0
        else:
            fps = 0
        
        # --- 组合所有调试信息 ---
        debug_text = (
            f"FPS: {fps:.1f}\n"
            f"CPU: {self._cpu_usage:.1f}%\n"
            f"Mem: {self._mem_usage_mb:.1f} MB\n"
            f"Total: {self._total_count}\n"
            f"Active: {self._active_count}\n"
            f"Pool Free: {self._pool_free}"
        )
        
        painter.setFont(self._font)
        painter.setPen(QColor("lime"))
        painter.drawText(
            self.parent.rect().adjusted(10, 10, -10, -10),
            int(self._alignment),
            debug_text
        )