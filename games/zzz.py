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
        
        super().__init__(config, global_config)
        
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
        self.task_steps = self._get_multi_app_steps_by_uia()

        if self.config.get('auto_close', True):
            self.task_steps.append({
                'name': '关闭绝区零游戏',
                'type': 'close_app',
                'app_name': 'zzz_game',
                'force': False
            })
            self.task_steps.append({
                'name': '关闭zzz-onedragen辅助工具',
                'type': 'close_app',
                'app_name': 'zzz_onedragen',
                'force': False
            })
    
    def _get_multi_app_steps(self) -> list:
        """获取多应用辅助模式的操作步骤"""

        steps = [
            {
                'name': '启动绝区零',
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
            {
                'name': '等待辅助窗口激活',
                'type': 'sleep',
                'seconds': 10
            },
            {
                'name': '点击一条龙按钮',
                'type': 'click',
                'text': self.buttons['daily_task'],
                'timeout': 10
            },
            {
                'name': '等待一条龙任务执行完成（10分钟）',
                'type': 'sleep',
                'seconds': 100  # 可根据实际情况调整时间
            },
            {
                'name': "检测一条龙是否运行完成",
                'type': 'wait_for_telegram_text',
                'text': 'ZZZ一条龙运行通知\n一条龙运行完成',
                'sender_id': 8445448103,
                'timeout': 1800  # 可根据实际情况调整时间
            }
        ]
        
        return steps
    
    def _get_multi_app_steps_by_uia(self) -> list:
        """获取多应用辅助模式的操作步骤"""

        steps = [
            {
                'name': '启动绝区零',
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
            {
                'name': '等待辅助窗口激活',
                'type': 'sleep',
                'seconds': 10
            },
            {
                'name': '点击一条龙按钮',
                'type': 'click_control_by_properties',
                'properties': {'source': 'uia','automation_id': 'QApplication.PhosWindow.areaWidget.StackedWidget.PopUpAniStackedWidget.home_interface.SingleDirectionScrollArea.qt_scrollarea_viewport.Banner.QWidget.QWidget.start_button'},
                'timeout': 10
            },
            {
                'name': '等待一条龙任务执行完成（10分钟）',
                'type': 'sleep',
                'seconds': 600  # 可根据实际情况调整时间
            },
            {
                'name': "检测一条龙是否运行完成",
                'type': 'wait_for_telegram_text',
                'text': 'ZZZ一条龙运行通知\n一条龙运行完成',
                'sender_id': 8445448103,
                'timeout': 1800  # 可根据实际情况调整时间
            }
        ]
        
        return steps
    
    