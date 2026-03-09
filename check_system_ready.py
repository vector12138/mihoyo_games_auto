#!/usr/bin/env python3
"""
系统就绪检查脚本
检查电脑是否已启动完成并可以执行自动化任务
"""

import time
import socket
import subprocess
import platform
import json
import sys
from pathlib import Path

def ping_host(ip_address, timeout=2):
    """
    Ping指定IP地址
    :param ip_address: IP地址
    :param timeout: 超时时间（秒）
    :return: 是否可达
    """
    try:
        # 根据操作系统选择ping命令
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        
        # 执行ping命令
        result = subprocess.run(
            ['ping', param, '1', '-w', str(timeout * 1000), ip_address],
            capture_output=True,
            text=True
        )
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"⚠️  Ping检查异常: {e}")
        return False

def check_port_open(ip_address, port, timeout=2):
    """
    检查端口是否开放
    :param ip_address: IP地址
    :param port: 端口号
    :param timeout: 超时时间（秒）
    :return: 端口是否开放
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip_address, port))
        sock.close()
        
        return result == 0
        
    except Exception as e:
        print(f"⚠️  端口检查异常: {e}")
        return False

def check_windows_services():
    """
    检查Windows关键服务是否运行
    :return: 服务状态
    """
    if platform.system().lower() != 'windows':
        return True  # 非Windows系统跳过
    
    try:
        # 检查关键服务
        critical_services = ['Winmgmt', 'EventLog', 'Dhcp', 'Netlogon']
        
        for service in critical_services:
            result = subprocess.run(
                ['sc', 'query', service],
                capture_output=True,
                text=True
            )
            
            if 'RUNNING' not in result.stdout:
                print(f"⚠️  服务 {service} 未运行")
                return False
        
        return True
        
    except Exception as e:
        print(f"⚠️  服务检查异常: {e}")
        return True  # 检查失败时继续

def check_disk_space(min_gb=5):
    """
    检查磁盘空间
    :param min_gb: 最小所需空间（GB）
    :return: 是否有足够空间
    """
    try:
        import shutil
        
        # 检查C盘空间
        total, used, free = shutil.disk_usage("C:\\" if platform.system().lower() == 'windows' else "/")
        free_gb = free / (1024**3)
        
        if free_gb < min_gb:
            print(f"⚠️  磁盘空间不足: {free_gb:.1f}GB < {min_gb}GB")
            return False
        
        print(f"💾 磁盘空间充足: {free_gb:.1f}GB")
        return True
        
    except Exception as e:
        print(f"⚠️  磁盘空间检查异常: {e}")
        return True  # 检查失败时继续

def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent / 'config.json'
    if not config_path.exists():
        config_path = Path(__file__).parent / 'config.example.json'
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return None

def wait_for_system_ready(config, max_wait_minutes=10):
    """
    等待系统就绪
    :param config: 配置字典
    :param max_wait_minutes: 最大等待时间（分钟）
    :return: 系统是否就绪
    """
    wol_config = config.get('wol', {})
    ip_address = wol_config.get('ip_address')
    
    if not ip_address:
        print("❌ 配置文件中缺少IP地址")
        return False
    
    max_wait_seconds = max_wait_minutes * 60
    check_interval = 10  # 检查间隔（秒）
    start_time = time.time()
    
    print("🔍 等待系统就绪...")
    print(f"   IP地址: {ip_address}")
    print(f"   最大等待时间: {max_wait_minutes}分钟")
    
    checks_passed = {
        'ping': False,
        'rdp_port': False,  # Windows远程桌面端口
        'services': False,
        'disk_space': False
    }
    
    while time.time() - start_time < max_wait_seconds:
        elapsed = int(time.time() - start_time)
        print(f"\n⏰ 已等待: {elapsed}秒")
        
        # 检查Ping
        if not checks_passed['ping']:
            if ping_host(ip_address):
                checks_passed['ping'] = True
                print("✅ 网络连接正常")
            else:
                print("❌ 网络不可达，继续等待...")
        
        # 检查RDP端口（3389） - 表示Windows已启动
        if checks_passed['ping'] and not checks_passed['rdp_port']:
            if check_port_open(ip_address, 3389):
                checks_passed['rdp_port'] = True
                print("✅ Windows系统已启动")
            else:
                print("⏳ Windows启动中...")
        
        # 检查服务
        if checks_passed['rdp_port'] and not checks_passed['services']:
            if check_windows_services():
                checks_passed['services'] = True
                print("✅ 关键服务运行正常")
        
        # 检查磁盘空间
        if not checks_passed['disk_space']:
            if check_disk_space():
                checks_passed['disk_space'] = True
                print("✅ 磁盘空间充足")
        
        # 检查是否所有条件都满足
        if all(checks_passed.values()):
            print("\n🎉 系统就绪检查完成！")
            print("💻 电脑已完全启动，可以执行自动化任务")
            return True
        
        # 等待下一次检查
        print(f"⏳ 等待 {check_interval} 秒后再次检查...")
        time.sleep(check_interval)
    
    print(f"\n❌ 系统就绪检查超时（{max_wait_minutes}分钟）")
    print("未通过的检查:")
    for check_name, passed in checks_passed.items():
        if not passed:
            print(f"  - {check_name}")
    
    return False

def main():
    """主函数"""
    print("=" * 50)
    print("米哈游游戏自动化 - 系统就绪检查")
    print("=" * 50)
    
    # 加载配置
    config = load_config()
    if not config:
        print("❌ 无法加载配置，请检查配置文件")
        return False
    
    # 等待系统就绪
    max_wait = config.get('timing', {}).get('wake_wait_seconds', 60) // 60 + 1
    ready = wait_for_system_ready(config, max_wait_minutes=max_wait)
    
    if ready:
        print("\n✅ 系统已就绪，可以开始自动化任务")
        return True
    else:
        print("\n❌ 系统未就绪，自动化任务无法继续")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)