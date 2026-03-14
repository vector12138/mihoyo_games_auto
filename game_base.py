import time
import win32gui
from typing import List, Dict, Callable, Optional
from loguru import logger
from screen_capture import ScreenCapture
from ocr_recognizer import OCRRecognizer
from input_controller import InputController
from retry_manager import RetryManager


class GameBase:
    """游戏自动化基类，所有游戏继承此类实现"""
    
    def __init__(self, config: Dict):
        """
        初始化游戏
        :param config: 游戏配置
        """
        self.config = config
        self.game_name = config.get('game_name', 'Unknown')
        self.window_title = config.get('window_title', '')
        
        # 初始化核心组件
        self.screen_capture = ScreenCapture(self.window_title)
        self.ocr = OCRRecognizer(use_gpu=config.get('use_gpu', True))
        self.input = InputController(
            click_delay=config.get('click_delay', 0.2),
            type_delay=config.get('type_delay', 0.05)
        )
        self.retry = RetryManager(
            max_retries=config.get('max_retries', 3),
            retry_delay=config.get('retry_delay', 1)
        )
        
        # 游戏按钮配置，子类需要覆盖
        self.buttons: Dict[str, str] = {}
        # 游戏操作步骤，子类需要覆盖
        self.steps: List[Dict] = []
        
        logger.info(f"初始化游戏: {self.game_name}")
    
    def wait_for_text(self, target_text: str, timeout: int = 10, 
                     threshold: float = 0.8, interval: float = 0.5) -> Optional[Dict]:
        """
        等待指定文本出现
        :param target_text: 目标文本
        :param timeout: 超时时间（秒）
        :param threshold: 置信度阈值
        :param interval: 检查间隔（秒）
        :return: 匹配到的文本信息，超时返回None
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            img = self.screen_capture.capture()
            res = self.ocr.find_text(img, target_text, threshold)
            if res:
                return res
            time.sleep(interval)
        
        logger.warning(f"等待文本超时: {target_text}")
        return None
    
    def click_text(self, target_text: str, timeout: int = 10, 
                  threshold: float = 0.8, double: bool = False) -> bool:
        """
        点击指定文本
        :param target_text: 目标文本
        :param timeout: 超时时间
        :param threshold: 置信度阈值
        :param double: 是否双击
        :return: 是否点击成功
        """
        res = self.wait_for_text(target_text, timeout, threshold)
        if not res:
            logger.error(f"点击失败，未找到文本: {target_text}")
            return False
        
        x, y = res['center']
        # 窗口坐标转屏幕坐标（如果是窗口模式）
        if self.screen_capture.hwnd:
            left, top, _, _ = win32gui.GetWindowRect(self.screen_capture.hwnd)
            x += left
            y += top
        
        self.input.click(int(x), int(y), double=double)
        logger.info(f"点击文本成功: {target_text} 位置: ({int(x)}, {int(y)})")
        return True
    
    def execute_step(self, step: Dict) -> bool:
        """
        执行单个操作步骤
        :param step: 步骤配置
        支持的步骤类型:
        - click: 点击文本 {"type": "click", "text": "按钮文本", "timeout": 10}
        - wait: 等待文本出现 {"type": "wait", "text": "等待的文本", "timeout": 10}
        - sleep: 等待固定时间 {"type": "sleep", "seconds": 2}
        - press: 按下按键 {"type": "press", "key": "w"}
        - hotkey: 按下组合键 {"type": "hotkey", "keys": ["ctrl", "v"]}
        - custom: 自定义方法 {"type": "custom", "func": 方法名}
        """
        step_type = step.get('type')
        step_name = step.get('name', f'未命名步骤({step_type})')
        logger.info(f"执行步骤: {step_name}")
        
        try:
            if step_type == 'click':
                return self.click_text(
                    step['text'], 
                    timeout=step.get('timeout', 10),
                    double=step.get('double', False)
                )
            elif step_type == 'wait':
                return self.wait_for_text(
                    step['text'],
                    timeout=step.get('timeout', 10)
                ) is not None
            elif step_type == 'sleep':
                time.sleep(step.get('seconds', 1))
                return True
            elif step_type == 'press':
                self.input.press_key(step['key'])
                return True
            elif step_type == 'hotkey':
                self.input.hotkey(*step['keys'])
                return True
            elif step_type == 'custom':
                func = getattr(self, step['func'])
                return func()
            else:
                logger.error(f"未知步骤类型: {step_type}")
                return False
        except Exception as e:
            logger.error(f"步骤执行失败: {step_name} 错误: {str(e)}")
            return False
    
    def run(self) -> bool:
        """执行所有操作步骤"""
        logger.info(f"开始执行{self.game_name}自动化任务")
        success_count = 0
        total_steps = len(self.steps)
        
        for i, step in enumerate(self.steps, 1):
            logger.info(f"步骤 [{i}/{total_steps}]")
            result = self.retry.run(lambda: self.execute_step(step))
            
            if not result:
                logger.error(f"任务失败，第{i}步执行失败")
                return False
            
            success_count += 1
        
        logger.info(f"任务执行完成，成功{success_count}/{total_steps}步")
        return True
