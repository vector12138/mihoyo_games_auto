import os
import ctypes
import sys
import platform
import datetime
import win32evtlog
import subprocess
from loguru import logger
from typing import Optional
from pycaw.pycaw import AudioUtilities

# 全局变量
_original_volume = 0

def mute_system_volume() -> bool:
    """静音系统音量"""
    global _original_volume
    
    try:
        # 获取扬声器的音量控制接口
        devices = AudioUtilities.GetSpeakers()
        volume = devices.EndpointVolume
        
        # 保存当前音量（范围 0.0-1.0）
        current_vol = volume.GetMasterVolumeLevelScalar()
        _original_volume = int(current_vol * 100)
        
        # 静音
        volume.SetMute(True, None)
        
        logger.info(f"系统已静音，原始音量: {_original_volume}%")
        return True
        
    except Exception as e:
        logger.error(f"静音失败: {e}")
        return False

def unmute_system_volume() -> bool:
    """恢复音量"""
    global _original_volume
    
    if _original_volume == 0:
        return False
    
    try:
        devices = AudioUtilities.GetSpeakers()
        volume = devices.EndpointVolume
        
        # 取消静音
        volume.SetMute(False, None)
        
        # 恢复原始音量
        volume.SetMasterVolumeLevelScalar(_original_volume / 100.0, None)
        
        logger.info(f"系统已恢复音量: {_original_volume}%")
        return True
        
    except Exception as e:
        logger.error(f"恢复音量失败: {e}")
        return False

def get_prj_root()->str:
    """获取项目根目录（适配任意脚本位置）"""
    # 当前脚本的绝对路径
    current_path = os.path.abspath(__file__)
    # 向上递归，直到找到包含 main.py 的目录（根目录标志）
    while True:
        # 检查当前目录是否包含根目录的标志性文件（按需修改，如 requirements.txt）
        if os.path.exists(os.path.join(current_path, "main.py")):
            return current_path
        # 向上找父目录，直到根目录
        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:  # 到达系统根目录（如 D:\）仍未找到
            raise FileNotFoundError("未找到项目根目录（未发现 main.py）")
        current_path = parent_path

def is_running_as_admin() -> bool:
    """
    检测当前脚本是否以管理员权限运行（仅Windows平台）
    :return: True 是管理员，False 不是
    """
    try:
        # 调用Windows API检查管理员权限
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        # 非Windows平台或其他错误，默认返回False
        return False

def run_as_admin(args: Optional[list] = None) -> bool:
    """
    以管理员权限重新启动当前脚本（仅Windows平台）
    :param args: 启动参数，不传则使用当前脚本的参数
    :return: 成功发起重新启动返回True，失败返回False
    """
    if is_running_as_admin():
        return True
    
    if args is None:
        args = sys.argv
    
    try:
        # 以管理员权限重新启动脚本
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join(f'"{arg}"' for arg in args),
            None,
            1  # 显示窗口
        )
        sys.exit(0)
    except Exception as e:
        print(f"请求管理员权限失败: {str(e)}")
        return False
    

def is_remote_wake_boot() -> bool:
    """判断是否为远程唤醒/自动开机场景（WOL冷启动/睡眠远程唤醒）"""
    now = datetime.datetime.now().astimezone()
    # 检查过去30分钟内的启动/唤醒事件，时间窗口更宽松避免漏判
    thirty_minutes_ago = now - datetime.timedelta(minutes=30)
    logger.debug(f"检查WOL唤醒事件，时间范围：{thirty_minutes_ago} 到 {now}")

    try:
        # 先读取系统事件日志
        hand = win32evtlog.OpenEventLog('localhost', 'System')
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        system_events = []
        
        # 循环读取所有事件，避免只读取第一批漏掉
        while True:
            batch = win32evtlog.ReadEventLog(hand, flags, 0)
            if not batch:
                break
            system_events.extend(batch)
        
        # 检查是否有最近30分钟内的启动事件
        has_recent_boot = False
        boot_time = None
        for event in system_events:
            event_time = event.TimeGenerated.astimezone()
            if event_time < thirty_minutes_ago:
                break
            
            # 场景1：WOL冷启动（系统刚开机，唤醒源为网卡）
            if event.SourceName == 'Microsoft-Windows-Kernel-General' and event.EventID == 12:
                logger.debug(f"检测到系统启动事件（ID:12），时间：{event_time}")
                boot_time = event_time
                has_recent_boot = True
                # 检查最后一次唤醒源是否为网卡
                wake_result = subprocess.run(
                    ['powercfg', '/lastwake'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                wake_output = wake_result.stdout.lower()
                logger.debug(f"powercfg /lastwake输出：{wake_output}")
                # 匹配网卡相关特征，增加更多关键词兼容不同网卡
                wol_keywords = ['pci\\ven_', 'ethernet', 'network controller', 'wake on lan', 'nic', 'magic packet',
                               'wake source', 'lan', 'network', '以太网', '网卡', '魔术包', 'wol']
                if any(keyword in wake_output for keyword in wol_keywords):
                    logger.info("检测到WOL冷启动（通过唤醒源匹配）")
                    return True
                # 兜底判断：如果唤醒历史计数为0，并且是最近15分钟内启动的，大概率是WOL冷启动（部分系统冷启动不记录唤醒源）
                if ('唤醒历史记录计数 - 0' in wake_output or 'wake history count - 0' in wake_output) and (now - event_time).total_seconds() < 900:
                    logger.info("检测到WOL冷启动（唤醒历史为空兜底判断）")
                    return True
            
            # 场景2：远程唤醒（从睡眠/休眠被网络唤醒）
            if event.SourceName == 'Power-Troubleshooter' and event.EventID == 1:
                logger.debug(f"检测到系统唤醒事件（ID:1），时间：{event_time}")
                wake_result = subprocess.run(
                    ['powercfg', '/lastwake'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                wake_output = wake_result.stdout.lower()
                logger.debug(f"powercfg /lastwake输出：{wake_output}")
                wol_keywords = ['pci\\ven_', 'ethernet', 'network controller', 'wake on lan', 'nic', 'magic packet',
                               'wake source', 'lan', 'network', '以太网', '网卡', '魔术包', 'wol']
                if any(keyword in wake_output for keyword in wol_keywords):
                    logger.info("检测到WOL远程唤醒")
                    return True
        
        # 兜底逻辑：最近30分钟内启动，且没有交互式登录记录，判定为WOL自动开机
        if has_recent_boot and boot_time:
            logger.debug("检查最近30分钟内是否有交互式登录事件")
            try:
                # 读取安全日志，检查登录事件
                sec_hand = win32evtlog.OpenEventLog('localhost', 'Security')
                sec_events = []
                while True:
                    batch = win32evtlog.ReadEventLog(sec_hand, flags, 0)
                    if not batch:
                        break
                    sec_events.extend(batch)
                
                has_interactive_login = False
                for event in sec_events:
                    event_time = event.TimeGenerated.astimezone()
                    if event_time < boot_time:
                        break
                    # 登录事件ID 4624，登录类型2是交互式登录（本地键盘登录）
                    if event.EventID == 4624:
                        try:
                            login_type = event.StringInserts[8]
                            if login_type == '2':  # 交互式本地登录
                                logger.debug(f"检测到本地交互式登录事件，时间：{event_time}，登录类型：{login_type}")
                                has_interactive_login = True
                                break
                        except:
                            pass
                
                if not has_interactive_login:
                    logger.info("检测到WOL冷启动（无本地登录兜底判断）")
                    return True
            except Exception as e:
                logger.debug(f"读取安全日志失败（无权限或未开启），跳过登录检查: {str(e)}")
        
        logger.info("未检测到WOL唤醒事件")
        return False
    except Exception as e:
        logger.warning(f"检测远程唤醒场景失败: {str(e)}，将不执行自动关机")
        return False

def shutdown(delay: int = 60, force: bool = False):
    """
    优雅关机（Windows专用）
    :param delay: 关机延迟时间（秒），默认60秒
    :param force: 是否强制关机
    :return: 是否成功
    """
    
    logger.info("准备关机...")
    
    # 检查操作系统
    system = platform.system().lower()
    if system != 'windows':
        logger.error(f"不支持的操作系统: {system}，本项目仅支持Windows")
        return False
    
    # 2. 执行关机命令
    logger.info("执行关机...")
    
    try:
        # Windows关机命令
        # /s: 关机
        # /f: 强制关闭应用程序
        # /t 0: 立即执行
        force_flag = '/f' if force else ''
        command = f'shutdown /s {force_flag} /t {delay}'
        
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