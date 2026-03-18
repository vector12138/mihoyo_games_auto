#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 消息等待功能使用示例
展示如何在自动化任务中集成 Telegram 消息交互
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO")

def demonstrate_telegram_integration():
    """演示Telegram消息集成功能"""
    print("=" * 70)
    print("Telegram 消息等待功能使用示例")
    print("=" * 70)
    
    print("\n📋 功能概述:")
    print("在自动化任务中集成 Telegram 消息交互，实现:")
    print("1. 等待用户确认后再继续执行")
    print("2. 接收验证码或授权码")
    print("3. 实现远程控制功能")
    print("4. 多机器人协作")
    
    print("\n🔧 配置要求:")
    print("1. 在 config.yaml 中配置多个 Telegram 机器人")
    print("2. 确保机器人有权限接收消息")
    print("3. 网络可访问 Telegram API")
    
    print("\n📝 配置示例 (config.yaml):")
    print("""
# 多个Telegram机器人配置
telegram_bots:
  # 默认通知机器人
  default:
    enabled: true
    token: "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    chat_id: "-1001234567890"
  
  # 控制机器人
  controller:
    enabled: true
    token: "0987654321:ZYXWVUTSRQPONMLKJIHGFEDCBA"
    chat_id: "-1009876543210"
  
  # 验证码机器人
  verification:
    enabled: true
    token: "1122334455:AAABBBCCCDDDEEEFFFGGGHHH"
    chat_id: "-1001122334455"
""")
    
    print("\n🎯 使用场景示例:")
    
    print("\n1. 等待用户确认后继续执行:")
    print("""
task_steps = [
    # ... 其他步骤
    
    # 发送确认请求
    {
        'name': '发送确认请求',
        'type': 'send_telegram_message',
        'bot_name': 'controller',
        'text': '⚠️ 即将执行重要操作，请回复"确认"继续执行',
        'parse_mode': 'HTML'
    },
    
    # 等待用户确认
    {
        'name': '等待用户确认',
        'type': 'wait_for_telegram_text',
        'bot_name': 'controller',
        'expected_text': '确认',
        'timeout': 300  # 5分钟超时
    },
    
    # 继续执行后续操作
    {
        'name': '执行重要操作',
        'type': 'click',
        'text': '确定按钮'
    }
]
""")
    
    print("\n2. 接收验证码:")
    print("""
task_steps = [
    # ... 其他步骤
    
    # 触发验证码发送
    {
        'name': '点击发送验证码',
        'type': 'click',
        'text': '发送验证码'
    },
    
    # 等待验证码消息
    {
        'name': '等待验证码',
        'type': 'wait_for_telegram_message',
        'bot_name': 'verification',
        'timeout': 120,
        'filter_func': "lambda msg: '验证码' in msg.get('text', '') and any(c.isdigit() for c in msg.get('text', ''))"
    },
    
    # 提取验证码并输入
    {
        'name': '输入验证码',
        'type': 'send_text_to_control_by_properties',
        'properties': {
            'source': 'uia',
            'control_type': 'EditControl',
            'name': '验证码输入框'
        },
        'text': '{{提取验证码逻辑}}'  # 可以从step['_result']中提取
    }
]
""")
    
    print("\n3. 远程控制游戏操作:")
    print("""
task_steps = [
    # ... 其他步骤
    
    # 等待远程控制命令
    {
        'name': '等待控制命令',
        'type': 'wait_for_telegram_command',
        'bot_name': 'controller',
        'command': 'start_mission',
        'timeout': 3600  # 1小时超时
    },
    
    # 执行对应操作
    {
        'name': '开始任务',
        'type': 'click',
        'text': '开始任务'
    },
    
    # 发送完成通知
    {
        'name': '发送完成通知',
        'type': 'send_telegram_message',
        'bot_name': 'controller',
        'text': '✅ 任务已完成',
        'parse_mode': 'HTML'
    }
]
""")
    
    print("\n4. 多机器人协作:")
    print("""
task_steps = [
    # ... 其他步骤
    
    # 使用默认机器人发送状态通知
    {
        'name': '发送状态通知',
        'type': 'send_telegram_message',
        'bot_name': 'default',
        'text': '🔄 自动化任务开始执行',
        'parse_mode': 'HTML'
    },
    
    # 使用控制机器人等待授权
    {
        'name': '等待授权',
        'type': 'wait_for_telegram_sender',
        'bot_name': 'controller',
        'sender_id': 123456789,  # 管理员ID
        'timeout': 300
    },
    
    # 使用验证码机器人接收动态密码
    {
        'name': '接收动态密码',
        'type': 'wait_for_telegram_text',
        'bot_name': 'verification',
        'expected_text': '动态密码',
        'timeout': 120
    }
]
""")
    
    print("\n🔍 消息过滤函数示例:")
    print("""
# 1. 过滤包含特定关键词的消息
filter_func: "lambda msg: '重要' in msg.get('text', '')"

# 2. 过滤来自特定用户的消息
filter_func: "lambda msg: msg.get('from', {}).get('id') == 123456789"

# 3. 过滤包含数字的消息（用于验证码）
filter_func: "lambda msg: any(c.isdigit() for c in msg.get('text', ''))"

# 4. 复合条件过滤
filter_func: "lambda msg: '验证码' in msg.get('text', '') and msg.get('from', {}).get('username') == 'admin'"
""")
    
    print("\n⚠️ 注意事项:")
    print("1. 确保网络可访问 Telegram API (可能需要代理)")
    print("2. 机器人需要先添加到聊天中才能接收消息")
    print("3. 长时间等待时设置合理的超时时间")
    print("4. 使用 filter_func 时注意安全性")
    print("5. 多个机器人可以同时工作，互不干扰")
    
    print("\n🚀 高级功能:")
    print("1. 动态消息处理: 根据收到的消息内容决定后续步骤")
    print("2. 消息解析: 从消息中提取验证码、命令参数等")
    print("3. 状态同步: 实时同步自动化任务状态到Telegram")
    print("4. 错误恢复: 收到错误时等待人工干预")
    
    print("\n" + "=" * 70)
    print("Telegram 消息集成功能已就绪！")
    print("现在可以在自动化任务中添加消息交互了。")
    print("=" * 70)

def show_step_types():
    """展示所有Telegram相关的步骤类型"""
    print("\n\n📋 Telegram 步骤类型汇总:")
    print("\n1. send_telegram_message - 发送消息")
    print("""
{
    'name': '发送消息',
    'type': 'send_telegram_message',
    'bot_name': 'default',           # 可选，默认'default'
    'text': '消息内容',
    'parse_mode': 'HTML',            # 可选，'HTML'或'Markdown'
    'disable_notification': False    # 可选，是否禁用通知
}
""")
    
    print("\n2. wait_for_telegram_message - 等待消息")
    print("""
{
    'name': '等待消息',
    'type': 'wait_for_telegram_message',
    'bot_name': 'default',           # 可选
    'timeout': 60,                   # 可选，秒
    'filter_func': "lambda msg: ..." # 可选，过滤函数
}
""")
    
    print("\n3. wait_for_telegram_text - 等待特定文本")
    print("""
{
    'name': '等待文本',
    'type': 'wait_for_telegram_text',
    'bot_name': 'default',           # 可选
    'expected_text': '确认',
    'timeout': 60,                   # 可选
    'case_sensitive': False          # 可选，是否区分大小写
}
""")
    
    print("\n4. wait_for_telegram_command - 等待命令")
    print("""
{
    'name': '等待命令',
    'type': 'wait_for_telegram_command',
    'bot_name': 'default',           # 可选
    'command': 'start',              # 命令（不带斜杠）
    'timeout': 60                    # 可选
}
""")
    
    print("\n5. wait_for_telegram_sender - 等待特定发送者")
    print("""
{
    'name': '等待发送者',
    'type': 'wait_for_telegram_sender',
    'bot_name': 'default',           # 可选
    'sender_id': 123456789,          # 发送者ID
    'timeout': 60                    # 可选
}
""")

if __name__ == "__main__":
    demonstrate_telegram_integration()
    show_step_types()
    
    print("\n💡 使用建议:")
    print("1. 在关键操作前添加确认步骤，提高安全性")
    print("2. 使用不同的机器人处理不同类型的消息")
    print("3. 合理设置超时时间，避免无限等待")
    print("4. 记录收到的消息，便于调试和审计")
    print("\n现在可以开始使用 Telegram 消息交互功能了！")