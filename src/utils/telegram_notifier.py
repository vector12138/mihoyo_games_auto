#!/usr/bin/env python3
"""
Telegram工具类
融合通知功能和消息等待功能
支持代理配置、消息发送、图片发送、消息监听等
"""

import requests
import yaml
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Callable, List
from loguru import logger

class TelegramNotifier:
    """Telegram通知器，支持代理"""
    
    def __init__(self, config=None):
        """初始化Telegram工具类"""
        self.config = config or {}
        self.bot_token = self.config.get('bot_token', '')
        self.chat_id = self.config.get('chat_id', '')
        self.enabled = self.config.get('enabled', False) and self.bot_token and self.chat_id
        
        # 代理配置
        self.proxy_config = self.config.get('proxy', {})
        self.proxy_enabled = self.proxy_config.get('enabled', False)
        self.proxy_url = self.proxy_config.get('url', '')
        self.proxy_auth = self.proxy_config.get('auth', {})
        
        # 创建会话
        self.session = self._create_session()
        
        # 消息监听相关属性
        self.last_update_id = 0
        self.running = False
        self.listen_thread: Optional[threading.Thread] = None
        self.message_queue = []
        
        if self.enabled:
            proxy_info = "（使用代理）" if self.proxy_enabled else ""
            logger.info(f"Telegram已启用{proxy_info}，Chat ID: {self.chat_id}")
        else:
            logger.warning("Telegram未启用，请检查配置")
    
    def _create_session(self):
        """创建HTTP会话，配置代理"""
        session = requests.Session()
        
        if self.proxy_enabled and self.proxy_url:
            try:
                proxies = {
                    'http': self.proxy_url,
                    'https': self.proxy_url
                }
                
                # 配置代理认证
                if self.proxy_auth:
                    username = self.proxy_auth.get('username')
                    password = self.proxy_auth.get('password')
                    if username and password:
                        from requests.auth import HTTPProxyAuth
                        session.proxies = proxies
                        session.auth = HTTPProxyAuth(username, password)
                    else:
                        session.proxies = proxies
                
                logger.debug(f"已配置代理: {self.proxy_url}")
            except Exception as e:
                logger.error(f"配置代理失败: {e}")
        
        # 设置默认超时
        session.timeout = 10
        
        return session
    
    def send_message(self, text, parse_mode='Markdown', disable_notification=False):
        """
        发送消息到Telegram
        :param text: 消息内容
        :param parse_mode: 解析模式（Markdown/HTML）
        :param disable_notification: 是否静默发送
        :return: 是否成功
        """
        if not self.enabled:
            logger.debug("Telegram通知未启用，跳过发送")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_notification': disable_notification
            }
            
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Telegram消息发送成功: {text[:50]}...")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"发送Telegram消息失败: {e}")
            return False
        except Exception as e:
            logger.error(f"Telegram消息异常: {e}")
            return False
    
    def send_photo(self, photo_path, caption='', disable_notification=False):
        """
        发送图片到Telegram
        :param photo_path: 图片路径
        :param caption: 图片说明
        :param disable_notification: 是否静默发送
        :return: 是否成功
        """
        if not self.enabled:
            logger.debug("Telegram通知未启用，跳过发送")
            return False
        
        if not Path(photo_path).exists():
            logger.error(f"图片不存在: {photo_path}")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            
            with open(photo_path, 'rb') as photo_file:
                files = {'photo': photo_file}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption,
                    'disable_notification': disable_notification
                }
                
                response = self.session.post(url, files=files, data=data, timeout=30)
                response.raise_for_status()
            
            logger.info(f"Telegram图片发送成功: {photo_path}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"发送Telegram图片失败: {e}")
            return False
        except Exception as e:
            logger.error(f"Telegram图片异常: {e}")
            return False
    
    def notify_task_start(self, task_name):
        """通知任务开始"""
        text = f"🚀 *任务开始*\n\n*任务*: {task_name}\n*时间*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(text)
    
    def notify_task_complete(self, task_name, duration_seconds, success=True):
        """通知任务完成"""
        status = "✅ 成功" if success else "❌ 失败"
        duration = f"{duration_seconds:.1f}秒 ({duration_seconds/60:.1f}分钟)"
        
        text = f"{status} *任务完成*\n\n*任务*: {task_name}\n*状态*: {status}\n*耗时*: {duration}\n*时间*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(text)
    
    def notify_task_error(self, task_name, error_message, screenshot_path=None):
        """通知任务错误"""
        text = f"⚠️ *任务错误*\n\n*任务*: {task_name}\n*错误*: {error_message}\n*时间*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        success = self.send_message(text)
        
        # 如果有截图，发送截图
        if screenshot_path and Path(screenshot_path).exists():
            self.send_photo(screenshot_path, caption=f"错误截图: {task_name}")
        
        return success
    
    def notify_system_status(self, status, details=''):
        """通知系统状态"""
        text = f"📊 *系统状态*\n\n*状态*: {status}\n*详情*: {details}\n*时间*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return self.send_message(text)
    
    def test_connection(self):
        """
        测试Telegram连接（包括代理）
        :return: 是否连接成功
        """
        if not self.enabled:
            logger.warning("Telegram通知未启用，无法测试连接")
            return False
        
        try:
            # 使用getMe方法测试连接
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                username = bot_info.get('username', '未知')
                logger.info(f"Telegram连接测试成功，Bot: @{username}")
                
                # 测试代理连接
                if self.proxy_enabled:
                    logger.info(f"代理配置: {self.proxy_url}")
                
                return True
            else:
                logger.error(f"Telegram API返回错误: {data}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram连接测试失败: {e}")
            return False
        except Exception as e:
            logger.error(f"连接测试异常: {e}")
            return False
    
    def notify_daily_report(self, report_data):
        """发送每日报告"""
        if not report_data:
            return False
        
        success_count = report_data.get('success_count', 0)
        total_count = report_data.get('total_count', 0)
        total_time = report_data.get('total_time', 0)
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        text = f"📈 *每日自动化报告*\n\n"
        text += f"*日期*: {datetime.now().strftime('%Y-%m-%d')}\n"
        text += f"*成功率*: {success_count}/{total_count} ({success_rate:.1f}%)\n"
        text += f"*总耗时*: {total_time/60:.1f}分钟\n"
        text += f"*完成时间*: {datetime.now().strftime('%H:%M:%S')}\n\n"
        
        # 添加详细结果
        details = report_data.get('details', [])
        if details:
            text += "*详细结果*:\n"
            for detail in details:
                status = "✅" if detail.get('success') else "❌"
                text += f"{status} {detail.get('task', '未知')}: {detail.get('duration', 0):.1f}秒\n"
        
        return self.send_message(text)

def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent / 'config.yaml'
    if not config_path.exists():
        config_path = Path(__file__).parent / 'config.example.yaml'
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return None

def test_notifier():
    """测试通知功能"""
    logger.info("测试Telegram通知功能...")
    
    config = load_config()
    if not config:
        logger.error("❌ 无法加载配置")
        return False
    
    telegram_config = config.get('telegram', {})
    notifier = TelegramNotifier(telegram_config)
    
    if not notifier.enabled:
        logger.error("❌ Telegram通知未启用，请检查配置")
        return False
    
    # 测试连接
    logger.info("测试Telegram连接...")
    if not notifier.test_connection():
        logger.error("❌ Telegram连接测试失败")
        return False
    
    # 测试消息
    logger.info("发送测试消息...")
    success = notifier.send_message("🔧 *测试消息*\n\n这是米哈游游戏自动化的测试通知。\n*时间*: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    if success:
        logger.info("✅ 测试消息发送成功")
    else:
        logger.error("❌ 测试消息发送失败")
    
    return success

    # ==================== 消息等待功能 ====================
    def get_updates(self, timeout: int = 30) -> List[Dict]:
        """
        获取Telegram更新
        :param timeout: 长轮询超时时间（秒）
        :return: 更新列表
        """
        if not self.enabled:
            logger.error("Telegram未启用，无法获取更新")
            return []
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            params = {
                'timeout': timeout,
                'allowed_updates': ['message'],
                'offset': self.last_update_id + 1 if self.last_update_id else None
            }
            
            response = self.session.get(url, params=params, timeout=timeout + 5)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                updates = result.get('result', [])
                if updates:
                    self.last_update_id = updates[-1]['update_id']
                return updates
            else:
                logger.error(f"获取更新失败: {result.get('description', '未知错误')}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"获取Telegram更新失败: {e}")
            return []
        except Exception as e:
            logger.error(f"获取更新异常: {e}")
            return []
    
    def wait_for_message(self, timeout: int = 60, 
                        filter_func: Optional[Callable[[Dict], bool]] = None) -> Optional[Dict]:
        """
        等待特定消息
        :param timeout: 超时时间（秒）
        :param filter_func: 过滤函数，接收消息字典，返回True表示匹配成功
        :return: 匹配的消息字典，超时返回None
        """
        if not self.enabled:
            logger.error("Telegram未启用，无法等待消息")
            return None
        
        start_time = time.time()
        logger.info(f"开始等待Telegram消息，超时时间: {timeout}秒")
        
        while time.time() - start_time < timeout:
            remaining_time = int(timeout - (time.time() - start_time))
            if remaining_time <= 0:
                break
                
            updates = self.get_updates(timeout=min(10, remaining_time))
            
            for update in updates:
                message = update.get('message', {})
                if not message:
                    continue
                
                # 只处理来自配置的聊天ID的消息
                if str(message.get('chat', {}).get('id', '')) != str(self.chat_id):
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
                     case_sensitive: bool = False) -> Optional[Dict]:
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
    
    def wait_for_command(self, command: str, timeout: int = 60) -> Optional[Dict]:
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
    
    def is_available(self) -> bool:
        """检查Telegram是否可用"""
        return self.enabled

# 全局实例
_telegram_instance: Optional[TelegramNotifier] = None

def get_telegram_instance(config: Dict = None) -> Optional[TelegramNotifier]:
    """
    获取Telegram单例
    :param config: 配置字典，首次调用时需要
    :return: TelegramNotifier实例
    """
    global _telegram_instance
    if _telegram_instance is None and config is not None:
        # 构建Telegram配置
        telegram_config = {}
        
        # 从全局配置加载
        global_config = config.get('global', {})
        if global_config.get('telegram_notify', False):
            telegram_config = {
                'enabled': True,
                'bot_token': global_config.get('telegram_token', ''),
                'chat_id': global_config.get('telegram_chat_id', ''),
                'proxy': config.get('telegram_proxy', {})
            }
        
        # 从新的配置格式加载
        telegram_bots_config = config.get('telegram_bots', {}).get('main', {})
        if telegram_bots_config.get('enabled', False):
            telegram_config = {
                'enabled': telegram_bots_config.get('enabled', False),
                'bot_token': telegram_bots_config.get('token', ''),
                'chat_id': telegram_bots_config.get('chat_id', ''),
                'proxy': config.get('telegram_proxy', {})
            }
        
        _telegram_instance = TelegramNotifier(telegram_config)
    
    return _telegram_instance

if __name__ == '__main__':
    test_notifier()