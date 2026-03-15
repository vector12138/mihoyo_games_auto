from paddleocr import PaddleOCR
import numpy as np
from typing import List, Tuple, Dict, Optional
from loguru import logger


class OCRRecognizer:
    """PaddleOCR封装，识别图像中的文本和位置"""
    
    def __init__(self, lang: str = 'ch', use_gpu: bool = True):
        """
        初始化OCR识别器
        :param lang: 语言，默认中文
        :param use_gpu: 是否使用GPU加速
        """
        logger.info("初始化OCR识别器...")
        # 新版本PaddleOCR使用device参数替代use_gpu
        device = 'gpu' if use_gpu else 'cpu'
        self.ocr = PaddleOCR(
            use_textline_orientation=True,  # 替代旧的use_angle_cls
            lang=lang,
            device=device,
            text_rec_score_thresh=0.5  # 设置识别分数阈值
        )
    
    def recognize(self, image: np.ndarray, threshold: float = 0.8) -> List[Dict]:
        """
        识别图像中的文本
        :param image: BGR格式图像数组
        :param threshold: 置信度阈值，低于这个值的结果会被过滤
        :return: 识别结果列表，每个元素包含text, confidence, bbox
        """
        result = self.ocr.predict(image)
        if not result or not result[0]:
            return []
        
        recognized = []
        for line in result[0]:
            bbox = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text_info = line[1]
            
            if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                text = text_info[0]
                confidence = text_info[1]
                
                if confidence >= threshold:
                    # 计算中心点坐标
                    center_x = (bbox[0][0] + bbox[2][0]) / 2
                    center_y = (bbox[0][1] + bbox[2][1]) / 2
                    # 计算宽高
                    width = bbox[1][0] - bbox[0][0]
                    height = bbox[2][1] - bbox[1][1]
                    
                    recognized.append({
                        'text': text.strip(),
                        'confidence': confidence,
                        'bbox': bbox,
                        'center': (center_x, center_y),
                        'width': width,
                        'height': height
                    })
        
        logger.debug(f"识别到{len(recognized)}个有效文本")
        return recognized
    
    def find_text(self, image: np.ndarray, target_text: str, 
                 threshold: float = 0.8, fuzzy_match: bool = True) -> Optional[Dict]:
        """
        查找指定文本的位置
        :param image: 图像
        :param target_text: 目标文本
        :param threshold: 置信度阈值
        :param fuzzy_match: 是否模糊匹配（包含目标文本就算匹配）
        :return: 匹配到的结果，没找到返回None
        """
        results = self.recognize(image, threshold)
        target_text = target_text.strip().lower()
        
        for res in results:
            text = res['text'].lower()
            if (fuzzy_match and target_text in text) or (not fuzzy_match and text == target_text):
                logger.info(f"找到文本: {res['text']} 位置: {res['center']} 置信度: {res['confidence']:.2f}")
                return res
        
        logger.debug(f"未找到文本: {target_text}")
        return None
    
    def find_all_text(self, image: np.ndarray, target_text: str, 
                     threshold: float = 0.8, fuzzy_match: bool = True) -> List[Dict]:
        """查找所有匹配的文本"""
        results = self.recognize(image, threshold)
        target_text = target_text.strip().lower()
        matches = []
        
        for res in results:
            text = res['text'].lower()
            if (fuzzy_match and target_text in text) or (not fuzzy_match and text == target_text):
                matches.append(res)
        
        return matches