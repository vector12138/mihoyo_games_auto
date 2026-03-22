"""
核心模块包
包含游戏自动化所需的所有核心组件
"""

__all__ = [
    'MultiAppBase',
    'ScreenCapture',
    'OCRRecognizer',
    'InputController',
    'RetryManager',
    'shutdown'
]

def __getattr__(name):
    if name == 'MultiAppBase':
        from .game_base import MultiAppBase
        return MultiAppBase
    elif name == 'ScreenCapture':
        from .screen_capture import ScreenCapture
        return ScreenCapture
    elif name == 'OCRRecognizer':
        from .ocr_recognizer import OCRRecognizer
        return OCRRecognizer
    elif name == 'InputController':
        from .input_controller import InputController
        return InputController
    elif name == 'RetryManager':
        from .retry_manager import RetryManager
        return RetryManager
    elif name == 'shutdown':
        from .shutdown import shutdown
        return shutdown
    raise AttributeError(f"module {__name__} has no attribute {name}")