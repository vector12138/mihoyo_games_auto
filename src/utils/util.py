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

def run_as_admin(args: Optional[list] = None) -> bool:
    """
    以管理员权限重新启动当前脚本（仅Windows平台）
    :param args: 启动参数，不传则使用当前脚本的参数
    :return: 成功发起重新启动返回True，失败返回False
    """
    import sys
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
