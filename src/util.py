import os
import ctypes
import sys
import platform
import psutil
import win32evtlog
import subprocess
from loguru import logger
from typing import Optional
from datetime import datetime, timedelta
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
    

def is_remote_wake_boot(wol_mode: str = "auto") -> bool:
    """判断是否为远程唤醒/自动开机场景（WOL冷启动/睡眠远程唤醒）
    :param wol_mode: WOL模式，可选值：auto（自动检测）、force_on（强制判定为WOL）、force_off（强制判定为非WOL）
    """
    # 优先处理强制模式
    if wol_mode == "force_on":
        logger.info("WOL模式强制开启，判定为WOL唤醒")
        return True
    if wol_mode == "force_off":
        logger.info("WOL模式强制关闭，判定为本地开机")
        return False
    
    # 此电脑判断远程开机不可行，直接判断是否12:00左右开机的
     # 1. 获取系统开机时间（时间戳）
    boot_timestamp = psutil.boot_time()
    
    # 2. 转成 datetime 对象
    boot_time = datetime.fromtimestamp(boot_timestamp)

    logger.info(f"系统开机时间: {boot_time}")
    
    # 3. 构造当天 12:00
    noon_time = datetime(boot_time.year, boot_time.month, boot_time.day, 12, 0, 0)
    
    # 4. 计算时间差
    time_diff = abs(boot_time - noon_time)
    
    # 5. 判断是否在允许范围内
    return time_diff <= timedelta(minutes=5)

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