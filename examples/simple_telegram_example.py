#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单机器人Telegram功能使用示例
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.game_base import MultiAppBase
from src.utils.config_loader import load_config


class TelegramDemo(MultiAppBase):
    """Telegram功能演示类"""
    
    def __init__(self, config):
        super().__init__(config, config)
        
        # 定义任务步骤
        self.task_steps = [
            # 步骤1：发送测试消息
            {
                'type': 'send_telegram_message',
                'text': '🤖 自动化任务开始执行，请确认是否继续？\n\n回复 "继续" 或发送 /continue 命令继续执行',
                'disable_notification': False
            },
            # 步骤2：等待用户回复"继续"
            {
                'type': 'wait_for_telegram_text',
                'expected_text': '继续',
                'timeout': 300,  # 等待5分钟
                'case_sensitive': False
            },
            # 步骤3：收到确认后继续执行
            {
                'type': 'send_telegram_message',
                'text': '✅ 收到确认，开始执行任务...'
            },
            # 步骤4：等待命令
            {
                'type': 'wait_for_telegram_command',
                'command': 'stop',
                'timeout': 600  # 等待10分钟停止命令
            },
            {
                'type': 'send_telegram_message',
                'text': '🛑 收到停止命令，任务结束'
            }
        ]
    
    def run(self):
        """运行任务"""
        if not self.telegram_client or not self.telegram_client.is_available():
            print("❌ Telegram未配置，请先在config.yaml中配置Telegram机器人信息")
            return False
        
        print("🚀 开始Telegram功能演示")
        return self.execute_steps()


if __name__ == '__main__':
    # 加载配置
    config = load_config('config.yaml')
    
    # 创建演示实例
    demo = TelegramDemo(config)
    
    # 运行演示
    demo.run()
