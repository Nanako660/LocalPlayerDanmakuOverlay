# danmaku_parser.py
import xml.etree.ElementTree as ET
from PyQt6.QtGui import QColor
from danmaku_models import DanmakuData

def load_from_xml(filepath: str) -> list[DanmakuData]:
    """
    从Bilibili风格的XML文件中加载、解析并排序弹幕。

    Args:
        filepath (str): XML弹幕文件的路径。

    Returns:
        list[DanmakuData]: 一个按开始时间排序的DanmakuData对象列表。
                          如果文件未找到或解析失败，返回空列表。

    Example:
        # danmaku_list = load_from_xml("my_danmaku.xml")
        # if danmaku_list:
        #     print(f"成功加载 {len(danmaku_list)} 条弹幕。")
    """
    danmaku_list = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        for d_element in root.findall('d'):
            p_attr = d_element.get('p', '').split(',')
            if len(p_attr) > 4:
                try:
                    start_time = float(p_attr[0])
                    mode = int(p_attr[1])
                    color_decimal = int(p_attr[3])
                    text = d_element.text
                    
                    if text and mode in [1, 4, 5]: # 只处理滚动、顶部、底部弹幕
                        color = QColor((color_decimal >> 16) & 255, 
                                       (color_decimal >> 8) & 255, 
                                       color_decimal & 255)
                        danmaku_list.append(DanmakuData(start_time, mode, text, color))
                except (ValueError, IndexError):
                    # 忽略格式错误的弹幕行
                    continue
        
        # 按开始时间排序，这是同步的关键
        danmaku_list.sort(key=lambda x: x.start_time)
        print(f"成功加载 {len(danmaku_list)} 条有效弹幕。")
        return danmaku_list
    except FileNotFoundError:
        print(f"错误: 弹幕文件 '{filepath}' 未找到。")
        return []
    except ET.ParseError as e:
        print(f"解析XML时发生错误: {e}")
        return []
    except Exception as e:
        print(f"加载弹幕时发生未知错误: {e}")
        return []