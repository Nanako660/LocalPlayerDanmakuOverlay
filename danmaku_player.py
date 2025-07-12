# danmaku_player.py (v8 - Fixed TypeError)
import sys
import random
import asyncio
import bisect
import xml.etree.ElementTree as ET
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QColor, QScreen, QPainter, QFont, QPen, QFontMetrics
import time

from media_monitor import MediaMonitor, MediaMonitorError

# --- 配置区 ---
DANMAKU_XML_FILE = '958151789.xml'
DANMAKU_FONT_SIZE = 24
DANMAKU_SPEED_PIXELS_PER_SEC = 200
DANMAKU_FIXED_DURATION_MS = 5000
MONITOR_REFRESH_RATE_MS = 100
ANIMATION_FPS = 60
TARGET_AUMID = "PotPlayerMini64.exe"

class Danmaku:
    """存储从XML加载的单条弹幕信息的数据类。"""
    def __init__(self, start_time: float, mode: int, text: str, color: QColor):
        self.start_time = start_time
        self.mode = mode
        self.text = text
        self.color = color

class ActiveDanmaku:
    """存储当前在屏幕上活动弹幕状态的数据类。"""
    def __init__(self, text: str, color: QColor, mode: int, y_pos: float, width: int):
        self.text = text
        self.color = color
        self.mode = mode
        self.width = width
        
        screen_width = QApplication.primaryScreen().geometry().width()

        if mode in [1, 2, 3]:
            self.position = QPointF(screen_width, y_pos)
            self.speed = DANMAKU_SPEED_PIXELS_PER_SEC * (1 + len(text) / 20)
        else:
            x_pos = (screen_width - width) / 2
            self.position = QPointF(x_pos, y_pos)
            self.speed = 0
            self.creation_time = time.monotonic()


class DanmakuPlayerWindow(QMainWindow):
    """
    功能完善的高性能弹幕播放器。
    """
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(QScreen.availableGeometry(QApplication.primaryScreen()))

        self._all_danmaku_data = []
        self._danmaku_start_times = []
        self._active_danmaku = []
        self._monitor = MediaMonitor()
        self._font = QFont("Arial", DANMAKU_FONT_SIZE, QFont.Weight.Bold)
        self._font_metrics = QFontMetrics(self._font)
        self._danmaku_idx = 0
        self._last_known_position = -1.0
        
        track_height = DANMAKU_FONT_SIZE + 5
        num_tracks = self.height() // track_height
        self._top_tracks = [0] * num_tracks
        self._bottom_tracks = [0] * num_tracks

        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._sync_and_spawn_danmaku)
        
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._update_danmaku_states)
        self._animation_timer.start(1000 // ANIMATION_FPS)

    def load_danmaku_from_xml(self, filepath: str) -> bool:
        """从 B站 XML 文件加载并解析弹幕。"""
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            for d_element in root.findall('d'):
                p_attr = d_element.get('p', '').split(',')
                if len(p_attr) > 4:
                    start_time = float(p_attr[0])
                    mode = int(p_attr[1])
                    text = d_element.text
                    color_decimal = int(p_attr[3])
                    color = QColor((color_decimal >> 16) & 255, (color_decimal >> 8) & 255, color_decimal & 255)
                    if text and mode in [1, 4, 5]:
                        self._all_danmaku_data.append(Danmaku(start_time, mode, text, color))
            self._all_danmaku_data.sort(key=lambda x: x.start_time)
            self._danmaku_start_times = [d.start_time for d in self._all_danmaku_data]
            print(f"成功加载 {len(self._all_danmaku_data)} 条弹幕。")
            return True
        except Exception as e:
            print(f"加载或解析弹幕文件时发生错误: {e}")
            return False

    def start_sync(self):
        """开始同步循环。"""
        print(f"开始同步 '{TARGET_AUMID}' 的播放进度...")
        self._sync_timer.start(MONITOR_REFRESH_RATE_MS)

    def _sync_and_spawn_danmaku(self):
        """同步播放器进度，并根据进度生成新的活动弹幕。"""
        try:
            info = asyncio.run(self._monitor.get_current_session_info())
        except Exception:
            info = None

        if not info or info.source_aumid != TARGET_AUMID or info.status != "PLAYING":
            return

        current_position = info.position.total_seconds()
        
        if current_position < self._last_known_position and (self._last_known_position - current_position > 2.0):
            print(f"\n检测到播放回退，重置弹幕索引...")
            self._danmaku_idx = bisect.bisect_left(self._danmaku_start_times, current_position)
            self._active_danmaku.clear()

        self._last_known_position = current_position
        
        while (self._danmaku_idx < len(self._all_danmaku_data) and
               self._all_danmaku_data[self._danmaku_idx].start_time <= current_position):
            
            self._spawn_new_danmaku(self._all_danmaku_data[self._danmaku_idx])
            self._danmaku_idx += 1

    def _spawn_new_danmaku(self, danmaku_data: Danmaku):
        """根据弹幕数据创建一条新的活动弹幕。"""
        text_width = self._font_metrics.horizontalAdvance(danmaku_data.text)
        
        y_pos = 0
        track_height = DANMAKU_FONT_SIZE + 5

        if danmaku_data.mode == 1: # 滚动弹幕
            y_pos = random.randint(0, self.height() - track_height)
        elif danmaku_data.mode == 5: # 顶部弹幕
            for i, track_time in enumerate(self._top_tracks):
                if time.monotonic() > track_time:
                    y_pos = i * track_height
                    self._top_tracks[i] = time.monotonic() + 0.5 
                    break
            else: return
        elif danmaku_data.mode == 4: # 底部弹幕
            for i, track_time in enumerate(self._bottom_tracks):
                if time.monotonic() > track_time:
                    y_pos = self.height() - (i + 1) * track_height
                    self._bottom_tracks[i] = time.monotonic() + 0.5
                    break
            else: return
        
        # ==================== 代码修正点 ====================
        # 此处调用 ActiveDanmaku 时补上了缺失的 mode 参数
        self._active_danmaku.append(ActiveDanmaku(
            danmaku_data.text, danmaku_data.color, danmaku_data.mode, y_pos, text_width
        ))
        # ====================================================

    def _update_danmaku_states(self):
        """更新所有活动弹幕的状态。"""
        delta_time = 1 / ANIMATION_FPS
        current_time = time.monotonic()
        
        still_active = []
        for d in self._active_danmaku:
            if d.mode == 1: # 滚动弹幕
                d.position.setX(d.position.x() - d.speed * delta_time)
                if d.position.x() + d.width > 0:
                    still_active.append(d)
            else: # 顶部/底部弹幕
                if current_time < d.creation_time + (DANMAKU_FIXED_DURATION_MS / 1000):
                    still_active.append(d)
        
        self._active_danmaku = still_active
        self.update()

    def paintEvent(self, event):
        """核心绘图事件。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self._font)
        
        for danmaku in self._active_danmaku:
            pen = QPen(QColor("black"), 2)
            painter.setPen(pen)
            x, y = danmaku.position.x(), danmaku.position.y()
            painter.drawText(QPointF(x - 1, y - 1), danmaku.text)
            painter.drawText(QPointF(x + 1, y - 1), danmaku.text)
            painter.drawText(QPointF(x - 1, y + 1), danmaku.text)
            painter.drawText(QPointF(x + 1, y + 1), danmaku.text)
            
            painter.setPen(danmaku.color)
            painter.drawText(danmaku.position, danmaku.text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player_window = DanmakuPlayerWindow()
    if player_window.load_danmaku_from_xml(DANMAKU_XML_FILE):
        player_window.show()
        player_window.start_sync()
        sys.exit(app.exec())
    else:
        sys.exit(1)