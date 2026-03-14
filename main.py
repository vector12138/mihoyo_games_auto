#!/usr/bin/env python3
"""
米哈游游戏自动化工具 - 优化版
统一架构，代码精简
"""
import os
import sys
import time
from loguru import logger
from config import Config
from games.genshin import GenshinImpact
from games.zzz import ZenlessZoneZero, ZZZMultiApp
from telegram_notifier import TelegramNotifier
from shutdown import ShutdownManager

# 配置日志
logger.add("logs/automation_{time}.log", rotation="10MB", retention="7 days", level="INFO")


def main():
    logger.info("=== 米哈游游戏自动化工具启动 ===")
    
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
        # 如果使用BetterGI模式，直接启动BetterGI一条龙
        if config.get("genshin.use_bettergi"):
            logger.info("使用BetterGI模式运行原神")
            games_to_run.append(("genshin_bettergi", genshin_config, None))
        else:
            # 普通游戏内自动化模式
            games_to_run.append(("genshin", genshin_config, GenshinImpact))
    
    # 绝区零（单应用模式）
    if config.get("zzz.enabled"):
        zzz_config = config.get_game_config("zzz")
        games_to_run.append(("zzz", zzz_config, ZenlessZoneZero))
    
    # 绝区零（多应用模式）
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
    
    for game_key, game_config, GameClass in games_to_run:
        game_name = game_config.get('game_name', game_key)
        logger.info(f"=== 开始处理{game_name}任务")
        
        try:
            # 原神BetterGI特殊处理
            if game_key == "genshin_bettergi":
                genshin = GenshinImpact(game_config)
                result = genshin.launch_bettergi()
            else:
                # 其他游戏正常执行
                game = GameClass(game_config)
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
