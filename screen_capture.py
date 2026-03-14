import win32gui
import win32ui
import win32con
import numpy as np
from typing import Tuple, Optional


class ScreenCapture:
    """BitBlt高速截图实现，仅支持Windows系统"""
    
    def __init__(self, window_title: Optional[str] = None):
        """
        初始化截图器
        :param window_title: 窗口标题，不传则截取全屏
        """
        self.window_title = window_title
        self.hwnd = None
        if window_title:
            self.hwnd = win32gui.FindWindow(None, window_title)
            if not self.hwnd:
                raise Exception(f"未找到窗口: {window_title}")
    
    def capture(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """
        截图
        :param region: 截图区域 (x1, y1, x2, y2)，不传则截取整个窗口/全屏
        :return: BGR格式的图像数组，和OpenCV兼容
        """
        hwnd = self.hwnd or win32gui.GetDesktopWindow()
        
        # 获取窗口尺寸
        if region:
            left, top, right, bottom = region
            width = right - left
            height = bottom - top
        else:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
        
        # 创建设备上下文
        hwindc = win32gui.GetWindowDC(hwnd)
        srcdc = win32ui.CreateDCFromHandle(hwindc)
        memdc = srcdc.CreateCompatibleDC()
        
        # 创建位图对象
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(srcdc, width, height)
        memdc.SelectObject(bmp)
        
        # 拷贝图像
        memdc.BitBlt((0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY)
        
        # 转换为numpy数组
        signedIntsArray = bmp.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype='uint8')
        img.shape = (height, width, 4)
        
        # 释放资源
        srcdc.DeleteDC()
        memdc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwindc)
        win32gui.DeleteObject(bmp.GetHandle())
        
        # 转换为BGR格式（去掉alpha通道）
        return img[..., :3]
    
    def get_window_list(self) -> list:
        """获取所有窗口标题列表，方便查找游戏窗口"""
        windows = []
        def enum_window(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append(title)
            return True
        win32gui.EnumWindows(enum_window, None)
        return windows
