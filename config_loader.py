# config_loader.py
import configparser

class Config:
    def __init__(self, filepath='config.ini'):
        parser = configparser.ConfigParser()
        defaults = {
            'Display': {
                'font_name': '微软雅黑',
                'font_size': '24',
                'stroke_width': '2',
                'max_tracks': '18'
            },
            'Danmaku': {
                'scroll_speed': '180',
                'fixed_duration': '5000',
                'max_on_screen': '200'
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
            }
        }
        parser.read_dict(defaults)
        parser.read(filepath, encoding='utf-8')

        # Display
        self.font_name = parser.get('Display', 'font_name')
        self.font_size = parser.getint('Display', 'font_size')
        self.stroke_width = parser.getint('Display', 'stroke_width')
        self.max_tracks = parser.getint('Display', 'max_tracks')

        # Danmaku
        self.scroll_speed = parser.getint('Danmaku', 'scroll_speed')
        self.fixed_duration_ms = parser.getint('Danmaku', 'fixed_duration')
        self.max_on_screen = parser.getint('Danmaku', 'max_on_screen')

        # Sync
        self.target_aumid = parser.get('Sync', 'target_aumid')
        
        # Debug
        self.debug_enabled = parser.getboolean('Debug', 'enabled')
        self.debug_info_position = parser.get('Debug', 'info_position')
        
        # OnTopStrategy
        self.on_top_method = parser.getint('OnTopStrategy', 'method')