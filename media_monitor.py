# media_monitor.py

"""
一个使用 Windows 系统媒体传输控件 (SMTC) 来监控媒体播放状态的模块。
依赖:
- winsdk: 请运行 `pip install winsdk` 来安装。
"""

import asyncio
from datetime import timedelta

import win32gui
import win32process
from psutil import Process

try:
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus
    )
except ImportError:
    # 定义一个虚拟的异常类，以便在导入失败时可以捕获
    class MediaMonitorError(Exception):
        pass
    
    # 抛出自定义异常，以便调用方可以优雅地处理
    raise MediaMonitorError("winsdk 库未安装或不完整。请运行 'pip install winsdk'。")


class MediaMonitorError(Exception):
    """模块自定义的异常基类。"""
    pass

class SessionInfo:
    """一个简单的数据类，用于存储媒体会话信息。"""
    def __init__(self, title, artist, status, position, duration, aumid):
        self.title = title
        self.artist = artist
        self.status = status
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
        h = ts // 3600
        m = (ts % 3600) // 60
        s = ts % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

def get_foreground_window_aumid():
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = Process(pid)
            # This is a simplification. A robust solution might need to check
            # the process executable path against a known list for the player.
            # AUMID is not directly retrievable from process info alone.
            # We will use process name as a proxy.
            return process.name()
    except Exception as e:
        print(f"Error getting foreground window info: {e}")
    return None

class MediaMonitor:
    """
    主监控类，提供方法来获取和筛选媒体会话信息。
    """
    def __init__(self):
        # 仅用于检查 winsdk 是否已成功导入
        if 'MediaManager' not in globals():
            raise MediaMonitorError("winsdk 库未正确加载。")

    async def _get_all_sessions(self):
        """(私有) 获取所有媒体会话的列表。"""
        try:
            manager = await MediaManager.request_async()
            return manager.get_sessions()
        except Exception as e:
            # 在某些系统状态下，请求可能会失败
            raise MediaMonitorError(f"无法获取媒体会话管理器: {e}")

    async def list_sessions(self) -> list:
        """
        列出所有当前活动的媒体会话的基本信息，主要用于发现目标程序的 AUMID。
        返回: 一个包含字典的列表，每个字典包含 'aumid' 和 'title'。
        """
        sessions = await self._get_all_sessions()
        session_list = []
        if not sessions:
            return session_list

        for session in sessions:
            try:
                info = await session.try_get_media_properties_async()
                if info.title: # 只列出有标题的会话
                    session_list.append({
                        "aumid": session.source_app_user_model_id,
                        "title": info.title
                    })
            except Exception:
                continue # 忽略无法获取信息的会话
        return session_list

    async def get_current_session_info(self) -> SessionInfo | None:
        """
        获取当前置于顶层的媒体会话的详细信息。
        返回: 一个 SessionInfo 对象，或在没有活动会话时返回 None。
        """
        try:
            manager = await MediaManager.request_async()
            session = manager.get_current_session()
            if session:
                return await self._get_session_details(session)
        except Exception:
            return None
        return None
        
    async def get_filtered_session_info(self, target_aumid: str) -> SessionInfo | None:
        """
        获取具有特定 AUMID 的媒体会话的详细信息。
        参数:
            target_aumid: 你想监控的程序的 App User Model ID (例如 "PotPlayer64")。
        返回:
            一个 SessionInfo 对象，或在找不到匹配会话时返回 None。
        """
        sessions = await self._get_all_sessions()
        if not sessions:
            return None

        for session in sessions:
            if session.source_app_user_model_id == target_aumid:
                return await self._get_session_details(session)
        
        return None # 没有找到匹配的会话

    async def _get_session_details(self, session) -> SessionInfo:
        """(私有) 从一个会话对象中提取完整的媒体信息。"""
        info = await session.try_get_media_properties_async()
        timeline = session.get_timeline_properties()
        status = PlaybackStatus(session.get_playback_info().playback_status).name

        return SessionInfo(
            title=info.title,
            artist=info.artist,
            status=status,
            position=timeline.position,
            duration=timeline.end_time,
            aumid=session.source_app_user_model_id
        )