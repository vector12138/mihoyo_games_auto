#!/usr/bin/env python3
"""
重试管理器
实现错误重试机制，支持指数退避
"""

import time
from functools import wraps
from typing import Callable, Any, Optional
from loguru import logger

class RetryManager:
    """重试管理器"""
    
    def __init__(self, config=None):
        """初始化重试管理器"""
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        self.max_retries = self.config.get('max_retries', 3)
        self.retry_delay = self.config.get('retry_delay', 10)
        self.backoff_factor = self.config.get('backoff_factor', 2)
        self.max_delay_seconds = self.config.get('max_delay_seconds', 300)
        
        # 重试条件配置
        self.retry_on_timeout = self.config.get('retry_on_timeout', True)
        self.retry_on_image_not_found = self.config.get('retry_on_image_not_found', True)
        self.retry_on_network_error = self.config.get('retry_on_network_error', True)
        self.retry_on_game_error = self.config.get('retry_on_game_error', True)
        
        if self.enabled:
            logger.info(f"重试机制已启用，最大尝试次数: {self.max_retries}")
        else:
            logger.info("重试机制未启用")
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        判断是否应该重试
        :param error: 异常对象
        :param attempt: 当前尝试次数
        :return: 是否应该重试
        """
        if not self.enabled:
            return False
        
        if attempt >= self.max_retries:
            logger.debug(f"达到最大尝试次数: {attempt}/{self.max_retries}")
            return False
        
        error_str = str(error).lower()
        
        # 根据错误类型决定是否重试
        if self.retry_on_timeout and any(keyword in error_str for keyword in ['timeout', 'timed out', '超时']):
            return True
        
        if self.retry_on_image_not_found and any(keyword in error_str for keyword in ['image not found', 'template not found', '未找到图像']):
            return True
        
        if self.retry_on_network_error and any(keyword in error_str for keyword in ['network', 'connection', 'socket', '网络', '连接']):
            return True
        
        if self.retry_on_game_error and any(keyword in error_str for keyword in ['game', '游戏', 'launch', '启动']):
            return True
        
        # 默认重试所有异常
        return True
    
    def calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟时间（指数退避）
        :param attempt: 当前尝试次数（从1开始）
        :return: 延迟时间（秒）
        """
        if attempt <= 1:
            return self.retry_delay
        
        delay = self.retry_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay_seconds)
    
    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        执行带重试的函数
        :param func: 要执行的函数
        :param args: 函数参数
        :param kwargs: 函数关键字参数
        :return: 函数返回值
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"尝试执行函数: {func.__name__}, 尝试次数: {attempt}/{self.max_retries}")
                return func(*args, **kwargs)
                
            except Exception as e:
                last_error = e
                logger.warning(f"函数执行失败: {func.__name__}, 尝试次数: {attempt}, 错误: {e}")
                
                # 检查是否应该重试
                if not self.should_retry(e, attempt):
                    logger.error(f"不再重试: {func.__name__}")
                    raise
                
                # 计算并等待延迟
                if attempt < self.max_retries:
                    delay = self.calculate_delay(attempt)
                    logger.info(f"等待 {delay:.1f} 秒后重试 ({attempt}/{self.max_retries})...")
                    time.sleep(delay)
        
        # 所有尝试都失败
        logger.error(f"函数执行完全失败: {func.__name__}, 尝试次数: {self.max_retries}")
        raise last_error
    
    def retry_decorator(self, max_retries: Optional[int] = None, 
                       retry_delay: Optional[float] = None):
        """
        创建重试装饰器
        :param max_retries: 最大尝试次数（覆盖配置）
        :param retry_delay: 初始延迟时间（覆盖配置）
        :return: 装饰器函数
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 创建临时配置
                temp_config = self.config.copy()
                if max_retries is not None:
                    temp_config['max_retries'] = max_retries
                if retry_delay is not None:
                    temp_config['retry_delay'] = retry_delay
                
                # 创建临时重试管理器
                temp_retry = RetryManager(temp_config)
                return temp_retry.retry(func, *args, **kwargs)
            return wrapper
        return decorator

# 预定义的重试策略
RETRY_STRATEGIES = {
    'aggressive': {
        'max_retries': 5,
        'retry_delay': 5,
        'backoff_factor': 1.5,
        'max_delay_seconds': 60
    },
    'conservative': {
        'max_retries': 3,
        'retry_delay': 30,
        'backoff_factor': 2,
        'max_delay_seconds': 300
    },
    'quick': {
        'max_retries': 2,
        'retry_delay': 2,
        'backoff_factor': 1,
        'max_delay_seconds': 10
    }
}

def with_retry(config=None, strategy=None):
    """
    创建带重试的装饰器（简化版）
    :param config: 重试配置
    :param strategy: 预定义策略名称
    :return: 装饰器
    """
    if strategy and strategy in RETRY_STRATEGIES:
        config = RETRY_STRATEGIES[strategy]
    
    retry_manager = RetryManager(config)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_manager.retry(func, *args, **kwargs)
        return wrapper
    return decorator

def test_retry_function():
    """测试重试功能"""
    import random
    
    @with_retry(strategy='aggressive')
    def unreliable_function(success_rate=0.3):
        """不可靠的函数，有一定概率失败"""
        if random.random() < success_rate:
            return "成功！"
        else:
            raise Exception("随机失败")
    
    print("测试重试机制...")
    print("函数成功率为30%，使用积极重试策略（最多5次）")
    
    try:
        result = unreliable_function(success_rate=0.3)
        print(f"✅ 最终结果: {result}")
        return True
    except Exception as e:
        print(f"❌ 最终失败: {e}")
        return False

if __name__ == '__main__':
    test_retry_function()