#!/usr/bin/env python3
"""
米哈游游戏自动化工具 - 优化版
统一架构，代码精简
"""
import os
import sys

# 启动优化：最高级别Python优化，减少内存占用
sys.dont_write_bytecode = True
os.environ['PYTHONOPTIMIZE'] = '2'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['PYTHONUNBUFFERED'] = '1'

# 权限检测放在最前面，避免提前加载大模块浪费内存
from src.utils.util import run_as_admin
if not run_as_admin():
    print("需要管理员权限才能运行！")
    sys.exit(1)

# 延迟导入其他模块，启动时只加载必要的
import time
import ctypes
from loguru import logger
from src.config.logging_config import setup_logging

# 配置日志
setup_logging()


def main():
    logger.info("=== 米哈游游戏自动化工具启动 ===")
    
    # 加载配置（延迟导入配置模块）
    try:
        from src.config import Config
        config = Config()
        debug = config.get("global.debug", False)
        if debug:
            logger.info("调试模式已开启")
            setup_logging(log_level="DEBUG")
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        sys.exit(1)
    
    # 所有任务执行前先全局静音（延迟导入音量模块）
    from src.utils import mute_system_volume, unmute_system_volume
    mute_system_volume()
    
    try:
        # 初始化通知器（按需导入）
        notifier = None
        if config.get("telegram.enabled"):
            from src.utils import get_telegram_bridge_client
            notifier = get_telegram_bridge_client(config.get("telegram"))
            notifier.send_message("🎮 游戏自动化任务开始执行")
        
        # 需要执行的游戏列表（配置化，无需单独游戏类）
        games_to_run = []
        all_games_config = config.get("games", {})
        
        # 遍历所有游戏配置
        for game_key, game_config in all_games_config.items():
            if not game_config.get("enabled", False):
                continue
            game_name = game_config.get("name", game_key)
            logger.info(f"{game_name}已启用")
            games_to_run.append((game_name, game_config))
        
        if not games_to_run:
            logger.warning("没有启用任何游戏自动化任务")
            if notifier:
                notifier.send_message("⚠️ 没有启用任何游戏自动化任务")
            return
        
        # 延迟导入通用多应用执行器和YAML加载
        from src.core.game_base import MultiAppBase
        import yaml
        import os
        
        # 执行每个游戏的自动化
        success_count = 0
        total_count = len(games_to_run)
        all_game_results = []
        
        for game_name, game_config in games_to_run:
            logger.info(f"=== 开始处理{game_name}任务")
            
            try:
                # 加载对应游戏的steps配置文件
                steps_file = game_config.get("steps", "")
                steps_path = os.path.join("games", steps_file)
                if not os.path.exists(steps_path):
                    raise ValueError(f"步骤配置文件不存在: {steps_path}")
                
                with open(steps_path, "r", encoding="utf-8") as f:
                    task_steps = yaml.safe_load(f)
                
                if not task_steps or not isinstance(task_steps, list):
                    raise ValueError(f"步骤配置文件格式错误: {steps_path}")
                
                # 直接使用通用多应用执行器，不需要单独的游戏类
                game_executor = MultiAppBase(game_config, global_config=config.get("global"))
                game_executor.task_steps = task_steps
                result = game_executor.run()
                
                # 任务完成后自动关闭游戏（如果配置了auto_close）
                if game_config.get("auto_close", True):
                    logger.info(f"自动关闭{game_name}所有应用")
                    for app_key in game_config.get("apps", {}).keys():
                        try:
                            game_executor.close_app(app_key, force=True)
                        except Exception as e:
                            logger.warning(f"关闭应用[{app_key}]失败: {str(e)}")
                
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
        
        # 自动关机（按需导入）
        if config.get("global.auto_shutdown"):
            from src.core import shutdown
            logger.info("任务完成，即将自动关机")
            if notifier:
                notifier.send_message("🔌 任务完成，即将自动关机")
            shutdown(delay=60)
    finally:
        # 无论任务是否成功、是否出错，都全局恢复音量
        unmute_system_volume()


if __name__ == "__main__":
    # 创建日志目录
    os.makedirs("logs", exist_ok=True)
    main()
