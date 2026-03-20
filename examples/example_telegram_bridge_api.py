#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bridge API客户端使用示例
"""
import yaml
import time
from src.utils.telegram_bridge_api_client import get_telegram_bridge_client


# 加载配置
def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def message_handler(message: dict):
    """
    自定义消息处理器
    :param message: 消息字典
    """
    client = get_telegram_bridge_client()
    
    # 处理命令
    if client.is_command(message, 'start'):
        args = client.get_command_args(message)
        print(f"收到启动命令，参数: {args}")
        # 这里可以添加启动游戏任务的逻辑
        # 回复消息
        client.send_message(message['chat_id'], f"✅ 收到启动命令，参数: {args}")
    
    elif client.is_command(message, 'stop'):
        print("收到停止命令")
        client.send_message(message['chat_id'], "🛑 已停止任务")
    
    elif client.is_command(message, 'status'):
        print("收到状态查询命令")
        client.send_message(message['chat_id'], "📊 当前任务运行正常")
    
    else:
        # 普通消息
        print(f"收到普通消息: {message['text']}")
        # 自动回复
        client.send_message(message['chat_id'], f"收到消息: {message['text']}")


def main():
    config = load_config()
    
    # 获取客户端实例
    client = get_telegram_bridge_client(config.get('telegram_bridge', {}))
    
    if not client.enabled:
        print("Telegram Bridge未启用，请在config.yaml中开启telegram_bridge.enabled并配置api_url")
        return
    
    # 测试发送消息
    chat_id = config.get('global', {}).get('telegram_chat_id')
    if chat_id:
        task_id = client.send_message(chat_id, "🚀 Telegram Bridge客户端已启动")
        print(f"发送消息任务ID: {task_id}")
    
    # 测试等待命令
    print("等待/hello命令...")
    args = client.wait_for_command('hello', timeout=30)
    if args is not None:
        print(f"收到/hello命令，参数: {args}")
        client.send_message(chat_id, f"👋 Hello! 你的参数是: {args}")
    
    # 添加消息处理器并开始轮询
    client.add_message_handler(message_handler)
    print("开始监听消息，按Ctrl+C退出")
    try:
        client.start_polling(blocking=True)
    except KeyboardInterrupt:
        print("程序退出")


if __name__ == "__main__":
    main()
