"""
配置模块包
包含配置管理相关功能
"""
from __future__ import annotations
from typing import TYPE_CHECKING

# 类型检查阶段(IDE跳转、mypy检查)直接导入所有符号，支持跳转和类型提示
if TYPE_CHECKING:
    from .config import (
        Config
    )
    from .logging_config import (
        setup_logging
    )

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