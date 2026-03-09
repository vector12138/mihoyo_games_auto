#!/usr/bin/env python3
"""
图像识别模块
使用OpenCV进行游戏界面识别和状态检测
"""

import os
import sys
import time
import logging
from pathlib import Path

try:
    import cv2
    import numpy as np
    from PIL import ImageGrab, Image
    import pyautogui
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

class ImageRecognizer:
    """图像识别器"""
    
    def __init__(self, config=None):
        """初始化图像识别器"""
        self.config = config or {}
        self.enabled = self.config.get('enabled', False) and OPENCV_AVAILABLE
        self.template_dir = Path(__file__).parent / 'templates'
        self.template_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger('ImageRecognizer')
        
        if not OPENCV_AVAILABLE:
            self.logger.warning("OpenCV未安装，图像识别功能不可用")
            self.logger.info("安装命令: pip install opencv-python pillow pyautogui numpy")
            self.enabled = False
        elif self.enabled:
            self.logger.info("图像识别功能已启用")
        else:
            self.logger.info("图像识别功能未启用")
    
    def capture_screen(self, region=None, save_path=None):
        """
        截取屏幕
        :param region: 截取区域 (x, y, width, height)，None表示全屏
        :param save_path: 保存路径，None表示不保存
        :return: 截取的图像（OpenCV格式）
        """
        try:
            # 使用PIL截屏
            screenshot = ImageGrab.grab(bbox=region)
            
            # 转换为OpenCV格式
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 保存截图
            if save_path:
                save_path = Path(save_path)
                save_path.parent.mkdir(exist_ok=True)
                cv2.imwrite(str(save_path), screenshot_cv)
                self.logger.debug(f"截图已保存: {save_path}")
            
            return screenshot_cv
            
        except Exception as e:
            self.logger.error(f"截屏失败: {e}")
            return None
    
    def find_template(self, template_name, screen_image=None, region=None, threshold=0.8, save_debug=False):
        """
        在屏幕中查找模板图像
        :param template_name: 模板图像文件名（在templates目录中）
        :param screen_image: 屏幕图像，None表示重新截屏
        :param region: 搜索区域，None表示全屏
        :param threshold: 匹配阈值（0-1）
        :param save_debug: 是否保存调试图像
        :return: (x, y, width, height) 或 None
        """
        if not self.enabled:
            self.logger.warning("图像识别未启用")
            return None
        
        try:
            # 加载模板图像
            template_path = self.template_dir / template_name
            if not template_path.exists():
                self.logger.error(f"模板图像不存在: {template_path}")
                return None
            
            template = cv2.imread(str(template_path))
            if template is None:
                self.logger.error(f"无法加载模板图像: {template_path}")
                return None
            
            template_height, template_width = template.shape[:2]
            
            # 获取屏幕图像
            if screen_image is None:
                screen_image = self.capture_screen(region)
                if screen_image is None:
                    return None
            
            # 模板匹配
            result = cv2.matchTemplate(screen_image, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            self.logger.debug(f"模板匹配: {template_name}, 最大相似度: {max_val:.3f}, 阈值: {threshold}")
            
            # 检查是否匹配成功
            if max_val >= threshold:
                top_left = max_loc
                bottom_right = (top_left[0] + template_width, top_left[1] + template_height)
                
                self.logger.info(f"找到模板: {template_name}, 位置: {top_left}, 相似度: {max_val:.3f}")
                
                # 保存调试图像
                if save_debug:
                    debug_image = screen_image.copy()
                    cv2.rectangle(debug_image, top_left, bottom_right, (0, 255, 0), 2)
                    cv2.putText(debug_image, f"{template_name}: {max_val:.3f}", 
                               (top_left[0], top_left[1] - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    debug_path = self.template_dir / 'debug' / f"match_{template_name}_{int(time.time())}.png"
                    debug_path.parent.mkdir(exist_ok=True)
                    cv2.imwrite(str(debug_path), debug_image)
                    self.logger.debug(f"调试图像已保存: {debug_path}")
                
                return (top_left[0], top_left[1], template_width, template_height)
            else:
                self.logger.debug(f"未找到模板: {template_name}, 最大相似度: {max_val:.3f} < {threshold}")
                return None
                
        except Exception as e:
            self.logger.error(f"模板匹配失败: {template_name} - {e}")
            return None
    
    def wait_for_template(self, template_name, timeout=30, interval=1, threshold=0.8, region=None):
        """
        等待模板图像出现
        :param template_name: 模板图像文件名
        :param timeout: 超时时间（秒）
        :param interval: 检查间隔（秒）
        :param threshold: 匹配阈值
        :param region: 搜索区域
        :return: 找到的位置或None
        """
        if not self.enabled:
            self.logger.warning("图像识别未启用，跳过等待")
            return None
        
        self.logger.info(f"等待模板: {template_name}, 超时: {timeout}秒")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            position = self.find_template(template_name, region=region, threshold=threshold)
            
            if position:
                return position
            
            self.logger.debug(f"未找到 {template_name}，等待 {interval} 秒后重试")
            time.sleep(interval)
        
        self.logger.warning(f"等待模板超时: {template_name}")
        return None
    
    def click_template(self, template_name, offset_x=0, offset_y=0, timeout=30, threshold=0.8):
        """
        找到模板并点击
        :param template_name: 模板图像文件名
        :param offset_x: X轴偏移
        :param offset_y: Y轴偏移
        :param timeout: 超时时间
        :param threshold: 匹配阈值
        :return: 是否成功
        """
        if not self.enabled:
            self.logger.warning("图像识别未启用，无法点击")
            return False
        
        position = self.wait_for_template(template_name, timeout=timeout, threshold=threshold)
        
        if position:
            x, y, width, height = position
            click_x = x + width // 2 + offset_x
            click_y = y + height // 2 + offset_y
            
            self.logger.info(f"点击模板: {template_name}, 位置: ({click_x}, {click_y})")
            
            # 移动鼠标并点击
            pyautogui.moveTo(click_x, click_y, duration=0.2)
            pyautogui.click()
            
            return True
        else:
            self.logger.error(f"无法找到模板进行点击: {template_name}")
            return False
    
    def check_color_at_point(self, x, y, target_color, tolerance=10):
        """
        检查指定点的颜色
        :param x: X坐标
        :param y: Y坐标
        :param target_color: 目标颜色 (B, G, R)
        :param tolerance: 容差
        :return: 是否匹配
        """
        if not self.enabled:
            self.logger.warning("图像识别未启用，无法检查颜色")
            return False
        
        try:
            # 截取单点
            screenshot = self.capture_screen(region=(x, y, x+1, y+1))
            if screenshot is None:
                return False
            
            actual_color = screenshot[0, 0]  # 获取像素颜色
            
            # 计算颜色差异
            diff = np.abs(actual_color - target_color)
            
            if np.all(diff <= tolerance):
                self.logger.debug(f"颜色匹配: ({x}, {y}) - 目标: {target_color}, 实际: {actual_color}")
                return True
            else:
                self.logger.debug(f"颜色不匹配: ({x}, {y}) - 目标: {target_color}, 实际: {actual_color}, 差异: {diff}")
                return False
                
        except Exception as e:
            self.logger.error(f"检查颜色失败: ({x}, {y}) - {e}")
            return False
    
    def save_template(self, image, template_name, region=None):
        """
        保存模板图像
        :param image: 图像数据或路径
        :param template_name: 模板名称
        :param region: 截取区域 (x, y, width, height)
        :return: 是否成功
        """
        try:
            template_path = self.template_dir / template_name
            
            if isinstance(image, str) or isinstance(image, Path):
                # 从文件加载
                img = cv2.imread(str(image))
            else:
                # 使用提供的图像
                img = image
            
            if img is None:
                self.logger.error(f"无法加载图像: {image}")
                return False
            
            # 截取指定区域
            if region:
                x, y, w, h = region
                img = img[y:y+h, x:x+w]
            
            # 保存模板
            cv2.imwrite(str(template_path), img)
            self.logger.info(f"模板已保存: {template_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存模板失败: {template_name} - {e}")
            return False
    
    def capture_and_save_template(self, template_name, region=None):
        """
        截屏并保存为模板
        :param template_name: 模板名称
        :param region: 截取区域
        :return: 是否成功
        """
        screenshot = self.capture_screen(region=region)
        if screenshot is None:
            return False
        
        return self.save_template(screenshot, template_name)

# 预定义的模板名称（用于游戏界面识别）
TEMPLATES = {
    # 原神相关
    'genshin_launch_button': 'genshin_launch.png',  # BetterGI启动按钮
    'genshin_login_screen': 'genshin_login.png',    # 登录界面
    'genshin_main_menu': 'genshin_menu.png',        # 主菜单
    'genshin_daily_quests': 'genshin_daily.png',    # 日常任务界面
    'genshin_claim_reward': 'genshin_claim.png',    # 领取奖励按钮
    
    # 绝区零相关
    'zzz_launch_button': 'zzz_launch.png',          # 启动按钮
    'zzz_login_screen': 'zzz_login.png',            # 登录界面
    'zzz_main_menu': 'zzz_menu.png',                # 主菜单
    'zzz_daily_quests': 'zzz_daily.png',            # 日常任务界面
    
    # 通用
    'close_button': 'close.png',                    # 关闭按钮
    'confirm_button': 'confirm.png',                # 确认按钮
    'cancel_button': 'cancel.png',                  # 取消按钮
}

def test_image_recognition():
    """测试图像识别功能"""
    print("测试图像识别功能...")
    
    if not OPENCV_AVAILABLE:
        print("❌ OpenCV未安装，无法测试")
        print("安装命令: pip install opencv-python pillow pyautogui numpy")
        return False
    
    recognizer = ImageRecognizer({'enabled': True})
    
    if not recognizer.enabled:
        print("❌ 图像识别未启用")
        return False
    
    # 测试截屏
    print("1. 测试截屏...")
    screenshot = recognizer.capture_screen(save_path='test_screenshot.png')
    if screenshot is not None:
        print(f"✅ 截屏成功，尺寸: {screenshot.shape[1]}x{screenshot.shape[0]}")
    else:
        print("❌ 截屏失败")
        return False
    
    # 测试保存模板
    print("\n2. 测试保存模板...")
    success = recognizer.capture_and_save_template('test_template.png', region=(100, 100, 200, 200))
    if success:
        print("✅ 模板保存成功")
    else:
        print("❌ 模板保存失败")
    
    # 测试颜色检查
    print("\n3. 测试颜色检查...")
    # 获取屏幕中心点颜色
    screen_width, screen_height = pyautogui.size()
    center_x, center_y = screen_width // 2, screen_height // 2
    
    color_match = recognizer.check_color_at_point(center_x, center_y, (0, 0, 0), tolerance=50)
    print(f"中心点颜色检查: {'匹配' if color_match else '不匹配'}")
    
    print("\n✅ 图像识别测试完成")
    return True

if __name__ == '__main__':
    test_image_recognition()