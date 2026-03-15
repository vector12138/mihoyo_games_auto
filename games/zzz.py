from src.core import MultiAppBase
from typing import Dict
from loguru import logger


class ZenlessZoneZero(MultiAppBase):
    """绝区零多应用自动化实现（支持纯游戏模式 + 多应用辅助模式）"""
    
    def __init__(self, config: Dict, global_config: Dict = None):
        """
        初始化绝区零自动化
        :param config: 游戏配置
        :param global_config: 全局配置（可选）
        """
        if global_config is None:
            global_config = {}
            
        app_configs = {}
        
        # 基础游戏应用
        app_configs['zzz_game'] = {
            'app_path': config.get('game_path', ''),
            'window_title': config.get('window_title', '绝区零')
        }
        
        # 如果使用onedragen辅助，添加辅助工具应用
        if config.get('use_onedragen', False):
            app_configs['zzz_onedragen'] = {
                'app_path': config.get('onedragen_path', ''),
                'window_title': 'zzz-onedragen'
            }
        
        # 组装多应用配置
        multi_config = {
            **config,
            'apps': app_configs
        }
        
        super().__init__(multi_config, global_config)
        
        # 按钮文本配置
        self.buttons = {
            'start_game': '开始游戏',
            'enter_game': '点击进入游戏',
            'daily_checkin': '每日签到',
            'claim_all': '一键领取',
            'confirm': '确认',
            'daily_task': '启动一条龙',
            'exit': '退出'
        }
        
        # 根据模式选择操作步骤
        self.task_steps = self._get_multi_app_steps()
    
    def _get_multi_app_steps(self) -> list:
        """获取多应用辅助模式的操作步骤"""
        return [
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
                'timeout': 60
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
                'text': self.buttons['enter_game'],
                'timeout': 60
            },
            {
                'name': '点击进入游戏',
                'type': 'click',
                'text': self.buttons['enter_game']
            },
            {
                'name': '等待游戏加载',
                'type': 'sleep',
                'seconds': 15
            },
            {
                'name': '领取月卡奖励',
                'type': 'click',
                'text': self.buttons['claim_all'],
                'timeout': 10
            },
            {
                'name': '确认领取',
                'type': 'click',
                'text': self.buttons['confirm'],
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
                'text': self.buttons['daily_task'],
                'timeout': 10
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
                'force': True
            },
            {
                'name': '关闭zzz-onedragen辅助工具',
                'type': 'close_app',
                'app_name': 'zzz_onedragen',
                'force': True
            }
        ]
