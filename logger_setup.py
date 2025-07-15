# logger_setup.py
import logging
import os
import sys
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

# 定义日志信号，用于与GUI通信
class LogSignals(QObject):
    log_message = pyqtSignal(str)

# 自定义日志处理器，将日志记录发送到GUI
class QtLogHandler(logging.Handler):
    def __init__(self, signals: LogSignals):
        super().__init__()
        self.signals = signals

    def emit(self, record):
        try:
            msg = self.format(record)
            self.signals.log_message.emit(msg)
        except Exception:
            self.handleError(record)

def setup_logging(config):
    """
    配置全局日志系统。

    Args:
        config (Config): 全局配置对象。

    Returns:
        LogSignals: 包含信号的对象，用于连接到GUI。
    """
    log_level_str = config.log_level.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    log_formatter = logging.Formatter('%(asctime)s [%(levelname)-8s] %(message)s', datefmt='%H:%M:%S')

    # 获取根logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除任何可能存在的旧处理器
    root_logger.handlers.clear()

    # 1. 配置命令行输出 (StreamHandler)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(log_formatter)
    root_logger.addHandler(stream_handler)

    # 2. 配置GUI输出 (QtLogHandler)
    log_signals = LogSignals()
    gui_handler = QtLogHandler(log_signals)
    gui_handler.setFormatter(log_formatter)
    root_logger.addHandler(gui_handler)

    # 3. 配置可选的文件输出 (FileHandler)
    if config.log_to_file:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file = os.path.join(log_dir, f"{timestamp}.log")
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_handler)
        
        logging.info(f"日志将保存到: {log_file}")

    logging.info(f"日志系统初始化完成，级别: {log_level_str}")
    return log_signals