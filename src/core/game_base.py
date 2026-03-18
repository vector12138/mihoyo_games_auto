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


import win32api
import win32process
import ctypes
from .control_operator import ControlOperator, ControlInfo

# 第一步：设置系统权限（允许设置前台窗口）

class MultiAppBase:
    """多应用切换自动化基类，适用于需要多个软件配合的场景"""
    
    def __init__(self, config: Dict, global_config: Dict):
        """
        初始化多应用自动化
        :param config: 配置包含apps字段，定义所有需要用到的应用
        """
        self.config = config
        self.global_config = global_config
        self.apps_config = config.get('apps', {})
        if not self.apps_config:
            raise ValueError("多应用配置不能为空，请在配置中添加apps字段")
        
        # 全局组件
        self.ocr = OCRRecognizer(use_gpu=global_config.get('use_gpu', True), 
                                 debug=global_config.get('debug', False))
        
        self.input_controller = InputController(
            click_delay=global_config.get('click_delay', 0.2),
            type_delay=global_config.get('type_delay', 0.05)
        )
        self.retry_manager = RetryManager(global_config)
        
        # 控件操作器
        self.control_operator = ControlOperator(global_config.get('control_operator', {}))
        
        # 应用状态管理
        self.app_states: Dict[str, Dict[str, Any]] = {}  # 每个应用的状态
        self.active_app: Optional[str] = None  # 当前活跃的应用
        self.active_capture: Optional[ScreenCapture] = None  # 当前应用的截图实例
        
        # 操作步骤，子类需要覆盖
        self.task_steps: List[Dict] = []
        
        logger.info(f"初始化多应用自动化，包含应用: {list(self.apps_config.keys())}")

    # 第二步：组合操作切换窗口（Alt键 + 恢复窗口 + 强制前台）
    def _force_set_foreground(self, hwnd):
        # 1. 前置：确保窗口有效且未最小化
        if not win32gui.IsWindow(hwnd):
            return False, "窗口句柄无效"
        if win32gui.IsIconic(hwnd):  # 如果窗口最小化，先恢复
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.1)  # 等待窗口恢复
        
        # 2. 获取前台权限（核心：模拟Alt键 + 权限设置）
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        # 获取当前进程ID
        pid = win32process.GetCurrentProcessId()
        # 允许当前进程设置前台窗口（参数为0表示允许所有进程，也可填当前pid）
        user32.AllowSetForegroundWindow(pid)
        # 另一个关键API：解除前台窗口锁定
        user32.SystemParametersInfoW(win32con.SPI_SETFOREGROUNDLOCKTIMEOUT, 0, 0, 0)
        # 发送Alt键按下+松开（让系统认为当前进程有用户交互）
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.1)
        
        # 3. 尝试多种方式切换前台
        # 方式1：SetForegroundWindow
        res1 = win32gui.SetForegroundWindow(hwnd)
        # 方式2：BringWindowToTop（备用）
        win32gui.BringWindowToTop(hwnd)
        # 方式3：SetActiveWindow（补充）
        win32gui.SetActiveWindow(hwnd)
        
        # 验证：检查是否真的切换成功
        current_foreground_hwnd = win32gui.GetForegroundWindow()
        if current_foreground_hwnd != hwnd:
            raise ValueError(f"切换失败，当前前台窗口句柄：{current_foreground_hwnd}（目标：{hwnd}）")
        
    def _find_windows_by_title(self, keyword: str) -> List[int]:
        """
        查找标题中包含指定关键词的所有窗口
        返回窗口句柄列表
        :param keyword: 窗口标题中包含的关键词
        :return: 包含所有匹配窗口句柄的列表
        """
        hwnds = []
        
        def callback(hwnd, _):
            title = win32gui.GetWindowText(hwnd)
            if keyword in title:  # 使用 in 进行模糊匹配
                hwnds.append(hwnd)
        
        win32gui.EnumWindows(callback, None)

        return hwnds
    
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
        app_path = app_config.get('app_path', '')
        window_title = app_config.get('window_title')
        notify_window = app_config.get('notify_window', False)
        
        if (not app_path or not os.path.exists(app_path)) and not notify_window:
            logger.error(f"应用[{window_title}]路径不存在: {app_path}")
            return False
        
        if not window_title:
            logger.error(f"应用[{window_title}]未配置窗口标题")
            return False
        
        # 检查是否已经运行
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            logger.info(f"应用[{window_title}]已经在运行，直接激活")
            self.app_states[app_name] = {
                'hwnd': hwnd,
                'window_title': window_title,
                'running': True
            }
            return self.switch_app(app_name)
        
        # 启动应用
        if not notify_window:
            logger.info(f"启动应用[{window_title}]: {app_path}")
            try:
                subprocess.Popen(app_path)
            except Exception as e:
                logger.error(f"启动应用[{window_title}]失败: {str(e)}")
                return False
        
        # 等待窗口出现
        logger.info(f"等待应用[{window_title}]窗口加载...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            hwnds = self._find_windows_by_title(window_title)
            if hwnds:
                hwnd = hwnds[0]
                self.app_states[app_name] = {
                    'hwnd': hwnd,
                    'window_title': window_title,
                    'running': True
                }
                logger.info(f"应用[{window_title}]启动成功")
                return self.switch_app(app_name)
            
            time.sleep(1)
        
        logger.error(f"等待应用[{window_title}]窗口超时")
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
            self._force_set_foreground(hwnd)
            time.sleep(0.5)
            
            # 更新当前应用和截图实例
            self.active_app = app_name
            self.active_capture = ScreenCapture(hwnd)
            logger.info(f"切换到应用[{window_title}]成功")
            return True
        except Exception as e:
            logger.error(f"切换到应用[{window_title}]失败: {str(e)}")
            return False
    
    def close_app(self, app_name: str, force: bool = False) -> bool:
        """
        关闭指定应用
        :param app_name: 应用名称
        :param force: 是否强制关闭
        :return: 是否关闭成功
        """
        window_title = self.apps_config[app_name].get('window_title')

        if app_name not in self.app_states or not self.app_states[app_name]['running']:
            logger.info(f"应用[{window_title}]未运行，无需关闭")
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
            
            logger.info(f"应用[{window_title}]已关闭")
            return True
        except Exception as e:
            logger.error(f"关闭应用[{window_title}]失败: {str(e)}")
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
                  threshold: float = 0.8, double: bool = False, interval: float = 0.5) -> bool:
        """点击当前应用中的指定文本"""
        if not self.active_capture or not self.active_app:
            logger.error("没有活跃应用，请先切换到对应应用")
            return False
        
        res = self.wait_for_text(target_text, timeout, threshold, interval)
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
        - click/wait/sleep/press/hotkey/custom
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
                    double=step.get('double', False),
                    interval=step.get('interval', 0.5)
                )
            elif step_type == 'wait':
                return self.wait_for_text(
                    step['text'],
                    timeout=step.get('timeout', 10),
                    interval=step.get('interval', 0.5)
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
            
            # 新增控件操作步骤（使用新的控件操作器）
            elif step_type == 'find_control':
                # 查找控件，支持Win32和UIA控件
                properties = step.get('properties', {})
                if not properties:
                    # 兼容旧格式
                    properties = {
                        'source': step.get('source', 'win32'),
                        'class_name': step.get('class_name'),
                        'window_text': step.get('window_text'),
                        'name': step.get('name'),
                        'control_type': step.get('control_type'),
                        'automation_id': step.get('automation_id'),
                        'control_id': step.get('control_id')
                    }
                
                control_info = self.find_control(
                    app_name=step.get('app_name'),
                    properties=properties
                )
                if control_info:
                    # 保存找到的控件信息到step_result，供后续步骤使用
                    step['_result'] = control_info
                    return True
                return False
            
            elif step_type == 'click_control_by_properties':
                # 根据属性点击控件
                properties = step.get('properties', {})
                if not properties:
                    logger.error("未指定控件属性")
                    return False
                
                return self.click_control_by_properties(
                    app_name=step.get('app_name'),
                    properties=properties,
                    double=step.get('double', False)
                )
            
            elif step_type == 'send_text_to_control_by_properties':
                # 根据属性给控件发送文本
                properties = step.get('properties', {})
                if not properties:
                    logger.error("未指定控件属性")
                    return False
                
                return self.send_text_to_control_by_properties(
                    app_name=step.get('app_name'),
                    properties=properties,
                    text=step.get('text', '')
                )
            
            elif step_type == 'find_control_by_hierarchy':
                # 层级查找控件
                hierarchy = step.get('hierarchy', [])
                if not hierarchy:
                    logger.error("未指定层级查找条件")
                    return False
                
                control_info = self.find_control_by_hierarchy(
                    app_name=step.get('app_name'),
                    hierarchy=hierarchy
                )
                if control_info:
                    # 保存找到的控件信息到step_result
                    step['_result'] = control_info
                    return True
                return False
            
            elif step_type == 'click_control_by_hierarchy':
                # 层级查找控件并点击，一步完成
                hierarchy = step.get('hierarchy', [])
                if not hierarchy:
                    logger.error("未指定层级查找条件")
                    return False
                
                control_info = self.find_control_by_hierarchy(
                    app_name=step.get('app_name'),
                    hierarchy=hierarchy
                )
                if not control_info:
                    return False
                
                return self.control_operator.click(
                    control_info, 
                    double=step.get('double', False)
                )
            
            elif step_type == 'send_text_to_control_by_hierarchy':
                # 层级查找控件并发送文本，一步完成
                hierarchy = step.get('hierarchy', [])
                text = step.get('text', '')
                if not hierarchy:
                    logger.error("未指定层级查找条件")
                    return False
                
                control_info = self.find_control_by_hierarchy(
                    app_name=step.get('app_name'),
                    hierarchy=hierarchy
                )
                if not control_info:
                    return False
                
                return self.control_operator.send_text(
                    control_info, 
                    text
                )
            
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
            result = self.retry_manager.retry(lambda: self.execute_step(step))
            
            if not result:
                logger.error(f"任务失败，第{i}步执行失败")
                continue
            
            success_count += 1
        
        logger.info(f"任务执行完成，成功{success_count}/{total_steps}步")
        return True
    
    def find_control(self, app_name: Optional[str] = None, properties: Dict = None) -> Optional[ControlInfo]:
        """
        查找控件，支持Win32和UIA控件
        :param app_name: 应用名称，不传则使用当前活跃应用
        :param properties: 控件属性字典，可包含：
            - source: "win32" 或 "uia"
            - class_name: 类名
            - window_text: 窗口文本
            - name: UIA控件名称
            - control_type: UIA控件类型
            - automation_id: UIA自动化ID
            - control_id: Win32控件ID
        :return: 找到的控件信息，找不到返回None
        """
        if not properties:
            logger.error("未指定控件属性")
            return None
        
        # 确定目标应用
        target_app = app_name or self.active_app
        if not target_app:
            logger.error("未指定应用且当前无活跃应用，请传入app_name参数")
            return None
        
        if target_app not in self.app_states or not self.app_states[target_app]['running']:
            logger.error(f"应用[{target_app}]未运行，请先启动")
            return None
        
        hwnd = self.app_states[target_app]['hwnd']
        return self.control_operator.find_by_properties(hwnd, properties)
    
    def click_control_by_properties(self, app_name: Optional[str] = None, properties: Dict = None, double: bool = False) -> bool:
        """
        根据属性点击控件，支持Win32和UIA控件
        :param app_name: 应用名称，不传则使用当前活跃应用
        :param properties: 控件属性字典
        :param double: 是否双击
        :return: 是否成功
        """
        control_info = self.find_control(app_name, properties)
        if not control_info:
            logger.error(f"未找到控件: {properties}")
            return False
        
        return self.control_operator.click(control_info, double)
    
    def send_text_to_control_by_properties(self, app_name: Optional[str] = None, properties: Dict = None, text: str = "") -> bool:
        """
        根据属性给控件发送文本，支持Win32和UIA控件
        :param app_name: 应用名称，不传则使用当前活跃应用
        :param properties: 控件属性字典
        :param text: 要发送的文本
        :return: 是否成功
        """
        control_info = self.find_control(app_name, properties)
        if not control_info:
            logger.error(f"未找到控件: {properties}")
            return False
        
        return self.control_operator.send_text(control_info, text)
    
    # ===================== 层级查找功能封装 =====================
    def find_control_by_hierarchy(self, app_name: Optional[str] = None, hierarchy: List[Dict] = None) -> Optional[ControlInfo]:
        """
        层级查找控件，按照列表顺序一级一级查找，返回最后一级的控件
        :param app_name: 应用名称，不传则使用当前活跃应用
        :param hierarchy: 层级查找条件列表，每个元素是一级的属性字典
        :return: 最后一级找到的控件，任何一级找不到都返回None
        """
        if not hierarchy:
            logger.error("未指定层级查找条件")
            return None
        
        # 确定目标应用
        target_app = app_name or self.active_app
        if not target_app:
            logger.error("未指定应用且当前无活跃应用，请传入app_name参数")
            return False
        
        if target_app not in self.app_states or not self.app_states[target_app]['running']:
            logger.error(f"应用[{target_app}]未运行，请先启动")
            return False
        
        hwnd = self.app_states[target_app]['hwnd']
        return self.control_operator.find_by_hierarchy(hwnd, hierarchy)