import time
import win32gui
import subprocess
import os
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
        self.global_config = global_config
        app_configs = {}
        
        # 基础游戏应用
        app_configs['genshin_game'] = {
            'app_path': config.get('game_path', ''),
            'window_title': config.get('window_title', '原神')
        }
        
        # 如果使用BetterGI，添加BetterGI应用
        if config.get('use_bettergi', False):
            app_configs['bettergi'] = {
                'app_path': config.get('bettergi_path', ''),
                'window_title': 'BetterGI'
            }
        
        # 组装多应用配置
        multi_config = {
            **config,
            'apps': app_configs
        }
        
        super().__init__(multi_config)
        
        # 按钮文本配置
        self.buttons = {
            'login': '登录',
            'enter_game': '进入游戏',
            'daily_reward': '每日奖励',
            'claim': '领取',
            'confirm': '确定',
            'exit': '退出游戏'
        }
        
        # 根据模式选择操作步骤
        use_bettergi = config.get('use_bettergi', False)
        if use_bettergi:
            self.task_steps = self._get_bettergi_steps()
        else:
            self.task_steps = self._get_normal_game_steps()
    
    def _get_normal_game_steps(self) -> list:
        """获取纯游戏模式的操作步骤"""
        return [
            {
                'name': '启动原神游戏',
                'type': 'launch_app',
                'app_name': 'genshin_game',
                'timeout': 60
            },
            {
                'name': '等待登录按钮',
                'type': 'wait',
                'text': self.buttons['login'],
                'timeout': 30
            },
            {
                'name': '点击登录',
                'type': 'click',
                'text': self.buttons['login']
            },
            {
                'name': '等待进入游戏按钮',
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
                'name': '等待游戏加载完成',
                'type': 'sleep',
                'seconds': 20
            },
            {
                'name': '打开每日奖励界面',
                'type': 'custom',
                'func': 'open_daily_reward'
            },
            {
                'name': '领取每日奖励',
                'type': 'click',
                'text': self.buttons['claim']
            },
            {
                'name': '确认领取',
                'type': 'click',
                'text': self.buttons['confirm']
            },
            {
                'name': '完成每日委托',
                'type': 'custom',
                'func': 'do_daily_quests'
            },
            {
                'name': '退出游戏',
                'type': 'click',
                'text': self.buttons['exit']
            }
        ]
    
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
                'seconds': 60
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
                'name': '点击日常任务按钮（备用）',
                'type': 'click',
                'text': '日常任务',
                'timeout': 5
            },
            {
                'name': '点击自动任务按钮（备用）',
                'type': 'click',
                'text': '自动任务',
                'timeout': 5
            },
            {
                'name': '点击执行按钮',
                'type': 'click',
                'text': '▶',
                'timeout': 10
            },
            {
                'name': '点击执行按钮（执行）',
                'type': 'click',
                'text': '执行',
                'timeout': 10
            },
            {
                'name': '点击执行按钮（开始）',
                'type': 'click',
                'text': '开始',
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
                'force': False
            },
            {
                'name': '关闭BetterGI工具',
                'type': 'close_app',
                'app_name': 'bettergi',
                'force': False
            }
        ]
    
    def open_daily_reward(self) -> bool:
        """自定义方法：打开每日奖励界面"""
        logger.info("打开每日奖励界面")
        # 按F3打开活动界面（根据实际游戏设置修改）
        self.input_controller.press_key('f3')
        time.sleep(2)
        # 点击每日奖励标签
        return self.click_text(self.buttons['daily_reward'])
    
    def do_daily_quests(self) -> bool:
        """自定义方法：完成每日委托"""
        logger.info("开始执行每日委托")
        # 这里可以实现具体的每日委托逻辑
        # 比如传送、打怪、提交任务等
        time.sleep(10)
        return True
