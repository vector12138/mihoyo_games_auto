import time

import cv2
import paddle
import paddleocr

from src.core.screen_capture import ScreenCapture
from src.utils.util import get_prj_root

"""
OCR识别测试脚本
直接读取PNG文件进行识别
"""
import os
import cv2
from loguru import logger
from src.core.ocr_recognizer import OCRRecognizer
from src.config.logging_config import setup_logging

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
        output_path = os.path.join(get_prj_root(), 'tmp', f"test_{i}.png")
        if not cv2.imwrite(output_path, image):
            logger.error(f"保存截图失败: {output_path}")
        logger.info(f"截图已保存: {output_path}")

        time.sleep(1)

if __name__ == "__main__":
    sw = 2
    if sw == 1:
        test_capture()
    elif sw == 2:
        cur_prj_path = get_prj_root()
        image_path = os.path.join(cur_prj_path+'\\tmp', "test.png")

        test_ocr(image_path)