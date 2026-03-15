from paddleocr import PaddleOCR
import numpy as np
from typing import List, Tuple, Dict, Optional
from loguru import logger
import cv2
import os
import time
from ..utils import get_prj_root

class OCRRecognizer:
    """PaddleOCR封装，识别图像中的文本和位置"""
    
    def __init__(self, lang: str = 'ch', use_gpu: bool = True, debug: bool = False):
        """
        初始化OCR识别器
        :param lang: 语言，默认中文
        :param use_gpu: 是否使用GPU加速
        """
        self.debug = debug

        logger.info("初始化OCR识别器...")
        # 新版本PaddleOCR使用device参数替代use_gpu
        device = 'gpu' if use_gpu else 'cpu'
        self.ocr = PaddleOCR(
            use_textline_orientation=True,  # 替代旧的use_angle_cls
            lang=lang,
            device=device,
            text_rec_score_thresh=0.5,  # 设置识别分数阈值
            text_det_thresh=0.3,   # 降低检测分数阈值
            text_det_box_thresh=0.3,  # 降低检测框阈值
            text_det_unclip_ratio=2.0 # 增大检测框大小
        )
    
    def recognize(self, image: np.ndarray, threshold: float = 0.8) -> List[Dict]:
        """
        识别图像中的文本
        :param image: BGR格式图像数组
        :param threshold: 置信度阈值，低于这个值的结果会被过滤
        :return: 识别结果列表，每个元素包含text, confidence, bbox
        """
        result = self.ocr.predict(image)
        
        recognized = []
        for res in result:
            texts = res.get('rec_texts', [])
            scores = res.get('rec_scores', [])
            bboxs = res.get('rec_polys', [])

            min_len = min(len(texts), len(scores), len(bboxs))
            for j in range(min_len):
                text = texts[j]
                confidence = scores[j]
                bbox = bboxs[j]
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
                    
        # 保存调试信息
        if self.debug:
            self._save_debug_info(image, recognized)
        
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
    
    def _save_debug_info(self, image: np.ndarray, recognized: List[Dict]):
        """
        保存调试信息，包括截图和识别的文本
        :param image: 原始图像
        :param recognized: 识别结果
        """
        cur_prj_path = get_prj_root()

        # 创建tmp文件夹
        tmp_dir = os.path.join(cur_prj_path, 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        
        # 生成时间戳作为文件名
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        # 保存截图
        image_path = os.path.join(tmp_dir, f'ocr_debug_{timestamp}.png')
        cv2.imwrite(image_path, image)
        logger.debug(f"保存OCR调试截图到: {image_path}")
        
        # 保存识别的文本
        text_path = os.path.join(tmp_dir, f'ocr_debug_{timestamp}.txt')
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(f"识别时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"识别到的文本数量: {len(recognized)}\n\n")
            for i, item in enumerate(recognized, 1):
                f.write(f"[{i}] 文本: {item['text']}\n")
                f.write(f"   置信度: {item['confidence']:.4f}\n")
                f.write(f"   位置: {item['center']}\n")
                f.write(f"   边界框: {item['bbox']}\n\n")
        
        logger.debug(f"保存OCR调试文本到: {text_path}")