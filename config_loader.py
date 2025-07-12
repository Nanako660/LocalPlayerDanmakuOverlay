# config_loader.py
import configparser

class Config:
    def __init__(self, filepath='config.ini'):
        self.filepath = filepath
        self.parser = configparser.ConfigParser()
        self.load()

    def load(self):
        defaults = {
            'Display': {
                'font_name': '微软雅黑',
                'font_size': '24',
                'stroke_width': '2',
                'max_tracks': '18',
                'opacity': '0.85',
                'line_spacing_ratio': '0.2'
            },
            'Danmaku': {
                'scroll_speed': '180',
                'fixed_duration': '5000',
                'max_danmaku_count': '200'
            },
            'Sync': {
                'target_aumid': 'PotPlayer64'
            },
            'Debug': {
                'enabled': 'false',
                'info_position': 'bottom_left'
            },
            'OnTopStrategy': {
                'method': '1'
            },
            'DEFAULT': {
                'LastDanmakuPath': ''
            }
        }
        # Create a new parser with defaults, then read the user's config over it
        parser = configparser.ConfigParser()
        parser.read_dict(defaults)
        parser.read(self.filepath, encoding='utf-8')
        self.parser = parser
        self._load_values()

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
        self.fixed_duration_ms = self.parser.getint('Danmaku', 'fixed_duration')
        self.max_danmaku_count = self.parser.getint('Danmaku', 'max_danmaku_count')

        # Sync
        self.target_aumid = self.parser.get('Sync', 'target_aumid')

        # Last State
        self.last_danmaku_path = self.parser.get('DEFAULT', 'LastDanmakuPath')
        
        # Debug
        self.debug = self.parser.getboolean('Debug', 'enabled')
        self.debug_info_position = self.parser.get('Debug', 'info_position')
        
        # OnTopStrategy
        self.ontop_strategy = self.parser.get('OnTopStrategy', 'method')

    def save(self):
        """将当前配置值保存到 .ini 文件。"""
        # Update parser object from instance attributes before writing
        self.parser.set('Display', 'font_name', self.font_name)
        self.parser.set('Display', 'font_size', str(self.font_size))
        self.parser.set('Display', 'stroke_width', str(self.stroke_width))
        self.parser.set('Display', 'max_tracks', str(self.max_tracks))
        self.parser.set('Display', 'opacity', str(self.opacity))
        self.parser.set('Display', 'line_spacing_ratio', str(self.line_spacing_ratio))
        self.parser.set('Danmaku', 'scroll_speed', str(self.scroll_speed))
        self.parser.set('Danmaku', 'fixed_duration', str(self.fixed_duration_ms))
        self.parser.set('Danmaku', 'max_danmaku_count', str(self.max_danmaku_count))
        self.parser.set('Sync', 'target_aumid', self.target_aumid)
        self.parser.set('Debug', 'enabled', str(self.debug))
        self.parser.set('Debug', 'info_position', self.debug_info_position)
        self.parser.set('OnTopStrategy', 'method', self.ontop_strategy)
        self.parser.set('DEFAULT', 'LastDanmakuPath', self.last_danmaku_path)

        try:
            with open(self.filepath, 'w', encoding='utf-8') as configfile:
                self.parser.write(configfile)
            print(f"配置已成功保存到 {self.filepath}")
        except Exception as e:
            print(f"保存配置失败: {e}")

    def reload(self):
        """从文件重新加载配置。"""
        self.load()
        print("配置已重新加载。")