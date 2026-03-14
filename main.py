import os
import sys
import subprocess
import time
from loguru import logger
from config import Config
from games.genshin import GenshinImpact
from games.zzz import ZenlessZoneZero
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
        notifier = TelegramNotifier(
            token=config.get("global.telegram_token"),
            chat_id=config.get("global.telegram_chat_id")
        )
        notifier.send_msg("🎮 游戏自动化任务开始执行")
    
    # 需要执行的游戏列表
    games_to_run = []
    
    # 原神
    if config.get("genshin.enabled"):
        genshin_config = config.get_game_config("genshin")
        games_to_run.append(("genshin", genshin_config, GenshinImpact))
    
    # 绝区零
    if config.get("zzz.enabled"):
        zzz_config = config.get_game_config("zzz")
        games_to_run.append(("zzz", zzz_config, ZenlessZoneZero))
    
    if not games_to_run:
        logger.warning("没有启用任何游戏自动化任务")
        if notifier:
            notifier.send_msg("⚠️ 没有启用任何游戏自动化任务")
        return
    
    # 执行每个游戏的自动化
    success_count = 0
    total_count = len(games_to_run)
    
    for game_key, game_config, GameClass in games_to_run:
        game_name = game_config.get('game_name')
        logger.info(f"=== 开始处理{game_name}任务")
        
        try:
            # 自动启动游戏
            if game_config.get("auto_launch"):
                if not launch_game(game_config):
                    logger.error(f"{game_name}启动失败，跳过此游戏")
                    if notifier:
                        notifier.send_msg(f"❌ {game_name}启动失败，跳过此游戏")
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
                    notifier.send_msg(f"✅ {game_name}任务执行成功")
            else:
                logger.error(f"{game_name}任务执行失败")
                if notifier:
                    notifier.send_msg(f"❌ {game_name}任务执行失败")
        
        except Exception as e:
            logger.error(f"{game_name}任务执行出错: {str(e)}")
            if notifier:
                notifier.send_msg(f"❌ {game_name}任务执行出错: {str(e)}")
    
    # 任务完成
    logger.info(f"=== 所有任务执行完成 成功: {success_count}/{total_count}")
    
    if notifier:
        notifier.send_msg(f"🎮 所有任务执行完成 成功: {success_count}/{total_count}")
    
    # 自动关机
    if config.get("global.auto_shutdown"):
        logger.info("任务完成，即将自动关机")
        if notifier:
            notifier.send_msg("🔌 任务完成，即将自动关机")
        ShutdownManager.shutdown(delay=60)


if __name__ == "__main__":
    # 创建日志目录
    os.makedirs("logs", exist_ok=True)
    main()
