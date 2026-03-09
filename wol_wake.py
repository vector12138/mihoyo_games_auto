#!/usr/bin/env python3
"""
WOL (Wake-on-LAN) 唤醒脚本
发送魔术包唤醒远程电脑
"""

import socket
import struct
import json
import sys
import os
from pathlib import Path

def create_magic_packet(mac_address):
    """
    创建WOL魔术包
    :param mac_address: MAC地址，格式为 "XX:XX:XX:XX:XX:XX"
    :return: 魔术包字节数据
    """
    # 移除分隔符
    mac_clean = mac_address.replace(':', '').replace('-', '').replace('.', '')
    
    if len(mac_clean) != 12:
        raise ValueError(f"无效的MAC地址: {mac_address}")
    
    # 转换为字节
    mac_bytes = bytes.fromhex(mac_clean)
    
    # 魔术包格式：6个0xFF + 16次重复MAC地址
    magic_packet = b'\xff' * 6 + mac_bytes * 16
    
    return magic_packet

def send_wol(mac_address, broadcast_address='255.255.255.255', port=9):
    """
    发送WOL魔术包
    :param mac_address: MAC地址
    :param broadcast_address: 广播地址
    :param port: 端口，默认为9
    :return: 是否成功发送
    """
    try:
        # 创建UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # 创建魔术包
        magic_packet = create_magic_packet(mac_address)
        
        # 发送到广播地址
        sock.sendto(magic_packet, (broadcast_address, port))
        sock.close()
        
        print(f"✅ 已发送WOL魔术包到 {broadcast_address}:{port}")
        print(f"   MAC地址: {mac_address}")
        return True
        
    except Exception as e:
        print(f"❌ 发送WOL失败: {e}")
        return False

def load_config():
    """加载配置文件"""
    config_path = Path(__file__).parent / 'config.json'
    if not config_path.exists():
        # 使用示例配置
        config_path = Path(__file__).parent / 'config.example.json'
        print(f"⚠️  配置文件不存在，使用示例配置: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return None

def main():
    """主函数"""
    print("=" * 50)
    print("米哈游游戏自动化 - WOL唤醒工具")
    print("=" * 50)
    
    # 加载配置
    config = load_config()
    if not config:
        print("❌ 无法加载配置，请检查配置文件")
        return False
    
    wol_config = config.get('wol', {})
    
    # 获取参数
    mac_address = wol_config.get('mac_address')
    broadcast_address = wol_config.get('broadcast_address', '255.255.255.255')
    port = wol_config.get('port', 9)
    
    if not mac_address or mac_address == 'XX:XX:XX:XX:XX:XX':
        print("❌ 请先在 config.json 中配置正确的MAC地址")
        print("   格式: XX:XX:XX:XX:XX:XX")
        return False
    
    # 发送WOL
    print(f"🔌 尝试唤醒电脑...")
    print(f"   MAC地址: {mac_address}")
    print(f"   广播地址: {broadcast_address}")
    print(f"   端口: {port}")
    
    success = send_wol(mac_address, broadcast_address, port)
    
    if success:
        print(f"\n✅ WOL唤醒请求已发送")
        print(f"💤 电脑正在启动，请等待...")
        
        # 显示预计等待时间
        wake_wait = config.get('timing', {}).get('wake_wait_seconds', 60)
        print(f"⏰ 预计等待时间: {wake_wait}秒")
        
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)