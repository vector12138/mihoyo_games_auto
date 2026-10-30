#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bridge API 客户端
通过HTTP API调用telegram-bridge-service的接口，不直接操作Redis
"""
import time
import socket
import requests
from typing import Dict, List, Optional, Callable, Tuple
from urllib.parse import urlparse
from loguru import logger


class TelegramBridgeApiClient:
    """Telegram Bridge API 客户端"""
    
    def __init__(self, config: Dict):
        """
        初始化客户端
        :param config: 配置字典，对应telegram_bridge配置块
        """
        self.config = config
        self.enabled = config.get('enabled', False)
        self.mode = config.get('mode', 'telegram')  # 支持bridge/telegram两种模式
        # Bridge模式配置
        self.api_url = config.get('api_url', 'http://127.0.0.1:8080')
        self.api_key = config.get('api_key', '')
        # Telegram原生API模式配置
        self.telegram_api_host = config.get('api_url', 'https://api.telegram.org')
        # 通用配置
        self.bot_token = config.get('bot_token', '')
        self.bot_name = config.get('bot_name', '')
        self.chat_id = config.get('chat_id', '')

        self.listen_chat_ids = config.get('listen_chat_ids', [])
        self.poll_interval = float(config.get('poll_interval', 1))
        self.command_prefix = config.get('command_prefix', '/')

        # 连通性预检配置（默认开启）
        # 开启后，等待Telegram消息前会先探测服务地址，不通则不再使用Telegram超时检测
        self.reachability_check = bool(config.get('reachability_check', True))
        self.reachability_timeout = float(config.get('reachability_timeout', 3))
        self.reachability_fallback_seconds = int(config.get('reachability_fallback_seconds', 1800))
        self._reachable_cache: Optional[bool] = None

        self.running = False
        self.last_processed_timestamp = 0
        self._message_handlers: List[Callable] = []
        
        if self.enabled:
            # 初始化上次处理时间为当前时间，只处理启动后的新消息
            self.last_processed_timestamp = int(time.time())
            if self.mode == 'telegram':
                if not self.bot_token:
                    logger.error("Telegram原生API模式需要配置bot_token")
                    self.enabled = False
                else:
                    logger.info(f"✅ Telegram原生API客户端初始化成功，API Host: {self.telegram_api_host}")
            else:
                logger.info("✅ Telegram Bridge API客户端初始化成功")

    def get_api_endpoint(self) -> Tuple[str, int]:
        """
        获取Telegram服务的主机与端口，用于连通性检测
        :return: (host, port)，无法解析时返回 ('', 0)
        """
        raw = self.telegram_api_host if self.mode == 'telegram' else self.api_url
        raw = str(raw or '').strip()
        if not raw:
            return '', 0
        if '://' not in raw:
            raw = f'http://{raw}'
        try:
            parsed = urlparse(raw)
            host = parsed.hostname or ''
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            return host, int(port)
        except ValueError as e:
            logger.warning(f"解析Telegram服务地址失败: {raw} - {e}")
            return '', 0

    def check_api_reachable(self, timeout: Optional[float] = None, force: bool = False) -> bool:
        """
        检测Telegram服务地址是否可达
        采用TCP连接探测而非ICMP：既能验证主机在线，也能验证端口上的服务可用，
        且不受部分网络屏蔽ICMP的影响；结果在进程内缓存，避免每次等待都重复探测
        :param timeout: 探测超时（秒），默认取配置项reachability_timeout
        :param force: 是否忽略缓存重新探测
        :return: True=可达，False=不可达
        """
        if self._reachable_cache is not None and not force:
            return bool(self._reachable_cache)

        host, port = self.get_api_endpoint()
        if not host:
            logger.warning("Telegram服务地址未配置，连通性检测不通过")
            self._reachable_cache = False
            return False

        timeout = float(timeout) if timeout is not None else self.reachability_timeout
        start_time = time.time()
        sock = None
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
            self._reachable_cache = True
            logger.info(f"✅ Telegram服务连通性检测通过: {host}:{port}（耗时 {time.time() - start_time:.2f}秒）")
        except Exception as e:
            self._reachable_cache = False
            logger.warning(f"❌ Telegram服务连通性检测失败: {host}:{port} - {e}（耗时 {time.time() - start_time:.2f}秒）")
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
        return bool(self._reachable_cache)

    def reset_reachability_cache(self):
        """清除连通性检测缓存，下次检测重新探测"""
        self._reachable_cache = None

    def _request(self, method: str, path: str, params: Dict = None, json: Dict = None) -> Optional[Dict]:
        """
        发送API请求
        """
        url = f"{self.api_url.rstrip('/')}{path}"
        headers = {}
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        
        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API请求失败 {method} {url}: {str(e)}")
            return None
    
    def send_message(self, text: str = '', chat_id: int = None, parse_mode: str = "Markdown", disable_notification: bool = False) -> Optional[str]:
        """
        发送消息
        :return: 任务ID(bridge模式)或消息ID(telegram模式)，失败返回None
        """
        if not self.enabled:
            return None
        
        if self.mode == 'telegram':
            # 直接调用Telegram原生API
            url = f"{self.telegram_api_host.rstrip('/')}/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": chat_id or self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_notification": disable_notification
            }
            try:
                response = requests.post(url, json=data, timeout=10)
                response.raise_for_status()
                result = response.json()
                if result.get('ok'):
                    msg_id = result['result']['message_id']
                    logger.debug(f"Telegram消息发送成功，消息ID: {msg_id}")
                    return str(msg_id)
                else:
                    logger.error(f"Telegram API返回错误: {result.get('description')}")
                    return None
            except Exception as e:
                logger.error(f"调用Telegram API发送消息失败: {str(e)}")
                return None
        else:
            # Bridge模式
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_notification": disable_notification
            }
            result = self._request("POST", "/api/v1/message/send", json=data)
            return result.get('task_id') if result else None
    
    def get_new_messages(self) -> List[Dict]:
        """
        获取新的消息（启动后未处理过的）
        """
        if not self.enabled:
            return []
        
        # 拉取最新100条消息
        result = self._request("GET", "/api/v1/message/received", params={"limit": 100})
        if not result or not isinstance(result, list):
            return []
        
        new_messages = []
        max_timestamp = self.last_processed_timestamp
        
        for msg in result:
            msg_timestamp = msg.get('timestamp', 0)
            # 只处理启动后且未处理过的消息
            if msg_timestamp > self.last_processed_timestamp:
                # 过滤聊天ID
                if self.listen_chat_ids and msg['chat_id'] not in self.listen_chat_ids:
                    continue
                # 过滤自己发送的消息
                if msg.get('source') == 'bot' and msg.get('sender_name') == self.bot_name:
                    continue
                new_messages.append(msg)
                if msg_timestamp > max_timestamp:
                    max_timestamp = msg_timestamp
        
        # 更新最后处理时间
        if max_timestamp > self.last_processed_timestamp:
            self.last_processed_timestamp = max_timestamp
        
        return new_messages
    
    def add_message_handler(self, handler: Callable[[Dict], None]):
        """
        添加消息处理器
        :param handler: 处理函数，接收消息字典作为参数
        """
        self._message_handlers.append(handler)
        logger.debug(f"已添加消息处理器，当前处理器数量: {len(self._message_handlers)}")
    
    def _process_message(self, message: Dict):
        """处理单条消息"""
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
    
    def wait_for_message(self, timeout: int = 300, filter_func: Callable[[Dict], bool] = None) -> Optional[Dict]:
        """
        等待匹配条件的消息
        :param timeout: 超时时间，秒
        :param filter_func: 过滤函数，返回True表示匹配成功
        :return: 匹配到的消息，超时返回None
        """
        if not self.enabled:
            logger.warning("Telegram Bridge未启用，无法等待消息")
            return None
        
        start_time = time.time()
        logger.info(f"⏳ 等待消息，超时时间: {timeout}秒")
        
        while time.time() - start_time < timeout:
            messages = self.get_new_messages()
            for msg in messages:
                if filter_func is None or filter_func(msg):
                    logger.info(f"✅ 匹配到符合条件的消息")
                    return msg
            time.sleep(self.poll_interval)
        
        logger.warning(f"⌛ 等待消息超时，{timeout}秒内未收到符合条件的消息")
        return None
    
    def wait_for_command(self, command: str, timeout: int = 300) -> Optional[str]:
        """
        等待指定命令
        :param command: 命令名称，不带前缀
        :param timeout: 超时时间，秒
        :return: 命令参数，超时返回None
        """
        def filter_func(msg):
            return self.is_command(msg, command)
        
        msg = self.wait_for_message(timeout, filter_func)
        return self.get_command_args(msg) if msg else None
    
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
                    messages = self.get_new_messages()
                    for msg in messages:
                        self._process_message(msg)
                    await asyncio.sleep(self.poll_interval)
            return async_poll()
        
        # 阻塞模式
        while self.running:
            try:
                messages = self.get_new_messages()
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
        logger.info("👋 Telegram Bridge监听已停止")


# 全局单例
_client_instance: Optional[TelegramBridgeApiClient] = None


def get_telegram_bridge_client(config: Dict = None) -> TelegramBridgeApiClient:
    global _client_instance
    if _client_instance is None and config is not None:
        _client_instance = TelegramBridgeApiClient(config)
    return _client_instance
