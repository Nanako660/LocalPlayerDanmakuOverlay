# danmaku_renderer.py
import logging
import time
import random
from collections import deque
from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.QtCore import Qt, QTimer, QPointF, QSize
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QFontMetrics, QPainterPath,
    QPainterPathStroker, QPixmap
)

from config_loader import get_config
from danmaku_models import DanmakuData, ActiveDanmaku
from debug_overlay import DebugOverlay

try:
    import win32gui
    import win32con
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


class DanmakuWindow(QMainWindow):
    # ======================= 核心修正点 =======================
    def __init__(self, total_danmaku_count: int, parent=None):
    # ========================================================
        super().__init__(parent)
        self.config = get_config()
        self.config.screen_geometry = QApplication.primaryScreen().geometry()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        if not self.config.debug:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.setGeometry(self.config.screen_geometry)
        self._font = QFont(self.config.font_name, self.config.font_size, QFont.Weight.Bold)
        self._font_metrics = QFontMetrics(self._font)

        pool_size = self.config.max_danmaku_count
        logging.info(f"Initializing object pool with size: {pool_size}")
        self._danmaku_pool = [ActiveDanmaku() for _ in range(pool_size)]
        self._free_danmaku = deque(self._danmaku_pool)
        self._active_danmaku = []

        font_height = self._font_metrics.height()
        line_spacing = int(font_height * self.config.line_spacing_ratio)
        self.track_height = font_height + line_spacing
        self.y_offset = self._font_metrics.ascent() + 5
        num_tracks = self.config.max_tracks
        self._scroll_tracks = [0] * num_tracks
        self._top_tracks = [0] * num_tracks
        self._bottom_tracks = [0] * num_tracks

        # ======================= 核心修正点 =======================
        # 创建 DebugOverlay 时，将弹幕总数传递进去
        if self.config.debug:
            self.debug_overlay = DebugOverlay(self, self.config, total_danmaku_count)
        else:
            self.debug_overlay = None
        # ========================================================
        
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self.update_states)
        self._animation_timer.start(1000 // 60)

        self._on_top_timer = QTimer(self)
        self._on_top_timer.timeout.connect(self._force_on_top_win32_if_needed)

    def set_stay_on_top(self, stay_on_top: bool):
        current_on_top_flag = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        if current_on_top_flag == stay_on_top:
            return

        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, stay_on_top)

        if stay_on_top and int(self.config.ontop_strategy) > 1:
            if not self._on_top_timer.isActive():
                self._on_top_timer.start(2000)
        else:
            if self._on_top_timer.isActive():
                self._on_top_timer.stop()
        self.show()

    def _force_on_top_win32_if_needed(self):
        strategy = int(self.config.ontop_strategy)
        if not PYWIN32_AVAILABLE or strategy < 2: return
        try:
            hwnd = int(self.winId())
            if strategy == 2:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0,0,0,0,
                                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
            elif strategy == 3:
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                if not (style & win32con.WS_EX_TOPMOST):
                    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0,0,0,0,
                                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
        except Exception as e:
            logging.error(f"Win32置顶错误: {e}")
            self._on_top_timer.stop()

    def add_danmaku(self, danmaku_data: DanmakuData):
        if not self._free_danmaku:
            return
        text_width = self._font_metrics.horizontalAdvance(danmaku_data.text)
        y_pos, track_found = self._find_track(danmaku_data, text_width)
        if not track_found: return
        danmaku_obj = self._free_danmaku.popleft()
        danmaku_obj.init(danmaku_data, y_pos, text_width, self.config)
        self._active_danmaku.append(danmaku_obj)

    def update_states(self):
        delta_time = 1 / 60
        current_time = time.monotonic()
        still_active = []
        for d in self._active_danmaku:
            if d.is_active(current_time, delta_time):
                still_active.append(d)
            else:
                self._free_danmaku.append(d)
        self._active_danmaku = still_active
        if self.debug_overlay:
            self.debug_overlay.update_stats(
                active_count=len(self._active_danmaku),
                pool_free=len(self._free_danmaku)
            )
        self.update()

    def _render_danmaku_to_pixmap(self, danmaku: ActiveDanmaku):
        stroke_offset = self.config.stroke_width
        bounding_rect = self._font_metrics.boundingRect(danmaku.text)
        pixmap_size = QSize(bounding_rect.width() + stroke_offset * 2, bounding_rect.height() + stroke_offset * 2)

        pixmap = QPixmap(pixmap_size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self._font)

        path = QPainterPath()
        path.addText(stroke_offset, self._font_metrics.ascent() + stroke_offset, self._font, danmaku.text)

        if self.config.stroke_width > 0:
            stroker = QPainterPathStroker()
            stroker.setWidth(self.config.stroke_width * 2)
            stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
            stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            stroke_path = stroker.createStroke(path)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.fillPath(stroke_path, QColor("black"))

        painter.fillPath(path, danmaku.color)
        painter.end()

        danmaku.pixmap_cache = pixmap

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(self.config.opacity)

        for danmaku in self._active_danmaku:
            if danmaku.pixmap_cache is None:
                self._render_danmaku_to_pixmap(danmaku)

            if danmaku.pixmap_cache:
                draw_pos = QPointF(danmaku.position.x() - self.config.stroke_width,
                                   danmaku.position.y() - self.config.stroke_width - self._font_metrics.ascent())
                painter.drawPixmap(draw_pos, danmaku.pixmap_cache)

        painter.setOpacity(1.0)

        if self.debug_overlay:
            self.debug_overlay.paint(painter)

    def clear_danmaku(self):
        self._free_danmaku.extend(self._active_danmaku)
        self._active_danmaku.clear()
        self.update()

    def pause(self):
        if self._animation_timer.isActive():
            self._animation_timer.stop()

    def resume(self):
        if not self._animation_timer.isActive():
            self._animation_timer.start(1000 // 60)

    def _find_track(self, danmaku_data, text_width):
        current_time = time.monotonic()
        mode = danmaku_data.mode
        
        if mode == 1:
            available_tracks = [i for i, t in enumerate(self._scroll_tracks) if current_time > t]
            if not available_tracks: return 0, False
            track_idx = random.choice(available_tracks)
            y_pos = (track_idx * self.track_height) + self.y_offset
            self._scroll_tracks[track_idx] = current_time + (text_width / self.config.scroll_speed) * 0.8
            return y_pos, True
        elif mode == 5:
            for i, track_time in enumerate(self._top_tracks):
                if current_time > track_time:
                    y_pos = (i * self.track_height) + self.y_offset
                    self._top_tracks[i] = current_time + (self.config.fixed_duration_ms / 1000)
                    return y_pos, True
            return 0, False
        elif mode == 4:
            for i, track_time in enumerate(self._bottom_tracks):
                if current_time > track_time:
                    y_pos = self.height() - ((i + 1) * self.track_height)
                    self._bottom_tracks[i] = current_time + (self.config.fixed_duration_ms / 1000)
                    return y_pos, True
            return 0, False
        return 0, False