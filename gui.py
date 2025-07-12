# gui.py
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QStackedWidget, QListWidgetItem, QLabel, QPushButton,
    QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit, QCheckBox,
    QFileDialog
)
from PyQt6.QtCore import Qt, QSize, QObject
from PyQt6.QtGui import QIcon
from config_loader import Config
from danmaku_parser import load_from_xml
from main import Application  # We will refactor Application to be controllable

from PyQt6.QtCore import QTimer

class SettingsWidget(QWidget):
    def __init__(self, config, main_window, parent=None):
        super().__init__(parent)
        self.config = config
        self.main_window = main_window # Reference to the main window for controller access

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        form_layout = QFormLayout()

        # Display settings
        self.font_name_input = QLineEdit(self.config.font_name)
        self.font_size_input = QSpinBox()
        self.font_size_input.setRange(10, 72)
        self.font_size_input.setValue(self.config.font_size)
        
        # Danmaku settings
        self.scroll_speed_input = QSpinBox()
        self.scroll_speed_input.setRange(50, 1000)
        self.scroll_speed_input.setValue(self.config.scroll_speed)

        # Sync settings
        self.target_aumid_input = QLineEdit(self.config.target_aumid)

        form_layout.addRow("字体名称:", self.font_name_input)
        form_layout.addRow("字体大小:", self.font_size_input)
        form_layout.addRow("滚动速度 (像素/秒):", self.scroll_speed_input)
        form_layout.addRow("目标播放器AUMID:", self.target_aumid_input)

        # Opacity
        self.opacity_input = QDoubleSpinBox()
        self.opacity_input.setRange(0.0, 1.0)
        self.opacity_input.setSingleStep(0.1)
        self.opacity_input.setValue(self.config.opacity)
        form_layout.addRow("不透明度 (0.0 - 1.0):", self.opacity_input)

        # Max Danmaku Count
        self.max_danmaku_input = QSpinBox()
        self.max_danmaku_input.setRange(1, 1000)
        self.max_danmaku_input.setValue(self.config.max_danmaku_count)
        form_layout.addRow("最大弹幕数量:", self.max_danmaku_input)

        # OnTop Strategy
        self.ontop_strategy_input = QComboBox()
        self.ontop_strategy_input.addItems(["1", "2"])
        self.ontop_strategy_input.setCurrentText(self.config.ontop_strategy)
        form_layout.addRow("置顶策略:", self.ontop_strategy_input)

        # Debug Mode
        self.debug_mode_checkbox = QCheckBox("调试模式")
        self.debug_mode_checkbox.setChecked(self.config.debug)
        form_layout.addRow("调试模式:", self.debug_mode_checkbox)

        layout.addLayout(form_layout)

        # Save button
        button_layout = QHBoxLayout()
        self.reload_button = QPushButton("应用更改 (热重载)")
        self.save_button = QPushButton("保存到文件")
        self.reload_button.clicked.connect(self.reload_settings)
        self.save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(self.reload_button)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

    def _update_config_from_inputs(self):
        """Helper to read values from UI inputs into the config object."""
        self.config.font_name = self.font_name_input.text()
        self.config.font_size = self.font_size_input.value()
        self.config.scroll_speed = self.scroll_speed_input.value()
        self.config.target_aumid = self.target_aumid_input.text()
        self.config.opacity = self.opacity_input.value()
        self.config.max_danmaku_count = self.max_danmaku_input.value()
        self.config.ontop_strategy = self.ontop_strategy_input.currentText()
        self.config.debug = self.debug_mode_checkbox.isChecked()

    def save_settings(self):
        self._update_config_from_inputs()
        self.config.save()

    def reload_settings(self):
        """Applies settings and restarts the danmaku if it's running."""
        self._update_config_from_inputs()
        print("配置已在内存中更新。")

        # Check if the controller and app are running
        if self.main_window.controller and self.main_window.controller.app_instance:
            print("检测到弹幕正在运行，将自动重启以应用新设置...")
            self.main_window.stop_danmaku()
            # Need a small delay to ensure resources are released before restarting
            QTimer.singleShot(100, self.main_window.start_danmaku)


class DanmakuController(QObject):
    def __init__(self, config, main_window):
        super().__init__()
        self.config = config
        self.main_window = main_window # Keep a reference to the main window
        self.app_instance = None

    def start(self, danmaku_path):
        if not danmaku_path:
            print("错误: 请先选择一个弹幕文件。")
            return

        if self.app_instance:
            print("弹幕已在运行中。")
            return

        danmaku_data = load_from_xml(danmaku_path)
        if not danmaku_data:
            print(f"错误: 无法从 '{danmaku_path}' 加载弹幕。")
            return

        print(f"正在从 '{danmaku_path}' 加载弹幕...")
        self.app_instance = Application(self.config, danmaku_data, parent=self.main_window)
        self.app_instance.start()
        print("弹幕已启动。")

    def stop(self):
        if self.app_instance:
            self.app_instance.stop()
            self.app_instance = None
        else:
            print("弹幕尚未运行。")

class MainWidget(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Danmaku file path input
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(self.config.last_danmaku_path)
        self.path_input.setPlaceholderText("请在此处输入或选择弹幕文件路径 (.xml)")
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_file)

        path_layout.addWidget(QLabel("弹幕文件:"))
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(self.browse_button)
        
        layout.addLayout(path_layout)

        # Spacer
        layout.addStretch(1)

        # Control buttons
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("▶ 开始播放")
        self.stop_button = QPushButton("■ 停止播放")
        self.stop_button.setEnabled(False)

        control_layout.addStretch()
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addStretch()
        layout.addLayout(control_layout)

        # Spacer
        layout.addStretch(1)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择弹幕文件", 
            "", 
            "XML 文件 (*.xml);;所有文件 (*)"
        )
        if file_path:
            self.path_input.setText(file_path)
            self.config.last_danmaku_path = file_path
            self.config.save()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.controller = DanmakuController(self.config, self)
        self.setWindowTitle("本地弹幕播放器控制台")
        self.resize(800, 600)

        # Main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Navigation
        self.nav_bar = QListWidget()
        self.nav_bar.setFixedWidth(150)
        main_layout.addWidget(self.nav_bar)

        # Content area
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create pages
        self.main_widget = MainWidget(self.config)
        self.settings_widget = SettingsWidget(config=self.config, main_window=self)

        self.stacked_widget.addWidget(self.main_widget)
        self.stacked_widget.addWidget(self.settings_widget)

        self.setup_nav()

        self.nav_bar.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)

        # Connect signals
        self.main_widget.start_button.clicked.connect(self.start_danmaku)
        self.main_widget.stop_button.clicked.connect(self.stop_danmaku)

    def start_danmaku(self):
        danmaku_path = self.main_widget.path_input.text()
        self.controller.start(danmaku_path)
        self.main_widget.start_button.setEnabled(False)
        self.main_widget.stop_button.setEnabled(True)

    def stop_danmaku(self):
        self.controller.stop()
        self.main_widget.start_button.setEnabled(True)
        self.main_widget.stop_button.setEnabled(False)

    def setup_nav(self):
        main_item = QListWidgetItem("主界面")
        self.nav_bar.addItem(main_item)

        settings_item = QListWidgetItem("设置")
        self.nav_bar.addItem(settings_item)

        self.nav_bar.setCurrentRow(0)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())