# main.py
import sys
import asyncio
import bisect
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from config_loader import Config
from danmaku_parser import load_from_xml
from danmaku_renderer import DanmakuWindow
from media_monitor import MediaMonitor, MediaMonitorError, get_foreground_window_aumid
import win32gui

class Application:
    def __init__(self, config, all_danmaku, parent=None):
        self.config = config
        self.all_danmaku = all_danmaku
        self.danmaku_start_times = [d.start_time for d in self.all_danmaku]
        
        # The QApplication is now managed by the GUI
        self.renderer = DanmakuWindow(self.config, parent=parent)
        self.monitor = MediaMonitor()
        
        self.danmaku_idx = 0
        self.last_known_position = -1.0

        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_loop)

    def start(self):
        # Discover sessions asynchronously without blocking
        asyncio.run(self.discover_sessions())
        self.renderer.show()
        self.sync_timer.start(100)

    def stop(self):
        self.sync_timer.stop()
        self.renderer.close()
        print("弹幕已停止并关闭窗口。")

    async def discover_sessions(self):
        print("--- 正在发现所有活动媒体会话 ---")
        try:
            active_sessions = await self.monitor.list_sessions()
            if not active_sessions:
                print("未发现任何活动媒体会话。请打开播放器并播放媒体以进行识别。")
            else:
                print(f"当前配置的目标 AUMID: '{self.config.target_aumid}'")
                print("若需更改, 请修改 config.ini 文件。发现的可选ID如下:")
                for sess in active_sessions:
                    print(f"  - AUMID: {sess['aumid']:<50} | 标题: {sess['title']}")
        except MediaMonitorError as e:
            print(f"错误: {e}")
        print("-------------------------------------\n")
    
    def sync_loop(self):
        foreground_aumid = get_foreground_window_aumid()
        # Check if the target player or the GUI is in the foreground
        is_player_foreground = foreground_aumid and self.config.target_aumid.lower() in foreground_aumid.lower()
        is_gui_foreground = False
        try:
            # This requires the main GUI window to be the parent of the DanmakuWindow.
            # A bit of a hack to get the main window's handle.
            main_gui_window = self.renderer.parent()
            if main_gui_window:
                gui_hwnd = main_gui_window.winId()
                is_gui_foreground = win32gui.GetForegroundWindow() == gui_hwnd
        except AttributeError:
            # In case parent() or winId() is not what we expect.
            pass

        if not is_player_foreground and not is_gui_foreground:
            self.renderer.hide()
            return
        else:
            self.renderer.show()

        try:
            info = asyncio.run(self.monitor.get_current_session_info())
        except Exception:
            info = None

        if not info or info.source_aumid != self.config.target_aumid:
            self.renderer.pause()
            return

        if info.status == "PLAYING":
            self.renderer.resume()
        else:  # Covers PAUSED, STOPPED, etc.
            self.renderer.pause()
            return

        current_position = info.position.total_seconds()
        
        # 检测到进度条跳转（包括前进和后退）
        if abs(current_position - self.last_known_position) > 2.0:
            print(f"\n检测到播放进度跳跃，清空屏幕并重置弹幕索引...")
            self.renderer.clear_danmaku()
            self.danmaku_idx = bisect.bisect_left(self.danmaku_start_times, current_position)

        self.last_known_position = current_position

        while (self.danmaku_idx < len(self.all_danmaku) and
               self.all_danmaku[self.danmaku_idx].start_time <= current_position):
            
            self.renderer.add_danmaku(self.all_danmaku[self.danmaku_idx])
            self.danmaku_idx += 1


if __name__ == "__main__":
    # This file is no longer the main entry point.
    # The GUI is now launched from gui.py for development or a new entry script.
    print("请通过 gui.py 或新的主入口脚本启动程序。")
    # To run the GUI from here for convenience:
    from gui import MainWindow
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())