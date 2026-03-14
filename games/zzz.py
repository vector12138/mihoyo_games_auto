import time
from game_base import GameBase, MultiAppGameBase
from typing import Dict
from loguru import logger


class ZZZMultiApp(MultiAppGameBase):
    """绝区零多应用自动化（游戏本体 + zzz-onedragen辅助工具）"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # 操作步骤，完全按照需求实现
        self.task_steps = [
            # ========== 第一步：启动两个应用 ==========
            {
                'name': '启动绝区零游戏本体',
                'type': 'launch_app',
                'app_name': 'zzz_game',
                'timeout': 60
            },
            {
                'name': '启动zzz-onedragen辅助工具',
                'type': 'launch_app',
                'app_name': 'zzz_onedragen',
                'timeout': 30
            },
            
            # ========== 第二步：在游戏本体里领月卡 ==========
            {
                'name': '切换到绝区零游戏窗口',
                'type': 'switch_app',
                'app_name': 'zzz_game'
            },
            {
                'name': '等待进入游戏',
                'type': 'wait',
                'text': '进入游戏',
                'timeout': 60
            },
            {
                'name': '点击进入游戏',
                'type': 'click',
                'text': '进入游戏'
            },
            {
                'name': '等待游戏加载',
                'type': 'sleep',
                'seconds': 15
            },
            {
                'name': '点击月卡/签到界面',
                'type': 'click',
                'text': '月卡',
                'timeout': 10
            },
            {
                'name': '领取月卡奖励',
                'type': 'click',
                'text': '领取',
                'timeout': 10
            },
            {
                'name': '确认领取',
                'type': 'click',
                'text': '确认',
                'timeout': 5
            },
            
            # ========== 第三步：切换到辅助工具启动一条龙 ==========
            {
                'name': '切换到zzz-onedragen辅助窗口',
                'type': 'switch_app',
                'app_name': 'zzz_onedragen'
            },
            {
                'name': '等待辅助窗口激活',
                'type': 'sleep',
                'seconds': 2
            },
            {
                'name': '点击一条龙按钮',
                'type': 'click',
                'text': '一条龙',
                'timeout': 10
            },
            {
                'name': '点击启动/运行按钮',
                'type': 'click',
                'text': '启动',
                'timeout': 5
            },
            
            # ========== 第四步：等待任务执行 ==========
            {
                'name': '等待一条龙任务执行完成（30分钟）',
                'type': 'sleep',
                'seconds': 1800  # 可根据实际情况调整时间
            },
            
            # ========== 第五步：关闭两个应用 ==========
            {
                'name': '关闭绝区零游戏',
                'type': 'close_app',
                'app_name': 'zzz_game',
                'force': False
            },
            {
                'name': '关闭zzz-onedragen辅助工具',
                'type': 'close_app',
                'app_name': 'zzz_onedragen',
                'force': False
            }
        ]
    
    def get_running_status(self) -> bool:
        """自定义方法：检查一条龙是否运行完成（可选实现）"""
        # 可以通过识别辅助工具里的"完成/已结束"文本判断是否执行完成
        # 替代固定等待时间，更灵活
        pass
