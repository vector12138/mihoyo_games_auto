from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key
import time
from typing import Tuple, Optional
from loguru import logger


class InputController:
    """鼠标键盘输入控制器"""
    
    def __init__(self, click_delay: float = 0.2, type_delay: float = 0.05):
        """
        初始化控制器
        :param click_delay: 点击后的延迟时间（秒）
        :param type_delay: 打字每个字符的延迟时间（秒）
        """
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.click_delay = click_delay
        self.type_delay = type_delay
    
    def move_mouse(self, x: int, y: int):
        """移动鼠标到指定坐标"""
        self.mouse.position = (x, y)
        logger.debug(f"移动鼠标到: ({x}, {y})")
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None, 
             button: Button = Button.left, double: bool = False):
        """
        点击鼠标
        :param x: 点击位置x，不传则点击当前位置
        :param y: 点击位置y，不传则点击当前位置
        :param button: 鼠标按钮，默认左键
        :param double: 是否双击
        """
        if x is not None and y is not None:
            self.move_mouse(x, y)
        
        if double:
            self.mouse.click(button, 2)
            logger.debug(f"双击位置: ({x}, {y})")
        else:
            self.mouse.click(button, 1)
            logger.debug(f"点击位置: ({x}, {y})")
        
        time.sleep(self.click_delay)
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None):
        """右键点击"""
        self.click(x, y, Button.right)
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None):
        """双击"""
        self.click(x, y, double=True)
    
    def press_key(self, key: str | Key):
        """按下并释放单个按键"""
        self.keyboard.press(key)
        self.keyboard.release(key)
        logger.debug(f"按下按键: {key}")
        time.sleep(self.click_delay)
    
    def type_text(self, text: str):
        """输入文本"""
        self.keyboard.type(text, self.type_delay)
        logger.debug(f"输入文本: {text}")
        time.sleep(self.click_delay)
    
    def hotkey(self, *keys: str | Key):
        """按下组合键"""
        with self.keyboard.pressed(*keys):
            pass
        logger.debug(f"按下组合键: {'+'.join(map(str, keys))}")
        time.sleep(self.click_delay)
    
    def scroll(self, dx: int, dy: int):
        """滚动鼠标滚轮，dy>0向上滚动，dy<0向下滚动"""
        self.mouse.scroll(dx, dy)
        logger.debug(f"滚动鼠标: dx={dx}, dy={dy}")
        time.sleep(0.1)
