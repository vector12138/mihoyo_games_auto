import time
import win32gui
import win32con
import subprocess
import os
from typing import List, Dict, Optional, Any
from loguru import logger
from .screen_capture import ScreenCapture
from .input_controller import InputController
from .retry_manager import RetryManager


import win32api
import win32process
import ctypes
from .control_operator import ControlOperator, ControlInfo

# Windows进程创建标志：独立进程，主程序退出不影响子进程
CREATE_NEW_PROCESS_GROUP = 0x00000200
DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000

# 尝试导入Telegram Bridge客户端
try:
    from ..telegram_bridge_api_client import get_telegram_bridge_client
    TELEGRAM_BRIDGE_AVAILABLE = True
except ImportError:
    TELEGRAM_BRIDGE_AVAILABLE = False
    logger.warning("Telegram Bridge模块不可用，相关功能将被禁用")

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
        ocr_enabled = global_config.get('ocr_enabled', True)
        if ocr_enabled:        
            from .ocr_recognizer import OCRRecognizer
            # 使能才加载OCR识别器
            self.ocr = OCRRecognizer(use_gpu=global_config.get('use_gpu', True),
                                     debug=global_config.get('debug', False))
            logger.info("OCR识别功能已启用")
        else:
            self.ocr = None
            logger.info("⚠️ OCR识别功能已禁用")
        
        self.input_controller = InputController(
            click_delay=global_config.get('click_delay', 0.2),
            type_delay=global_config.get('type_delay', 0.05)
        )
        self.retry_manager = RetryManager(global_config)
        
        # 控件操作器
        self.control_operator = ControlOperator(global_config.get('control_operator', {}))
        
        # Telegram Bridge客户端（如果可用）
        self.telegram_bridge_client = None
        if TELEGRAM_BRIDGE_AVAILABLE:
            try:
                self.telegram_bridge_client = get_telegram_bridge_client(global_config.get('telegram', {}))
                if self.telegram_bridge_client and self.telegram_bridge_client.enabled:
                    logger.info("Telegram Bridge客户端初始化成功")
            except Exception as e:
                logger.error(f"初始化Telegram Bridge客户端失败: {str(e)}")
                self.telegram_bridge_client = None
        
        # 应用状态管理
        self.app_states: Dict[str, Dict[str, Any]] = {}  # 每个应用的状态
        self.active_app: Optional[str] = None  # 当前活跃的应用
        self.active_capture: Optional[ScreenCapture] = None  # 当前应用的截图实例
        
        # 操作步骤，子类需要覆盖
        self.task_steps: List[Dict] = []
        
        # 步骤类型到处理方法的映射，子类可直接扩展无需修改execute_step
        self.step_handlers = {
            'launch_app': self._step_launch_app,
            'switch_app': self._step_switch_app,
            'close_app': self._step_close_app,
            'click': self._step_click,
            'wait': self._step_wait,
            'sleep': self._step_sleep,
            'press': self._step_press,
            'hotkey': self._step_hotkey,
            'run_command': self._step_run_command,
            'custom': self._step_custom,
            'find_control': self._step_find_control,
            'click_control_by_properties': self._step_click_control_by_properties,
            'send_text_to_control_by_properties': self._step_send_text_to_control_by_properties,
            'find_control_by_hierarchy': self._step_find_control_by_hierarchy,
            'click_control_by_hierarchy': self._step_click_control_by_hierarchy,
            'send_text_to_control_by_hierarchy': self._step_send_text_to_control_by_hierarchy,
            'send_telegram_message': self._step_send_telegram_message,
            'wait_for_telegram_text': self._step_wait_for_telegram_text,
        }
        
        logger.info(f"初始化多应用自动化，包含应用: {list(self.apps_config.keys())}")

    # 第二步：组合操作切换窗口（Alt键 + 恢复窗口 + 强制前台）
    def _force_set_foreground(self, hwnd):
        # 1. 前置：确保窗口有效且未最小化
        if not win32gui.IsWindow(hwnd):
            return False, "窗口句柄无效"
        if win32gui.IsIconic(hwnd):  # 如果窗口最小化，先恢复
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.1)  # 等待窗口恢复
        
        # 2. 核心权限获取（兼容计划任务/后台运行场景）
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        target_thread_id = None
        current_thread_id = None
        
        try:
            # 解除前台窗口锁定（计划任务场景关键，避免系统拦截）
            user32.SystemParametersInfoW(win32con.SPI_SETFOREGROUNDLOCKTIMEOUT, 0, ctypes.c_int(0), 0)
            
            # AttachThreadInput方案：将当前线程附加到目标窗口线程，获取焦点权限
            # 解决Session 0/计划任务下无焦点权限的问题
            target_thread_id = win32process.GetWindowThreadProcessId(hwnd)[0]
            current_thread_id = win32api.GetCurrentThreadId()
            
            if target_thread_id != current_thread_id:
                # 附加线程，共享输入队列
                user32.AttachThreadInput(current_thread_id, target_thread_id, True)
                # 允许目标进程和当前进程设置前台窗口
                user32.AllowSetForegroundWindow(win32process.GetWindowThreadProcessId(hwnd)[1])
                user32.AllowSetForegroundWindow(win32process.GetCurrentProcessId())
            
            # 模拟用户交互：发送Alt键，让系统认为有用户操作
            win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.1)
            
            # 3. 多方法尝试设置前台，兼容各种权限场景
            success = False
            # 方法1: 标准SetForegroundWindow
            try:
                win32gui.SetForegroundWindow(hwnd)
                success = True
            except:
                pass
            
            # 方法2: BringWindowToTop兜底
            if not success:
                try:
                    win32gui.BringWindowToTop(hwnd)
                    success = True
                except:
                    pass
            
            # 方法3: SetWindowPos强制置顶再取消置顶
            if not success:
                try:
                    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                    win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                    success = True
                except:
                    pass
            
            # 方法4: SetActiveWindow补充
            try:
                win32gui.SetActiveWindow(hwnd)
            except:
                pass
            
            time.sleep(0.1)
            
            # 计划任务场景下放宽验证：即使没完全拿到前台也继续执行（很多操作无需前台焦点）
            current_foreground_hwnd = win32gui.GetForegroundWindow()
            if current_foreground_hwnd != hwnd:
                logger.warning(f"未完全获取前台焦点，将继续执行：当前句柄{current_foreground_hwnd}，目标句柄{hwnd}")
            
            return True, "窗口激活完成"
        
        finally:
            # 必须清理：解除线程附加，避免影响系统其他窗口
            try:
                if target_thread_id and current_thread_id and target_thread_id != current_thread_id:
                    user32.AttachThreadInput(current_thread_id, target_thread_id, False)
            except:
                pass
        
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
    

    
    # ==================== 步骤执行私有方法 ====================
    def _step_launch_app(self, step: Dict) -> bool:
        """
        处理launch_app步骤（核心实现）
        :param step: 步骤配置，包含app_name、timeout等参数
        :return: 是否启动成功
        """
        app_name = step['app_name']
        timeout = step.get('timeout', 30)
        
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
            return self._step_switch_app({'app_name': app_name})
        
        # 启动应用
        if not notify_window:
            logger.info(f"启动应用[{window_title}]: {app_path}")
            try:
                # 计划任务场景兼容启动标志：CREATE_BREAKAWAY_FROM_JOB 脱离任务计划程序的Job限制
                # 避免计划任务终止时连带关闭启动的应用，同时解决Session下启动权限问题
                creation_flags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
                if os.name == 'nt':
                    # Windows特有的标志，允许脱离Job对象
                    creation_flags |= 0x00000010  # CREATE_BREAKAWAY_FROM_JOB
                
                # 优先使用ShellExecute启动（兼容快捷方式、URL、各种文件类型，权限更友好）
                import ctypes
                shell32 = ctypes.windll.shell32
                # ShellExecuteEx参数
                SEE_MASK_NOCLOSEPROCESS = 0x00000040
                SW_SHOWNORMAL = 1
                
                class SHELLEXECUTEINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", ctypes.c_ulong),
                        ("fMask", ctypes.c_ulong),
                        ("hwnd", ctypes.c_void_p),
                        ("lpVerb", ctypes.c_wchar_p),
                        ("lpFile", ctypes.c_wchar_p),
                        ("lpParameters", ctypes.c_wchar_p),
                        ("lpDirectory", ctypes.c_wchar_p),
                        ("nShow", ctypes.c_int),
                        ("hInstApp", ctypes.c_void_p),
                        ("lpIDList", ctypes.c_void_p),
                        ("lpClass", ctypes.c_wchar_p),
                        ("hkeyClass", ctypes.c_void_p),
                        ("dwHotKey", ctypes.c_ulong),
                        ("hIcon", ctypes.c_void_p),
                        ("hProcess", ctypes.c_void_p),
                    ]
                
                sei = SHELLEXECUTEINFO()
                sei.cbSize = ctypes.sizeof(sei)
                sei.fMask = SEE_MASK_NOCLOSEPROCESS
                sei.hwnd = None
                sei.lpVerb = "open"  # 用open动作，和用户双击效果一致
                sei.lpFile = app_path
                sei.lpParameters = ""
                sei.lpDirectory = os.path.dirname(app_path) if os.path.dirname(app_path) else None
                sei.nShow = SW_SHOWNORMAL
                
                # 执行启动
                success = shell32.ShellExecuteExW(ctypes.byref(sei))
                if not success or sei.hInstApp <= 32:
                    # ShellExecute启动失败，回退到subprocess方式
                    logger.warning(f"ShellExecute启动失败，回退到subprocess方式，错误码: {sei.hInstApp}")
                    if app_path.lower().endswith('.exe'):
                        # EXE应用直接启动，独立进程
                        subprocess.Popen(
                            app_path,
                            creationflags=creation_flags,
                            close_fds=True
                        )
                    else:
                        # 非EXE应用（比如快捷方式、脚本）
                        subprocess.Popen(
                            app_path,
                            shell=True,
                            creationflags=creation_flags,
                            close_fds=True
                        )
                else:
                    logger.info(f"ShellExecute启动成功，进程ID: {ctypes.windll.kernel32.GetProcessId(sei.hProcess)}")
                    # 关闭进程句柄，不影响子进程运行
                    ctypes.windll.kernel32.CloseHandle(sei.hProcess)
                
                logger.info(f"应用[{window_title}]已独立启动，不受主程序退出影响")
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
                return self._step_switch_app({'app_name': app_name})
            
            time.sleep(1)
        
        logger.error(f"等待应用[{window_title}]窗口超时")
        return False
    
    def _step_switch_app(self, step: Dict) -> bool:
        """
        处理switch_app步骤（核心实现）
        :param step: 步骤配置，包含app_name参数
        :return: 是否切换成功
        """
        app_name = step['app_name']
        
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
    
    def _step_close_app(self, step: Dict) -> bool:
        """
        处理close_app步骤（核心实现）
        :param step: 步骤配置，包含app_name、force等参数
        :return: 是否关闭成功
        """
        app_name = step['app_name']
        force = step.get('force', False)
        window_title = self.apps_config[app_name].get('window_title')

        if app_name not in self.app_states or not self.app_states[app_name]['running']:
            logger.info(f"应用[{window_title}]未运行，无需关闭")
            return True
        
        app_state = self.app_states[app_name]
        hwnd = app_state['hwnd']
        
        try:
            # 关闭前先切换到目标应用，确保窗口处于可操作状态
            logger.info(f"关闭前先切换到应用[{window_title}]")
            self._step_switch_app({'app_name': app_name})
            time.sleep(0.5)
            
            if force:
                # 强制关闭：优先杀进程，再尝试发关闭消息兜底
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid:
                        logger.info(f"强制杀进程: {window_title} PID: {pid}")
                        subprocess.run(f'taskkill /F /T /PID {pid}', shell=True, capture_output=True, timeout=10)
                except Exception as e:
                    logger.warning(f"杀进程失败，回退到WM_CLOSE: {str(e)}")
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            else:
                # 尝试正常关闭，失败则自动杀进程
                try:
                    win32gui.SendMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    # 等待3秒看是否关闭
                    closed = False
                    for _ in range(6):
                        if not win32gui.IsWindow(hwnd):
                            closed = True
                            break
                        time.sleep(0.5)
                    if not closed:
                        logger.warning(f"应用{window_title}正常关闭失败，强制杀进程")
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if pid:
                            subprocess.run(f'taskkill /F /T /PID {pid}', shell=True, capture_output=True, timeout=10)
                except Exception as e:
                    logger.error(f"正常关闭失败: {str(e)}")
            
            # 最终等待关闭确认
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
    
    def _step_click(self, step: Dict) -> bool:
        """
        处理click步骤（核心实现）
        :param step: 步骤配置，包含text、timeout、double等参数
        :return: 是否点击成功
        """
        target_text = step['text']
        timeout = step.get('timeout', 10)
        threshold = step.get('threshold', 0.8)
        double = step.get('double', False)
        interval = step.get('interval', 0.5)
        
        if not self.active_capture or not self.active_app:
            logger.error("没有活跃应用，请先切换到对应应用")
            return False
        
        # 内部调用_wait步骤获取结果
        wait_step = {
            'text': target_text,
            'timeout': timeout,
            'threshold': threshold,
            'interval': interval
        }
        success = self._step_wait(wait_step)
        res = wait_step.get('_result', None) if success else None
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
    
    def _step_wait(self, step: Dict) -> bool:
        """
        处理wait步骤（核心实现）
        :param step: 步骤配置，包含text、timeout、threshold等参数
        :return: 是否找到指定文本
        """
        target_text = step['text']
        timeout = step.get('timeout', 10)
        threshold = step.get('threshold', 0.8)
        interval = step.get('interval', 0.5)
        
        if not self.active_capture or not self.ocr:
            logger.error("没有活跃应用或OCR功能未启用，无法等待文本")
            return False
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            img = self.active_capture.capture()
            res = self.ocr.find_text(img, target_text, threshold)
            if res:
                # 保存OCR结果到步骤结果
                step['_result'] = res
                return True
            time.sleep(interval)
        
        logger.warning(f"等待OCR文本超时: {target_text}")
        return False
    
    def _step_sleep(self, step: Dict) -> bool:
        """处理sleep步骤"""
        time.sleep(step.get('seconds', 1))
        return True
    
    def _step_press(self, step: Dict) -> bool:
        """处理press步骤"""
        self.input_controller.press_key(step['key'])
        return True
    
    def _step_hotkey(self, step: Dict) -> bool:
        """处理hotkey步骤"""
        self.input_controller.hotkey(*step['keys'])
        return True
    
    def _step_run_command(self, step: Dict) -> bool:
        """
        处理run_command步骤
        参数说明：
        - command: 要执行的命令字符串（必填）
        - cwd: 工作目录（可选，默认None）
        - shell: 是否使用shell执行（可选，默认True）
        - timeout: 命令超时时间（秒，可选，默认30）
        - capture_output: 是否捕获命令输出（可选，默认False）
        - background: 是否后台运行（可选，默认False，后台运行不等待结果直接返回成功）
        - raise_on_error: 命令执行失败（返回码非0）时是否抛出异常（可选，默认False）
        """
        command = step.get('command')
        if not command:
            logger.error("执行命令步骤缺少必填参数: command")
            return False
        
        cwd = step.get('cwd')
        shell = step.get('shell', True)
        timeout = step.get('timeout', 30)
        capture_output = step.get('capture_output', False)
        background = step.get('background', False)
        raise_on_error = step.get('raise_on_error', False)
        
        logger.info(f"执行系统命令: {command}" + (f" 工作目录: {cwd}" if cwd else "") + (f" 后台运行: {background}" if background else ""))
        
        try:
            if background:
                # 后台运行模式，独立进程不阻塞
                subprocess.Popen(
                    command,
                    shell=shell,
                    cwd=cwd,
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
                    close_fds=True
                )
                logger.info("命令已后台执行，不等待结果")
                return True
            
            # 前台执行模式，等待结果
            result = subprocess.run(
                command,
                shell=shell,
                cwd=cwd,
                timeout=timeout,
                capture_output=capture_output,
                text=capture_output  # 捕获输出时自动解码为字符串
            )
            
            # 处理执行结果
            if result.returncode != 0:
                error_msg = f"命令执行失败，返回码: {result.returncode}"
                if capture_output:
                    error_msg += f"\n标准错误: {result.stderr}"
                logger.error(error_msg)
                if raise_on_error:
                    raise RuntimeError(error_msg)
                return False
            
            logger.info("命令执行成功")
            if capture_output:
                # 保存输出到步骤结果供后续使用
                step['_result'] = {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                }
                logger.debug(f"命令输出: {result.stdout}")
            return True
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"命令执行超时({timeout}秒): {str(e)}")
            return False
        except Exception as e:
            logger.error(f"命令执行出错: {str(e)}")
            return False
    
    def _step_custom(self, step: Dict) -> bool:
        """处理custom步骤"""
        func = getattr(self, step['func'])
        return func()
    
    def _step_find_control(self, step: Dict) -> bool:
        """处理find_control步骤"""
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
    
    def _step_click_control_by_properties(self, step: Dict) -> bool:
        """处理click_control_by_properties步骤"""
        properties = step.get('properties', {})
        if not properties:
            logger.error("未指定控件属性")
            return False
        
        return self.click_control_by_properties(
            app_name=step.get('app_name'),
            properties=properties,
            double=step.get('double', False)
        )
    
    def _step_send_text_to_control_by_properties(self, step: Dict) -> bool:
        """处理send_text_to_control_by_properties步骤"""
        properties = step.get('properties', {})
        if not properties:
            logger.error("未指定控件属性")
            return False
        
        return self.send_text_to_control_by_properties(
            app_name=step.get('app_name'),
            properties=properties,
            text=step.get('text', '')
        )
    
    def _step_find_control_by_hierarchy(self, step: Dict) -> bool:
        """处理find_control_by_hierarchy步骤"""
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
    
    def _step_click_control_by_hierarchy(self, step: Dict) -> bool:
        """处理click_control_by_hierarchy步骤"""
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
    
    def _step_send_text_to_control_by_hierarchy(self, step: Dict) -> bool:
        """处理send_text_to_control_by_hierarchy步骤"""
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
    
    def _step_send_telegram_message(self, step: Dict) -> bool:
        """处理send_telegram_message步骤"""
        bot_name = step.get('bot_name', 'default')
        text = step.get('text', '')
        parse_mode = step.get('parse_mode', 'HTML')
        disable_notification = step.get('disable_notification', False)
        
        if not text:
            logger.error("未指定消息文本")
            return False
        
        return self.send_telegram_message(
            bot_name=bot_name,
            text=text,
            parse_mode=parse_mode,
            disable_notification=disable_notification
        )
    
    def _step_wait_for_telegram_text(self, step: Dict) -> bool:
        """处理wait_for_telegram_text步骤"""
        expected_text = step.get('text', '')
        timeout = step.get('timeout', 60)
        case_sensitive = step.get('case_sensitive', False)
        sender_id = step.get('sender_id')
        
        if not expected_text:
            logger.error("未指定期望的文本")
            return False
        
        message = self.wait_for_telegram_text(
            expected_text=expected_text,
            timeout=timeout,
            case_sensitive=case_sensitive,
            sender_id=sender_id
        )
        
        if message:
            step['_result'] = message
            return True
        return False
    
    def execute_step(self, step: Dict) -> bool:
        """
        执行单个操作步骤，支持多应用相关步骤
        步骤类型分发器，具体逻辑由对应私有方法实现
        """
        step_type = step.get('type')
        step_name = step.get('name', f'未命名步骤({step_type})')
        logger.info(f"执行步骤: {step_name}")
        
        ignore_error = step.get('ignore_error', False)
        try:
            handler = self.step_handlers.get(step_type)
            if not handler:
                error_msg = f"未知步骤类型: {step_type}"
                if ignore_error:
                    warning_msg = f"步骤[{step_name}]执行异常（已忽略）: {error_msg}"
                    logger.warning(warning_msg)
                    step['_warning'] = warning_msg
                    return True
                logger.error(error_msg)
                return False
            
            result = handler(step)
            if not result:
                error_msg = f"步骤执行失败: {step_name}"
                if ignore_error:
                    warning_msg = f"步骤[{step_name}]执行异常（已忽略）: {error_msg}"
                    logger.warning(warning_msg)
                    step['_warning'] = warning_msg
                    return True
                logger.error(error_msg)
                return False
            return result
        except Exception as e:
            error_msg = f"步骤执行失败: {step_name} 错误: {str(e)}"
            if ignore_error:
                warning_msg = f"步骤[{step_name}]执行异常（已忽略）: {str(e)}"
                logger.warning(warning_msg)
                step['_warning'] = warning_msg
                return True
            logger.error(error_msg)
            return False
    
    def run(self) -> Dict:
        """执行所有操作步骤
        返回结果字典：
        {
            "success": bool,  # 整体是否成功（所有步骤都成功才为True）
            "success_count": int,  # 成功步骤数
            "total_steps": int,  # 总步骤数
            "failed_steps": List[str]  # 失败的步骤名称列表
        }
        """
        logger.info("开始执行多应用自动化任务")
        success_count = 0
        total_steps = len(self.task_steps)
        failed_steps = []
        warning_steps = []  # 忽略错误的警告步骤列表
        
        for i, step in enumerate(self.task_steps, 1):
            step_name = step.get('name', f'步骤{i}')
            logger.info(f"步骤 [{i}/{total_steps}] - {step_name}")
            result = self.retry_manager.retry(lambda: self.execute_step(step))
            
            if not result:
                logger.error(f"第{i}步执行失败: {step_name}")
                failed_steps.append(f"❌ {step_name}")
                continue
            
            # 检查是否有忽略的错误警告
            if '_warning' in step:
                warning_steps.append(step['_warning'])
            
            success_count += 1
        
        # 输出结果汇总
        if warning_steps:
            logger.info(f"任务执行完成，成功{success_count}/{total_steps}步，{len(warning_steps)}个警告:\n" + '\n'.join(warning_steps))
        else:
            logger.info(f"任务执行完成，成功{success_count}/{total_steps}步")
        
        return {
            "success": len(failed_steps) == 0,
            "success_count": success_count,
            "total_steps": total_steps,
            "failed_steps": failed_steps,
            "warning_steps": warning_steps  # 新增警告步骤字段
        }
    
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
    
    def wait_for_telegram_text(self, expected_text: str = '', 
                              timeout: int = 60, case_sensitive: bool = False,
                              sender_id: Optional[int] = None, **kwargs) -> Optional[Dict]:
        """
        等待特定文本的Telegram消息
        :param expected_text: 期望的文本，为空则等待任意文本
        :param timeout: 超时时间（秒）
        :param case_sensitive: 是否区分大小写
        :param sender_id: 可选，仅匹配指定发送者ID的消息
        :return: 匹配的消息字典，超时返回None
        """
        if not self.telegram_bridge_client or not self.telegram_bridge_client.enabled:
            logger.error("Telegram Bridge客户端未初始化或未启用，无法等待消息")
            return None
        
        try:
            filter_desc = []
            if sender_id:
                filter_desc.append(f"发送者ID: {sender_id}")
                
            logger.info(f"等待Telegram文本消息: '{expected_text}'，超时: {timeout}秒，过滤条件: {', '.join(filter_desc) if filter_desc else '无'}")
            
            # 定义过滤函数
            def filter_func(msg):
                # 过滤发送者ID
                if sender_id and msg.get('sender_id') != sender_id:
                    return False
                # 过滤文本内容
                text = msg.get('text', '').strip()
                if not expected_text:
                    return True
                if case_sensitive:
                    return expected_text in text
                else:
                    return expected_text.lower() in text.lower()
            
            message = self.telegram_bridge_client.wait_for_message(timeout=timeout, filter_func=filter_func)
            
            if message:
                sender_name = message.get('sender_name', '未知用户')
                logger.info(f"收到期望的Telegram文本消息: {sender_name} -> '{message.get('text', '')}'")
            
            return message
        except Exception as e:
            logger.error(f"等待Telegram文本消息失败: {str(e)}")
            return None