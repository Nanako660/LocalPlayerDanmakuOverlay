# main.py
import sys
import logging
from PyQt6.QtWidgets import QApplication

from config_loader import get_config
from control_panel import MainWindow
from danmaku_controller import DanmakuController
from logger_setup import setup_logging # 【新】导入日志设置函数

def main():
    app = QApplication(sys.argv)
    
    config = get_config() # <-- 修改获取方式
    log_signals = setup_logging(config)
    main_window = MainWindow(log_signals) # <-- 不再需要传递config
    controller = DanmakuController(main_window.winId()) # <-- 不再需要传递config
    main_window.set_controller(controller)
    main_window.show()
    
    logging.info("控制面板启动成功。")
    sys.exit(app.exec())

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # 捕获顶层异常并记录
        logging.critical("应用程序发生未捕获的严重错误: %s", e, exc_info=True)
        sys.exit(1)