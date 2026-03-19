#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 客户端工具
单机器人模式，支持消息发送和等待特定消息
"""

import threading
import time
from typing import Optional, Callable, Any
from loguru import logger
import requests


class TelegramClient:
    """Telegram 客户端，单机器人模式"""
    
    def __init__(self, config: dict):
        """
        初始化 Telegram 客户端
        :param config: 配置字典，包含单个机器人的配置
        """
        self.config = config
        self.bot_config: dict = None  # 机器人配置
        self.last_update_id: int = 0  # 最后更新ID
        self.running = False
        self.listen_thread: Optional[threading.Thread] = None
        self.message_queue = []  # 消息队列
        
        # 初始化机器人配置
        self._init_bot()
    
    def _init_bot(self):
        """初始化机器人配置"""
        # 从配置中获取主机器人
        telegram_config = self.config.get('telegram_bots', {}).get('main', {})
        if telegram_config.get('enabled', False):
            token = telegram_config.get('token', '')
            chat_id = telegram_config.get('chat_id', '')
            if token and chat_id:
                self.bot_config = {
                    'token': token,
                    'chat_id': chat_id
                }
                logger.info(f"Telegram机器人初始化成功，聊天ID: {chat_id}")
                return
        
        # 兼容旧配置：从全局配置获取
        global_config = self.config.get('global', {})
        if global_config.get('telegram_notify', False):
            token = global_config.get('telegram_token', '')
            chat_id = global_config.get('telegram_chat_id', '')
            if token and chat_id:
                self.bot_config = {
                    'token': token,
                    'chat_id': chat_id
                }
                logger.info(f"从全局配置初始化Telegram机器人成功，聊天ID: {chat_id}")
                return
        
        logger.warning("未找到有效的Telegram机器人配置")
    
    def is_available(self) -> bool:
        """检查机器人是否可用"""
        return self.bot_config is not None
    
    def send_message(self, text: str = '', parse_mode: str = 'HTML', 
                    disable_notification: bool = False) -> bool:
        """
        发送文本消息
        :param text: 消息文本
        :param parse_mode: 解析模式，支持HTML和Markdown
        :param disable_notification: 是否禁用通知
        :return: 发送是否成功
        """
        if not self.is_available():
            logger.error("Telegram机器人未配置")
            return False
        
        token = self.bot_config['token']
        chat_id = self.bot_config['chat_id']
        
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_notification': disable_notification
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.debug(f"消息发送成功到 {chat_id}")
                return True
            else:
                logger.error(f"消息发送失败: {response.status_code}, {response.text}")
                return False
        except Exception as e:
            logger.error(f"发送消息时出错: {str(e)}")
            return False
    
    def get_updates(self, timeout: int = 30) -> list[dict]:
        """
        获取更新
        :param timeout: 长轮询超时时间（秒）
        :return: 更新列表
        """
        if not self.is_available():
            logger.error("Telegram机器人未配置")
            return []
        
        token = self.bot_config['token']
        
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            params = {
                'timeout': timeout,
                'allowed_updates': ['message'],
                'offset': self.last_update_id + 1 if self.last_update_id else None
            }
            
            response = requests.get(url, params=params, timeout=timeout + 5)
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    updates = result.get('result', [])
                    if updates:
                        self.last_update_id = updates[-1]['update_id']
                    return updates
                else:
                    logger.error(f"获取更新失败: {result.get('description', '未知错误')}")
                    return []
            else:
                logger.error(f"获取更新HTTP错误: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"获取Telegram更新时出错: {str(e)}")
            return []
    
    def wait_for_message(self, timeout: int = 60, 
                        filter_func: Optional[Callable[[dict], bool]] = None) -> Optional[dict]:
        """
        等待特定消息
        :param timeout: 超时时间（秒）
        :param filter_func: 过滤函数，接收消息字典，返回True表示匹配成功
        :return: 匹配的消息字典，超时返回None
        """
        if not self.is_available():
            logger.error("Telegram机器人未配置")
            return None
        
        start_time = time.time()
        logger.info(f"开始等待Telegram消息，超时时间: {timeout}秒")
        
        while time.time() - start_time < timeout:
            updates = self.get_updates(timeout=min(10, int(timeout - (time.time() - start_time))))
            
            for update in updates:
                message = update.get('message', {})
                if not message:
                    continue
                
                # 只处理来自配置的聊天ID的消息
                if str(message.get('chat', {}).get('id', '')) != str(self.bot_config['chat_id']):
                    logger.debug(f"忽略来自其他聊天的消息: {message.get('chat', {}).get('id')}")
                    continue
                
                # 如果没有过滤函数，直接返回第一条消息
                if filter_func is None:
                    logger.info(f"收到消息: {message.get('text', '')[:50]}...")
                    return message
                
                # 使用过滤函数匹配
                if filter_func(message):
                    logger.info(f"收到匹配的消息: {message.get('text', '')[:50]}...")
                    return message
            
            # 短暂休眠避免频繁请求
            time.sleep(0.5)
        
        logger.warning(f"等待Telegram消息超时: {timeout}秒")
        return None
    
    def wait_for_text(self, expected_text: str, timeout: int = 60, 
                     case_sensitive: bool = False) -> Optional[dict]:
        """
        等待包含特定文本的消息
        :param expected_text: 期望的文本
        :param timeout: 超时时间（秒）
        :param case_sensitive: 是否区分大小写
        :return: 匹配的消息字典，超时返回None
        """
        def filter_func(message):
            text = message.get('text', '')
            if not case_sensitive:
                return expected_text.lower() in text.lower()
            return expected_text in text
        
        return self.wait_for_message(timeout=timeout, filter_func=filter_func)
    
    def wait_for_command(self, command: str, timeout: int = 60) -> Optional[dict]:
        """
        等待特定命令（以/开头）
        :param command: 命令，不需要带/
        :param timeout: 超时时间（秒）
        :return: 匹配的消息字典，超时返回None
        """
        expected_command = f"/{command.lower()}"
        
        def filter_func(message):
            text = message.get('text', '').strip().lower()
            return text == expected_command or text.startswith(f"{expected_command} ")
        
        return self.wait_for_message(timeout=timeout, filter_func=filter_func)


# 全局实例
_telegram_client: Optional[TelegramClient] = None


def get_telegram_client(config: dict = None) -> Optional[TelegramClient]:
    """
    获取Telegram客户端单例
    :param config: 配置字典，首次调用时需要
    :return: Telegram客户端实例
    """
    global _telegram_client
    if _telegram_client is None and config is not None:
        _telegram_client = TelegramClient(config)
    return _telegram_client
