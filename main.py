#!/usr/bin/env python3
"""
米哈游游戏自动化工具 - 优化版
统一架构，代码精简
"""
import os
import sys
import time
from loguru import logger
from src.config.logging_config import setup_logging
from src.config import Config
from games.genshin import GenshinImpact
from games.zzz import ZenlessZoneZero
from src.utils import get_telegram_bridge_client
from src.utils.util import run_as_admin
from src.core import shutdown

# 配置日志
setup_logging()

# 启动时检测权限，无管理员权限则自动提权
if not run_as_admin():
    print("需要管理员权限才能运行！")
    sys.exit(1)


def main():
    logger.info("=== 米哈游游戏自动化工具启动 ===")
    
    # 加载配置
    try:
        config = Config()
        debug = config.get("global.debug", False)
        if debug:
            logger.info("调试模式已开启")
            setup_logging(log_level="DEBUG")
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        sys.exit(1)
    
    # 初始化通知器
    notifier = None
    if config.get("telegram.enabled"):
        notifier = get_telegram_bridge_client(config.get("telegram"))
        notifier.send_message("🎮 游戏自动化任务开始执行")
    
    # 需要执行的游戏列表
    games_to_run = []
    
    # 原神（统一多应用模式，自动识别是否使用BetterGI）
    if config.get("genshin.enabled"):
        genshin_config = config.get_game_config("genshin")
        mode_str = "（BetterGI模式）"
        logger.info(f"原神已启用{mode_str}")
        games_to_run.append(("原神", genshin_config, GenshinImpact))
    
    # 绝区零（统一多应用模式，自动识别是否使用辅助工具）
    if config.get("zzz.enabled"):
        zzz_config = config.get_game_config("zzz")
        mode_str = "（多应用辅助模式）"
        logger.info(f"绝区零已启用{mode_str}")
        games_to_run.append(("绝区零", zzz_config, ZenlessZoneZero))
    
    if not games_to_run:
        logger.warning("没有启用任何游戏自动化任务")
        if notifier:
            notifier.send_message("⚠️ 没有启用任何游戏自动化任务")
        return
    
    # 执行每个游戏的自动化
    success_count = 0
    total_count = len(games_to_run)
    all_game_results = []
    
    for game_name, game_config, GameClass in games_to_run:
        logger.info(f"=== 开始处理{game_name}任务")
        
        try:
            # 传递游戏配置 + 全局配置
            game = GameClass(game_config, global_config=config.get("global"))
            result = game.run()
            
            if result["success"]:
                success_count += 1
                logger.info(f"{game_name}任务执行成功")
                msg = f"✅ {game_name}任务执行成功\n📊 步骤完成: {result['success_count']}/{result['total_steps']}"
                all_game_results.append(msg)
                if notifier:
                    notifier.send_message(msg)
            else:
                logger.error(f"{game_name}任务执行失败")
                failed_steps_str = '\n'.join(result["failed_steps"])
                msg = f"❌ {game_name}任务执行失败\n📊 步骤完成: {result['success_count']}/{result['total_steps']}\n❌ 失败步骤:\n{failed_steps_str}"
                all_game_results.append(msg)
                if notifier:
                    notifier.send_message(msg)
        
        except Exception as e:
            logger.error(f"{game_name}任务执行出错: {str(e)}")
            import traceback
            print(traceback.format_exc())
            msg = f"❌ {game_name}任务执行出错: {str(e)}"
            all_game_results.append(msg)
            if notifier:
                notifier.send_message(msg)
    
    # 任务完成
    logger.info(f"=== 所有任务执行完成 成功: {success_count}/{total_count}")
    
    if notifier:
        # 汇总所有游戏结果发送总通知
        all_results_str = '\n'.join(all_game_results)
        total_msg = f"🎮 所有任务执行完成 成功: {success_count}/{total_count}\n\n{all_results_str}"
        notifier.send_message(total_msg)
    
    # 自动关机
    if config.get("global.auto_shutdown"):
        logger.info("任务完成，即将自动关机")
        if notifier:
            notifier.send_message("🔌 任务完成，即将自动关机")
        shutdown(delay=60)


if __name__ == "__main__":
    # 创建日志目录
    os.makedirs("logs", exist_ok=True)
    main()
