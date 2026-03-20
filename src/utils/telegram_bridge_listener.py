#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bridge 消息监听器
用于监听telegram-bridge-service存储在Redis中的消息
"""
import time
import redis
from typing import Dict, List, Optional, Callable
from loguru import logger


class TelegramBridgeListener:
    """Telegram Bridge 消息监听器"""
    
    def __init__(self, config: Dict):
        """
        初始化监听器
        :param config: 配置字典，对应telegram_bridge配置块
        """
        self.config = config
        self.enabled = config.get('enabled', False)
        self.redis_host = config.get('redis_host', '127.0.0.1')
        self.redis_port = int(config.get('redis_port', 6379))
        self.redis_db = int(config.get('redis_db', 2))
        self.redis_password = config.get('redis_password', '')
        self.key_prefix = config.get('key_prefix', 'telegram:bridge:')
        self.listen_chat_ids = config.get('listen_chat_ids', [])
        self.poll_interval = float(config.get('poll_interval', 1))
        self.command_prefix = config.get('command_prefix', '/')
        
        self.running = False
        self.client: Optional[redis.Redis] = None
        self.last_processed_timestamp = 0
        self._message_handlers: List[Callable] = []
        
        # 初始化Redis连接
        if self.enabled:
            self._init_redis()
    
    def _init_redis(self) -> bool:
        """初始化Redis连接"""
        try:
            self.client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                password=self.redis_password if self.redis_password else None,
                decode_responses=True
            )
            self.client.ping()
            logger.info("✅ Telegram Bridge Redis连接成功")
            # 初始化上次处理时间为当前时间，只处理启动后的新消息
            self.last_processed_timestamp = int(time.time())
            return True
        except Exception as e:
            logger.error(f"❌ Telegram Bridge Redis连接失败: {str(e)}")
            self.enabled = False
            return False
    
    def add_message_handler(self, handler: Callable[[Dict], None]):
        """
        添加消息处理器
        :param handler: 处理函数，接收消息字典作为参数
        """
        self._message_handlers.append(handler)
        logger.debug(f"已添加消息处理器，当前处理器数量: {len(self._message_handlers)}")
    
    def _get_new_messages(self) -> List[Dict]:
        """获取新的消息"""
        if not self.client:
            return []
        
        try:
            # 获取所有新消息（时间大于上次处理时间）
            zkey = f"{self.key_prefix}msg:all"
            # zrangebyscore获取大于上次处理时间的消息
            msg_keys = self.client.zrangebyscore(zkey, self.last_processed_timestamp + 1, '+inf')
            
            messages = []
            for key in msg_keys:
                chat_id_str, msg_id_str = key.split(':')
                chat_id = int(chat_id_str)
                msg_id = int(msg_id_str)
                
                # 获取消息详情
                msg_key = f"{self.key_prefix}msg:{chat_id}:{msg_id}"
                msg = self.client.hgetall(msg_key)
                if not msg:
                    continue
                
                # 格式化消息字段
                formatted_msg = self._format_message(msg)
                
                # 过滤聊天ID
                if self.listen_chat_ids and formatted_msg['chat_id'] not in self.listen_chat_ids:
                    continue
                
                messages.append(formatted_msg)
                
                # 更新上次处理时间
                if formatted_msg['timestamp'] > self.last_processed_timestamp:
                    self.last_processed_timestamp = formatted_msg['timestamp']
            
            return messages
        except Exception as e:
            logger.error(f"获取新消息失败: {str(e)}")
            return []
    
    def _format_message(self, msg: Dict) -> Dict:
        """格式化消息字段类型"""
        formatted = msg.copy()
        for field in ['message_id', 'chat_id', 'sender_id', 'timestamp']:
            if field in formatted and formatted[field]:
                try:
                    formatted[field] = int(float(formatted[field])) if '.' in formatted[field] else int(formatted[field])
                except:
                    pass
        for field in ['is_bot', 'has_media']:
            if field in formatted:
                formatted[field] = formatted[field] == 'True'
        return formatted
    
    def _process_message(self, message: Dict):
        """处理单条消息"""
        # 只处理用户发送的消息，不处理bot自己发送的消息
        if message.get('source') == 'bot':
            return
        
        logger.info(f"📥 收到Telegram消息: 聊天ID={message['chat_id']}, 发送者={message['sender_name']}, 内容={message['text'][:100]}")
        
        # 调用所有注册的处理器
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"消息处理器执行失败: {str(e)}")
    
    def is_command(self, message: Dict, command: str = None) -> bool:
        """
        检查消息是否是命令
        :param message: 消息字典
        :param command: 可选，指定命令名称，不传则只检查是否是命令
        """
        text = message.get('text', '').strip()
        if not text.startswith(self.command_prefix):
            return False
        if command is None:
            return True
        return text[len(self.command_prefix):].lower().startswith(command.lower())
    
    def get_command_args(self, message: Dict) -> str:
        """获取命令参数"""
        text = message.get('text', '').strip()
        if not self.is_command(message):
            return ''
        parts = text.split(maxsplit=1)
        return parts[1] if len(parts) > 1 else ''
    
    def start_polling(self, blocking: bool = True) -> Optional[object]:
        """
        开始轮询消息
        :param blocking: 是否阻塞运行，False则返回协程对象
        """
        if not self.enabled:
            logger.warning("⚠️ Telegram Bridge监听未启用，跳过启动")
            return None
        
        self.running = True
        logger.info("🚀 开始监听Telegram Bridge消息")
        
        if not blocking:
            # 返回协程供asyncio运行
            import asyncio
            async def async_poll():
                while self.running:
                    messages = self._get_new_messages()
                    for msg in messages:
                        self._process_message(msg)
                    await asyncio.sleep(self.poll_interval)
            return async_poll()
        
        # 阻塞模式
        while self.running:
            try:
                messages = self._get_new_messages()
                for msg in messages:
                    self._process_message(msg)
                time.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("收到停止信号，停止监听")
                self.stop()
            except Exception as e:
                logger.error(f"轮询异常: {str(e)}")
                time.sleep(self.poll_interval)
    
    def stop(self):
        """停止监听"""
        self.running = False
        if self.client:
            self.client.close()
        logger.info("👋 Telegram Bridge监听已停止")


# 全局单例
_listener_instance: Optional[TelegramBridgeListener] = None


def get_telegram_bridge_listener(config: Dict = None) -> TelegramBridgeListener:
    global _listener_instance
    if _listener_instance is None and config is not None:
        _listener_instance = TelegramBridgeListener(config)
    return _listener_instance
