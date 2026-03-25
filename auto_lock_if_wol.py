import win32evtlog
import datetime
import ctypes
import subprocess
import sys
import re

def is_wol_boot():
    """精准判断是否为WOL远程开机场景"""
    now = datetime.datetime.now().astimezone()
    three_minute_ago = now - datetime.timedelta(minutes=3)
    
    # 1. 首先判断是不是3分钟内刚冷启动
    hand = win32evtlog.OpenEventLog('localhost', 'System')
    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
    is_recent_boot = False
    
    events = win32evtlog.ReadEventLog(hand, flags, 0)
    for event in events:
        # 系统冷启动事件ID 12
        if event.SourceName == 'Microsoft-Windows-Kernel-General' and event.EventID == 12:
            event_time = event.TimeGenerated.astimezone()
            if event_time >= three_minute_ago:
                is_recent_boot = True
                break
    if not is_recent_boot:
        return False
    
    # 2. 检查最后一次唤醒源是不是网卡（WOL唤醒）
    try:
        result = subprocess.run(
            ['powercfg', '/lastwake'],
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout.lower()
        # 匹配网卡关键词，包含PCI\VEN_或者Ethernet、Network Controller、Wake on LAN等特征
        wol_patterns = [
            r'pci\\ven_',  # 网卡设备PCI路径
            r'ethernet',
            r'network controller',
            r'wake on lan',
            r'lan connection',
            r'nic '
        ]
        for pattern in wol_patterns:
            if re.search(pattern, output):
                return True
        return False
    except:
        return False

if __name__ == "__main__":
    if is_wol_boot():
        print("检测到WOL远程开机，自动锁屏")
        ctypes.windll.user32.LockWorkStation()
    else:
        print("非WOL开机场景，不锁屏")
        sys.exit(0)
