from loguru import logger
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