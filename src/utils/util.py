import os
import ctypes
from typing import Optional

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
