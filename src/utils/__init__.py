"""
工具模块包
包含各种工具和辅助功能
"""

__all__ = [
    'get_prj_root',
    'TelegramBridgeApiClient',
    'get_telegram_bridge_client',
    'mute_system_volume',
    'unmute_system_volume'
]

def __getattr__(name):
    if name == 'get_prj_root':
        from .util import get_prj_root
        return get_prj_root
    elif name == 'TelegramBridgeApiClient':
        from .telegram_bridge_api_client import TelegramBridgeApiClient
        return TelegramBridgeApiClient
    elif name == 'get_telegram_bridge_client':
        from .telegram_bridge_api_client import get_telegram_bridge_client
        return get_telegram_bridge_client
    elif name == 'mute_system_volume':
        from .volume import mute_system_volume
        return mute_system_volume
    elif name == 'unmute_system_volume':
        from .volume import unmute_system_volume
        return unmute_system_volume
    raise AttributeError(f"module {__name__} has no attribute {name}")