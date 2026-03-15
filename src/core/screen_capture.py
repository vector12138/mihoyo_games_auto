import win32gui
import win32ui
import win32con
import win32api
import numpy as np
from typing import Tuple, Optional, List
import ctypes


class ScreenCapture:
    """高速截图实现，支持多屏幕和DPI缩放"""
    
    def __init__(self, hwnd: int):
        """
        初始化截图器
        :param hwnd: 窗口句柄
        """
        self.hwnd = hwnd
        self.monitors = []
        
        # 启用DPI感知
        self._enable_dpi_awareness()
        
        # 获取显示器信息
        self._get_monitor_info()
    
    def _enable_dpi_awareness(self):
        """启用DPI感知"""
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass
    
    def _get_dpi_for_monitor(self, hMonitor):
        """获取显示器DPI"""
        try:
            dpi_x = ctypes.c_uint()
            dpi_y = ctypes.c_uint()
            if ctypes.windll.shcore.GetDpiForMonitor(hMonitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)) == 0:
                return dpi_x.value
        except:
            pass
        return 96
    
    def _monitor_enum_proc(self, hMonitor, hdcMonitor, lprcMonitor, dwData):
        """显示器枚举回调"""
        try:
            monitor_info = win32api.GetMonitorInfo(hMonitor)
            monitor_rect = monitor_info['Monitor']
            
            # 获取物理分辨率
            dpi = self._get_dpi_for_monitor(hMonitor)
            scale = dpi / 96.0
            
            left, top, right, bottom = monitor_rect
            logical_width = right - left
            logical_height = bottom - top
            
            physical_width = int(logical_width * scale)
            physical_height = int(logical_height * scale)
            
            self.monitors.append({
                'handle': hMonitor,
                'physical_rect': (left, top, left + physical_width, top + physical_height),
                'is_primary': monitor_info['Flags'] == 1,
                'scale': scale
            })
        except:
            pass
        return True
    
    def _get_monitor_info(self):
        """获取显示器信息"""
        try:
            self.monitors = []
            win32api.EnumDisplayMonitors(None, None, self._monitor_enum_proc)
            
            if not self.monitors:
                # 备用方法
                width = win32api.GetSystemMetrics(0)
                height = win32api.GetSystemMetrics(1)
                self.monitors.append({
                    'handle': None,
                    'physical_rect': (0, 0, width, height),
                    'is_primary': True,
                    'scale': 1.0
                })
        except:
            # 最后的保底
            self.monitors = [{
                'handle': None,
                'physical_rect': (0, 0, 1920, 1080),
                'is_primary': True,
                'scale': 1.0
            }]
    
    def _get_monitor_from_point(self, x: int, y: int) -> dict:
        """获取点所在的显示器"""
        for monitor in self.monitors:
            left, top, right, bottom = monitor['physical_rect']
            if left <= x < right and top <= y < bottom:
                return monitor
        return self.monitors[0]
    
    def _get_monitor_from_rect(self, rect: Tuple[int, int, int, int]) -> dict:
        """获取矩形所在的显示器"""
        x1, y1, x2, y2 = rect
        return self._get_monitor_from_point((x1 + x2) // 2, (y1 + y2) // 2)
    
    def capture(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """
        截图
        :param region: 截图区域 (x1, y1, x2, y2)，使用物理像素坐标
        :return: BGR格式的图像数组
        """
        try:
            if region:
                return self._capture_region(region)
            elif self.hwnd:
                return self._capture_window()
            else:
                return self._capture_all_monitors()
        except Exception as e:
            return self._capture_fallback(region)
    
    def _capture_window(self) -> np.ndarray:
        """截取窗口"""
        left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
        width = right - left
        height = bottom - top
        
        monitor = self._get_monitor_from_rect((left, top, right, bottom))
        monitor_rect = monitor['physical_rect']
        
        return self._capture_from_monitor(
            monitor, 
            left - monitor_rect[0], 
            top - monitor_rect[1], 
            width, height
        )
    
    def _capture_region(self, region: Tuple[int, int, int, int]) -> np.ndarray:
        """截取区域"""
        x1, y1, x2, y2 = region
        width = x2 - x1
        height = y2 - y1
        
        monitor = self._get_monitor_from_rect(region)
        monitor_rect = monitor['physical_rect']
        
        rel_x = max(0, x1 - monitor_rect[0])
        rel_y = max(0, y1 - monitor_rect[1])
        monitor_width = monitor_rect[2] - monitor_rect[0]
        monitor_height = monitor_rect[3] - monitor_rect[1]
        rel_x = min(rel_x, monitor_width - width)
        rel_y = min(rel_y, monitor_height - height)
        
        return self._capture_from_monitor(monitor, rel_x, rel_y, width, height)
    
    def _capture_from_monitor(self, monitor: dict, x: int, y: int, width: int, height: int) -> np.ndarray:
        """从指定显示器截图"""
        monitor_rect = monitor['physical_rect']
        
        hdesktop = win32gui.GetDC(0)
        desktop_dc = win32ui.CreateDCFromHandle(hdesktop)
        mem_dc = desktop_dc.CreateCompatibleDC()
        
        screenshot = win32ui.CreateBitmap()
        screenshot.CreateCompatibleBitmap(desktop_dc, width, height)
        mem_dc.SelectObject(screenshot)
        
        try:
            mem_dc.BitBlt((0, 0), (width, height), desktop_dc, 
                         (monitor_rect[0] + x, monitor_rect[1] + y), 
                         win32con.SRCCOPY)
            
            bits = screenshot.GetBitmapBits(True)
            img = np.frombuffer(bits, dtype='uint8')
            img.shape = (height, width, 4)
            
        finally:
            desktop_dc.DeleteDC()
            mem_dc.DeleteDC()
            win32gui.ReleaseDC(0, hdesktop)
            win32gui.DeleteObject(screenshot.GetHandle())
        
        return img[..., :3]
    
    def _capture_all_monitors(self) -> np.ndarray:
        """截取所有显示器（拼接）"""
        if len(self.monitors) == 1:
            monitor = self.monitors[0]
            rect = monitor['physical_rect']
            return self._capture_from_monitor(monitor, 0, 0, 
                                             rect[2] - rect[0], 
                                             rect[3] - rect[1])
        
        screens = [self.capture_monitor(i) for i in range(len(self.monitors))]
        
        left = min(m['physical_rect'][0] for m in self.monitors)
        top = min(m['physical_rect'][1] for m in self.monitors)
        right = max(m['physical_rect'][2] for m in self.monitors)
        bottom = max(m['physical_rect'][3] for m in self.monitors)
        
        combined = np.zeros((bottom - top, right - left, 3), dtype=np.uint8)
        
        for i, monitor in enumerate(self.monitors):
            rect = monitor['physical_rect']
            screen = screens[i]
            x_offset = rect[0] - left
            y_offset = rect[1] - top
            combined[y_offset:y_offset+screen.shape[0], 
                    x_offset:x_offset+screen.shape[1]] = screen
        
        return combined
    
    def capture_monitor(self, monitor_index: int) -> np.ndarray:
        """截取指定显示器"""
        if monitor_index < 0 or monitor_index >= len(self.monitors):
            raise Exception(f"显示器索引 {monitor_index} 不存在")
        
        monitor = self.monitors[monitor_index]
        rect = monitor['physical_rect']
        return self._capture_from_monitor(monitor, 0, 0, 
                                         rect[2] - rect[0], 
                                         rect[3] - rect[1])
    
    def _capture_fallback(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """备用截图方法"""
        try:
            from PIL import ImageGrab
            
            if region:
                bbox = region
            else:
                left = min(m['physical_rect'][0] for m in self.monitors)
                top = min(m['physical_rect'][1] for m in self.monitors)
                right = max(m['physical_rect'][2] for m in self.monitors)
                bottom = max(m['physical_rect'][3] for m in self.monitors)
                bbox = (left, top, right, bottom)
            
            pil_img = ImageGrab.grab(bbox=bbox)
            img = np.array(pil_img)
            return img[..., ::-1] if len(img.shape) == 3 else img
            
        except ImportError:
            raise Exception("请安装PIL: pip install Pillow")
    
    def get_monitor_count(self) -> int:
        """获取显示器数量"""
        return len(self.monitors)
    
    def get_monitor_resolution(self, monitor_index: int) -> Tuple[int, int]:
        """获取指定显示器的分辨率"""
        if monitor_index < 0 or monitor_index >= len(self.monitors):
            raise Exception(f"显示器索引 {monitor_index} 不存在")
        
        rect = self.monitors[monitor_index]['physical_rect']
        return (rect[2] - rect[0], rect[3] - rect[1])
    
    def get_window_list(self) -> List[str]:
        """获取所有可见窗口标题"""
        windows = []
        def enum_callback(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append(title)
            return True
        win32gui.EnumWindows(enum_callback, None)
        return windows


# 使用示例
if __name__ == "__main__":
    # 创建截图器
    capturer = ScreenCapture()
    
    # 获取显示器信息
    print(f"显示器数量: {capturer.get_monitor_count()}")
    for i in range(capturer.get_monitor_count()):
        w, h = capturer.get_monitor_resolution(i)
        print(f"显示器 {i}: {w}x{h}")
    
    # 截取整个屏幕
    img = capturer.capture()
    print(f"全屏截图尺寸: {img.shape}")
    
    # 截取指定显示器
    if capturer.get_monitor_count() > 1:
        img2 = capturer.capture_monitor(1)
        print(f"显示器1截图尺寸: {img2.shape}")