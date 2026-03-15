"""
核心模块包
包含游戏自动化所需的所有核心组件
"""

from .game_base import GameBase, MultiAppBase
from .screen_capture import ScreenCapture
from .ocr_recognizer import OCRRecognizer
from .input_controller import InputController
from .retry_manager import RetryManager
from .shutdown import shutdown

__all__ = [
    'GameBase',
    'MultiAppBase',
    'ScreenCapture',
    'OCRRecognizer',
    'InputController',
    'RetryManager',
    'shutdown'
]