"""
配置模块包
包含配置管理相关功能
"""

__all__ = [
    'Config',
    'setup_logging'
]

def __getattr__(name):
    if name == 'Config':
        from .config import Config
        return Config
    elif name == 'setup_logging':
        from .logging_config import setup_logging
        return setup_logging
    raise AttributeError(f"module {__name__} has no attribute {name}")