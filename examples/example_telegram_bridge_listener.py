#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bridge 监听器使用示例
"""
import yaml
import time
from src.utils.telegram_bridge_listener import get_telegram_bridge_listener


# 加载配置
def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def message_handler(message: dict):
    """
    自定义消息处理器
    :param message: 消息字典
    """
    listener = get_telegram_bridge_listener()
    
    # 处理命令
    if listener.is_command(message, 'start'):
        print(f"收到启动命令，参数: {listener.get_command_args(message)}")
        # 这里可以添加启动游戏任务的逻辑
    
    elif listener.is_command(message, 'stop'):
        print("收到停止命令")
        # 这里可以添加停止任务的逻辑
    
    elif listener.is_command(message, 'status'):
        print("收到状态查询命令")
        # 这里可以添加查询当前任务状态的逻辑
    
    else:
        # 普通消息
        print(f"收到普通消息: {message['text']}")


def main():
    config = load_config()
    
    # 获取监听器实例
    listener = get_telegram_bridge_listener(config.get('telegram_bridge', {}))
    
    if not listener.enabled:
        print("Telegram Bridge监听未启用，请在config.yaml中开启telegram_bridge.enabled")
        return
    
    # 添加自定义消息处理器
    listener.add_message_handler(message_handler)
    
    # 开始阻塞轮询
    try:
        listener.start_polling(blocking=True)
    except KeyboardInterrupt:
        print("程序退出")


if __name__ == "__main__":
    main()
