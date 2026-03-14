#!/usr/bin/env python3
"""
关机脚本
安全关闭电脑
"""

import os
import sys
import time
import yaml
import subprocess
import platform
from pathlib import Path

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

def check_running_processes():
    """
    检查是否有重要进程在运行
    返回需要关闭的进程列表
    """
    system = platform.system().lower()
    
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
        if system == 'windows':
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
        
        elif system in ['linux', 'darwin']:  # Linux或macOS
            # 使用ps命令
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.split('\n'):
                for process in game_processes:
                    if process in line:
                        running_processes.append((process, 'N/A'))
                        break
    
    except Exception as e:
        print(f"⚠️  检查进程异常: {e}")
    
    return running_processes

def kill_processes(processes):
    """
    结束指定进程
    :param processes: 进程列表，每个元素为(进程名, PID)
    :return: 是否成功结束所有进程
    """
    if not processes:
        print("✅ 没有需要结束的进程")
        return True
    
    system = platform.system().lower()
    all_success = True
    
    for process_name, pid in processes:
        print(f"🛑 结束进程: {process_name} (PID: {pid})")
        
        try:
            if system == 'windows':
                if pid != 'N/A':
                    # 使用taskkill结束进程
                    subprocess.run(['taskkill', '/PID', pid, '/F'], check=True)
                else:
                    # 使用进程名结束
                    subprocess.run(['taskkill', '/IM', process_name, '/F'], check=True)
            
            elif system in ['linux', 'darwin']:
                # 使用pkill结束进程
                subprocess.run(['pkill', '-f', process_name], check=True)
            
            print(f"✅ 进程已结束: {process_name}")
            time.sleep(1)  # 短暂等待
            
        except subprocess.CalledProcessError:
            print(f"⚠️  无法结束进程: {process_name}，可能已退出")
        except Exception as e:
            print(f"❌ 结束进程异常: {process_name} - {e}")
            all_success = False
    
    return all_success

def graceful_shutdown(config):
    """
    优雅关机
    :param config: 配置字典
    :return: 是否成功
    """
    shutdown_config = config.get('shutdown', {})
    force = shutdown_config.get('force_shutdown', False)
    timeout = shutdown_config.get('timeout_seconds', 60)
    
    print("🔌 准备关机...")
    
    # 1. 检查并结束游戏进程
    print("\n1. 检查运行中的进程...")
    running_processes = check_running_processes()
    
    if running_processes:
        print(f"发现 {len(running_processes)} 个运行中的进程:")
        for proc, pid in running_processes:
            print(f"  - {proc} (PID: {pid})")
        
        if not force:
            print("\n⚠️  有关闭中的进程，建议先手动保存")
            user_input = input("是否继续关机？(y/N): ")
            if user_input.lower() != 'y':
                print("❌ 用户取消关机")
                return False
        
        # 结束进程
        print("\n2. 结束进程...")
        if not kill_processes(running_processes):
            if not force:
                print("❌ 无法结束所有进程，取消关机")
                return False
            else:
                print("⚠️  强制关机，忽略进程结束失败")
    
    # 2. 执行关机命令
    print("\n3. 执行关机...")
    system = platform.system().lower()
    
    try:
        if system == 'windows':
            # Windows关机命令
            # /s: 关机
            # /f: 强制关闭应用程序
            # /t 0: 立即执行
            force_flag = '/f' if force else ''
            command = f'shutdown /s {force_flag} /t 0'
            
        elif system == 'linux':
            # Linux关机命令
            force_flag = '-f' if force else ''
            command = f'shutdown -h now {force_flag}'
            
        elif system == 'darwin':
            # macOS关机命令
            command = 'sudo shutdown -h now'
        
        else:
            print(f"❌ 不支持的操作系统: {system}")
            return False
        
        print(f"执行命令: {command}")
        
        if system == 'darwin':
            # macOS需要sudo权限
            print("⚠️  macOS关机需要sudo权限，请输入密码:")
        
        subprocess.run(command, shell=True, check=True)
        
        print("✅ 关机命令已执行")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 关机命令执行失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 关机异常: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("米哈游游戏自动化 - 关机脚本")
    print("=" * 50)
    
    # 加载配置
    config = load_config()
    if not config:
        print("❌ 无法加载配置，请检查配置文件")
        return False
    
    # 确认关机
    print("\n⚠️  警告：此操作将关闭电脑")
    print("请确保所有重要工作已保存")
    
    # 检查是否有其他参数（如--force）
    force_shutdown = '--force' in sys.argv or '-f' in sys.argv
    
    if not force_shutdown:
        user_input = input("\n确认关机？(y/N): ")
        if user_input.lower() != 'y':
            print("❌ 用户取消关机")
            return False
    
    # 执行关机
    success = graceful_shutdown(config)
    
    if success:
        print("\n✅ 电脑将在短时间内关闭")
        print("💤 再见！")
    else:
        print("\n❌ 关机失败，请手动检查")
    
    return success

class ShutdownManager:
    """关机管理器类"""
    
    @staticmethod
    def shutdown(delay: int = 60, force: bool = False):
        """
        执行关机操作
        :param delay: 延迟时间（秒）
        :param force: 是否强制关机
        :return: 是否成功
        """
        print(f"[ShutdownManager] 准备关机，延迟 {delay} 秒，强制模式: {force}")
        
        # 加载配置
        config = load_config()
        if not config:
            print("[ShutdownManager] 错误: 无法加载配置，关机失败")
            return False
        
        # 如果有延迟，等待
        if delay > 0:
            print(f"[ShutdownManager] 等待 {delay} 秒后关机...")
            time.sleep(delay)
        
        # 设置强制关机标志
        if force:
            config['shutdown'] = config.get('shutdown', {})
            config['shutdown']['force_shutdown'] = True
        
        # 执行关机
        success = graceful_shutdown(config)
        
        if success:
            print("[ShutdownManager] 关机命令已执行")
        else:
            print("[ShutdownManager] 关机失败")
        
        return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)