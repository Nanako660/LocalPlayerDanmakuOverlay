# main.py
import sys
import asyncio
import bisect
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from config_loader import Config
from danmaku_parser import load_from_xml
from danmaku_renderer import DanmakuWindow
from media_monitor import MediaMonitor, MediaMonitorError

class Application:
    def __init__(self, config, all_danmaku):
        self.config = config
        self.all_danmaku = all_danmaku
        self.danmaku_start_times = [d.start_time for d in self.all_danmaku]
        
        self.app = QApplication(sys.argv)
        self.renderer = DanmakuWindow(self.config)
        self.monitor = MediaMonitor()
        
        self.danmaku_idx = 0
        self.last_known_position = -1.0

        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.sync_loop)

    def run(self):
        # 首次运行时帮助用户发现 AUMID
        asyncio.run(self.discover_sessions())

        self.renderer.show()
        self.sync_timer.start(100) # 每100ms同步一次状态
        sys.exit(self.app.exec())

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
        try:
            info = asyncio.run(self.monitor.get_current_session_info())
        except Exception:
            info = None

        if not info or info.source_aumid != self.config.target_aumid or info.status != "PLAYING":
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
    config = Config()
    danmaku_data = load_from_xml('958151789.xml')
    
    if not danmaku_data:
        print("弹幕加载失败，程序退出。")
        sys.exit(1)
        
    app_instance = Application(config, danmaku_data)
    app_instance.run()