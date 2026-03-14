#!/usr/bin/env python3
"""
Telegram通知模块
发送任务状态通知到Telegram
"""

import requests
import yaml
from pathlib import Path
from datetime import datetime
from loguru import logger

class TelegramNotifier:
    """Telegram通知器"""
    
    def __init__(self, config=None):
        """初始化通知器"""
        self.config = config or {}
        self.bot_token = self.config.get('bot_token', '')
        self.chat_id = self.config.get('chat_id', '')
        self.enabled = self.config.get('enabled', False) and self.bot_token and self.chat_id
        
        if self.enabled:
            logger.info(f"Telegram通知已启用，Chat ID: {self.chat_id}")
        else:
            logger.warning("Telegram通知未启用，请检查配置")
    
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
            
            response = requests.post(url, json=payload, timeout=10)
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
                
                response = requests.post(url, files=files, data=data, timeout=30)
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
    print("测试Telegram通知功能...")
    
    config = load_config()
    if not config:
        print("❌ 无法加载配置")
        return False
    
    telegram_config = config.get('telegram', {})
    notifier = TelegramNotifier(telegram_config)
    
    if not notifier.enabled:
        print("❌ Telegram通知未启用，请检查配置")
        return False
    
    # 测试消息
    print("发送测试消息...")
    success = notifier.send_message("🔧 *测试消息*\n\n这是米哈游游戏自动化的测试通知。\n*时间*: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    if success:
        print("✅ 测试消息发送成功")
    else:
        print("❌ 测试消息发送失败")
    
    return success

if __name__ == '__main__':
    test_notifier()