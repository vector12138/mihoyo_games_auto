"""
工具模块包
包含各种工具和辅助功能
"""

from .telegram_client import TelegramClient
from .util import get_prj_root


__all__ = [
    'TelegramClient',
    'get_prj_root',
    # 兼容旧导出
    'TelegramNotifier'
]

# 兼容旧导入
TelegramNotifier = TelegramClient