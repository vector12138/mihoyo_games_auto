#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
控件操作模块 - 从win-control-inspector移植的UIA控件查找和操作逻辑
支持先用id查，不行再用综合条件查的策略
已重构：分离UIA和Win32实现，简化方法命名
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
        # 内部字段，用于UIA子控件查找
        self._uia_obj = None
    
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


class BaseOperator:
    """操作器基类"""
    def __init__(self, config: Dict):
        self.config = config
    
    def click(self, control: ControlInfo, double: bool = False) -> bool:
        """点击控件，子类实现"""
        raise NotImplementedError
    
    def send_text(self, control: ControlInfo, text: str) -> bool:
        """发送文本到控件，子类实现"""
        raise NotImplementedError
    
    def find_by_properties(self, hwnd: int, properties: Dict) -> Optional[ControlInfo]:
        """根据属性查找控件，子类实现"""
        raise NotImplementedError
    
    def _activate_window(self, hwnd: int) -> None:
        """激活窗口到前台"""
        if not self.config["auto_activate_window"] or not hwnd:
            return
        root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
        if win32gui.IsIconic(root_hwnd):
            win32gui.ShowWindow(root_hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(root_hwnd)
        win32api.Sleep(50)
    
    def _click_by_coordinate(self, rect: Tuple[int, int, int, int], double: bool = False) -> bool:
        """通过坐标点击兜底"""
        try:
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
            return True
        except Exception as e:
            logger.error(f"坐标点击失败: {str(e)}")
            return False
    
    def _send_text_by_coordinate(self, rect: Tuple[int, int, int, int], text: str) -> bool:
        """通过坐标点击后输入文本兜底"""
        try:
            center_x = (rect[0] + rect[2]) // 2
            center_y = (rect[1] + rect[3]) // 2
            # 点击激活
            win32api.SetCursorPos((center_x, center_y))
            win32api.Sleep(20)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, center_x, center_y, 0, 0)
            win32api.Sleep(10)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, center_x, center_y, 0, 0)
            win32api.Sleep(50)
            # 全选删除原有内容
            shell.SendKeys("^a", 0)
            win32api.Sleep(10)
            shell.SendKeys("{DEL}", 0)
            win32api.Sleep(10)
            # 输入新文本
            shell.SendKeys(text, 0)
            return True
        except Exception as e:
            logger.error(f"坐标输入失败: {str(e)}")
            return False


class UiaOperator(BaseOperator):
    """UIA控件操作器"""
    
    def click(self, control: ControlInfo, double: bool = False) -> bool:
        """点击UIA控件"""
        try:
            self._activate_window(control.hwnd)
            root_hwnd = win32gui.GetAncestor(control.hwnd, win32con.GA_ROOT)
            root_ctrl = auto.ControlFromHandle(root_hwnd)
            uia_ctrl = None
            
            # 优先用automation_id查找
            if control.automation_id:
                try:
                    uia_ctrl = root_ctrl.Control(AutomationId=control.automation_id, searchDepth=10)
                    if uia_ctrl.Exists(0):
                        logger.debug(f"通过automation_id找到控件: {control.automation_id}")
                        if double:
                            uia_ctrl.DoubleClick()
                        else:
                            uia_ctrl.Click()
                        return True
                except Exception as e:
                    logger.debug(f"UIA ID查找失败: {str(e)}")
            
            # 综合条件查找
            if not uia_ctrl or not uia_ctrl.Exists(0):
                kwargs = {}
                if control.name:
                    kwargs['Name'] = control.name.strip()
                if control.class_name:
                    kwargs['ClassName'] = control.class_name.strip()
                if control.control_type:
                    type_name = control.control_type.replace('Control', '')
                    if hasattr(auto, type_name):
                        kwargs['controlType'] = getattr(auto, type_name)
                kwargs['searchDepth'] = 10
                
                try:
                    uia_ctrl = root_ctrl.Control(**kwargs)
                    if uia_ctrl.Exists(0):
                        logger.debug(f"UIA综合条件查找找到控件")
                        if double:
                            uia_ctrl.DoubleClick()
                        else:
                            uia_ctrl.Click()
                        return True
                except Exception as e:
                    logger.debug(f"UIA综合查找失败: {str(e)}")
            
            # 兜底：坐标点击
            return self._click_by_coordinate(control.rect, double)
        except Exception as e:
            logger.debug(f"UIA点击异常: {str(e)}，使用坐标点击兜底")
            return self._click_by_coordinate(control.rect, double)
    
    def send_text(self, control: ControlInfo, text: str) -> bool:
        """发送文本到UIA控件"""
        try:
            self._activate_window(control.hwnd)
            root_hwnd = win32gui.GetAncestor(control.hwnd, win32con.GA_ROOT)
            root_ctrl = auto.ControlFromHandle(root_hwnd)
            uia_ctrl = None
            
            # 优先用automation_id查找
            if control.automation_id:
                try:
                    uia_ctrl = root_ctrl.Control(AutomationId=control.automation_id, searchDepth=10)
                    if uia_ctrl.Exists(0):
                        logger.debug(f"通过automation_id找到输入控件: {control.automation_id}")
                        uia_ctrl.SendKeys("{Ctrl}a{Del}", waitTime=0.05)
                        uia_ctrl.SendKeys(text, waitTime=0.01)
                        return True
                except Exception as e:
                    logger.debug(f"UIA输入ID查找失败: {str(e)}")
            
            # 综合条件查找
            if not uia_ctrl or not uia_ctrl.Exists(0):
                kwargs = {}
                if control.name:
                    kwargs['Name'] = control.name.strip()
                if control.class_name:
                    kwargs['ClassName'] = control.class_name.strip()
                if control.control_type:
                    type_name = control.control_type.replace('Control', '')
                    if hasattr(auto, type_name):
                        kwargs['controlType'] = getattr(auto, type_name)
                kwargs['searchDepth'] = 10
                
                try:
                    uia_ctrl = root_ctrl.Control(**kwargs)
                    if uia_ctrl.Exists(0):
                        logger.debug(f"UIA综合查找找到输入控件")
                        uia_ctrl.SendKeys("{Ctrl}a{Del}", waitTime=0.05)
                        uia_ctrl.SendKeys(text, waitTime=0.01)
                        return True
                except Exception as e:
                    logger.debug(f"UIA输入综合查找失败: {str(e)}")
            
            # 兜底：坐标输入
            return self._send_text_by_coordinate(control.rect, text)
        except Exception as e:
            logger.debug(f"UIA输入异常: {str(e)}，使用坐标输入兜底")
            return self._send_text_by_coordinate(control.rect, text)
    
    def find_by_properties(self, hwnd: int, properties: Dict) -> Optional[ControlInfo]:
        """根据属性查找UIA控件"""
        try:
            root_ctrl = auto.ControlFromHandle(hwnd)
            uia_ctrl = None
            
            # 优先用automation_id查找
            automation_id = properties.get('automation_id')
            if automation_id:
                try:
                    uia_ctrl = root_ctrl.Control(AutomationId=automation_id, searchDepth=10)
                    if not uia_ctrl.Exists(0):
                        uia_ctrl = None
                except Exception as e:
                    logger.debug(f"UIA查找ID失败: {str(e)}")
            
            # 综合条件查找
            if not uia_ctrl:
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
                
                try:
                    uia_ctrl = root_ctrl.Control(**kwargs)
                    if not uia_ctrl.Exists(0):
                        uia_ctrl = None
                except Exception as e:
                    logger.debug(f"UIA综合查找失败: {str(e)}")
            
            if uia_ctrl:
                control_info = ControlInfo()
                control_info.source = "uia"
                control_info.hwnd = hwnd
                control_info.name = uia_ctrl.Name
                control_info.automation_id = uia_ctrl.AutomationId
                control_info.control_type = str(uia_ctrl.ControlTypeName)
                control_info.class_name = uia_ctrl.ClassName
                control_info._uia_obj = uia_ctrl
                
                rect = uia_ctrl.BoundingRectangle
                if rect:
                    control_info.rect = (rect.left, rect.top, rect.right, rect.bottom)
                
                control_info.is_enabled = uia_ctrl.IsEnabled
                control_info.is_visible = uia_ctrl.IsOffscreen == False
                return control_info
            
        except Exception as e:
            logger.error(f"UIA查找控件失败: {str(e)}")
        return None


class Win32Operator(BaseOperator):
    """Win32控件操作器"""
    
    def click(self, control: ControlInfo, double: bool = False) -> bool:
        """点击Win32控件"""
        try:
            self._activate_window(control.hwnd)
            
            if not win32gui.IsWindow(control.hwnd):
                return self._click_by_coordinate(control.rect, double)
            
            try:
                if double:
                    win32gui.SendMessage(control.hwnd, win32con.WM_LBUTTONDBLCLK, win32con.MK_LBUTTON, 0)
                    win32gui.SendMessage(control.hwnd, win32con.WM_LBUTTONUP, 0, 0)
                else:
                    res = win32gui.SendMessage(control.hwnd, win32con.BM_CLICK, 0, 0)
                    if res == 0:
                        win32gui.SendMessage(control.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, 0)
                        win32api.Sleep(10)
                        win32gui.SendMessage(control.hwnd, win32con.WM_LBUTTONUP, 0, 0)
                return True
            except Exception as e:
                logger.debug(f"Win32消息点击失败: {str(e)}")
            
            # 兜底：坐标点击
            return self._click_by_coordinate(control.rect, double)
        except Exception as e:
            logger.debug(f"Win32点击异常: {str(e)}，使用坐标点击兜底")
            return self._click_by_coordinate(control.rect, double)
    
    def send_text(self, control: ControlInfo, text: str) -> bool:
        """发送文本到Win32控件"""
        try:
            self._activate_window(control.hwnd)
            
            # 设置焦点
            if self.config["send_text_set_focus"] and control.hwnd:
                win32gui.SetFocus(control.hwnd)
                win32api.Sleep(20)
            
            if win32gui.IsWindow(control.hwnd):
                try:
                    win32gui.SendMessage(control.hwnd, win32con.WM_SETTEXT, 0, text)
                    logger.debug(f"WM_SETTEXT发送成功: {text}")
                    return True
                except Exception as e:
                    logger.debug(f"WM_SETTEXT失败: {str(e)}")
            
            # 兜底：坐标输入
            return self._send_text_by_coordinate(control.rect, text)
        except Exception as e:
            logger.debug(f"Win32输入异常: {str(e)}，使用坐标输入兜底")
            return self._send_text_by_coordinate(control.rect, text)
    
    def find_by_properties(self, hwnd: int, properties: Dict) -> Optional[ControlInfo]:
        """根据属性查找Win32控件"""
        try:
            found_hwnd = None
            
            def enum_child_callback(child_hwnd, _):
                nonlocal found_hwnd
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
                    return False
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


class ControlOperator:
    """控件操作器，统一入口，自动区分UIA和Win32实现"""
    
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
        
        # 初始化具体操作器
        self.uia_op = UiaOperator(self.config)
        self.win32_op = Win32Operator(self.config)
    
    def click(self, control: ControlInfo, double: bool = False) -> bool:
        """
        点击控件，支持Win32和UIA控件，多方式兜底
        :param control: 控件信息对象
        :param double: 是否双击
        :return: 是否成功
        """
        if not control:
            logger.error("控件为空")
            return False
        
        if not control.is_visible:
            logger.error("控件不可见")
            return False
        
        if not control.is_enabled:
            logger.error("控件已禁用，无法点击")
            return False
        
        try:
            if control.source == "uia":
                return self.uia_op.click(control, double)
            else:
                return self.win32_op.click(control, double)
        except Exception as e:
            logger.error(f"点击控件失败: {str(e)}")
            return False
    
    def send_text(self, control: ControlInfo, text: str) -> bool:
        """
        给控件发送文本，支持Win32和UIA控件，多方式兜底
        :param control: 控件信息对象
        :param text: 要发送的文本
        :return: 是否成功
        """
        if not control or not text:
            logger.error("控件为空或文本为空")
            return False
        
        if not control.is_visible:
            logger.error("控件不可见，无法输入文本")
            return False
        
        if not control.is_enabled:
            logger.error("控件已禁用，无法输入文本")
            return False
        
        try:
            if control.source == "uia":
                return self.uia_op.send_text(control, text)
            else:
                return self.win32_op.send_text(control, text)
        except Exception as e:
            logger.error(f"发送文本失败: {str(e)}")
            return False
    
    def find_by_properties(self, hwnd: int, properties: Dict) -> Optional[ControlInfo]:
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
        
        source = properties.get('source', self.config["control_analysis_mode"])
        if source == "uia" or source == "auto":
            result = self.uia_op.find_by_properties(hwnd, properties)
            if result:
                return result
        
        if source == "win32" or source == "auto":
            result = self.win32_op.find_by_properties(hwnd, properties)
            if result:
                return result
        
        return None
    
    # ===================== 层级查找功能 =====================
    def find_by_hierarchy(self, parent_hwnd: int, hierarchy: List[Dict]) -> Optional[ControlInfo]:
        """
        层级查找控件，按照列表顺序一级一级查找，返回最后一级的控件
        :param parent_hwnd: 顶级父窗口句柄
        :param hierarchy: 层级查找条件列表，每个元素是一级的属性字典
        :return: 最后一级找到的控件，任何一级找不到都返回None
        """
        current_parent_hwnd = parent_hwnd
        current_ctrl = None
        
        for i, level_props in enumerate(hierarchy):
            if i == 0 or current_ctrl is None:
                # 第一级或父控件是Win32控件，在当前父句柄下查找
                current_ctrl = self.find_by_properties(current_parent_hwnd, level_props)
            else:
                # 父控件是UIA控件，在当前UIA控件下查找子控件
                if current_ctrl.source == 'uia' and current_ctrl._uia_obj:
                    children = []
                    def enum_uia_children(ctrl, depth=0):
                        if depth > 5:
                            return
                        try:
                            for child in ctrl.GetChildren():
                                child_info = self._uia_to_control_info(child)
                                if child_info:
                                    child_info._uia_obj = child
                                    children.append(child_info)
                                    enum_uia_children(child, depth + 1)
                        except:
                            pass
                    
                    enum_uia_children(current_ctrl._uia_obj)
                    
                    # 匹配属性
                    current_ctrl = None
                    for child in children:
                        if self._match_control_properties(child, level_props):
                            current_ctrl = child
                            break
                
                # 父控件是Win32控件，枚举子窗口查找
                elif current_ctrl.source == 'win32' and current_ctrl.hwnd != 0:
                    children = []
                    def enum_win32_children(child_hwnd, _):
                        child_info = ControlInfo()
                        child_info.source = "win32"
                        child_info.hwnd = child_hwnd
                        child_info.class_name = win32gui.GetClassName(child_hwnd)
                        child_info.window_text = win32gui.GetWindowText(child_hwnd)
                        child_info.control_id = win32gui.GetDlgCtrlID(child_hwnd)
                        child_info.rect = win32gui.GetWindowRect(child_hwnd)
                        child_info.parent_hwnd = current_ctrl.hwnd
                        child_info.is_enabled = win32gui.IsWindowEnabled(child_hwnd)
                        child_info.is_visible = win32gui.IsWindowVisible(child_hwnd)
                        children.append(child_info)
                        return True
                    
                    win32gui.EnumChildWindows(current_ctrl.hwnd, enum_win32_children, None)
                    
                    # 匹配属性
                    current_ctrl = None
                    for child in children:
                        if self._match_control_properties(child, level_props):
                            current_ctrl = child
                            break
            
            if not current_ctrl:
                logger.error(f"层级查找失败，第{i+1}级未找到控件: {level_props}")
                return None
        
        return current_ctrl
    
    def _uia_to_control_info(self, uia_ctrl) -> Optional[ControlInfo]:
        """将UIA控件对象转换为ControlInfo"""
        try:
            control_info = ControlInfo()
            control_info.source = "uia"
            control_info.name = uia_ctrl.Name
            control_info.automation_id = uia_ctrl.AutomationId
            control_info.control_type = str(uia_ctrl.ControlTypeName)
            control_info.class_name = uia_ctrl.ClassName
            rect = uia_ctrl.BoundingRectangle
            if rect:
                control_info.rect = (rect.left, rect.top, rect.right, rect.bottom)
            control_info.is_enabled = uia_ctrl.IsEnabled
            control_info.is_visible = uia_ctrl.IsOffscreen == False
            return control_info
        except Exception as e:
            logger.debug(f"UIA控件转换失败: {str(e)}")
            return None
    
    def _match_control_properties(self, control: ControlInfo, properties: Dict) -> bool:
        """
        匹配控件属性是否符合要求
        :param control: 控件信息
        :param properties: 属性字典
        :return: 是否匹配
        """
        for key, value in properties.items():
            if not value:
                continue
            # 通用属性
            if key == 'source' and control.source != value:
                return False
            if key == 'class_name' and control.class_name != value:
                return False
            if key == 'window_text' and control.window_text != value:
                return False
            if key == 'name' and control.name != value:
                return False
            if key == 'control_type' and control.control_type != value:
                return False
            if key == 'automation_id' and control.automation_id != value:
                return False
            if key == 'control_id' and control.control_id != value:
                return False
        return True
