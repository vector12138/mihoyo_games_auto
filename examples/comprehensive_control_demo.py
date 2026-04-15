#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合控件操作演示
演示如何使用新的ControlOperator替代所有旧版控件操作方法
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.game_base import MultiAppBase
from src.core.control_operator import ControlInfo
from loguru import logger
import time


class ComprehensiveControlDemo(MultiAppBase):
    """综合控件操作演示类"""
    
    def __init__(self, config_path: str = "examples/genshin_active_config.yaml"):
        """初始化演示类"""
        # 使用已有的配置文件
        super().__init__({"apps": {}, "steps": []}, {})
        
        # 示例控件配置 - 直接定义，无需外部文件
        self.demo_apps = {
            "calculator": {
                "app_path": "calc.exe",
                "window_title": "计算器",
                "control_mappings": {
                    "num_7": {"automation_id": "num7Button"},
                    "num_8": {"automation_id": "num8Button"}, 
                    "num_9": {"automation_id": "num9Button"},
                    "plus": {"automation_id": "plusButton"},
                    "equals": {"automation_id": "equalButton"},
                    "clear": {"automation_id": "clearButton"}
                }
            }
        }
        
    def setup_demo_environment(self):
        """设置演示环境"""
        logger.info("🎯 正在设置演示环境...")
        
        # 首次创建任务步骤以确保基础环境准备完成
        self.task_steps = []
        
        # 模拟多个场景的应用界面
        import subprocess
        import win32gui
        
        # 启动计算器作为模拟环境
        try:
            process = subprocess.Popen(["calc.exe"], shell=True)
            if process:
                time.sleep(2)
            
            # 等待计算器窗口出现
            start_time = time.time()
            hwnd = None
            while time.time() - start_time < 5:
                hwnd = win32gui.FindWindow(None, "计算器")
                if hwnd:
                    break
                time.sleep(0.5)
            
            if hwnd:
                self.app_states["calculator"] = {
                    'hwnd': hwnd,
                    'window_title': "计算器", 
                    'running': True
                }
                self.active_app = "calculator"
                self.active_capture = None
                logger.info(f"✅ 找到计算器窗口: 0x{hwnd:X}")
                return True
            else:
                logger.warning("❌ 计算器窗口未找到，使用云端模拟环境")
                return False
                
        except Exception as e:
            logger.warning(f"❌ 启动计算器失败: {e}，使用云端模拟环境")
            return False
    
    def demo_advanced_control_operations(self):
        """演示高级控件操作技巧"""
        logger.info("🚀 开始进行高级控件操作演示")
        
        if "calculator" not in self.app_states or not self.active_app:
            logger.error("演示环境未就绪")
            return False
            
        hwnd = self.app_states["calculator"]['hwnd']
        
        # 演示1: 使用固定配置查找计算器按钮
        print("\n🧮 场景1: 计算器按钮查找和点击")
        
        # 查找数字按钮
        number_buttons = ["7", "8", "9", "add", "equals", "clear"]
        for button_name in number_buttons:
            properties = self.get_button_properties(button_name)
            control_info = self.find_control("calculator", properties)
            
            if control_info:
                logger.info(f"✅ 找到按钮: {button_name}")
                self.print_control_summary(control_info)
            else:
                logger.warning(f"❌ 未找到按钮: {button_name}")
        
        # 演示2: 层级查找 - 查找计算路径中的复合控件
        print("\n📊 场景2: 计算器层级查找")
        
        hierarchy = [
            {"class_name": "CalcFrame", "control_type": "Window"},
            {"class_name": "LandmarkTarget", "control_type": "Pane"},
            {"automation_id": "CalculatorResults"}
        ]
        
        result_display = self.find_control_by_hierarchy("calculator", hierarchy)
        if result_display:
            logger.info("✅ 层级查找成功 - 计算器结果显示区域")
            self.print_control_summary(result_display)
        
        # 演示3: 控件状态监测和更新
        print("\n🔍 场景3: 控件状态监测")
        
        button_7 = self.find_control("calculator", {
            "automation_id": "num7Button",
            "control_type": "Button"
        })
        
        if button_7:
            logger.info("🔎 监测7号按钮状态")
            self.monitor_control_state(button_7)
            
            # 点击测试
            logger.info("🎯 准备点击7号按钮...")
            time.sleep(1)
            if self.click_control_by_properties("calculator", {
                "automation_id": "num7Button", 
                "control_type": "Button"
            }):
                logger.info("✅ 点击7号按钮成功")
            else:
                logger.warning("❌ 点击7号按钮失败")
        
        return True
        
    def demo_condition_based_control_flow(self):
        """演示基于控件状态的流程控制"""
        logger.info("⚙️ 启动基于条件的控件操作流")
        
        if "calculator" not in self.app_states:
            return False
            
        # 定义一系列条件检查和控制操作
        checks = [
            {
                "name": "计算器主界面检查",
                "type": "find_control",
                "properties": {
                    "class_name": "CalcFrame",
                    "control_type": "Window"
                }
            },
            {
                "name": "结果显示区域检查", 
                "type": "find_control",
                "properties": {
                    "automation_id": "CalculatorResults", 
                    "control_type": "TextBlock"
                }
            },
            {
                "name": "数字按钮可用性",
                "type": "find_control", 
                "properties": {
                    "automation_id": "num7Button",
                    "control_type": "Button",
                    "is_enabled": True,
                    "is_visible": True
                }
            }
        ]
        
        success_count = 0
        for check in checks:
            control_info = self.find_control("calculator", check["properties"])
            if control_info:
                logger.info(f"✅ {check['name']} - 通过")
                success_count += 1
            else:
                logger.warning(f"❌ {check['name']} - 失败")
        
        logger.info(f"条件检查结果: {success_count}/{len(checks)} 项通过")
        return success_count >= len(checks) // 2
    
    def get_button_properties(self, button_name):
        """获取特定按钮的映射配置"""
        mappings = {
            "7": {"automation_id": "num7Button", "control_type": "Button"},
            "8": {"automation_id": "num8Button", "control_type": "Button"},
            "9": {"automation_id": "num9Button", "control_type": "Button"},
            "add": {"automation_id": "plusButton", "control_type": "Button"},
            "equals": {"automation_id": "equalButton", "control_type": "Button"},
            "clear": {"automation_id": "clearButton", "control_type": "Button"},
            "multiply": {"automation_id": "multiplyButton", "control_type": "Button"}
        }
        return mappings.get(button_name, {"automation_id": button_name, "control_type": "Button"})
    
    def print_control_summary(self, control_info):
        """打印控件关键信息摘要"""
        print(f"   ├─ 类型: {control_info.control_type or 'Unknown'}")
        print(f"   ├─ 类名: {control_info.class_name}")
        print(f"   ├─ 启用: {'是' if control_info.is_enabled else '否'}")
        print(f"   ├─ 可见: {'是' if control_info.is_visible else '否'}")
        print(f"   └─ 位置: {