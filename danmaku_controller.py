# danmaku_controller.py
import asyncio
import bisect
import os
import psutil
import logging
from PyQt6.QtCore import QObject, QThread, pyqtSignal

# 从本地模块导入
from config_loader import get_config
from danmaku_parser import load_from_xml
from danmaku_renderer import DanmakuWindow
from danmaku_models import DanmakuData
from media_monitor import MediaMonitor, MediaMonitorError, get_foreground_window_aumid


class MediaSyncWorker(QObject):
    session_info_updated = pyqtSignal(object)

    def __init__(self, monitor: MediaMonitor):
        super().__init__()
        self.monitor = monitor
        self._is_running = True

    async def _loop_logic(self):
        logging.info("媒体同步工作线程循环已启动。")
        while self._is_running:
            try:
                info = await self.monitor.get_current_session_info()
                if not self._is_running: break
                self.session_info_updated.emit(info)
            except Exception as e:
                logging.error(f"在工作线程中获取媒体信息时出错: {e}")
                if not self._is_running: break
                self.session_info_updated.emit(None)
            
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
        logging.info("媒体同步工作线程循环已正常退出。")

    def run(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.main_task = self.loop.create_task(self._loop_logic())
            self.loop.run_until_complete(self.main_task)
        except Exception as e:
            logging.error(f"asyncio 事件循环中发生意外错误: {e}")

    def stop(self):
        logging.info("正在请求停止媒体同步工作线程...")
        self._is_running = False
        if hasattr(self, 'main_task') and self.main_task and not self.main_task.done():
            self.main_task.cancel()


class DanmakuController(QObject):
    def __init__(self, main_window_hwnd: int, monitor: MediaMonitor | None = None):
        super().__init__()
        self.config = get_config()
        self.main_window_hwnd = main_window_hwnd
        self.monitor = monitor or MediaMonitor()
        self._self_proc_name = psutil.Process(os.getpid()).name().lower()
        
        self.renderer: DanmakuWindow | None = None
        self.all_danmaku: list[DanmakuData] = []
        self.danmaku_start_times: list[float] = []

        self._danmaku_idx = 0
        self._last_known_position = -1.0
        self._is_running_flag = False
        
        self._worker_thread: QThread | None = None
        self._worker: MediaSyncWorker | None = None

    def _setup_worker(self):
        """创建并配置新的线程和工作者对象。"""
        logging.debug("正在设置新的工作线程和工作者对象...")
        self._worker_thread = QThread()
        self._worker = MediaSyncWorker(self.monitor)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.session_info_updated.connect(self._on_session_info_received)
        
        # 确保 QThread 对象在执行完毕后被删除
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)
        # 确保 Worker 对象在其所在的线程结束后被删除
        self._worker_thread.finished.connect(self._worker.deleteLater)


    def is_running(self) -> bool:
        return self._is_running_flag

    def start(self, danmaku_path: str):
        if self._is_running_flag:
            logging.warning("弹幕已经正在运行。")
            return

        logging.info("正在初始化弹幕...")
        self.all_danmaku = load_from_xml(danmaku_path)
        if not self.all_danmaku:
            logging.error(f"无法从 '{danmaku_path}' 加载或解析弹幕文件。")
            return
        self.danmaku_start_times = [d.start_time for d in self.all_danmaku]

        self._setup_worker()

        # 创建渲染器时，将弹幕总数传递进去
        self.renderer = DanmakuWindow(total_danmaku_count=len(self.all_danmaku))

        try:
            asyncio.run(self._discover_sessions())
        except Exception as e:
            logging.error(f"启动时发现媒体会话失败: {e}")

        self.renderer.show()
        
        self._worker_thread.start()
        
        self._is_running_flag = True
        logging.info("弹幕已启动。")

    def stop(self):
        if not self._is_running_flag:
            return

        if self._worker:
            self._worker.stop()
        if self._worker_thread and self._worker_thread.isRunning():
            self._worker_thread.quit()
            if not self._worker_thread.wait(500):
                logging.warning("工作线程未在500毫秒内正常停止。正在终止。")
                self._worker_thread.terminate()
                self._worker_thread.wait()

        self._worker_thread = None
        self._worker = None

        if self.renderer:
            self.renderer.close()
            self.renderer = None
        
        self.all_danmaku.clear()
        self.danmaku_start_times.clear()
        self._danmaku_idx = 0
        self._last_known_position = -1.0
        self._is_running_flag = False
        logging.info("弹幕已停止并清理资源。")

    def _on_session_info_received(self, info: object):
        if not self.renderer or not self._is_running_flag:
            return
            
        foreground_aumid = get_foreground_window_aumid()
        foreground_proc_name = foreground_aumid.lower() if foreground_aumid else ""
        is_player_foreground = self.config.target_aumid.lower() in foreground_proc_name
        is_gui_foreground = (foreground_proc_name == self._self_proc_name)

        if is_player_foreground:
            self.renderer.show()
            self.renderer.set_stay_on_top(True)
        elif is_gui_foreground:
            self.renderer.show()
            self.renderer.set_stay_on_top(False)
        else:
            self.renderer.hide()
            return

        if not info or info.source_aumid != self.config.target_aumid:
            self.renderer.pause()
            return

        if info.status == "PLAYING":
            self.renderer.resume()
        else:
            self.renderer.pause()
            return

        current_position = info.position.total_seconds()
        
        if abs(current_position - self._last_known_position) > 2.0:
            logging.info("检测到播放跳转，正在重置弹幕...")
            self.renderer.clear_danmaku()
            self._danmaku_idx = bisect.bisect_left(self.danmaku_start_times, current_position)

        self._last_known_position = current_position

        while (self._danmaku_idx < len(self.all_danmaku) and
               self.all_danmaku[self._danmaku_idx].start_time <= current_position):
            if self.renderer:
                self.renderer.add_danmaku(self.all_danmaku[self._danmaku_idx])
            self._danmaku_idx += 1
            
    async def _discover_sessions(self):
        logging.info("--- 正在发现活动媒体会话 ---")
        try:
            active_sessions = await self.monitor.list_sessions()
            if not active_sessions:
                logging.info("未找到活动媒体会话。")
            else:
                logging.info(f"当前目标 AUMID: '{self.config.target_aumid}'")
                logging.info("其他检测到的会话 (如有):")
                for sess in active_sessions:
                    logging.info(f"  - AUMID: {sess['aumid']:<50} | 标题: {sess['title']}")
        except MediaMonitorError as e:
            logging.error(f"发现媒体会话时出错: {e}")
        logging.info("-" * 45)