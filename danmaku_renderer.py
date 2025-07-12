# danmaku_renderer.py (v20 - Opacity and Adaptive Spacing)
import sys
import random
import time
from collections import deque
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QFontMetrics, QScreen

try:
    import win32gui
    import win32con
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False
    print("警告: pywin32 库未安装，置顶策略2和3将不可用。")

from danmaku_models import ActiveDanmaku

class DanmakuWindow(QMainWindow):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.config.screen_geometry = QApplication.primaryScreen().geometry()
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        if not self.config.debug_enabled:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.setGeometry(self.config.screen_geometry)

        self._active_danmaku = []
        self._font = QFont(self.config.font_name, self.config.font_size, QFont.Weight.Bold)
        self._font_metrics = QFontMetrics(self._font)

        # ==================== 自适应行间距修复 ====================
        font_height = self._font_metrics.height()
        line_spacing = int(font_height * self.config.line_spacing_ratio)
        self.track_height = font_height + line_spacing
        self.y_offset = self._font_metrics.ascent() + 5
        # ========================================================
        
        num_tracks = self.config.max_tracks
        self._scroll_tracks = [0] * num_tracks
        self._top_tracks = [0] * num_tracks
        self._bottom_tracks = [0] * num_tracks

        self._paint_times = deque(maxlen=60)

        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self.update_states)
        self._animation_timer.start(1000 // 60)

        strategy = self.config.on_top_method
        print(f"当前置顶策略: {strategy}")

        if strategy != 0:
            if strategy in [2, 3] and not PYWIN32_AVAILABLE:
                print("警告: Win32 策略需要 'pywin32' 库。请运行 'pip install pywin32'。")
            else:
                self._on_top_timer = QTimer(self)
                if strategy == 1:
                    self._on_top_timer.timeout.connect(self._force_on_top_qt)
                elif strategy == 2:
                    self._on_top_timer.timeout.connect(self._force_on_top_win32_unconditional)
                elif strategy == 3:
                    self._on_top_timer.timeout.connect(self._check_and_force_on_top_win32)
                
                if self._on_top_timer.receivers(self._on_top_timer.timeout) > 0:
                    self._on_top_timer.start(2000)
    
    def add_danmaku(self, danmaku_data):
        if len(self._active_danmaku) >= self.config.max_on_screen:
            return

        text_width = self._font_metrics.horizontalAdvance(danmaku_data.text)
        y_pos = 0

        track_found = False
        if danmaku_data.mode == 1:
            track_list = self._scroll_tracks
            for _ in range(len(track_list) * 2): 
                track_idx = random.randrange(len(track_list))
                if time.monotonic() > track_list[track_idx]:
                    y_pos = (track_idx * self.track_height) + self.y_offset
                    track_list[track_idx] = time.monotonic() + (text_width / self.config.scroll_speed) * 0.8
                    track_found = True
                    break
            if not track_found: return
        elif danmaku_data.mode == 5:
            track_list = self._top_tracks
            for i, track_time in enumerate(track_list):
                if time.monotonic() > track_time:
                    y_pos = (i * self.track_height) + self.y_offset
                    track_list[i] = time.monotonic() + (self.config.fixed_duration_ms / 1000)
                    track_found = True
                    break
            if not track_found: return
        elif danmaku_data.mode == 4:
            track_list = self._bottom_tracks
            for i, track_time in enumerate(track_list):
                if time.monotonic() > track_time:
                    y_pos = self.height() - ((i + 1) * self.track_height)
                    track_list[i] = time.monotonic() + (self.config.fixed_duration_ms / 1000)
                    track_found = True
                    break
            if not track_found: return
            
        new_active_danmaku = ActiveDanmaku(danmaku_data.text, danmaku_data.color, danmaku_data.mode, y_pos, text_width, self.config)
        self._active_danmaku.append(new_active_danmaku)

    def update_states(self):
        delta_time = 1 / 60
        current_time = time.monotonic()
        still_active = [d for d in self._active_danmaku if self.is_danmaku_active(d, current_time, delta_time)]
        self._active_danmaku = still_active
        self.update()

    def is_danmaku_active(self, danmaku, current_time, delta_time):
        if danmaku.mode_is_scroll():
            danmaku.position.setX(danmaku.position.x() - danmaku.speed * delta_time)
            return danmaku.position.x() + danmaku.width > 0
        else:
            return current_time < danmaku.disappear_time

    def clear_danmaku(self):
        self._active_danmaku.clear()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self._font)

        # ==================== 透明度配置应用 ====================
        painter.setOpacity(self.config.danmaku_opacity)
        # ========================================================
        
        for danmaku in self._active_danmaku:
            pen = QPen(QColor("black"), self.config.stroke_width)
            painter.setPen(pen)
            p = danmaku.position
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0: continue
                    painter.drawText(QPointF(p.x() + dx, p.y() + dy), danmaku.text)
            
            painter.setPen(danmaku.color)
            painter.drawText(p, danmaku.text)
        
        # 恢复不透明度，确保Debug信息清晰
        painter.setOpacity(1.0)
        
        if self.config.debug_enabled:
            self._paint_debug_info(painter)

    def _paint_debug_info(self, painter: QPainter):
        painter.setPen(QPen(QColor("red"), 2))
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        now = time.monotonic()
        self._paint_times.append(now)
        if len(self._paint_times) > 1:
            elapsed = self._paint_times[-1] - self._paint_times[0]
            fps = (len(self._paint_times) - 1) / elapsed if elapsed > 0 else 0
        else:
            fps = 0
        debug_text = f"FPS: {fps:.1f}\nDanmaku: {len(self._active_danmaku)}"
        painter.setPen(QColor("lime"))
        debug_font = QFont("Consolas", 12)
        painter.setFont(debug_font)
        pos_map = {'top_left': Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                   'top_right': Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
                   'bottom_right': Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
                   'bottom_left': Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft}
        alignment = pos_map.get(self.config.debug_info_position, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        painter.drawText(self.rect().adjusted(10, 10, -10, -10), int(alignment), debug_text)

    def _force_on_top_qt(self):
        if self.isMinimized(): return
        self.raise_()
        self.activateWindow()

    def _force_on_top_win32_unconditional(self):
        if not PYWIN32_AVAILABLE: return
        try:
            win32gui.SetWindowPos(int(self.winId()), win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
        except Exception: pass

    def _check_and_force_on_top_win32(self):
        if not PYWIN32_AVAILABLE: return
        try:
            hwnd = int(self.winId())
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if not (style & win32con.WS_EX_TOPMOST):
                print("检测到窗口被覆盖，正在尝试恢复置顶...")
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
        except Exception: pass