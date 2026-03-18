#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复后的控件使用示例
展示如何正确使用层级查找和直接操作控件
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO")

def demonstrate_fixed_usage():
    """演示修复后的控件使用方法"""
    print("=" * 60)
    print("修复后的控件使用示例")
    print("=" * 60)
    
    print("\n📋 问题描述:")
    print("之前：找到控件后，又用控件信息去重新查找控件再操作")
    print("现在：找到控件后直接操作，层级查找的作用真正生效")
    
    print("\n🔧 修复内容:")
    print("1. UIAOperator.click() 和 send_text() 方法现在会优先使用 control._uia_obj")
    print("2. 直接操作失败后才触发重新查找逻辑")
    print("3. 层级查找中的 hwnd 赋值逻辑已修复")
    
    print("\n📝 使用示例:")
    
    print("\n1. 层级查找控件（推荐方式）:")
    print("""
# 定义层级查找条件
hierarchy = [
    {
        'source': 'uia',
        'control_type': 'WindowControl',
        'name': '主窗口'
    },
    {
        'source': 'uia', 
        'control_type': 'PaneControl',
        'name': '工具栏'
    },
    {
        'source': 'uia',
        'control_type': 'ButtonControl',
        'name': '确定按钮',
        'automation_id': 'btn_ok'
    }
]

# 执行层级查找
control_info = control_operator.find_by_hierarchy(parent_hwnd, hierarchy)

# 直接操作找到的控件（不会重新查找！）
if control_info:
    # 点击控件
    control_operator.click(control_info)
    
    # 或者发送文本
    control_operator.send_text(control_info, "Hello World!")
""")
    
    print("\n2. 属性查找控件:")
    print("""
# 定义控件属性
properties = {
    'source': 'uia',
    'control_type': 'EditControl',
    'name': '用户名输入框',
    'automation_id': 'txt_username'
}

# 查找控件
control_info = control_operator.find_by_properties(parent_hwnd, properties)

# 直接操作找到的控件
if control_info:
    # 点击激活
    control_operator.click(control_info)
    
    # 输入文本
    control_operator.send_text(control_info, "my_username")
""")
    
    print("\n3. 在游戏基类中使用:")
    print("""
# 在游戏自动化步骤中使用
task_steps = [
    # ... 其他步骤
    
    # 层级查找并点击
    {
        'name': '点击确定按钮',
        'type': 'click_control_by_hierarchy',
        'hierarchy': [
            {'source': 'uia', 'control_type': 'WindowControl', 'name': '游戏窗口'},
            {'source': 'uia', 'control_type': 'ButtonControl', 'name': '确定'}
        ]
    },
    
    # 属性查找并输入
    {
        'name': '输入账号',
        'type': 'send_text_to_control_by_properties',
        'properties': {
            'source': 'uia',
            'control_type': 'EditControl',
            'name': '账号输入框'
        },
        'text': 'my_account'
    }
]
""")
    
    print("\n🎯 修复带来的好处:")
    print("1. ✅ 性能提升: 避免重复查找控件，操作更快速")
    print("2. ✅ 稳定性提高: 直接操作已找到的控件，减少查找失败风险")
    print("3. ✅ 层级查找真正有用: 复杂的嵌套控件结构可以一次查找多次使用")
    print("4. ✅ 向后兼容: 找不到UIA对象时仍会重新查找，确保功能正常")
    
    print("\n⚠️ 注意事项:")
    print("1. 控件信息对象（ControlInfo）需要正确保存和传递")
    print("2. 对于动态变化的界面，可能需要定期重新查找控件")
    print("3. 确保控件在操作前是可见和可用的")
    
    print("\n" + "=" * 60)
    print("修复完成！现在控件操作更加高效可靠。")
    print("=" * 60)

def compare_before_after():
    """对比修复前后的代码逻辑"""
    print("\n\n🔄 修复前后对比:")
    print("\n修复前（UIAOperator.click 方法）:")
    print("""
def click(self, control: ControlInfo, double: bool = False) -> bool:
    # 总是重新查找控件
    if control.automation_id:
        uia_ctrl = root_ctrl.Control(AutomationId=control.automation_id, ...)
        if uia_ctrl.Exists(0):
            uia_ctrl.Click()  # 点击
            return True
    # 如果ID查找失败，再用其他属性查找...
""")
    
    print("\n修复后（UIAOperator.click 方法）:")
    print("""
def click(self, control: ControlInfo, double: bool = False) -> bool:
    # 优先使用已有的UIA对象
    if control._uia_obj:
        try:
            control._uia_obj.Click()  # 直接点击，不重新查找！
            return True
        except:
            pass  # 失败后重新查找
    
    # 只有没有UIA对象或直接操作失败时才重新查找
    if control.automation_id:
        uia_ctrl = root_ctrl.Control(AutomationId=control.automation_id, ...)
        if uia_ctrl.Exists(0):
            uia_ctrl.Click()
            return True
    # ...
""")
    
    print("\n💡 关键改进:")
    print("• 从 '总是重新查找' 改为 '优先使用已有对象'")
    print("• 层级查找的结果可以被多次使用")
    print("• 减少了不必要的控件查找操作")

if __name__ == "__main__":
    demonstrate_fixed_usage()
    compare_before_after()
    
    print("\n📋 总结:")
    print("本次修复解决了控件操作中的重复查找问题，使得:")
    print("1. 层级查找功能真正发挥作用")
    print("2. 控件操作更加高效")
    print("3. 代码逻辑更加清晰合理")
    print("\n现在可以放心使用层级查找功能了！")