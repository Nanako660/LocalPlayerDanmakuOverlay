# config_loader.py
import logging
import configparser

class Config:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def __init__(self, filepath='config.ini'):
        if hasattr(self, '_initialized'):
            return
            
        self.filepath = filepath
        self.parser = configparser.ConfigParser()
        self._defaults = {
            'Display': {
                'font_name': '微软雅黑', 'font_size': '24', 'stroke_width': '2',
                'max_tracks': '18', 'opacity': '0.85', 'line_spacing_ratio': '0.2'
            },
            'Danmaku': {
                'scroll_speed': '180', 'fixed_duration_ms': '5000', 
                'max_danmaku_count': '250',
                'allow_overlap': 'false' # 【新增】允许弹幕重叠
            },
            'Sync': {'target_aumid': 'PotPlayer64'},
            'Debug': {'enabled': 'false', 'info_position': 'bottom_left'},
            'OnTopStrategy': {'method': '1'},
            'Logging': {'level': 'INFO', 'log_to_file': 'true'},
            'DEFAULT': {'LastDanmakuPath': ''}
        }
        self.load()
        self._initialized = True

    def load(self):
        parser = configparser.ConfigParser()
        parser.read_dict(self._defaults)
        parser.read(self.filepath, encoding='utf-8')
        self.parser = parser
        self._load_values()

    def restore_defaults(self):
        logging.info("正在恢复所有设置为默认值...")
        parser = configparser.ConfigParser()
        parser.read_dict(self._defaults)
        self.parser = parser
        self._load_values()
        self.save()

    def _load_values(self):
        # Display
        self.font_name = self.parser.get('Display', 'font_name')
        self.font_size = self.parser.getint('Display', 'font_size')
        self.stroke_width = self.parser.getint('Display', 'stroke_width')
        self.max_tracks = self.parser.getint('Display', 'max_tracks')
        self.opacity = self.parser.getfloat('Display', 'opacity')
        self.line_spacing_ratio = self.parser.getfloat('Display', 'line_spacing_ratio')
        # Danmaku
        self.scroll_speed = self.parser.getint('Danmaku', 'scroll_speed')
        self.fixed_duration_ms = self.parser.getint('Danmaku', 'fixed_duration_ms')
        self.max_danmaku_count = self.parser.getint('Danmaku', 'max_danmaku_count')
        self.allow_overlap = self.parser.getboolean('Danmaku', 'allow_overlap') # 【新增】
        # Sync
        self.target_aumid = self.parser.get('Sync', 'target_aumid')
        self.last_danmaku_path = self.parser.get('DEFAULT', 'LastDanmakuPath')
        # Debug
        self.debug = self.parser.getboolean('Debug', 'enabled')
        self.debug_info_position = self.parser.get('Debug', 'info_position')
        # OnTopStrategy
        self.ontop_strategy = self.parser.get('OnTopStrategy', 'method')
        # Logging
        self.log_level = self.parser.get('Logging', 'level')
        self.log_to_file = self.parser.getboolean('Logging', 'log_to_file')

    def save(self):
        # (大部分无变化)
        self.parser.set('Danmaku', 'allow_overlap', str(self.allow_overlap).lower()) # 【新增】
        # ... 其他 set ...
        self.parser.set('Display', 'font_name', self.font_name)
        self.parser.set('Display', 'font_size', str(self.font_size))
        self.parser.set('Display', 'stroke_width', str(self.stroke_width))
        self.parser.set('Display', 'max_tracks', str(self.max_tracks))
        self.parser.set('Display', 'opacity', str(self.opacity))
        self.parser.set('Display', 'line_spacing_ratio', str(self.line_spacing_ratio))
        self.parser.set('Danmaku', 'scroll_speed', str(self.scroll_speed))
        self.parser.set('Danmaku', 'fixed_duration_ms', str(self.fixed_duration_ms))
        self.parser.set('Danmaku', 'max_danmaku_count', str(self.max_danmaku_count))
        self.parser.set('Sync', 'target_aumid', self.target_aumid)
        self.parser.set('Debug', 'enabled', str(self.debug).lower())
        self.parser.set('Debug', 'info_position', self.debug_info_position)
        self.parser.set('OnTopStrategy', 'method', self.ontop_strategy)
        self.parser.set('Logging', 'level', self.log_level)
        self.parser.set('Logging', 'log_to_file', str(self.log_to_file).lower())
        self.parser.set('DEFAULT', 'LastDanmakuPath', self.last_danmaku_path)
        try:
            with open(self.filepath, 'w', encoding='utf-8') as configfile:
                self.parser.write(configfile)
            logging.info(f"配置已成功保存到 {self.filepath}")
        except Exception as e:
            logging.error(f"保存配置失败: {e}")

def get_config():
    return Config()