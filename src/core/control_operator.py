#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
控件操作模块 - 从win-control-inspector移植的UIA控件查找和操作逻辑
支持先用id查，不行再用综合条件查的策略
"""

import win32gui
import win32con
import win32api
import win32com.client
import time
from typing import Dict, List, Optional, Tuple, Union
from loguru import logger
import uiautomation as auto

# 兼容不同版本uiautomation API
auto.SetGlobalSearchTimeout(1000)
shell = win32com.client.Dispatch("WScript.Shell")


class ControlInfo:
    """控件信息数据结构，简化版"""
    def __init__(self):
        # 通用字段
        self.source: str = "win32"  # win32 或 uia
        self.hwnd: int = 0
        self.class_name: str = ""
        self.window_text: str = ""
        self.name: str = ""  # UIA控件名称
        self.control_type: str = ""  # UIA控件类型
        self.automation_id: str = ""  # UIA自动化ID（等效于Win32控件ID）
        self.control_id: int = 0  # Win32控件ID
        self.rect: Tuple[int, int, int, int] = (0, 0, 0, 0)
        self.parent_hwnd: int = 0
        self.is_enabled: bool = False
        self.is_visible: bool = False
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "source": self.source,
            "hwnd": f"0x{self.hwnd:X}" if self.hwnd else "无",
            "class_name": self.class_name,
            "window_text": self.window_text,
            "name": self.name,
            "control_type": self.control_type,
            "automation_id": self.automation_id,
            "control_id": self.control_id,
            "rect": self.rect,
            "parent_hwnd": f"0x{self.parent_hwnd:X}" if self.parent_hwnd else "无",
            "is_enabled": self.is_enabled,
            "is_visible": self.is_visible
        }


class ControlOperator:
    """控件操作器，支持Win32和UIA控件的查找和操作"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化控件操作器
        :param config: 配置字典
        """
        # 默认配置
        self.config = {
            "auto_activate_window": True,
            "click_use_coordinate": True,
            "send_text_set_focus": True,
            "control_analysis_mode": "auto",  # auto/win32/uia
        }
        
        if config:
            self.config.update(config)
    
    def click_control(self, control: ControlInfo, double: bool = False) -> bool:
        """
        点击控件，支持Win32和UIA控件，多方式兜底
        :param control: 控件信息对象
        :param double: 是否双击
        :return: 是否成功
        """
        if not control:
            logger.error("控件为空")
            return False
        
        # 先检查控件状态
        if not control.is_visible:
            logger.error("控件不可见，请开启配置项show_invisible_controls后重试")
            return False
        
        if not control.is_enabled:
            logger.error("控件已禁用，无法点击")
            return False
        
        try:
            # 自动激活窗口到前台（配置控制）
            root_hwnd = win32gui.GetAncestor(control.hwnd, win32con.GA_ROOT)
            if self.config["auto_activate_window"] and root_hwnd:
                # 先最小化再恢复，解决部分窗口无法激活的问题
                if win32gui.IsIconic(root_hwnd):
                    win32gui.ShowWindow(root_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(root_hwnd)
                win32api.Sleep(50)
            
            success = False
            
            if control.source == "uia":
                # UIA控件点击：优先用控件属性查找子控件，不要用hwnd（UIA子控件无独立hwnd）
                try:
                    # 从顶层窗口开始查找
                    root_hwnd = win32gui.GetAncestor(control.hwnd, win32con.GA_ROOT)
                    root_ctrl = auto.ControlFromHandle(root_hwnd)
                    uia_ctrl = None
                    
                    # 第一步：优先仅用automation_id查找（最稳定准确）
                    if control.automation_id:
                        try:
                            uia_ctrl = root_ctrl.Control(AutomationId=control.automation_id, searchDepth=10)
                            if uia_ctrl.Exists(0):
                                logger.debug(f"通过automation_id找到控件: {control.automation_id}")
                                # 找到控件后执行点击动作
                                if double:
                                    uia_ctrl.DoubleClick()
                                else:
                                    uia_ctrl.Click()
                                success = True
                        except Exception as e:
                            logger.debug(f"仅ID查找失败: {str(e)}，尝试综合条件查找")
                    
                    # 第二步：id查找失败或无id，用综合条件查找
                    if not success:
                        kwargs = {}
                        if control.name:
                            kwargs['Name'] = control.name.strip()
                            logger.debug(f"综合查找条件 Name: {repr(kwargs['Name'])}")
                        if control.class_name:
                            kwargs['ClassName'] = control.class_name.strip()
                        if control.control_type:
                            # 转换为UIA常量，例如"ButtonControl" -> auto.Button
                            type_name = control.control_type.replace('Control', '')
                            if hasattr(auto, type_name):
                                kwargs['controlType'] = getattr(auto, type_name)
                        kwargs['searchDepth'] = 10
                        
                        if kwargs:
                            try:
                                uia_ctrl = root_ctrl.Control(**kwargs)
                                if uia_ctrl.Exists(0):
                                    logger.debug(f"综合条件查找找到控件")
                                    # 找到控件后执行点击动作
                                    if double:
                                        uia_ctrl.DoubleClick()
                                    else:
                                        uia_ctrl.Click()
                                    success = True
                            except Exception as e:
                                logger.debug(f"综合条件查找失败: {str(e)}")
                    
                    # 第三步：查找都失败，直接用坐标点击
                    if not success:
                        logger.debug("UIA控件查找失败，直接用坐标点击")
                        # UIA子控件无独立hwnd，直接用坐标点击最可靠
                        rect = control.rect
                        center_x = (rect[0] + rect[2]) // 2
                        center_y = (rect[1] + rect[3]) // 2
                        win32api.SetCursorPos((center_x, center_y))
                        win32api.Sleep(20)
                        if double:
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                            win32api.Sleep(50)
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                        else:
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                            win32api.Sleep(10)
                            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                        success = True
                except Exception as e:
                    logger.debug(f"UIA点击失败: {str(e)}，自动使用坐标点击")
                    # 异常情况下也尝试坐标点击
                    rect = control.rect
                    center_x = (rect[0] + rect[2]) // 2
                    center_y = (rect[1] + rect[3]) // 2
                    win32api.SetCursorPos((center_x, center_y))
                    win32api.Sleep(20)
                    if double:
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                        win32api.Sleep(50)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                    else:
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                        win32api.Sleep(10)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                    success = True
            
            # Win32控件或UIA点击失败，尝试原生消息点击
            if not success and control.hwnd and win32gui.IsWindow(control.hwnd):
                try:
                    if double:
                        # 发送双击消息
                        win32gui.SendMessage(control.hwnd, win32con.WM_LBUTTONDBLCLK, win32con.MK_LBUTTON, 0)
                        win32gui.SendMessage(control.hwnd, win32con.WM_LBUTTONUP, 0, 0)
                    else:
                        # 先尝试BM_CLICK（按钮专用）
                        res = win32gui.SendMessage(control.hwnd, win32con.BM_CLICK, 0, 0)
                        if res == 0:
                            # 普通控件发送鼠标按下松开消息
                            win32gui.SendMessage(control.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, 0)
                            win32api.Sleep(10)
                            win32gui.SendMessage(control.hwnd, win32con.WM_LBUTTONUP, 0, 0)
                    success = True
                except Exception as e:
                    logger.debug(f"Win32消息点击失败: {str(e)}")
            
            # 都失败了，尝试坐标模拟点击兜底（配置控制）
            if not success and self.config["click_use_coordinate"]:
                try:
                    # 获取控件中心坐标
                    rect = control.rect
                    center_x = (rect[0] + rect[2]) // 2
                    center_y = (rect[1] + rect[3]) // 2
                    
                    # 移动鼠标到控件中心
                    win32api.SetCursorPos((center_x, center_y))
                    win32api.Sleep(20)
                    
                    # 模拟点击
                    if double:
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                        win32api.Sleep(50)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                    else:
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                        win32api.Sleep(10)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                    success = True
                    logger.debug(f"坐标点击成功: ({center_x}, {center_y})")
                except Exception as e:
                    logger.error(f"坐标点击也失败: {str(e)}")
                    return False
            
            return success
        except Exception as e:
            logger.error(f"点击控件失败: {str(e)}")
            return False
    
    def send_text_to_control(self, control: ControlInfo, text: str) -> bool:
        """
        给控件发送文本，支持Win32和UIA控件，多方式兜底
        :param control: 控件信息对象
        :param text: 要发送的文本
        :return: 是否成功
        """
        if not control or not text:
            logger.error("控件为空或文本为空")
            return False
        
        # 先检查控件状态
        if not control.is_visible:
            logger.error("控件不可见，无法输入文本")
            return False
        
        if not control.is_enabled:
            logger.error("控件已禁用，无法输入文本")
            return False
        
        try:
            # 自动激活窗口和设置焦点（配置控制）
            root_hwnd = win32gui.GetAncestor(control.hwnd, win32con.GA_ROOT)
            if self.config["auto_activate_window"] and root_hwnd:
                if win32gui.IsIconic(root_hwnd):
                    win32gui.ShowWindow(root_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(root_hwnd)
                win32api.Sleep(50)
            
            # 设置控件焦点（配置控制）
            if self.config["send_text_set_focus"] and control.hwnd:
                win32gui.SetFocus(control.hwnd)
                win32api.Sleep(20)
            
            success = False
            
            if control.source == "uia":
                # UIA控件发送文本：优先查找控件，查找失败直接点击坐标后输入
                try:
                    # 从顶层窗口开始查找
                    root_hwnd = win32gui.GetAncestor(control.hwnd, win32con.GA_ROOT)
                    root_ctrl = auto.ControlFromHandle(root_hwnd)
                    uia_ctrl = None
                    
                    # 第一步：优先仅用automation_id查找（最稳定准确）
                    if control.automation_id:
                        try:
                            uia_ctrl = root_ctrl.Control(AutomationId=control.automation_id, searchDepth=10)
                            if uia_ctrl.Exists(0):
                                logger.debug(f"通过automation_id找到输入控件: {control.automation_id}")
                                # 找到控件后执行输入动作
                                # 先清空原有文本
                                uia_ctrl.SendKeys("{Ctrl}a{Del}", waitTime=0.05)
                                uia_ctrl.SendKeys(text, waitTime=0.01)
                                success = True
                        except Exception as e:
                            logger.debug(f"仅ID查找失败: {str(e)}，尝试综合条件查找")
                    
                    # 第二步：id查找失败或无id，用综合条件查找
                    if not success:
                        kwargs = {}
                        if control.name:
                            kwargs['Name'] = control.name.strip()
                            logger.debug(f"查找条件 Name: {repr(kwargs['Name'])}")
                        if control.class_name:
                            kwargs['ClassName'] = control.class_name.strip()
                        if control.control_type:
                            # 转换为UIA常量，例如"EditControl" -> auto.Edit
                            type_name = control.control_type.replace('Control', '')
                            if hasattr(auto, type_name):
                                kwargs['controlType'] = getattr(auto, type_name)
                        kwargs['searchDepth'] = 10
                        
                        if kwargs:
                            try:
                                uia_ctrl = root_ctrl.Control(**kwargs)
                                if uia_ctrl.Exists(0):
                                    logger.debug(f"综合条件查找找到输入控件")
                                    # 找到控件后执行输入动作
                                    # 先清空原有文本
                                    uia_ctrl.SendKeys("{Ctrl}a{Del}", waitTime=0.05)
                                    uia_ctrl.SendKeys(text, waitTime=0.01)
                                    success = True
                            except Exception as e:
                                logger.debug(f"综合条件查找失败: {str(e)}")
                    
                    # 第三步：查找都失败，点击坐标后输入
                    if not success:
                        logger.debug("UIA输入控件查找失败，点击坐标后输入")
                        # 点击控件坐标激活输入
                        rect = control.rect
                        center_x = (rect[0] + rect[2]) // 2
                        center_y = (rect[1] + rect[3]) // 2
                        win32api.SetCursorPos((center_x, center_y))
                        win32api.Sleep(20)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                        win32api.Sleep(10)
                        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                        win32api.Sleep(50)
                        # 全选删除
                        shell.SendKeys("^a", 0)
                        win32api.Sleep(10)
                        shell.SendKeys("{DEL}", 0)
                        win32api.Sleep(10)
                        # 发送文本
                        shell.SendKeys(text, 0)
                        success = True
                except Exception as e:
                    logger.debug(f"UIA发送文本失败: {str(e)}，点击坐标后输入")
                    # 异常情况下也尝试坐标点击后输入
                    rect = control.rect
                    center_x = (rect[0] + rect[2]) // 2
                    center_y = (rect[1] + rect[3]) // 2
                    win32api.SetCursorPos((center_x, center_y))
                    win32api.Sleep(20)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                    win32api.Sleep(10)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                    win32api.Sleep(50)
                    # 全选删除
                    shell.SendKeys("^a", 0)
                    win32api.Sleep(10)
                    shell.SendKeys("{DEL}", 0)
                    win32api.Sleep(10)
                    # 发送文本
                    shell.SendKeys(text, 0)
                    success = True
            
            # Win32控件或UIA发送失败，尝试WM_SETTEXT
            if not success and control.hwnd and win32gui.IsWindow(control.hwnd):
                try:
                    # 发送WM_SETTEXT消息设置文本
                    win32gui.SendMessage(control.hwnd, win32con.WM_SETTEXT, 0, text)
                    success = True
                    logger.debug(f"WM_SETTEXT发送成功: {text}")
                except Exception as e:
                    logger.debug(f"WM_SETTEXT发送失败: {str(e)}")
            
            # 都失败了，尝试坐标点击后键盘输入兜底
            if not success:
                try:
                    # 获取控件中心坐标
                    rect = control.rect
                    center_x = (rect[0] + rect[2]) // 2
                    center_y = (rect[1] + rect[3]) // 2
                    
                    # 点击控件激活输入
                    win32api.SetCursorPos((center_x, center_y))
                    win32api.Sleep(20)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
                    win32api.Sleep(10)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
                    win32api.Sleep(50)
                    
                    # 全选删除
                    shell.SendKeys("^a", 0)
                    win32api.Sleep(10)
                    shell.SendKeys("{DEL}", 0)
                    win32api.Sleep(10)
                    
                    # 发送文本
                    shell.SendKeys(text, 0)
                    success = True
                    logger.debug(f"坐标点击后键盘输入成功: {text}")
                except Exception as e:
                    logger.error(f"坐标点击后键盘输入也失败: {str(e)}")
                    return False
            
            return success
        except Exception as e:
            logger.error(f"发送文本失败: {str(e)}")
            return False
    
    def find_control_by_properties(self, hwnd: int, properties: Dict) -> Optional[ControlInfo]:
        """
        根据属性查找控件
        :param hwnd: 父窗口句柄
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
        if not hwnd or not win32gui.IsWindow(hwnd):
            logger.error("无效的窗口句柄")
            return None
        
        source = properties.get('source', 'win32')
        
        if source == "uia":
            # UIA模式查找
            try:
                root_ctrl = auto.ControlFromHandle(hwnd)
                uia_ctrl = None
                
                # 第一步：优先仅用automation_id查找
                automation_id = properties.get('automation_id')
                if automation_id:
                    try:
                        uia_ctrl = root_ctrl.Control(AutomationId=automation_id, searchDepth=10)
                        if uia_ctrl.Exists(0):
                            logger.debug(f"通过automation_id找到控件: {automation_id}")
                    except Exception as e:
                        logger.debug(f"仅ID查找失败: {str(e)}，尝试综合条件查找")
                
                # 第二步：id查找失败或无id，用综合条件查找
                if not uia_ctrl or not uia_ctrl.Exists(0):
                    kwargs = {}
                    if properties.get('name'):
                        kwargs['Name'] = properties['name'].strip()
                    if properties.get('class_name'):
                        kwargs['ClassName'] = properties['class_name'].strip()
                    if properties.get('control_type'):
                        type_name = properties['control_type'].replace('Control', '')
                        if hasattr(auto, type_name):
                            kwargs['controlType'] = getattr(auto, type_name)
                    kwargs['searchDepth'] = 10
                    
                    if kwargs:
                        try:
                            uia_ctrl = root_ctrl.Control(**kwargs)
                            if not uia_ctrl.Exists(0):
                                uia_ctrl = None
                        except Exception as e:
                            logger.debug(f"综合条件查找失败: {str(e)}")
                
                if uia_ctrl and uia_ctrl.Exists(0):
                    # 获取控件信息
                    control_info = ControlInfo()
                    control_info.source = "uia"
                    control_info.hwnd = hwnd  # 父窗口句柄
                    control_info.name = uia_ctrl.Name
                    control_info.automation_id = uia_ctrl.AutomationId
                    control_info.control_type = str(uia_ctrl.ControlTypeName)
                    control_info.class_name = uia_ctrl.ClassName
                    
                    # 获取控件矩形
                    rect = uia_ctrl.BoundingRectangle
                    if rect:
                        control_info.rect = (rect.left, rect.top, rect.right, rect.bottom)
                    
                    control_info.is_enabled = uia_ctrl.IsEnabled
                    control_info.is_visible = uia_ctrl.IsVisible
                    
                    return control_info
                
            except Exception as e:
                logger.error(f"UIA查找控件失败: {str(e)}")
        
        else:
            # Win32模式查找
            try:
                found_hwnd = None
                
                def enum_child_callback(child_hwnd, _):
                    nonlocal found_hwnd
                    
                    # 检查所有属性
                    match = True
                    
                    if properties.get('class_name'):
                        current_class = win32gui.GetClassName(child_hwnd)
                        if current_class != properties['class_name']:
                            match = False
                    
                    if properties.get('window_text'):
                        current_text = win32gui.GetWindowText(child_hwnd)
                        if current_text != properties['window_text']:
                            match = False
                    
                    if properties.get('control_id'):
                        current_id = win32gui.GetDlgCtrlID(child_hwnd)
                        if current_id != properties['control_id']:
                            match = False
                    
                    if match:
                        found_hwnd = child_hwnd
                        return False  # 停止枚举
                    
                    return True
                
                win32gui.EnumChildWindows(hwnd, enum_child_callback, None)
                
                if found_hwnd:
                    control_info = ControlInfo()
                    control_info.source = "win32"
                    control_info.hwnd = found_hwnd
                    control_info.class_name = win32gui.GetClassName(found_hwnd)
                    control_info.window_text = win32gui.GetWindowText(found_hwnd)
                    control_info.control_id = win32gui.GetDlgCtrlID(found_hwnd)
                    control_info.rect = win32gui.GetWindowRect(found_hwnd)
                    control_info.parent_hwnd = hwnd
                    control_info.is_enabled = win32gui.IsWindowEnabled(found_hwnd)
                    control_info.is_visible = win32gui.IsWindowVisible(found_hwnd)
                    
                    return control_info
                
            except Exception as e:
                logger.error(f"Win32查找控件失败: {str(e)}")
        
        return None
    
    def create_control_from_properties(self, hwnd: int, properties: Dict) -> ControlInfo:
        """
        根据属性创建控件信息对象（不实际查找，仅创建对象）
        :param hwnd: 父窗口句柄
        :param properties: 控件属性字典
        :return: 控件信息对象
        """
        control_info = ControlInfo()
        control_info.source = properties.get('source', 'win32')
        control_info.hwnd = hwnd
        control_info.class_name = properties.get('class_name', '')
        control_info.window_text = properties.get('window_text', '')
        control_info.name = properties.get('name', '')
        control_info.control_type = properties.get('control_type', '')
        control_info.automation_id = properties.get('automation_id', '')
        control_info.control_id = properties.get('control_id', 0)
        control_info.rect = properties.get('rect', (0, 0, 0, 0))
        control_info.parent_hwnd = hwnd
        control_info.is_enabled = properties.get('is_enabled', True)
        control_info.is_visible = properties.get('is_visible', True)
        
        return control_info