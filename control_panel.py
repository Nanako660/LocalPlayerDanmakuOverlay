# control_panel.py
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QStackedWidget,
    QLabel, QPushButton, QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox,
    QLineEdit, QCheckBox, QFileDialog, QListWidgetItem, QPlainTextEdit,
    QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# 【重要】导入单例获取函数
from config_loader import get_config
from logger_setup import LogSignals
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from danmaku_controller import DanmakuController


class LogWidget(QWidget):
    """用于显示实时日志的UI组件。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.log_display = QPlainTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Consolas", 10))

        layout.addWidget(self.log_display)

    def append_log(self, message: str):
        self.log_display.appendPlainText(message)

class MainWindow(QMainWindow):
    """应用程序的主窗口（控制面板UI）。"""
    def __init__(self, log_signals: LogSignals):
        super().__init__()
        # 【修正】直接通过 get_config() 获取单例，不再通过构造函数传递
        self.config = get_config()
        self.controller: 'DanmakuController' | None = None
        self.setWindowTitle("本地弹幕播放器控制台")
        self.resize(800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.nav_bar = QListWidget()
        self.nav_bar.setFixedWidth(150)
        main_layout.addWidget(self.nav_bar)
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # ======================= 核心修正点 =======================
        # 创建子组件时，不再传递 config 参数，因为它们会自己获取单例
        self.main_widget = MainWidget()
        self.settings_widget = SettingsWidget(main_window=self)
        # ========================================================
        
        self.log_widget = LogWidget()

        self.stacked_widget.addWidget(self.main_widget)
        self.stacked_widget.addWidget(self.settings_widget)
        self.stacked_widget.addWidget(self.log_widget)

        self.setup_nav()
        self.nav_bar.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)
        
        log_signals.log_message.connect(self.log_widget.append_log)

    def set_controller(self, controller: 'DanmakuController'):
        self.controller = controller
        self.main_widget.start_button.clicked.connect(self.start_danmaku)
        self.main_widget.stop_button.clicked.connect(self.stop_danmaku)
        self.settings_widget.set_controller(controller)

    def start_danmaku(self):
        if not self.controller: return
        danmaku_path = self.main_widget.path_input.text()
        if not danmaku_path:
            logging.error("请先选择一个弹幕文件。")
            return
            
        self.controller.start(danmaku_path)
        self.main_widget.start_button.setEnabled(False)
        self.main_widget.stop_button.setEnabled(True)

    def stop_danmaku(self):
        if not self.controller: return
        self.controller.stop()
        self.main_widget.start_button.setEnabled(True)
        self.main_widget.stop_button.setEnabled(False)
        
    def closeEvent(self, event):
        self.stop_danmaku()
        event.accept()
        
    def setup_nav(self):
        self.nav_bar.addItem(QListWidgetItem("主界面"))
        self.nav_bar.addItem(QListWidgetItem("设置"))
        self.nav_bar.addItem(QListWidgetItem("日志"))
        self.nav_bar.setCurrentRow(0)


class SettingsWidget(QWidget):
    def __init__(self, main_window: MainWindow, parent=None):
        super().__init__(parent)
        # 【修正】直接通过 get_config() 获取单例
        self.config = get_config()
        self.main_window = main_window
        self.controller = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        form_layout = QFormLayout()

        # --- 创建所有UI控件 ---
        self.font_name_input = QLineEdit()
        self.font_size_input = QSpinBox()
        self.stroke_width_input = QSpinBox()
        self.opacity_input = QDoubleSpinBox()
        self.scroll_speed_input = QSpinBox()
        self.fixed_duration_input = QSpinBox()
        self.max_danmaku_input = QSpinBox()
        self.max_tracks_input = QSpinBox()
        self.line_spacing_input = QDoubleSpinBox()
        self.target_aumid_input = QLineEdit()
        self.ontop_strategy_input = QComboBox()
        self.debug_mode_checkbox = QCheckBox()
        self.debug_pos_input = QComboBox()
        self.log_level_input = QComboBox()
        self.log_to_file_checkbox = QCheckBox()
        
        # --- 将控件添加到布局 ---
        form_layout.addRow("--- 显示设置 ---", None)
        form_layout.addRow("字体名称:", self.font_name_input)
        form_layout.addRow("字体大小:", self.font_size_input)
        form_layout.addRow("描边宽度:", self.stroke_width_input)
        form_layout.addRow("不透明度:", self.opacity_input)
        form_layout.addRow("--- 弹幕设置 ---", None)
        form_layout.addRow("滚动速度 (像素/秒):", self.scroll_speed_input)
        form_layout.addRow("固定弹幕持续(毫秒):", self.fixed_duration_input)
        form_layout.addRow("最大弹幕数(对象池):", self.max_danmaku_input)
        form_layout.addRow("最大滚动轨道数:", self.max_tracks_input)
        form_layout.addRow("轨道行间距比例:", self.line_spacing_input)
        form_layout.addRow("--- 同步与行为 ---", None)
        form_layout.addRow("目标播放器AUMID:", self.target_aumid_input)
        form_layout.addRow("置顶策略 (0:无):", self.ontop_strategy_input)
        form_layout.addRow("--- 调试与日志 ---", None)
        form_layout.addRow("启用调试信息:", self.debug_mode_checkbox)
        form_layout.addRow("调试信息位置:", self.debug_pos_input)
        form_layout.addRow("日志级别:", self.log_level_input)
        form_layout.addRow("保存日志到文件:", self.log_to_file_checkbox)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("应用设置")
        self.restore_button = QPushButton("恢复默认配置")
        
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.restore_button)
        
        layout.addLayout(button_layout)

        self.apply_button.clicked.connect(self._apply_settings)
        self.restore_button.clicked.connect(self._restore_defaults)

        self._update_inputs_from_config()

    def _apply_settings(self):
        logging.info("正在应用并保存新设置...")
        self._update_config_from_inputs()
        self.config.save()
        self._hot_reload_danmaku()

    def _hot_reload_danmaku(self):
        if self.controller and self.controller.is_running():
            logging.info("热重载：正在重启弹幕以应用新设置...")
            self.main_window.stop_danmaku()
            QTimer.singleShot(100, self.main_window.start_danmaku)
    
    def _restore_defaults(self):
        reply = QMessageBox.question(self, '确认', '您确定要将所有设置恢复为默认值吗？\n此操作会立即保存并应用。',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.config.restore_defaults()
            self._update_inputs_from_config()
            self._hot_reload_danmaku()

    def _update_inputs_from_config(self):
        # (此方法无变化)
        self.font_name_input.setText(self.config.font_name)
        self.font_size_input.setRange(10, 72)
        self.font_size_input.setValue(self.config.font_size)
        self.stroke_width_input.setRange(0, 10)
        self.stroke_width_input.setValue(self.config.stroke_width)
        self.opacity_input.setRange(0.0, 1.0)
        self.opacity_input.setSingleStep(0.1)
        self.opacity_input.setValue(self.config.opacity)
        self.max_tracks_input.setRange(5, 50)
        self.max_tracks_input.setValue(self.config.max_tracks)
        self.line_spacing_input.setRange(0.0, 2.0)
        self.line_spacing_input.setSingleStep(0.1)
        self.line_spacing_input.setValue(self.config.line_spacing_ratio)
        self.scroll_speed_input.setRange(50, 1000)
        self.scroll_speed_input.setValue(self.config.scroll_speed)
        self.fixed_duration_input.setRange(1000, 20000)
        self.fixed_duration_input.setSingleStep(1000)
        self.fixed_duration_input.setValue(self.config.fixed_duration_ms)
        self.max_danmaku_input.setRange(50, 2000)
        self.max_danmaku_input.setValue(self.config.max_danmaku_count)
        self.target_aumid_input.setText(self.config.target_aumid)
        self.ontop_strategy_input.clear()
        self.ontop_strategy_input.addItems(["0", "1", "2", "3"])
        self.ontop_strategy_input.setCurrentText(self.config.ontop_strategy)
        self.debug_mode_checkbox.setChecked(self.config.debug)
        self.debug_pos_input.clear()
        self.debug_pos_input.addItems(['bottom_left', 'bottom_right', 'top_left', 'top_right'])
        self.debug_pos_input.setCurrentText(self.config.debug_info_position)
        self.log_level_input.clear()
        self.log_level_input.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR'])
        self.log_level_input.setCurrentText(self.config.log_level.upper())
        self.log_to_file_checkbox.setChecked(self.config.log_to_file)

    def _update_config_from_inputs(self):
        # (此方法无变化)
        self.config.font_name = self.font_name_input.text()
        self.config.font_size = self.font_size_input.value()
        self.config.stroke_width = self.stroke_width_input.value()
        self.config.opacity = self.opacity_input.value()
        self.config.scroll_speed = self.scroll_speed_input.value()
        self.config.fixed_duration_ms = self.fixed_duration_input.value()
        self.config.max_danmaku_count = self.max_danmaku_input.value()
        self.config.max_tracks = self.max_tracks_input.value()
        self.config.line_spacing_ratio = self.line_spacing_input.value()
        self.config.target_aumid = self.target_aumid_input.text()
        self.config.ontop_strategy = self.ontop_strategy_input.currentText()
        self.config.debug = self.debug_mode_checkbox.isChecked()
        self.config.debug_info_position = self.debug_pos_input.currentText()
        self.config.log_level = self.log_level_input.currentText()
        self.config.log_to_file = self.log_to_file_checkbox.isChecked()
        
    def set_controller(self, controller: 'DanmakuController'):
        self.controller = controller

class MainWidget(QWidget):
    """主操作界面的UI组件。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # 【修正】直接通过 get_config() 获取单例
        self.config = get_config()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
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
        layout.addStretch(1)
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("▶ 开始播放")
        self.stop_button = QPushButton("■ 停止播放")
        self.stop_button.setEnabled(False)
        control_layout.addStretch()
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addStretch()
        layout.addLayout(control_layout)
        layout.addStretch(1)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择弹幕文件", "", "XML 文件 (*.xml);;所有文件 (*)")
        if file_path:
            self.path_input.setText(file_path)
            self.config.last_danmaku_path = file_path
            self.config.save()