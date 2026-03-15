import time
import win32gui
import win32con
import subprocess
import os
from typing import List, Dict, Callable, Optional, Any
from loguru import logger
from .screen_capture import ScreenCapture
from .ocr_recognizer import OCRRecognizer
from .input_controller import InputController
from .retry_manager import RetryManager


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
        self.input_controller = InputController(
            click_delay=config.get('click_delay', 0.2),
            type_delay=config.get('type_delay', 0.05)
        )
        self.retry_manager = RetryManager(
            max_retries=config.get('max_retries', 3),
            retry_delay=config.get('retry_delay', 1)
        )
        
        # 游戏按钮配置，子类需要覆盖
        self.buttons: Dict[str, str] = {}
        # 游戏操作步骤，子类需要覆盖
        self.task_steps: List[Dict] = []
        
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
        
        self.input_controller.click(int(x), int(y), double=double)
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
                self.input_controller.press_key(step['key'])
                return True
            elif step_type == 'hotkey':
                self.input_controller.hotkey(*step['keys'])
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
        total_steps = len(self.task_steps)
        
        for i, step in enumerate(self.task_steps, 1):
            logger.info(f"步骤 [{i}/{total_steps}]")
            result = self.retry_manager.run(lambda: self.execute_step(step))
            
            if not result:
                logger.error(f"任务失败，第{i}步执行失败")
                return False
            
            success_count += 1
        
        logger.info(f"任务执行完成，成功{success_count}/{total_steps}步")
        return True


class MultiAppBase:
    """多应用切换自动化基类，适用于需要多个软件配合的场景"""
    
    def __init__(self, config: Dict):
        """
        初始化多应用自动化
        :param config: 配置包含apps字段，定义所有需要用到的应用
        """
        self.config = config
        self.apps_config = config.get('apps', {})
        if not self.apps_config:
            raise ValueError("多应用配置不能为空，请在配置中添加apps字段")
        
        # 全局组件
        self.ocr = OCRRecognizer(use_gpu=config.get('use_gpu', True))
        self.input_controller = InputController(
            click_delay=config.get('click_delay', 0.2),
            type_delay=config.get('type_delay', 0.05)
        )
        self.retry_manager = RetryManager(
            max_retries=config.get('max_retries', 3),
            retry_delay=config.get('retry_delay', 1)
        )
        
        # 应用状态管理
        self.app_states: Dict[str, Dict[str, Any]] = {}  # 每个应用的状态
        self.active_app: Optional[str] = None  # 当前活跃的应用
        self.active_capture: Optional[ScreenCapture] = None  # 当前应用的截图实例
        
        # 操作步骤，子类需要覆盖
        self.task_steps: List[Dict] = []
        
        logger.info(f"初始化多应用自动化，包含应用: {list(self.apps_config.keys())}")
    
    def launch_app(self, app_name: str, timeout: int = 30) -> bool:
        """
        启动指定应用
        :param app_name: 应用名称，对应配置里的key
        :param timeout: 等待窗口超时时间（秒）
        :return: 是否启动成功
        """
        if app_name not in self.apps_config:
            logger.error(f"应用[{app_name}]未在配置中定义")
            return False
        
        app_config = self.apps_config[app_name]
        app_path = app_config.get('app_path')
        window_title = app_config.get('window_title')
        
        if not app_path or not os.path.exists(app_path):
            logger.error(f"应用[{app_name}]路径不存在: {app_path}")
            return False
        
        if not window_title:
            logger.error(f"应用[{app_name}]未配置窗口标题")
            return False
        
        # 检查是否已经运行
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            logger.info(f"应用[{app_name}]已经在运行，直接激活")
            self.app_states[app_name] = {
                'hwnd': hwnd,
                'window_title': window_title,
                'running': True
            }
            return self.switch_app(app_name)
        
        # 启动应用
        logger.info(f"启动应用[{app_name}]: {app_path}")
        try:
            subprocess.Popen(app_path)
        except Exception as e:
            logger.error(f"启动应用[{app_name}]失败: {str(e)}")
            return False
        
        # 等待窗口出现
        logger.info(f"等待应用[{app_name}]窗口加载...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            hwnd = win32gui.FindWindow(None, window_title)
            if hwnd:
                self.app_states[app_name] = {
                    'hwnd': hwnd,
                    'window_title': window_title,
                    'running': True
                }
                logger.info(f"应用[{app_name}]启动成功")
                return self.switch_app(app_name)
            time.sleep(1)
        
        logger.error(f"等待应用[{app_name}]窗口超时")
        return False
    
    def switch_app(self, app_name: str) -> bool:
        """
        切换到指定应用，激活窗口
        :param app_name: 应用名称
        :return: 是否切换成功
        """
        if app_name not in self.app_states or not self.app_states[app_name]['running']:
            logger.error(f"应用[{app_name}]未运行，请先启动")
            return False
        
        app_state = self.app_states[app_name]
        hwnd = app_state['hwnd']
        window_title = app_state['window_title']
        
        try:
            # 激活窗口
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            
            # 更新当前应用和截图实例
            self.active_app = app_name
            self.active_capture = ScreenCapture(window_title)
            logger.info(f"切换到应用[{app_name}]成功")
            return True
        except Exception as e:
            logger.error(f"切换到应用[{app_name}]失败: {str(e)}")
            return False
    
    def close_app(self, app_name: str, force: bool = False) -> bool:
        """
        关闭指定应用
        :param app_name: 应用名称
        :param force: 是否强制关闭
        :return: 是否关闭成功
        """
        if app_name not in self.app_states or not self.app_states[app_name]['running']:
            logger.info(f"应用[{app_name}]未运行，无需关闭")
            return True
        
        app_state = self.app_states[app_name]
        hwnd = app_state['hwnd']
        
        try:
            if force:
                # 强制关闭
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            else:
                # 尝试正常关闭
                win32gui.SendMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            
            # 等待关闭
            for _ in range(10):
                if not win32gui.IsWindow(hwnd):
                    break
                time.sleep(0.5)
            
            self.app_states[app_name]['running'] = False
            if self.active_app == app_name:
                self.active_app = None
                self.active_capture = None
            
            logger.info(f"应用[{app_name}]已关闭")
            return True
        except Exception as e:
            logger.error(f"关闭应用[{app_name}]失败: {str(e)}")
            return False
    
    def wait_for_text(self, target_text: str, timeout: int = 10, 
                     threshold: float = 0.8, interval: float = 0.5) -> Optional[Dict]:
        """等待当前应用中出现指定文本"""
        if not self.active_capture:
            logger.error("没有活跃应用，请先切换到对应应用")
            return None
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            img = self.active_capture.capture()
            res = self.ocr.find_text(img, target_text, threshold)
            if res:
                return res
            time.sleep(interval)
        
        logger.warning(f"等待文本超时: {target_text}")
        return None
    
    def click_text(self, target_text: str, timeout: int = 10, 
                  threshold: float = 0.8, double: bool = False) -> bool:
        """点击当前应用中的指定文本"""
        if not self.active_capture or not self.active_app:
            logger.error("没有活跃应用，请先切换到对应应用")
            return False
        
        res = self.wait_for_text(target_text, timeout, threshold)
        if not res:
            logger.error(f"点击失败，未找到文本: {target_text}")
            return False
        
        x, y = res['center']
        # 转屏幕坐标
        app_state = self.app_states[self.active_app]
        left, top, _, _ = win32gui.GetWindowRect(app_state['hwnd'])
        screen_x = int(left + x)
        screen_y = int(top + y)
        
        self.input_controller.click(screen_x, screen_y, double=double)
        logger.info(f"点击文本成功: [{target_text}] 位置: ({screen_x}, {screen_y})")
        return True
    
    def execute_step(self, step: Dict) -> bool:
        """
        执行单个操作步骤，支持多应用相关步骤
        新增步骤类型:
        - launch_app: 启动应用 {"type": "launch_app", "app_name": "应用名", "timeout": 30}
        - switch_app: 切换应用 {"type": "switch_app", "app_name": "应用名"}
        - close_app: 关闭应用 {"type": "close_app", "app_name": "应用名", "force": false}
        - 其他步骤和GameBase一致: click/wait/sleep/press/hotkey/custom
        """
        step_type = step.get('type')
        step_name = step.get('name', f'未命名步骤({step_type})')
        logger.info(f"执行步骤: {step_name}")
        
        try:
            # 多应用专属步骤
            if step_type == 'launch_app':
                return self.launch_app(step['app_name'], timeout=step.get('timeout', 30))
            
            elif step_type == 'switch_app':
                return self.switch_app(step['app_name'])
            
            elif step_type == 'close_app':
                return self.close_app(step['app_name'], force=step.get('force', False))
            
            # 通用操作步骤，需要当前有活跃应用
            if not self.active_app:
                logger.error("执行操作步骤前请先切换到对应应用")
                return False
            
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
                self.input_controller.press_key(step['key'])
                return True
            elif step_type == 'hotkey':
                self.input_controller.hotkey(*step['keys'])
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
        logger.info("开始执行多应用自动化任务")
        success_count = 0
        total_steps = len(self.task_steps)
        
        for i, step in enumerate(self.task_steps, 1):
            logger.info(f"步骤 [{i}/{total_steps}]")
            result = self.retry_manager.run(lambda: self.execute_step(step))
            
            if not result:
                logger.error(f"任务失败，第{i}步执行失败")
                return False
            
            success_count += 1
        
        logger.info(f"任务执行完成，成功{success_count}/{total_steps}步")
        return True
