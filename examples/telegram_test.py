#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram功能测试脚本
测试连接、消息发送、消息等待等功能
"""

import sys
import os
import yaml
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.telegram_bridge_api_client import TelegramBridgeApiClient as TelegramClient
from loguru import logger


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')
    if not os.path.exists(config_path):
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.example.yaml')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"❌ 加载配置文件失败: {e}")
        return None


def test_telegram():
    """测试Telegram功能"""
    logger.info("=== 测试Telegram功能 ===")
    
    # 加载配置
    config = load_config()
    if not config:
        return False
    
    # 构建Telegram配置
    telegram_config = config.get('telegram', {})
    
    # 创建客户端
    client = TelegramClient(telegram_config)
    
    if not client.enabled:
        logger.error("❌ Telegram未启用，请先在config.yaml中配置Telegram机器人信息")
        return False
    
    # 测试2：发送消息
    logger.info("\n2. 测试发送消息...")
    test_text = "🔧 *Telegram功能测试*\n\n这是测试消息，来自米哈游游戏自动化工具。\n*时间*: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if not client.send_message(test_text, chat_id=-50437341):
        logger.error("❌ 发送消息失败")
        return False
    logger.info("✅ 发送消息成功")

    def filter_test_message(msg):
        return msg.get('sender_name', '') == 'games' and '这是一条测试消息' in msg.get('text', '')
    
    # 测试3：等待消息
    logger.info("\n3. 测试消息等待功能（请在30秒内回复任意消息）...")
    message = client.wait_for_message(timeout=30)
    if not message:
        logger.warning("⚠️  等待消息超时，跳过消息测试")
    else:
        logger.info(f"✅ 收到消息: {message.get('text', '')}")
        
        # 测试文本匹配
        logger.info("\n4. 测试文本匹配功能（请在30秒内回复包含\"这是一条测试消息\"的消息）...")
        message = client.wait_for_message(timeout=30, filter_func=filter_test_message)
        if not message:
            logger.warning("⚠️  等待文本超时")
        else:
            logger.info(f"✅ 收到匹配文本: {message.get('text', '')}")
    
    logger.info("\n🎉 所有测试完成！")
    return True


if __name__ == '__main__':
    from datetime import datetime
    test_telegram()
