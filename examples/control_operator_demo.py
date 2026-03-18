#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
控件操作器使用示例
演示如何使用新的控件操作方法替代原有的win32api消息发送
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.game_base import MultiAppBase
from src.core.control_operator import ControlInfo
from loguru import logger
import time


class ControlOperatorDemo(MultiAppBase):
    """控件操作器演示类"""
    
    def __init__(self, config_path: str = "config.yaml"):
        super().__init__(config_path)
        self.demo_app = "notepad"  # 演示用应用
    
    def setup_demo_environment(self):
        """设置演示环境"""
        logger.info("设置演示环境...")
        
        # 启动记事本作为演示应用
        import subprocess
        subprocess.Popen(["notepad.exe"])
        time.sleep(2)
        
        # 查找记事本窗口
        hwnd = self.find_window_by_title("无标题 - 记事本")
        if hwnd:
            self.app_states[self.demo_app] = {
                'running': True,
                'hwnd': hwnd,
                'window_title': "无标题 - 记事本",
                'process_id': 0
            }
            self.active_app = self.demo_app
            logger.info(f"找到记事本窗口: 句柄=0x{hwnd:X}")
            return True
        else:
            logger.error("未找到记事本窗口")
            return False
    
    def demo_find_control(self):
        """演示查找控件"""
        logger.info("=== 演示：查找控件 ===")
        
        # 查找记事本的编辑框（UIA控件）
        properties = {
            'source': 'uia',
            'control_type': 'EditControl',
            'name': '文本编辑器',
            'automation_id': '15'  # 记事本编辑框的automation_id通常是15
        }
        
        control_info = self.find_control(self.demo_app, properties)
        if control_info:
            logger.info(f"找到控件: {control_info.to_dict()}")
            return control_info
        else:
            logger.warning("未找到控件，尝试Win32模式")
            
            # 尝试Win32模式
            properties = {
                'source': 'win32',
                'class_name': 'Edit',
                'window_text': ''
            }
            
            control_info = self.find_control(self.demo_app, properties)
            if control_info:
                logger.info(f"找到控件: {control_info.to_dict()}")
                return control_info
        
        return None
    
    def demo_click_control(self):
        """演示点击控件"""
        logger.info("=== 演示：点击控件 ===")
        
        # 点击记事本的菜单栏（文件菜单）
        properties = {
            'source': 'uia',
            'control_type': 'MenuItemControl',
            'name': '文件(F)',
            'automation_id': 'Item 1'
        }
        
        success = self.click_control_by_properties(self.demo_app, properties)
        if success:
            logger.info("点击文件菜单成功")
            time.sleep(1)
            
            # 点击关闭菜单项
            close_properties = {
                'source': 'uia',
                'control_type': 'MenuItemControl',
                'name': '关闭(C)',
                'automation_id': 'Item 7'
            }
            
            # 使用双击演示
            success = self.click_control_by_properties(self.demo_app, close_properties, double=True)
            if success:
                logger.info("双击关闭菜单项成功")
            else:
                logger.warning("双击关闭菜单项失败")
        else:
            logger.warning("点击文件菜单失败")
        
        return success
    
    def demo_send_text_to_control(self):
        """演示发送文本到控件"""
        logger.info("=== 演示：发送文本到控件 ===")
        
        # 查找编辑框
        properties = {
            'source': 'uia',
            'control_type': 'EditControl',
            'name': '文本编辑器',
            'automation_id': '15'
        }
        
        # 发送文本
        text = "Hello, 这是通过控件操作器发送的文本！\n时间: " + time.strftime("%Y-%m-%d %H:%M:%S")
        success = self.send_text_to_control_by_properties(self.demo_app, properties, text)
        
        if success:
            logger.info(f"发送文本成功: {text}")
        else:
            logger.warning("发送文本失败")
        
        return success
    
    def demo_create_and_click(self):
        """演示创建控件信息并点击（不实际查找）"""
        logger.info("=== 演示：创建控件信息并点击 ===")
        
        # 假设我们知道控件的坐标和属性，可以直接创建控件信息
        # 例如点击记事本的"帮助"菜单
        properties = {
            'source': 'uia',
            'name': '帮助(H)',
            'control_type': 'MenuItemControl',
            'automation_id': 'Item 9',
            'rect': (100, 0, 150, 30),  # 假设的坐标
            'is_enabled': True,
            'is_visible': True
        }
        
        success = self.create_and_click_control(self.demo_app, properties)
        if success:
            logger.info("创建并点击帮助菜单成功")
            time.sleep(1)
            
            # 点击关于记事本
            about_properties = {
                'source': 'uia',
                'name': '关于记事本(A)',
                'control_type': 'MenuItemControl',
                'automation_id': 'Item 11',
                'rect': (100, 100, 200, 130),
                'is_enabled': True,
                'is_visible': True
            }
            
            success = self.create_and_click_control(self.demo_app, about_properties)
            if success:
                logger.info("创建并点击关于记事本成功")
                time.sleep(2)
                
                # 关闭关于对话框（假设的坐标）
                close_properties = {
                    'source': 'win32',
                    'class_name': 'Button',
                    'window_text': '确定',
                    'rect': (300, 200, 360, 230),
                    'is_enabled': True,
                    'is_visible': True
                }
                
                success = self.create_and_click_control(self.demo_app, close_properties)
                if success:
                    logger.info("创建并点击确定按钮成功")
        
        return success
    
    def run_demo(self):
        """运行所有演示"""
        logger.info("开始控件操作器演示")
        
        if not self.setup_demo_environment():
            return False
        
        try:
            # 演示1：查找控件
            control_info = self.demo_find_control()
            
            # 演示2：点击控件
            self.demo_click_control()
            
            # 演示3：发送文本到控件
            self.demo_send_text_to_control()
            
            # 演示4：创建控件信息并点击
            self.demo_create_and_click()
            
            logger.info("所有演示完成")
            return True
            
        except Exception as e:
            logger.error(f"演示过程中出错: {str(e)}")
            return False
        finally:
            # 关闭记事本
            if self.demo_app in self.app_states:
                hwnd = self.app_states[self.demo_app]['hwnd']
                import win32gui
                win32gui.PostMessage(hwnd, 0x0010, 0, 0)  # WM_CLOSE
                logger.info("已关闭记事本")


def main():
    """主函数"""
    demo = ControlOperatorDemo()
    demo.run_demo()


if __name__ == "__main__":
    main()