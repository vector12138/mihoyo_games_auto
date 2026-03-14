#!/usr/bin/env python3
"""
关机模块 - Windows专用
提供安全关机功能，支持延迟关机和强制关机
注意：本项目仅支持Windows系统
"""

import os
import sys
import time
import yaml
import subprocess
import platform
from pathlib import Path
from loguru import logger

def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent / 'config.yaml'
    if not config_path.exists():
        config_path = Path(__file__).parent / 'config.example.yaml'
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return None

def check_running_processes():
    """
    检查是否有重要进程在运行（Windows专用）
    返回需要关闭的进程列表
    """
    system = platform.system().lower()
    
    if system != 'windows':
        logger.error(f"不支持的操作系统: {system}，本项目仅支持Windows")
        return []
    
    # 需要检查的进程（游戏相关）
    game_processes = [
        'YuanShen.exe',      # 原神
        'GenshinImpact.exe', # 原神（可能的不同名称）
        'ZenlessZoneZero.exe', # 绝区零
        'bettergi.exe',      # BetterGI
        'AutoHotkey.exe',    # AutoHotkey
    ]
    
    running_processes = []
    
    try:
        # Windows: 使用tasklist命令
        result = subprocess.run(
            ['tasklist', '/FO', 'CSV'],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        for line in result.stdout.split('\n'):
            if ',' in line:
                parts = line.strip('"').split('","')
                if len(parts) >= 1:
                    process_name = parts[0].strip('"')
                    if process_name in game_processes:
                        pid = parts[1].strip('"') if len(parts) > 1 else 'N/A'
                        running_processes.append((process_name, pid))
    
    except Exception as e:
        logger.warning(f"检查进程异常: {e}")
    
    return running_processes

def kill_processes(processes):
    """
    结束指定进程（Windows专用）
    :param processes: 进程列表，每个元素为(进程名, PID)
    :return: 是否成功结束所有进程
    """
    if not processes:
        logger.info("没有需要结束的进程")
        return True
    
    system = platform.system().lower()
    
    if system != 'windows':
        logger.error(f"不支持的操作系统: {system}，无法结束进程")
        return False
    
    all_success = True
    
    for process_name, pid in processes:
        logger.info(f"结束进程: {process_name} (PID: {pid})")
        
        try:
            if pid != 'N/A':
                # 使用taskkill结束进程
                subprocess.run(['taskkill', '/PID', pid, '/F'], check=True)
            else:
                # 使用进程名结束
                subprocess.run(['taskkill', '/IM', process_name, '/F'], check=True)
            
            logger.info(f"进程已结束: {process_name}")
            time.sleep(1)  # 短暂等待
            
        except subprocess.CalledProcessError:
            logger.warning(f"无法结束进程: {process_name}，可能已退出")
        except Exception as e:
            logger.error(f"结束进程异常: {process_name} - {e}")
            all_success = False
    
    return all_success

def graceful_shutdown(config, force=False):
    """
    优雅关机（Windows专用）
    :param config: 配置字典
    :param force: 是否强制关机
    :return: 是否成功
    """
    shutdown_config = config.get('shutdown', {})
    force = force or shutdown_config.get('force_shutdown', False)
    
    logger.info("准备关机...")
    
    # 检查操作系统
    system = platform.system().lower()
    if system != 'windows':
        logger.error(f"不支持的操作系统: {system}，本项目仅支持Windows")
        return False
    
    # 1. 检查并结束游戏进程
    logger.info("检查运行中的进程...")
    running_processes = check_running_processes()
    
    if running_processes:
        logger.info(f"发现 {len(running_processes)} 个运行中的进程")
        for proc, pid in running_processes:
            logger.info(f"  - {proc} (PID: {pid})")
        
        # 结束进程
        logger.info("结束进程...")
        if not kill_processes(running_processes):
            if not force:
                logger.error("无法结束所有进程，取消关机")
                return False
            else:
                logger.warning("强制关机，忽略进程结束失败")
    
    # 2. 执行关机命令
    logger.info("执行关机...")
    
    try:
        # Windows关机命令
        # /s: 关机
        # /f: 强制关闭应用程序
        # /t 0: 立即执行
        force_flag = '/f' if force else ''
        command = f'shutdown /s {force_flag} /t 0'
        
        logger.info(f"执行命令: {command}")
        subprocess.run(command, shell=True, check=True)
        
        logger.info("关机命令已执行")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"关机命令执行失败: {e}")
        return False
    except Exception as e:
        logger.error(f"关机异常: {e}")
        return False

def shutdown(delay: int = 60, force: bool = False):
    """
    执行关机操作（Windows专用）
    :param delay: 延迟时间（秒）
    :param force: 是否强制关机
    :return: 是否成功
    """
    logger.info(f"准备关机，延迟 {delay} 秒，强制模式: {force}")
    
    # 检查操作系统
    system = platform.system().lower()
    if system != 'windows':
        logger.error(f"不支持的操作系统: {system}，本项目仅支持Windows")
        return False
    
    # 加载配置
    config = load_config()
    if not config:
        logger.error("无法加载配置，关机失败")
        return False
    
    # 如果有延迟，等待
    if delay > 0:
        logger.info(f"等待 {delay} 秒后关机...")
        time.sleep(delay)
    
    # 执行关机
    success = graceful_shutdown(config, force)
    
    if success:
        logger.info("关机命令已执行")
    else:
        logger.error("关机失败")
    
    return success

def main():
    """命令行主函数"""
    logger.info("=" * 50)
    logger.info("米哈游游戏自动化 - 关机脚本 (Windows专用)")
    logger.info("=" * 50)
    
    # 检查操作系统
    system = platform.system().lower()
    if system != 'windows':
        logger.error(f"错误：不支持的操作系统: {system}")
        logger.error("本项目仅支持Windows系统")
        return False
    
    # 加载配置
    config = load_config()
    if not config:
        logger.error("无法加载配置，请检查配置文件")
        return False
    
    # 确认关机
    logger.warning("警告：此操作将关闭电脑")
    logger.info("请确保所有重要工作已保存")
    
    # 检查是否有其他参数（如--force）
    force_shutdown = '--force' in sys.argv or '-f' in sys.argv
    
    if not force_shutdown:
        user_input = input("\n确认关机？(y/N): ")
        if user_input.lower() != 'y':
            logger.info("用户取消关机")
            return False
    
    # 执行关机
    success = graceful_shutdown(config, force_shutdown)
    
    if success:
        logger.info("电脑将在短时间内关闭")
        logger.info("再见！")
    else:
        logger.error("关机失败，请手动检查")
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)