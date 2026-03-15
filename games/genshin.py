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
        # 初始化多应用配置
        
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
        
        self.task_steps = self._get_bettergi_steps()
    
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
            # 第二步：处理新版本弹窗
            {
                'name': '处理新版本弹窗（取消）',
                'type': 'click',
                'text': '取消',
                'timeout': 3
            },
            {
                'name': '处理新版本弹窗（稍后）',
                'type': 'click',
                'text': '稍后',
                'timeout': 3
            },
            {
                'name': '处理新版本弹窗（跳过）',
                'type': 'click',
                'text': '跳过',
                'timeout': 3
            },
            {
                'name': '处理新版本弹窗（知道了）',
                'type': 'click',
                'text': '知道了',
                'timeout': 3
            },
            # 第三步：启动原神
            {
                'name': '点击启动游戏',
                'type': 'click',
                'text': '启动',
                'timeout': 10
            },
            {
                'name': '点击启动游戏（备用）',
                'type': 'click',
                'text': '启动游戏',
                'timeout': 5
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
