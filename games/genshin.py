from src.core import MultiAppBase
from typing import Dict
from loguru import logger


class GenshinImpact(MultiAppBase):
    """原神多应用自动化实现（支持纯游戏模式 + BetterGI模式）"""
    
    def __init__(self, config: Dict, global_config: Dict = None):
        """
        初始化原神自动化
        :param config: 游戏配置
        :param global_config: 全局配置（可选）
        """
        
        super().__init__(config, global_config)
        
        # 按钮文本配置
        self.buttons = {
            'login': '登录',
            'enter_game': '进入游戏',
            'daily_reward': '每日奖励',
            'claim': '领取',
            'confirm': '确定',
            'exit': '退出游戏'
        }
        
        self.task_steps = self._get_bettergi_steps_by_uia()
    
    def _get_bettergi_steps(self) -> list:
        """获取BetterGI模式的操作步骤"""
        return [
            # 第一步：启动BetterGI
            {
                'name': '启动BetterGI工具',
                'type': 'launch_app',
                'app_name': 'bettergi',
                'timeout': 30
            },
            {
                'name': '启动原神游戏',
                'type': 'launch_app',
                'app_name': 'genshin_game',
                'timeout': 30
            },{
                'name': '检测是否有新版本弹窗',
                'type': 'launch_app',
                'app_name': 'bettergi_pop',
                'timeout': 30
            },
            # 第二步：处理新版本弹窗
            {
                'name': '处理新版本弹窗（取消）',
                'type': 'close_app',
                'app_name': 'bettergi_pop'
            },
            # 第三步：启动原神
            {
                'name': '切换回BetterGI窗口',
                'type': 'switch_app',
                'app_name': 'bettergi'
            },
            {
                'name': '点击启动游戏',
                'type': 'click',
                'text': '启动',
                'timeout': 10
            },
            {
                'name': '等待原神启动完成',
                'type': 'sleep',
                'seconds': 120
            },
            # 第四步：启动一条龙
            {
                'name': '切换回BetterGI窗口',
                'type': 'switch_app',
                'app_name': 'bettergi'
            },
            {
                'name': '点击一条龙按钮',
                'type': 'click',
                'text': '一条龙',
                'timeout': 10
            },
            {
                'name': '等待切换到一条龙',
                'type': 'wait',
                'text': '▷',
                'timeout': 5
            },
            {
                'name': '点击执行按钮',
                'type': 'click',
                'text': '▷',
                'timeout': 10
            },
            # 第五步：等待任务完成
            {
                'name': '等待一条龙任务完成（30分钟）',
                'type': 'sleep',
                'seconds': 1800
            },
            # 第六步：关闭应用
            {
                'name': '关闭原神游戏',
                'type': 'close_app',
                'app_name': 'genshin_game',
                'force': True
            },
            {
                'name': '关闭BetterGI工具',
                'type': 'close_app',
                'app_name': 'bettergi',
                'force': True
            }
        ]

    def _get_bettergi_steps_by_uia(self) -> list:
        """获取BetterGI模式的操作步骤"""
        return [
            # 第一步：启动BetterGI
            {
                'name': '启动BetterGI工具',
                'type': 'launch_app',
                'app_name': 'bettergi',
                'timeout': 30
            },
            {
                'name': '启动原神游戏',
                'type': 'launch_app',
                'app_name': 'genshin_game',
                'timeout': 30
            },{
                'name': '检测是否有新版本弹窗',
                'type': 'launch_app',
                'app_name': 'bettergi_pop',
                'timeout': 30
            },
            # 第二步：处理新版本弹窗
            {
                'name': '处理新版本弹窗',
                'type': 'close_app',
                'app_name': 'bettergi_pop'
            },
            # 第三步：启动原神
            {
                'name': '切换回BetterGI窗口',
                'type': 'switch_app',
                'app_name': 'bettergi'
            },
            {
                'name': '点击一条龙按钮',
                'type': 'click_control_by_properties',
                'properties': {'source': 'uia','name': '一条龙', 'class_name': 'TextBlock', 'control_type': 'TextControl'},
                'timeout': 10
            },
            {
                'name': '点击运行按钮',
                'type': 'click_control_by_hierarchy',
                'hierarchy': [
                    {'source': 'uia', 'class_name': 'OneDragonFlowPage', 'control_type': 'CustomControl'},
                    {'source': 'uia','name': '\uF606', 'class_name': 'TextBlock', 'control_type': 'TextControl'}
                ],
                'timeout': 10
            },
            # 第五步：等待任务完成
            {
                'name': '等待一条龙任务完成（10分钟）',
                'type': 'sleep',
                'seconds': 60
            },
            {
                'name': '切换回原神本体',
                'type': 'switch_app',
                'app_name': 'genshin_game',
                'timeout': 10
            },
            {
                'name': "等待结束运行文本出现",
                'type': 'wait',
                'text': '一条龙和配置组任务结束',
                'timeout': 1800
            },
            # 第六步：关闭应用
            {
                'name': '关闭原神游戏',
                'type': 'close_app',
                'app_name': 'genshin_game',
                'force': False
            },
            {
                'name': '关闭BetterGI工具',
                'type': 'close_app',
                'app_name': 'bettergi',
                'force': False
            }
        ]
