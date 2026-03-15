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
from ..utils.telegram_notifier import TelegramNotifier


import win32api
import win32process
import ctypes

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
        
        # 初始化通知器
        self.telegram_notifier = TelegramNotifier(global_config.get('telegram', {}))
        
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
            
            # 新增Win32消息/控件操作步骤
            elif step_type == 'send_app_message':
                return self.send_app_message(
                    step['msg'],
                    wparam=step.get('wparam', 0),
                    lparam=step.get('lparam', 0),
                    app_name=step.get('app_name'),
                    use_post=step.get('use_post', False)
                )
            elif step_type == 'send_app_key':
                return self.send_app_key(
                    step['key_code'],
                    app_name=step.get('app_name'),
                    press=step.get('press', True)
                )
            elif step_type == 'find_control':
                control_hwnd = self.find_child_control(
                    app_name=step.get('app_name'),
                    class_name=step.get('class_name'),
                    window_title=step.get('window_title'),
                    control_id=step.get('control_id')
                )
                if control_hwnd:
                    # 保存找到的控件句柄到step_result，供后续步骤使用
                    step['_result'] = control_hwnd
                    return True
                return False
            elif step_type == 'send_control_message':
                # 支持直接传入control_hwnd或者从之前步骤获取
                control_hwnd = step.get('control_hwnd') or step.get('_previous_result')
                if not control_hwnd:
                    logger.error("未指定控件句柄，且无前置步骤结果")
                    return False
                return self.send_control_message(
                    control_hwnd,
                    step['msg'],
                    wparam=step.get('wparam', 0),
                    lparam=step.get('lparam', 0),
                    use_post=step.get('use_post', False)
                )
            elif step_type == 'set_control_text':
                control_hwnd = step.get('control_hwnd') or step.get('_previous_result')
                if not control_hwnd:
                    logger.error("未指定控件句柄，且无前置步骤结果")
                    return False
                return self.set_control_text(control_hwnd, step['text'])
            elif step_type == 'click_control':
                control_hwnd = step.get('control_hwnd') or step.get('_previous_result')
                if not control_hwnd:
                    logger.error("未指定控件句柄，且无前置步骤结果")
                    return False
                return self.click_control(control_hwnd)
            
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
    
    def send_message(self, text: str, parse_mode: str = 'Markdown', disable_notification: bool = False) -> bool:
        """
        发送文本消息到通知渠道
        :param text: 消息内容
        :param parse_mode: 解析模式（Markdown/HTML）
        :param disable_notification: 是否静默发送
        :return: 是否发送成功
        """
        return self.telegram_notifier.send_message(text, parse_mode, disable_notification)
    
    def send_photo(self, photo_path: str, caption: str = '', disable_notification: bool = False) -> bool:
        """
        发送图片到通知渠道
        :param photo_path: 图片路径
        :param caption: 图片说明
        :param disable_notification: 是否静默发送
        :return: 是否发送成功
        """
        return self.telegram_notifier.send_photo(photo_path, caption, disable_notification)
    
    def notify_task_status(self, task_name: str, status: str, duration: float = 0, error_msg: str = '') -> bool:
        """
        快捷发送任务状态通知
        :param task_name: 任务名称
        :param status: 状态：start/complete/success/fail/error
        :param duration: 耗时（秒）
        :param error_msg: 错误信息（失败时必填）
        :return: 是否发送成功
        """
        if status == 'start':
            return self.telegram_notifier.notify_task_start(task_name)
        elif status == 'complete' or status == 'success':
            return self.telegram_notifier.notify_task_complete(task_name, duration, success=True)
        elif status == 'fail' or status == 'error':
            return self.telegram_notifier.notify_task_error(task_name, error_msg)
        else:
            logger.warning(f"未知的通知状态: {status}")
            return False
    
    def send_app_message(self, msg: int, wparam: int = 0, lparam: int = 0, 
                        app_name: Optional[str] = None, use_post: bool = False) -> bool:
        """
        给指定应用发送Win32 API消息
        :param msg: 消息类型，如win32con.WM_CLOSE/WM_KEYDOWN等
        :param wparam: WPARAM参数
        :param lparam: LPARAM参数
        :param app_name: 应用名称，不传则使用当前活跃应用
        :param use_post: 是否使用PostMessage（异步，不等待返回），默认SendMessage（同步）
        :return: 是否发送成功
        """
        # 确定目标应用
        target_app = app_name or self.active_app
        if not target_app:
            logger.error("未指定应用且当前无活跃应用，请传入app_name参数")
            return False
        
        if target_app not in self.app_states or not self.app_states[target_app]['running']:
            logger.error(f"应用[{target_app}]未运行，请先启动")
            return False
        
        hwnd = self.app_states[target_app]['hwnd']
        window_title = self.app_states[target_app]['window_title']
        
        try:
            if use_post:
                # 异步发送，不等待返回
                win32gui.PostMessage(hwnd, msg, wparam, lparam)
                logger.debug(f"异步发送Win32消息成功: 应用[{window_title}] 消息: 0x{msg:X} wparam: {wparam} lparam: {lparam}")
            else:
                # 同步发送，等待返回结果
                result = win32gui.SendMessage(hwnd, msg, wparam, lparam)
                logger.debug(f"同步发送Win32消息成功: 应用[{window_title}] 消息: 0x{msg:X} 返回值: {result}")
            
            return True
        except Exception as e:
            logger.error(f"发送Win32消息失败: 应用[{window_title}] 错误: {str(e)}")
            return False
    
    def send_app_key(self, key_code: int, app_name: Optional[str] = None, press: bool = True) -> bool:
        """
        给应用发送键盘按键消息
        :param key_code: 按键码，如win32con.VK_RETURN/VK_SPACE等
        :param app_name: 应用名称，不传则使用当前活跃应用
        :param press: True为按下（WM_KEYDOWN），False为松开（WM_KEYUP）
        :return: 是否发送成功
        """
        msg = win32con.WM_KEYDOWN if press else win32con.WM_KEYUP
        return self.send_app_message(msg, wparam=key_code, lparam=0, app_name=app_name, use_post=True)
    
    def close_app_by_message(self, app_name: Optional[str] = None, force: bool = False) -> bool:
        """
        通过发送WM_CLOSE消息关闭应用（替代之前的关闭方法，更稳定）
        :param app_name: 应用名称，不传则使用当前活跃应用
        :param force: 是否强制关闭（发送WM_DESTROY）
        :return: 是否发送成功
        """
        msg = win32con.WM_DESTROY if force else win32con.WM_CLOSE
        return self.send_app_message(msg, app_name=app_name, use_post=True)
    
    def find_child_control(self, app_name: Optional[str] = None, 
                          class_name: Optional[str] = None, 
                          window_title: Optional[str] = None,
                          control_id: Optional[int] = None) -> Optional[int]:
        """
        查找应用内的子控件句柄
        :param app_name: 应用名称，不传则使用当前活跃应用
        :param class_name: 控件类名（如"Edit"、"Button"）
        :param window_title: 控件标题/文本
        :param control_id: 控件ID（可通过Spy++等工具获取）
        :return: 找到的控件句柄，找不到返回None
        """
        # 确定目标应用
        target_app = app_name or self.active_app
        if not target_app:
            logger.error("未指定应用且当前无活跃应用，请传入app_name参数")
            return None
        
        if target_app not in self.app_states or not self.app_states[target_app]['running']:
            logger.error(f"应用[{target_app}]未运行，请先启动")
            return None
        
        parent_hwnd = self.app_states[target_app]['hwnd']
        found_hwnd = None
        
        def enum_child_callback(hwnd, _):
            nonlocal found_hwnd
            # 按控件ID匹配
            if control_id is not None:
                current_id = win32gui.GetDlgCtrlID(hwnd)
                if current_id == control_id:
                    found_hwnd = hwnd
                    return False  # 停止枚举
            # 按类名和标题匹配
            match = True
            if class_name is not None:
                current_class = win32gui.GetClassName(hwnd)
                if current_class != class_name:
                    match = False
            if window_title is not None:
                current_title = win32gui.GetWindowText(hwnd)
                if current_title != window_title:
                    match = False
            if match:
                found_hwnd = hwnd
                return False  # 停止枚举
            return True
        
        try:
            win32gui.EnumChildWindows(parent_hwnd, enum_child_callback, None)
            if found_hwnd:
                logger.debug(f"找到子控件: 句柄=0x{found_hwnd:X} 类名={win32gui.GetClassName(found_hwnd)} 标题={win32gui.GetWindowText(found_hwnd)}")
            else:
                logger.warning(f"未找到子控件: 类名={class_name} 标题={window_title} ID={control_id}")
            return found_hwnd
        except Exception as e:
            logger.error(f"查找子控件失败: {str(e)}")
            return None
    
    def send_control_message(self, control_hwnd: int, msg: int, 
                           wparam: int = 0, lparam: int = 0, 
                           use_post: bool = False) -> bool:
        """
        给指定控件发送Win32消息
        :param control_hwnd: 控件句柄（通过find_child_control获取）
        :param msg: 消息类型
        :param wparam: WPARAM参数
        :param lparam: LPARAM参数
        :param use_post: 是否使用PostMessage异步发送
        :return: 是否发送成功
        """
        if not control_hwnd or not win32gui.IsWindow(control_hwnd):
            logger.error(f"无效的控件句柄: 0x{control_hwnd:X}")
            return False
        
        try:
            if use_post:
                win32gui.PostMessage(control_hwnd, msg, wparam, lparam)
                logger.debug(f"异步发送控件消息成功: 句柄=0x{control_hwnd:X} 消息=0x{msg:X}")
            else:
                result = win32gui.SendMessage(control_hwnd, msg, wparam, lparam)
                logger.debug(f"同步发送控件消息成功: 句柄=0x{control_hwnd:X} 消息=0x{msg:X} 返回值={result}")
            return True
        except Exception as e:
            logger.error(f"发送控件消息失败: 句柄=0x{control_hwnd:X} 错误={str(e)}")
            return False
    
    def set_control_text(self, control_hwnd: int, text: str) -> bool:
        """
        设置输入框/文本控件的内容
        :param control_hwnd: 控件句柄
        :param text: 要设置的文本
        :return: 是否设置成功
        """
        return self.send_control_message(control_hwnd, win32con.WM_SETTEXT, 0, text)
    
    def click_control(self, control_hwnd: int) -> bool:
        """
        点击按钮控件
        :param control_hwnd: 按钮控件句柄
        :return: 是否点击成功
        """
        # 发送BM_CLICK消息点击按钮
        return self.send_control_message(control_hwnd, win32con.BM_CLICK, 0, 0, use_post=True)
