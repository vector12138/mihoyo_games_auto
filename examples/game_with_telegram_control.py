#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏自动化与 Telegram 远程控制集成示例
展示如何在游戏自动化中集成 Telegram 消息控制
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.game_base import MultiAppBase
from loguru import logger
import yaml

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO")

class GameWithTelegramControl(MultiAppBase):
    """带有Telegram控制的游戏自动化示例"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """初始化"""
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # 使用绝区零配置作为示例
        game_config = config_data.get('zzz', {})
        global_config = config_data.get('global', {})
        
        super().__init__(game_config, global_config)
        
        # 定义任务步骤
        self.task_steps = self._create_task_steps()
    
    def _create_task_steps(self):
        """创建包含Telegram控制的任务步骤"""
        return [
            # 步骤1: 启动游戏
            {
                'name': '启动绝区零游戏',
                'type': 'launch_app',
                'app_name': 'zzz_game'
            },
            
            # 步骤2: 切换到游戏窗口
            {
                'name': '切换到游戏窗口',
                'type': 'switch_app',
                'app_name': 'zzz_game'
            },
            
            # 步骤3: 发送启动通知
            {
                'name': '发送游戏启动通知',
                'type': 'send_telegram_message',
                'bot_name': 'default',
                'text': '🎮 <b>绝区零自动化任务启动</b>\n'
                       '游戏已启动，等待远程控制命令...\n'
                       '可用命令:\n'
                       '• /start_daily - 开始日常任务\n'
                       '• /start_mission - 开始主线任务\n'
                       '• /pause - 暂停任务\n'
                       '• /stop - 停止任务',
                'parse_mode': 'HTML'
            },
            
            # 步骤4: 等待控制命令
            {
                'name': '等待控制命令',
                'type': 'wait_for_telegram_command',
                'bot_name': 'controller',
                'command': 'start_daily',
                'timeout': 3600  # 1小时超时
            },
            
            # 步骤5: 发送确认通知
            {
                'name': '发送任务开始确认',
                'type': 'send_telegram_message',
                'bot_name': 'default',
                'text': '✅ <b>开始执行日常任务</b>\n'
                       '正在登录游戏...',
                'parse_mode': 'HTML'
            },
            
            # 步骤6: 游戏登录（示例步骤）
            {
                'name': '点击登录按钮',
                'type': 'click',
                'text': '进入游戏',
                'timeout': 30
            },
            
            # 步骤7: 等待登录完成
            {
                'name': '等待登录完成',
                'type': 'wait',
                'text': '每日任务',
                'timeout': 60
            },
            
            # 步骤8: 发送进度通知
            {
                'name': '发送登录成功通知',
                'type': 'send_telegram_message',
                'bot_name': 'default',
                'text': '🔓 <b>登录成功</b>\n'
                       '已进入游戏主界面，开始日常任务...',
                'parse_mode': 'HTML'
            },
            
            # 步骤9: 执行日常任务（示例）
            {
                'name': '打开日常任务界面',
                'type': 'click',
                'text': '每日任务',
                'timeout': 10
            },
            
            # 步骤10: 等待任务界面加载
            {
                'name': '等待任务界面',
                'type': 'wait',
                'text': '今日任务',
                'timeout': 10
            },
            
            # 步骤11: 领取已完成任务
            {
                'name': '领取任务奖励',
                'type': 'click',
                'text': '领取',
                'timeout': 5
            },
            
            # 步骤12: 发送任务完成通知
            {
                'name': '发送任务完成通知',
                'type': 'send_telegram_message',
                'bot_name': 'default',
                'text': '🏆 <b>日常任务完成</b>\n'
                       '已领取所有任务奖励！\n'
                       '等待下一步指令...',
                'parse_mode': 'HTML'
            },
            
            # 步骤13: 等待继续指令或退出
            {
                'name': '等待下一步指令',
                'type': 'wait_for_telegram_message',
                'bot_name': 'controller',
                'timeout': 300,  # 5分钟超时
                'filter_func': "lambda msg: msg.get('text', '').startswith('/')"
            },
            
            # 步骤14: 根据指令执行不同操作
            {
                'name': '处理用户指令',
                'type': 'custom',
                'func': '_process_user_command'
            },
            
            # 步骤15: 关闭游戏
            {
                'name': '关闭游戏',
                'type': 'close_app',
                'app_name': 'zzz_game'
            },
            
            # 步骤16: 发送结束通知
            {
                'name': '发送任务结束通知',
                'type': 'send_telegram_message',
                'bot_name': 'default',
                'text': '🛑 <b>自动化任务结束</b>\n'
                       '游戏已关闭，任务完成！',
                'parse_mode': 'HTML'
            }
        ]
    
    def _process_user_command(self):
        """处理用户指令（自定义函数示例）"""
        # 获取上一步收到的消息
        last_step = self.task_steps[-3]  # 步骤13是等待指令
        message = last_step.get('_result')
        
        if not message:
            logger.warning("未收到用户指令")
            return False
        
        text = message.get('text', '')
        sender = message.get('from', {})
        sender_name = sender.get('first_name', '') + ' ' + sender.get('last_name', '')
        sender_name = sender_name.strip() or sender.get('username', '未知用户')
        
        logger.info(f"处理用户指令: {sender_name} -> {text}")
        
        # 根据指令执行不同操作
        if text == '/start_mission':
            self._execute_mission()
            return True
        elif text == '/pause':
            self._pause_task()
            return True
        elif text == '/stop':
            self._stop_task()
            return True
        else:
            logger.warning(f"未知指令: {text}")
            return False
    
    def _execute_mission(self):
        """执行主线任务（示例）"""
        logger.info("开始执行主线任务...")
        
        # 发送通知
        self.send_telegram_message(
            bot_name='default',
            text='🚀 <b>开始执行主线任务</b>\n'
                 '正在前往任务地点...',
            parse_mode='HTML'
        )
        
        # 这里可以添加具体的任务步骤
        # 例如：点击任务追踪、自动寻路、战斗等
        
        time.sleep(2)  # 模拟任务执行
        
        # 发送完成通知
        self.send_telegram_message(
            bot_name='default',
            text='✅ <b>主线任务完成</b>\n'
                 '任务已成功完成！',
            parse_mode='HTML'
        )
    
    def _pause_task(self):
        """暂停任务"""
        logger.info("任务暂停")
        
        self.send_telegram_message(
            bot_name='default',
            text='⏸️ <b>任务已暂停</b>\n'
                 '发送 /resume 继续执行',
            parse_mode='HTML'
        )
        
        # 等待继续指令
        message = self.wait_for_telegram_command(
            bot_name='controller',
            command='resume',
            timeout=3600  # 1小时超时
        )
        
        if message:
            self.send_telegram_message(
                bot_name='default',
                text='▶️ <b>任务继续执行</b>',
                parse_mode='HTML'
            )
            return True
        else:
            logger.warning("等待继续指令超时")
            return False
    
    def _stop_task(self):
        """停止任务"""
        logger.info("任务停止")
        return True

def demonstrate_verification_scenario():
    """演示验证码接收场景"""
    print("\n" + "=" * 70)
    print("验证码接收场景示例")
    print("=" * 70)
    
    print("\n📱 场景描述:")
    print("游戏登录时需要短信验证码，验证码会发送到Telegram")
    
    print("\n🔧 配置要求:")
    print("1. 配置一个专门的验证码机器人")
    print("2. 将验证码短信转发到该机器人的聊天")
    print("3. 在自动化任务中等待并提取验证码")
    
    print("\n📝 任务步骤示例:")
    verification_steps = [
        # 步骤1: 进入登录界面
        {
            'name': '进入登录界面',
            'type': 'click',
            'text': '账号登录'
        },
        
        # 步骤2: 输入账号
        {
            'name': '输入账号',
            'type': 'send_text_to_control_by_properties',
            'properties': {
                'source': 'uia',
                'control_type': 'EditControl',
                'name': '账号输入框'
            },
            'text': 'my_account'
        },
        
        # 步骤3: 点击发送验证码
        {
            'name': '发送验证码',
            'type': 'click_control_by_properties',
            'properties': {
                'source': 'uia',
                'control_type': 'ButtonControl',
                'name': '发送验证码'
            }
        },
        
        # 步骤4: 发送通知
        {
            'name': '发送验证码请求通知',
            'type': 'send_telegram_message',
            'bot_name': 'default',
            'text': '📱 <b>验证码已发送</b>\n'
                   '请在5分钟内将收到的验证码发送给验证码机器人',
            'parse_mode': 'HTML'
        },
        
        # 步骤5: 等待验证码
        {
            'name': '等待验证码',
            'type': 'wait_for_telegram_message',
            'bot_name': 'verification',
            'timeout': 300,
            'filter_func': "lambda msg: any(c.isdigit() for c in msg.get('text', '')) and len([c for c in msg.get('text', '') if c.isdigit()]) >= 4"
        },
        
        # 步骤6: 提取验证码
        {
            'name': '提取验证码',
            'type': 'custom',
            'func': '_extract_verification_code'
        },
        
        # 步骤7: 输入验证码
        {
            'name': '输入验证码',
            'type': 'send_text_to_control_by_properties',
            'properties': {
                'source': 'uia',
                'control_type': 'EditControl',
                'name': '验证码输入框'
            },
            'text': '{{verification_code}}'  # 从step['_result']中获取
        },
        
        # 步骤8: 点击登录
        {
            'name': '点击登录',
            'type': 'click_control_by_properties',
            'properties': {
                'source': 'uia',
                'control_type': 'ButtonControl',
                'name': '登录'
            }
        }
    ]
    
    # 打印步骤
    for i, step in enumerate(verification_steps, 1):
        print(f"\n步骤 {i}: {step['name']}")
        print(f"  类型: {step['type']}")
        if step['type'] == 'wait_for_telegram_message':
            print(f"  机器人: {step.get('bot_name', 'default')}")
            print(f"  超时: {step.get('timeout', 60)}秒")
            if 'filter_func' in step:
                print(f"  过滤: {step['filter_func'][:50]}...")
    
    print("\n💡 关键点:")
    print("1. 使用专门的验证码机器人，避免消息干扰")
    print("2. 过滤函数确保只接收包含数字的消息")
    print("3. 合理设置超时时间，避免无限等待")
    print("4. 提取验证码后立即使用，避免过期")

if __name__ == "__main__":
    import time
    
    print("=" * 70)
    print("游戏自动化与 Telegram 远程控制集成示例")
    print("=" * 70)
    
    print("\n🎮 示例1: 远程控制游戏自动化")
    print("这个示例展示了如何通过Telegram远程控制游戏自动化任务")
    
    # 创建示例实例
    try:
        game = GameWithTelegramControl()
        print(f"\n✅ 成功创建游戏自动化实例")
        print(f"任务步骤数: {len(game.task_steps)}")
        
        # 显示关键步骤
        print("\n📋 关键步骤:")
        key_steps = [0, 2, 3, 4, 11, 15]  # 显示关键步骤索引
        for idx in key_steps:
            if idx < len(game.task_steps):
                step = game.task_steps[idx]
                print(f"  {idx+1}. {step['name']} ({step['type']})")
        
    except Exception as e:
        print(f"\n❌ 创建实例失败: {str(e)}")
        print("请确保 config.yaml 文件存在且配置正确")
    
    # 演示验证码场景
    demonstrate_verification_scenario()
    
    print("\n" + "=" * 70)
    print("总结")
    print("=" * 70)
    print("\n🎯 Telegram 消息集成带来的优势:")
    print("1. 远程控制: 随时随地控制自动化任务")
    print("2. 安全确认: 关键操作前需要人工确认")
    print("3. 验证码处理: 自动接收和输入验证码")
    print("4. 状态通知: 实时了解任务进度")
    print("5. 错误处理: 遇到问题时等待人工干预")
    
    print("\n🚀 开始使用:")
    print("1. 配置多个Telegram机器人")
    print("2. 在游戏自动化任务中添加消息步骤")
    print("3. 测试消息发送和接收功能")
    print("4. 根据实际需求调整步骤和超时时间")
    
    print("\n现在可以开始创建支持Telegram消息交互的游戏自动化任务了！")