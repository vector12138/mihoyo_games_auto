#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram群聊消息接收调试脚本
"""
import sys
import os
import yaml
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.telegram_client import TelegramClient
from loguru import logger


def load_config():
    """加载配置"""
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        config_path = "config.example.yaml"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def debug_group_messages():
    """调试群消息接收"""
    logger.info("=== Telegram群聊消息调试 ===")
    
    config = load_config()
    
    # 构建Telegram配置
    telegram_config = {}
    global_config = config.get('global', {})
    if global_config.get('telegram_notify', False):
        telegram_config = {
            'enabled': True,
            'bot_token': global_config.get('telegram_token', ''),
            'chat_id': global_config.get('telegram_chat_id', ''),
            'proxy': config.get('telegram_proxy', {})
        }
    
    telegram_bots_config = config.get('telegram_bots', {}).get('main', {})
    if telegram_bots_config.get('enabled', False):
        telegram_config = {
            'enabled': telegram_bots_config.get('enabled', False),
            'bot_token': telegram_bots_config.get('token', ''),
            'chat_id': telegram_bots_config.get('chat_id', ''),
            'proxy': config.get('telegram_proxy', {})
        }
    
    logger.info(f"当前配置:")
    logger.info(f"Bot Token: {telegram_config.get('bot_token', '未配置')[:10]}...")
    logger.info(f"Chat ID: {telegram_config.get('chat_id', '未配置')}")
    
    # 创建客户端
    client = TelegramClient(telegram_config)
    
    if not client.enabled:
        logger.error("❌ Telegram未启用，请检查配置")
        return
    
    # 测试连接
    if not client.test_connection():
        logger.error("❌ 连接失败，请检查token和网络/代理配置")
        return
    logger.info("✅ 连接成功")
    
    # 先发送一条测试消息到群里
    test_text = "🔧 调试消息：我是当前Bot，正在测试消息接收"
    if client.send_message(test_text):
        logger.info("✅ 测试消息已发送到群里")
    else:
        logger.error("❌ 测试消息发送失败，请检查Bot是否在群里")
    
    logger.info("\n📡 开始监听群消息（60秒），请用其他账号/Bot往群里发任意消息...")
    logger.info("收到消息会打印完整内容，请检查是否能收到：")
    
    start_time = time.time()
    while time.time() - start_time < 60:
        updates = client.get_updates(timeout=10)
        for update in updates:
            message = update.get('message', {})
            if message:
                logger.info("\n" + "="*50)
                logger.info(f"收到消息，Chat ID: {message.get('chat', {}).get('id')}")
                logger.info(f"发送者: {message.get('from', {}).get('first_name', '未知')} (ID: {message.get('from', {}).get('id')}, Bot: {message.get('from', {}).get('is_bot', False)})")
                logger.info(f"消息内容: {message.get('text', '非文本消息')}")
                logger.info("="*50 + "\n")
        
        time.sleep(1)
    
    logger.info("\n⏰ 监听结束")
    logger.info("如果能收到消息但wait_for_*方法超时，请检查过滤条件（比如only_user=True会过滤Bot消息）")
    logger.info("如果收不到任何消息，请检查：")
    logger.info("1. 隐私模式是否关闭（必须Disable）")
    logger.info("2. Chat ID是否正确，是不是群ID")
    logger.info("3. Bot是否在群里，有权限读取消息")


if __name__ == '__main__':
    import time
    debug_group_messages()
