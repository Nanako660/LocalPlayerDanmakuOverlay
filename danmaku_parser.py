# danmaku_parser.py
import xml.etree.ElementTree as ET
from PyQt6.QtGui import QColor
from danmaku_models import DanmakuData

def load_from_xml(filepath: str) -> list[DanmakuData]:
    """从 B站 XML 文件加载并解析弹幕。"""
    danmaku_list = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        for d_element in root.findall('d'):
            p_attr = d_element.get('p', '').split(',')
            if len(p_attr) > 4:
                start_time = float(p_attr[0])
                mode = int(p_attr[1])
                text = d_element.text
                color_decimal = int(p_attr[3])
                color = QColor((color_decimal >> 16) & 255, (color_decimal >> 8) & 255, color_decimal & 255)
                
                if text and mode in [1, 4, 5]:
                    danmaku_list.append(DanmakuData(start_time, mode, text, color))
        
        danmaku_list.sort(key=lambda x: x.start_time)
        print(f"成功加载 {len(danmaku_list)} 条弹幕。")
        return danmaku_list
    except FileNotFoundError:
        print(f"错误: 弹幕文件 '{filepath}' 未找到。")
        return []
    except Exception as e:
        print(f"解析XML时发生错误: {e}")
        return []