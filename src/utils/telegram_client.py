#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 客户端工具
支持多个机器人应用的消息监听和发送
"""

import asyncio
import threading
import time
import json
from typing import Dict, List, Optional, Callable, Any
from loguru import logger
import requests
from urllib.parse import urljoin


class TelegramClient:
    """Telegram 客户端，支持多个机器人实例"""
    
    def __init__(self, config: Dict):
        """
        初始化 Telegram 客户端
        :param config: 配置字典，包含多个机器人的配置
        """
        self.config = config
        self.bots: Dict[str, Dict] = {}  # 机器人实例配置
        self.message_handlers: Dict[str, List[Callable]] = {}  # 消息处理器
        self.last_update_ids: Dict[str, int] = {}  # 每个机器人的最后更新ID
        self.running = False
        self.listen_thread: Optional[threading.Thread] = None
        
        # 初始化机器人配置
        self._init_bots()
    
    def _init_bots(self):
        """初始化机器人配置"""
        # 从全局配置获取默认机器人
        global_config = self.config.get('global', {})
        if global_config.get('telegram_notify', False):
            token = global_config.get('telegram_token', '')
            chat_id = global_config.get('telegram_chat_id', '')
            if token and chat_id:
                self.bots['default'] = {
                    'token': token,
                    'chat_id': chat_id,
                    'name': 'default'
                }
        
        # 从配置中获取其他机器人
        telegram_bots = self.config.get('telegram_bots', {})
        for bot_name, bot_config in telegram_bots.items():
            if bot_config.get('enabled', False):
                self.bots[bot_name] = {
                    'token': bot_config.get('token', ''),
                    'chat_id': bot_config.get('chat_id', ''),
                    'name': bot_name
                }
        
        logger.info(f"初始化了 {len(self.bots)} 个 Telegram 机器人")
    
    def send_message(self, bot_name: str = 'default', text: str = '', 
                    parse_mode: str = 'HTML', disable_notification: bool = False) -> bool:
        """
        发送消息到指定机器人
        :param bot_name: 机器人名称，默认为 'default'
        :param text: 消息文本
        :param parse_mode: 解析模式，支持 'HTML' 或 'Markdown'
        :param disable_notification: 是否禁用通知
        :return: 是否发送成功
        """
        if bot_name not in self.bots:
            logger.error(f"机器人 '{bot_name}' 未配置")
            return False
        
        bot = self.bots[bot_name]
        token = bot['token']
        chat_id = bot['chat_id']
        
        if not token or not chat_id:
            logger.error(f"机器人 '{bot_name}' 的 token 或 chat_id 未配置")
            return False
        
        # 构建请求URL
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        # 构建请求数据
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_notification': disable_notification
        }
        
        # 发送请求
        try:
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                logger.debug(f"Telegram 消息发送成功: {bot_name}")
                return True
            else:
                logger.error(f"Telegram 消息发送失败: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"发送 Telegram 消息时出错: {str(e)}")
            return False
    
    def get_updates(self, bot_name: str = 'default', timeout: int = 30, 
                   offset: Optional[int] = None) -> List[Dict]:
        """
        获取指定机器人的更新
        :param bot_name: 机器人名称
        :param timeout: 长轮询超时时间（秒）
        :param offset: 更新ID偏移量
        :return: 更新列表
        """
        if bot_name not in self.bots:
            logger.error(f"机器人 '{bot_name}' 未配置")
            return []
        
        bot = self.bots[bot_name]
        token = bot['token']
        
        if not token:
            logger.error(f"机器人 '{bot_name}' 的 token 未配置")
            return []
        
        # 构建请求URL
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        
        # 构建请求参数
        params = {
            'timeout': timeout,
            'allowed_updates': ['message']  # 只接收消息更新
        }
        
        if offset is not None:
            params['offset'] = offset
        
        # 发送请求
        try:
            response = requests.get(url, params=params, timeout=timeout + 5)
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    updates = result.get('result', [])
                    
                    # 更新最后更新ID
                    if updates:
                        last_update_id = updates[-1]['update_id']
                        self.last_update_ids[bot_name] = last_update_id + 1
                    
                    return updates
                else:
                    logger.error(f"获取更新失败: {result.get('description', '未知错误')}")
                    return []
            else:
                logger.error(f"获取更新HTTP错误: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"获取 Telegram 更新时出错: {str(e)}")
            return []
    
    def wait_for_message(self, bot_name: str = 'default', timeout: int = 60, 
                        filter_func: Optional[Callable[[Dict], bool]] = None) -> Optional[Dict]:
        """
        等待特定消息
        :param bot_name: 机器人名称
        :param timeout: 超时时间（秒）
        :param filter_func: 消息过滤函数，返回True表示匹配
        :return: 匹配的消息字典，超时返回None
        """
        start_time = time.time()
        last_update_id = self.last_update_ids.get(bot_name)
        
        while time.time() - start_time < timeout:
            updates = self.get_updates(bot_name, timeout=10, offset=last_update_id)
            
            for update in updates:
                message = update.get('message', {})
                
                # 如果没有过滤函数，返回第一条消息
                if filter_func is None:
                    return message
                
                # 使用过滤函数检查消息
                if filter_func(message):
                    return message
            
            # 更新最后更新ID
            if updates:
                last_update_id = self.last_update_ids.get(bot_name)
            
            # 短暂休眠避免过于频繁的请求
            time.sleep(0.5)
        
        logger.warning(f"等待 Telegram 消息超时 ({timeout}秒)")
        return None
    
    def wait_for_text(self, bot_name: str = 'default', expected_text: str = '', 
                     timeout: int = 60, case_sensitive: bool = False) -> Optional[Dict]:
        """
        等待特定文本消息
        :param bot_name: 机器人名称
        :param expected_text: 期望的文本
        :param timeout: 超时时间（秒）
        :param case_sensitive: 是否区分大小写
        :return: 匹配的消息字典，超时返回None
        """
        def text_filter(message: Dict) -> bool:
            text = message.get('text', '')
            if not text:
                return False
            
            if case_sensitive:
                return text == expected_text
            else:
                return text.lower() == expected_text.lower()
        
        return self.wait_for_message(bot_name, timeout, text_filter)
    
    def wait_for_command(self, bot_name: str = 'default', command: str = '', 
                        timeout: int = 60) -> Optional[Dict]:
        """
        等待特定命令消息
        :param bot_name: 机器人名称
        :param command: 命令（不带斜杠）
        :param timeout: 超时时间（秒）
        :return: 匹配的消息字典，超时返回None
        """
        def command_filter(message: Dict) -> bool:
            text = message.get('text', '')
            if not text or not text.startswith('/'):
                return False
            
            # 提取命令（去掉斜杠和可能的参数）
            cmd = text.split()[0][1:] if ' ' in text else text[1:]
            return cmd == command
        
        return self.wait_for_message(bot_name, timeout, command_filter)
    
    def wait_for_sender(self, bot_name: str = 'default', sender_id: int = None, 
                       timeout: int = 60) -> Optional[Dict]:
        """
        等待特定发送者的消息
        :param bot_name: 机器人名称
        :param sender_id: 发送者ID
        :param timeout: 超时时间（秒）
        :return: 匹配的消息字典，超时返回None
        """
        def sender_filter(message: Dict) -> bool:
            from_user = message.get('from', {})
            return from_user.get('id') == sender_id
        
        return self.wait_for_message(bot_name, timeout, sender_filter)
    
    def start_listening(self, bot_name: str = 'default', 
                       message_handler: Optional[Callable[[Dict], None]] = None):
        """
        开始监听指定机器人的消息（异步）
        :param bot_name: 机器人名称
        :param message_handler: 消息处理函数
        """
        if self.running:
            logger.warning("监听器已经在运行")
            return
        
        self.running = True
        
        def listen_loop():
            """监听循环"""
            while self.running:
                try:
                    updates = self.get_updates(bot_name, timeout=30)
                    
                    for update in updates:
                        message = update.get('message', {})
                        
                        # 调用消息处理器
                        if message_handler:
                            try:
                                message_handler(message)
                            except Exception as e:
                                logger.error(f"消息处理器出错: {str(e)}")
                        
                        # 调用注册的处理器
                        for handler in self.message_handlers.get(bot_name, []):
                            try:
                                handler(message)
                            except Exception as e:
                                logger.error(f"注册的消息处理器出错: {str(e)}")
                    
                    # 短暂休眠
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"监听循环出错: {str(e)}")
                    time.sleep(1)
        
        # 启动监听线程
        self.listen_thread = threading.Thread(target=listen_loop, daemon=True)
        self.listen_thread.start()
        logger.info(f"开始监听 Telegram 机器人: {bot_name}")
    
    def stop_listening(self):
        """停止监听"""
        self.running = False
        if self.listen_thread:
            self.listen_thread.join(timeout=5)
            self.listen_thread = None
        logger.info("停止监听 Telegram 消息")
    
    def register_handler(self, bot_name: str, handler: Callable[[Dict], None]):
        """
        注册消息处理器
        :param bot_name: 机器人名称
        :param handler: 消息处理函数
        """
        if bot_name not in self.message_handlers:
            self.message_handlers[bot_name] = []
        
        self.message_handlers[bot_name].append(handler)
        logger.debug(f"为机器人 '{bot_name}' 注册了消息处理器")
    
    def unregister_handler(self, bot_name: str, handler: Callable[[Dict], None]):
        """
        注销消息处理器
        :param bot_name: 机器人名称
        :param handler: 消息处理函数
        """
        if bot_name in self.message_handlers:
            if handler in self.message_handlers[bot_name]:
                self.message_handlers[bot_name].remove(handler)
                logger.debug(f"从机器人 '{bot_name}' 注销了消息处理器")


# 单例实例
_telegram_client_instance = None

def get_telegram_client(config: Optional[Dict] = None) -> TelegramClient:
    """
    获取 Telegram 客户端单例
    :param config: 配置字典，如果为None则使用默认配置
    :return: TelegramClient 实例
    """
    global _telegram_client_instance
    
    if _telegram_client_instance is None and config is not None:
        _telegram_client_instance = TelegramClient(config)
    
    return _telegram_client_instance