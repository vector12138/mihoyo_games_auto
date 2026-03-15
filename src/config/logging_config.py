#!/usr/bin/env python3
"""
日志配置模块
统一配置所有模块的日志输出
"""

import sys
from loguru import logger

def setup_logging(log_level="INFO", log_file="logs/automation.log"):
    """
    配置日志系统
    :param log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
    :param log_file: 日志文件路径
    """
    # 移除默认的日志处理器
    logger.remove()
    
    # 控制台输出配置
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # 文件输出配置
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",  # 日志文件大小达到10MB时轮转
        retention="7 days",  # 保留7天的日志
        compression="zip"  # 压缩旧日志
    )
    
    # 错误日志单独输出
    error_log_file = log_file.replace(".log", "_error.log")
    logger.add(
        error_log_file,
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",  # 错误日志保留30天
        compression="zip"
    )
    
    logger.info(f"日志系统已配置，级别: {log_level}，文件: {log_file}")

def get_logger(name=None):
    """
    获取日志记录器
    :param name: 模块名称
    :return: logger实例
    """
    return logger.bind(name=name) if name else logger

# 默认配置
if __name__ == "__main__":
    setup_logging()
    logger.info("日志配置模块测试")
    logger.debug("调试信息")
    logger.warning("警告信息")
    logger.error("错误信息")