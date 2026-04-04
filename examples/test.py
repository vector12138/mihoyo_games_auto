import time
import os
import cv2
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
prj_root = os.path.dirname(current_dir)

sys.path.append(prj_root)

from src.core.screen_capture import ScreenCapture

"""
OCR识别测试脚本
直接读取PNG文件进行识别
"""
import os
import cv2
from loguru import logger
from src.config.logging_config import setup_logging
from src.core.game_base import MultiAppBase
import uiautomation as auto



# 配置日志
setup_logging(log_level="DEBUG")

def test_ocr(image_path):
    """
    测试OCR识别
    :param image_path: 图像文件路径
    """
    logger.info(f"测试OCR识别: {image_path}")
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        logger.error(f"文件不存在: {image_path}")
        return
    
    # 读取图像
    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"无法读取图像: {image_path}")
        return
    
    # 初始化OCR识别器
    ocr = OCRRecognizer(debug=True)
    
    # 执行识别
    results = ocr.recognize(image, threshold=0.3)
    
    # 输出识别结果
    logger.info(f"识别结果数量: {len(results)}")
    for i, result in enumerate(results, 1):
        logger.info(f"[{i}] 文本: {result['text']}")
        logger.info(f"   置信度: {result['confidence']:.4f}")
        logger.info(f"   位置: {result['center']}")
        logger.info(f"   边界框: {result['bbox']}")
        logger.info("---")

def test_capture():
    """
    测试截图功能
    """
    logger.info("测试截图功能")
    
    # 初始化截图器
    screen_capture = ScreenCapture(window_title="哔哩哔哩 (゜-゜)つロ 干杯~-bilibili")
    
    for i in range(5):
        # 截图
        image = screen_capture.capture()
        if image is None:
            logger.error("截图失败")
            return
        
        # 保存截图
        output_path = os.path.join(prj_root, 'tmp', f"test_{i}.png")
        if not cv2.imwrite(output_path, image):
            logger.error(f"保存截图失败: {output_path}")
        logger.info(f"截图已保存: {output_path}")

        time.sleep(1)

def test_game_base():
    """
    test_game_base
    """
    logger.info("测试原神游戏操作")
    
    class TestGameBase(MultiAppBase):
        def __init__(self, config, global_config):
            super().__init__(config, global_config)

            self.app_name = 'genshin_game'
            self.task_steps = [
                {
                    'name': '启动BetterGI工具',
                    'type': 'launch_app',
                    'app_name': 'bettergi',
                    'timeout': 30
                },{
                    'name': '点击一条龙按钮',
                    'type': 'click_control_by_properties',
                    'properties': {'source': 'uia','name': '一条龙', 'class_name': 'TextBlock', 'control_type': 'TextControl'},
                    'timeout': 10
                },
                {
                    'name': '点击运行按钮',
                    'type': 'click_control_by_hierarchy',
                    'hierarchy': [
                        {'source': 'uia', 'class_name': 'OneDragonFlowPage', 'control_type': 'CustomControl'},
                        {'source': 'uia','name': '\uF606', 'class_name': 'TextBlock', 'control_type': 'TextControl'}
                    ],
                    'timeout': 10
                }
            ]
            
    config = {
        'apps': {
            'bettergi': {
                'app_name': 'bettergi',
                'window_title': '更好的原神',
                'app_path': 'G:\\software\\windows\\BetterGI\\BetterGI.exe'
            }
        }
    }

    test_game_base = TestGameBase(config, {})

    test_game_base.run()

def test_telegram_msgs():
    """
    测试Telegram消息
    """
    import yaml 
    from datetime import datetime
    from src import TelegramBridgeApiClient

    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    fixed_date = datetime(2026, 3, 31, 12, 0, 0)
    timestamp = fixed_date.timestamp()

    # 获取Telegram消息
    telegram_bridge_api_client = TelegramBridgeApiClient(config.get('telegram'))
    telegram_bridge_api_client.last_processed_timestamp = int(timestamp)
    msgs = telegram_bridge_api_client.get_new_messages()

    # 打印消息
    for msg in msgs:
        logger.info(msg)

if __name__ == "__main__":
    sw = 2
    if sw == 1:
        test_capture()
    elif sw == 2:
        test_telegram_msgs()
