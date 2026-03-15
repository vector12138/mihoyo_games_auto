import time
import win32gui
import subprocess
import os
from src.core import GameBase, ScreenCapture, OCRRecognizer, InputController
from typing import Dict
from loguru import logger


class GenshinImpact(GameBase):
    """原神自动化实现"""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # 按钮文本配置
        self.buttons = {
            'login': '登录',
            'enter_game': '进入游戏',
            'daily_reward': '每日奖励',
            'claim': '领取',
            'confirm': '确定',
            'exit': '退出游戏'
        }
        
        # 操作步骤配置，可根据实际情况修改
        self.task_steps = [
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

    def launch_bettergi(self) -> bool:
        """
        启动BetterGI并执行一条龙操作
        整合BetterGI启动、新版本弹窗处理、一条龙启动全流程
        """
        bettergi_path = self.config.get("bettergi_path")
        if not bettergi_path or not os.path.exists(bettergi_path):
            logger.error(f"BetterGI路径不存在: {bettergi_path}")
            return False
        
        logger.info("=== 开始启动BetterGI")
        
        try:
            # 1. 启动BetterGI
            logger.info(f"启动BetterGI: {bettergi_path}")
            subprocess.Popen(bettergi_path)
            
            # 2. 等待BetterGI窗口出现
            logger.info("等待BetterGI窗口加载...")
            bettergi_hwnd = None
            for _ in range(30):
                bettergi_hwnd = win32gui.FindWindow(None, "BetterGI")
                if bettergi_hwnd:
                    break
                time.sleep(1)
            
            if not bettergi_hwnd:
                logger.error("等待BetterGI窗口超时")
                return False
            
            # 3. 创建识别实例
            screen_capture = ScreenCapture("BetterGI")
            ocr = OCRRecognizer(use_gpu=self.config.get('use_gpu', True))
            input_controller = InputController(click_delay=0.2)
            
            def click_button(text: str, timeout: int = 10) -> bool:
                """通过文本识别点击按钮"""
                start_time = time.time()
                while time.time() - start_time < timeout:
                    img = screen_capture.capture()
                    res = ocr.find_text(img, text, threshold=0.8)
                    if res:
                        x, y = res['center']
                        left, top, _, _ = win32gui.GetWindowRect(bettergi_hwnd)
                        screen_x = int(left + x)
                        screen_y = int(top + y)
                        input_controller.click(screen_x, screen_y)
                        logger.info(f"点击按钮成功: [{text}] 位置: ({screen_x}, {screen_y})")
                        return True
                    time.sleep(0.5)
                logger.error(f"未找到按钮: [{text}]")
                return False
            
            # 4. 处理新版本弹窗
            logger.info("检查新版本弹窗...")
            update_buttons = ["取消", "稍后", "跳过", "知道了"]
            for btn_text in update_buttons:
                if click_button(btn_text, timeout=3):
                    logger.info(f"新版本弹窗已处理，点击了: [{btn_text}]")
                    break
            time.sleep(1)
            
            # 5. 点击启动按钮
            logger.info("点击启动按钮")
            if not click_button("启动", timeout=10):
                if not click_button("启动游戏", timeout=5):
                    logger.error("未找到启动按钮")
                    return False
            logger.info("原神启动中...")
            
            # 6. 等待原神窗口出现
            logger.info("等待原神窗口出现...")
            genshin_hwnd = None
            start_wait = time.time()
            while time.time() - start_wait < 300:  # 最多等5分钟
                genshin_hwnd = win32gui.FindWindow(None, "原神")
                if genshin_hwnd and win32gui.IsWindowVisible(genshin_hwnd):
                    logger.info("原神窗口已出现，等待游戏进入主界面...")
                    break
                time.sleep(5)
            
            if not genshin_hwnd:
                logger.error("等待原神窗口超时")
                return False
            
            # 7. 等待原神加载完成
            time.sleep(30)
            logger.info("原神已进入游戏，切回BetterGI窗口")
            
            # 8. 重新激活BetterGI窗口
            bettergi_hwnd = win32gui.FindWindow(None, "BetterGI")
            if not bettergi_hwnd:
                logger.error("未找到BetterGI窗口")
                return False
            win32gui.SetForegroundWindow(bettergi_hwnd)
            time.sleep(2)
            
            # 9. 点击一条龙按钮
            logger.info("点击一条龙按钮")
            if not click_button("一条龙", timeout=10):
                if not click_button("日常任务", timeout=5):
                    if not click_button("自动任务", timeout=5):
                        logger.error("未找到一条龙/日常任务按钮")
                        return False
            
            time.sleep(1)
            
            # 10. 点击执行按钮
            logger.info("点击任务执行按钮")
            exec_buttons = ["▶", "▶️", "执行", "开始", "运行", "启动"]
            for btn_text in exec_buttons:
                if click_button(btn_text, timeout=10):
                    logger.info(f"成功点击执行按钮: [{btn_text}]")
                    break
            else:
                logger.error("未找到执行按钮")
                return False
            
            logger.info("✅ BetterGI一条龙任务已成功启动！")
            return True
            
        except Exception as e:
            logger.error(f"启动BetterGI失败: {str(e)}")
            return False
