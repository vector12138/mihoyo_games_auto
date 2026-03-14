import os
import sys
import subprocess
import time
import pyautogui
import win32gui
import win32con
from loguru import logger
from config import Config
from games.genshin import GenshinImpact
from games.zzz import ZenlessZoneZero, ZZZMultiApp
from telegram_notifier import TelegramNotifier
from shutdown import ShutdownManager

# 配置日志
logger.add("logs/automation_{time}.log", rotation="10MB", retention="7 days", level="INFO")


def launch_game(game_config: dict) -> bool:
    """启动游戏"""
    game_path = game_config.get('game_path')
    if not game_path or not os.path.exists(game_path):
        logger.error(f"游戏路径不存在: {game_path}")
        return False
    
    logger.info(f"正在启动游戏: {game_config.get('game_name')}")
    try:
        subprocess.Popen(game_path)
        return True
    except Exception as e:
        logger.error(f"启动游戏失败: {str(e)}")
        return False


def launch_bettergi(config: Config) -> bool:
    """启动BetterGI并执行一条龙操作"""
    bettergi_path = config.get("genshin.bettergi_path")
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
        
        # 3. 创建临时的OCR识别实例，用于识别BetterGI界面按钮
        from screen_capture import ScreenCapture
        from ocr_recognizer import OCRRecognizer
        from input_controller import InputController
        
        capture = ScreenCapture("BetterGI")
        ocr = OCRRecognizer(use_gpu=config.get("global.use_gpu"))
        input_ctrl = InputController(click_delay=0.2)
        
        def click_button(text: str, timeout: int = 10) -> bool:
            """通过文本识别点击按钮"""
            start_time = time.time()
            while time.time() - start_time < timeout:
                img = capture.capture()
                res = ocr.find_text(img, text, threshold=0.8)
                if res:
                    x, y = res['center']
                    # 转屏幕坐标
                    left, top, _, _ = win32gui.GetWindowRect(bettergi_hwnd)
                    screen_x = int(left + x)
                    screen_y = int(top + y)
                    input_ctrl.click(screen_x, screen_y)
                    logger.info(f"点击按钮成功: [{text}] 位置: ({screen_x}, {screen_y})")
                    return True
                time.sleep(0.5)
            logger.error(f"未找到按钮: [{text}]")
            return False
        
        # 4. 处理新版本弹窗
        logger.info("检查新版本弹窗...")
        # 同时识别几个可能的弹窗按钮文本
        update_buttons = ["取消", "稍后", "跳过", "知道了"]
        for btn_text in update_buttons:
            if click_button(btn_text, timeout=3):
                logger.info(f"新版本弹窗已处理，点击了: [{btn_text}]")
                break
        time.sleep(1)
        
        # 5. 点击启动按钮
        logger.info("点击启动按钮")
        if not click_button("启动", timeout=10):
            # 尝试其他可能的启动按钮文本
            if not click_button("启动游戏", timeout=5):
                logger.error("未找到启动按钮")
                return False
        logger.info("原神启动中，等待游戏窗口出现...")
        
        # 6. 等待原神窗口出现
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
        
        # 7. 等待原神完全加载进入游戏
        # 这里可以根据需要增加检测"进入游戏"文本的逻辑，暂时等待30秒
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
            # 尝试其他可能的文本
            if not click_button("日常任务", timeout=5):
                if not click_button("自动任务", timeout=5):
                    logger.error("未找到一条龙/日常任务按钮")
                    return False
        
        time.sleep(1)
        
        # 10. 点击任务列表右边的▶️执行按钮
        logger.info("点击任务列表右侧的执行按钮")
        # 适配多种可能的按钮文本
        if not click_button("▶", timeout=10):
            if not click_button("▶️", timeout=5):
                if not click_button("执行", timeout=5):
                    if not click_button("开始", timeout=5):
                        if not click_button("运行", timeout=5):
                            logger.error("未找到执行按钮")
                            return False
        
        logger.info("✅ BetterGI一条龙任务已成功启动！")
        return True
            
    except Exception as e:
        logger.error(f"启动BetterGI失败: {str(e)}")
        return False


def main():
    logger.info("=== 米哈游游戏自动化工具启动")
    
    # 加载配置
    try:
        config = Config()
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        sys.exit(1)
    
    # 初始化通知器
    notifier = None
    if config.get("global.telegram_notify"):
        telegram_config = {
            'bot_token': config.get("global.telegram_token"),
            'chat_id': config.get("global.telegram_chat_id"),
            'enabled': True
        }
        notifier = TelegramNotifier(telegram_config)
        notifier.send_message("🎮 游戏自动化任务开始执行")
    
    # 需要执行的游戏列表
    games_to_run = []
    
    # 原神
    if config.get("genshin.enabled"):
        genshin_config = config.get_game_config("genshin")
        games_to_run.append(("genshin", genshin_config, GenshinImpact))
    
    # 绝区零（单应用模式）
    if config.get("zzz.enabled"):
        zzz_config = config.get_game_config("zzz")
        games_to_run.append(("zzz", zzz_config, ZenlessZoneZero))
    
    # 绝区零（多应用模式，游戏+辅助工具）
    if config.get("zzz_multi_app.enabled"):
        zzz_multi_config = config.get("zzz_multi_app")
        games_to_run.append(("zzz_multi", zzz_multi_config, ZZZMultiApp))
    
    if not games_to_run:
        logger.warning("没有启用任何游戏自动化任务")
        if notifier:
            notifier.send_message("⚠️ 没有启用任何游戏自动化任务")
        return
    
    # 执行每个游戏的自动化
    success_count = 0
    total_count = len(games_to_run)
    
    # 先处理BetterGI和原神
    genshin_run = False
    for game_key, game_config, GameClass in games_to_run:
        game_name = game_config.get('game_name')
        logger.info(f"=== 开始处理{game_name}任务")
        
        try:
            # 原神需要先启动BetterGI
            if game_key == "genshin":
                # 检查是否启用BetterGI
                if config.get("genshin.use_bettergi"):
                    logger.info("使用BetterGI启动原神")
                    if not launch_bettergi(config):
                        logger.error("BetterGI启动失败，跳过原神任务")
                        if notifier:
                            notifier.send_message(f"❌ BetterGI启动失败，跳过原神任务")
                        continue
                    genshin_run = True
                else:
                    # 不使用BetterGI的话直接启动游戏
                    if game_config.get("auto_launch"):
                        if not launch_game(game_config):
                            logger.error(f"{game_name}启动失败，跳过此游戏")
                            if notifier:
                                notifier.send_message(f"❌ {game_name}启动失败，跳过此游戏")
                            continue
                        # 等待游戏启动
                        time.sleep(30)
                
                # 原神任务由BetterGI执行，不需要再运行游戏内自动化
                logger.info("原神任务由BetterGI一条龙执行")
                success_count += 1
                continue
            
            # 其他游戏正常执行
            # 自动启动游戏
            if game_config.get("auto_launch"):
                if not launch_game(game_config):
                    logger.error(f"{game_name}启动失败，跳过此游戏")
                    if notifier:
                        notifier.send_message(f"❌ {game_name}启动失败，跳过此游戏")
                    continue
                # 等待游戏启动
                time.sleep(30)
            
            # 初始化游戏实例
            game = GameClass(game_config)
            # 执行任务
            result = game.run()
            
            if result:
                success_count += 1
                logger.info(f"{game_name}任务执行成功")
                if notifier:
                    notifier.send_message(f"✅ {game_name}任务执行成功")
            else:
                logger.error(f"{game_name}任务执行失败")
                if notifier:
                    notifier.send_message(f"❌ {game_name}任务执行失败")
        
        except Exception as e:
            logger.error(f"{game_name}任务执行出错: {str(e)}")
            if notifier:
                notifier.send_message(f"❌ {game_name}任务执行出错: {str(e)}")
    
    # 任务完成
    logger.info(f"=== 所有任务执行完成 成功: {success_count}/{total_count}")
    
    if notifier:
        notifier.send_message(f"🎮 所有任务执行完成 成功: {success_count}/{total_count}")
    
    # 自动关机
    if config.get("global.auto_shutdown"):
        logger.info("任务完成，即将自动关机")
        if notifier:
            notifier.send_message("🔌 任务完成，即将自动关机")
        ShutdownManager.shutdown(delay=60)


if __name__ == "__main__":
    # 创建日志目录
    os.makedirs("logs", exist_ok=True)
    main()
