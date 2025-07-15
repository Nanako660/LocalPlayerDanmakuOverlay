# media_monitor.py
import asyncio
from datetime import timedelta
import win32gui
import win32process
from psutil import Process

# 尝试导入 winsdk
try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus
    )
    WINSDK_AVAILABLE = True
except ImportError:
    WINSDK_AVAILABLE = False

class MediaMonitorError(Exception):
    """模块自定义的异常基类。"""
    pass

class SessionInfo:
    """一个简单的数据类，用于存储媒体会话的详细信息。"""
    def __init__(self, title, artist, status, position, duration, aumid):
        self.title = title
        self.artist = artist
        self.status = status.name # PlaybackStatus 枚举成员的名称
        self.position = position
        self.duration = duration
        self.source_aumid = aumid

    def __repr__(self):
        pos_str = self.format_time(self.position)
        dur_str = self.format_time(self.duration)
        return (f"<SessionInfo(aumid='{self.source_aumid}', status='{self.status}', "
                f"title='{self.title}', progress='{pos_str}/{dur_str}')>")

    @staticmethod
    def format_time(duration: timedelta) -> str:
        """将 timedelta 对象格式化为 HH:MM:SS"""
        ts = int(duration.total_seconds())
        return f"{ts // 3600:02d}:{(ts % 3600) // 60:02d}:{ts % 60:02d}"

def get_foreground_window_aumid() -> str | None:
    """
    获取当前前台窗口的进程名，作为AUMID的代理。
    注意：这只是一个近似方法，并非所有进程名都等于其AUMID。

    Returns:
        str | None: 进程名（如 "PotPlayerMini64.exe"），如果获取失败则返回None。
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return Process(pid).name()
    except Exception:
        return None
    return None

class MediaMonitor:
    """
    主监控类，使用Windows SMTC API来获取和筛选媒体会话信息。
    """
    def __init__(self):
        """
        初始化媒体监视器。
        如果 winsdk 不可用，将引发异常。

        Example:
            # try:
            #     monitor = MediaMonitor()
            # except MediaMonitorError as e:
            #     print(e)
        """
        if not WINSDK_AVAILABLE:
            raise MediaMonitorError("winsdk 库未安装或不完整。请运行 'pip install winsdk'。")

    async def list_sessions(self) -> list[dict]:
        """
        异步列出所有当前活动的媒体会话的基本信息。
        主要用于帮助用户发现目标播放器的 AUMID。

        Returns:
            list[dict]: 一个包含字典的列表，每个字典包含 'aumid' 和 'title'。
        
        Example:
            # monitor = MediaMonitor()
            # sessions = await monitor.list_sessions()
            # for s in sessions:
            #     print(f"AUMID: {s['aumid']}, Title: {s['title']}")
        """
        manager = await MediaManager.request_async()
        sessions = manager.get_sessions()
        session_list = []
        for session in sessions:
            try:
                info = await session.try_get_media_properties_async()
                if info.title:
                    session_list.append({
                        "aumid": session.source_app_user_model_id,
                        "title": info.title
                    })
            except Exception:
                continue
        return session_list

    async def get_current_session_info(self) -> SessionInfo | None:
        """
        异步获取当前SMTC托管的媒体会话的详细信息。

        Returns:
            SessionInfo | None: 一个 SessionInfo 对象，或在没有活动会话时返回 None。
        
        Example:
            # monitor = MediaMonitor()
            # info = await monitor.get_current_session_info()
            # if info:
            #     print(info.title, info.status, info.position)
        """
        try:
            manager = await MediaManager.request_async()
            session = manager.get_current_session()
            if session:
                return await self._get_session_details(session)
        except Exception:
            return None
        return None

    async def _get_session_details(self, session) -> SessionInfo:
        """从一个会话对象中异步提取完整的媒体信息。"""
        info = await session.try_get_media_properties_async()
        timeline = session.get_timeline_properties()
        playback_info = session.get_playback_info()
        return SessionInfo(
            title=info.title, artist=info.artist,
            status=PlaybackStatus(playback_info.playback_status),
            position=timeline.position, duration=timeline.end_time,
            aumid=session.source_app_user_model_id
        )