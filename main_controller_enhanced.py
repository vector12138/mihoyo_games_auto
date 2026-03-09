#!/usr/bin/env python3
"""
米哈游游戏自动化主控制器 v2
集成Telegram通知、图像识别和错误重试
"""

import os
import sys
import time
import json
import subprocess
import logging
import traceback
from pathlib import Path
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(str(Path(__file__).parent))

# 导入新模块
try:
    from telegram_notifier import TelegramNotifier
    from image_recognizer import ImageRecognizer
    from retry_manager import RetryManager, with_retry
    NEW_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  部分模块导入失败: {e}")
    NEW_MODULES_AVAILABLE = False

class EnhancedGameAutomationController:
    """增强版游戏自动化控制器"""
    
    def __init__(self, config_path=None):
        """初始化控制器"""
        self.script_dir = Path(__file__).parent
        self.config = self.load_config(config_path)
        self.setup_logging()
        self.setup_modules()
        
    def load_config(self, config_path=None):
        """加载配置文件"""
        if config_path is None:
            config_path = self.script_dir / 'config.json'
            if not config_path.exists():
                config_path = self.script_dir / 'config.example.json'
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return None
    
    def setup_logging(self):
        """设置日志"""
        log_config = self.config.get('logging', {})
        log_level = log_config.get('level', 'INFO')
        log_file = log_config.get('file', 'logs/automation.log')
        
        # 创建日志目录
        log_path = self.script_dir / log_file
        log_path.parent.mkdir(exist_ok=True)
        
        # 配置日志
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('GameAutomation')
    
    def setup_modules(self):
        """设置各个功能模块"""
        # Telegram通知
        telegram_config = self.config.get('telegram', {})
        self.telegram = TelegramNotifier(telegram_config) if NEW_MODULES_AVAILABLE else None
        
        # 图像识别
        image_config = self.config.get('image_recognition', {})
        self.image_recognizer = ImageRecognizer(image_config) if NEW_MODULES_AVAILABLE else None
        
        # 重试管理器
        retry_config = self.config.get('retry', {})
        self.retry_manager = RetryManager(retry_config) if NEW_MODULES_AVAILABLE else None
        
        self.logger.info("功能模块初始化完成")
    
    def send_notification(self, message_type, **kwargs):
        """发送通知（统一接口）"""
        if not self.telegram or not self.telegram.enabled:
            return False
        
        try:
            if message_type == 'task_start':
                return self.telegram.notify_task_start(kwargs.get('task_name'))
            elif message_type == 'task_complete':
                return self.telegram.notify_task_complete(
                    kwargs.get('task_name'),
                    kwargs.get('duration', 0),
                    kwargs.get('success', True)
                )
            elif message_type == 'task_error':
                return self.telegram.notify_task_error(
                    kwargs.get('task_name'),
                    kwargs.get('error_message', '未知错误'),
                    kwargs.get('screenshot_path')
                )
            elif message_type == 'system_status':
                return self.telegram.notify_system_status(
                    kwargs.get('status'),
                    kwargs.get('details', '')
                )
            elif message_type == 'daily_report':
                return self.telegram.notify_daily_report(kwargs.get('report_data'))
            else:
                self.logger.warning(f"未知的通知类型: {message_type}")
                return False
        except Exception as e:
            self.logger.error(f"发送通知失败: {e}")
            return False
    
    def capture_error_screenshot(self, task_name):
        """捕获错误截图"""
        if not self.image_recognizer or not self.image_recognizer.enabled:
            return None
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_path = self.script_dir / 'logs' / 'screenshots' / f"error_{task_name}_{timestamp}.png"
            screenshot_path.parent.mkdir(exist_ok=True)
            
            self.image_recognizer.capture_screen(save_path=str(screenshot_path))
            self.logger.info(f"错误截图已保存: {screenshot_path}")
            
            return str(screenshot_path)
        except Exception as e:
            self.logger.error(f"捕获截图失败: {e}")
            return None
    
    @with_retry
    def run_command_with_retry(self, command, timeout=None, task_name="命令执行"):
        """带重试的命令执行"""
        try:
            self.logger.info(f"执行命令: {command}")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                self.logger.info(f"命令执行成功: {task_name}")
                if result.stdout.strip():
                    self.logger.debug(f"输出: {result.stdout.strip()}")
                return True
            else:
                error_msg = result.stderr.strip() or f"退出码: {result.returncode}"
                raise Exception(f"{task_name}失败: {error_msg}")
                
        except subprocess.TimeoutExpired:
            raise Exception(f"{task_name}超时")
        except Exception as e:
            raise Exception(f"{task_name}异常: {e}")
    
    def wake_computer(self):
        """唤醒电脑（带重试和通知）"""
        task_name = "远程唤醒"
        self.send_notification('task_start', task_name=task_name)
        
        try:
            wol_script = self.script_dir / 'wol_wake.py'
            if not wol_script.exists():
                raise Exception("WOL唤醒脚本不存在")
            
            success = self.run_command_with_retry(
                f'python "{wol_script}"',
                task_name=task_name
            )
            
            if success:
                self.send_notification('task_complete', 
                                     task_name=task_name, 
                                     duration=0, 
                                     success=True)
            return success
            
        except Exception as e:
            self.logger.error(f"{task_name}失败: {e}")
            screenshot_path = self.capture_error_screenshot(task_name)
            self.send_notification('task_error', 
                                 task_name=task_name, 
                                 error_message=str(e),
                                 screenshot_path=screenshot_path)
            raise
    
    def check_system_ready(self):
        """检查系统就绪（带重试和通知）"""
        task_name = "系统就绪检查"
        self.send_notification('task_start', task_name=task_name)
        
        try:
            check_script = self.script_dir / 'check_system_ready.py'
            if not check_script.exists():
                raise Exception("系统检查脚本不存在")
            
            # 获取等待时间配置
            wake_wait = self.config.get('timing', {}).get('wake_wait_seconds', 60)
            timeout = wake_wait + 300  # 额外5分钟
            
            start_time = time.time()
            success = self.run_command_with_retry(
                f'python "{check_script}"',
                timeout=timeout,
                task_name=task_name
            )
            duration = time.time() - start_time
            
            if success:
                self.send_notification('task_complete', 
                                     task_name=task_name, 
                                     duration=duration, 
                                     success=True)
            return success
            
        except Exception as e:
            self.logger.error(f"{task_name}失败: {e}")
            screenshot_path = self.capture_error_screenshot(task_name)
            self.send_notification('task_error', 
                                 task_name=task_name, 
                                 error_message=str(e),
                                 screenshot_path=screenshot_path)
            raise
    
    def run_genshin_automation(self):
        """运行原神自动化（带重试和通知）"""
        task_name = "原神自动化"
        self.send_notification('task_start', task_name=task_name)
        
        try:
            # 获取AutoHotkey路径
            paths_config = self.config.get('paths', {})
            ahk_path = paths_config.get('autohotkey')
            if not ahk_path or not Path(ahk_path).exists():
                raise Exception(f"AutoHotkey路径不存在: {ahk_path}")
            
            # 原神自动化脚本
            genshin_script = self.script_dir / 'genshin_automation.ahk'
            if not genshin_script.exists():
                raise Exception("原神自动化脚本不存在")
            
            # 获取等待时间
            timing_config = self.config.get('timing', {})
            launch_wait = timing_config.get('genshin_launch_wait_seconds', 120)
            task_wait = timing_config.get('genshin_task_wait_minutes', 15)
            
            timeout = launch_wait + (task_wait * 60) + 300  # 额外5分钟
            
            start_time = time.time()
            command = f'"{ahk_path}" "{genshin_script}" run'
            success = self.run_command_with_retry(
                command,
                timeout=timeout,
                task_name=task_name
            )
            duration = time.time() - start_time
            
            if success:
                self.send_notification('task_complete', 
                                     task_name=task_name, 
                                     duration=duration, 
                                     success=True)
            return success
            
        except Exception as e:
            self.logger.error(f"{task_name}失败: {e}")
            screenshot_path = self.capture_error_screenshot(task_name)
            self.send_notification('task_error', 
                                 task_name=task_name, 
                                 error_message=str(e),
                                 screenshot_path=screenshot_path)
            raise
    
    def run_zzz_automation(self):
        """运行绝区零自动化（带重试和通知）"""
        task_name = "绝区零自动化"
        self.send_notification('task_start', task_name=task_name)
        
        try:
            # 获取AutoHotkey路径
            paths_config = self.config.get('paths', {})
            ahk_path = paths_config.get('autohotkey')
            if not ahk_path or not Path(ahk_path).exists():
                raise Exception(f"AutoHotkey路径不存在: {ahk_path}")
            
            # 绝区零自动化脚本
            zzz_script = self.script_dir / 'zzz_automation.ahk'
            if not zzz_script.exists():
                raise Exception("绝区零自动化脚本不存在")
            
            # 获取等待时间
            timing_config = self.config.get('timing', {})
            launch_wait = timing_config.get('zzz_launch_wait_seconds', 90)
            task_wait = timing_config.get('zzz_task_wait_minutes', 15)
            
            timeout = launch_wait + (task_wait * 60) + 300  # 额外5分钟
            
            start_time = time.time()
            command = f'"{ahk_path}" "{zzz_script}" run'
            success = self.run_command_with_retry(
                command,
                timeout=timeout,
                task_name=task_name
            )
            duration = time.time() - start_time
            
            if success:
                self.send_notification('task_complete', 
                                     task_name=task_name, 
                                     duration=duration, 
                                     success=True)
            return success
            
        except Exception as e:
            self.logger.error(f"{task_name}失败: {e}")
            screenshot_path = self.capture_error_screenshot(task_name)
            self.send_notification('task_error', 
                                 task_name=task_name, 
                                 error_message=str(e),
                                 screenshot_path=screenshot_path)
            raise
    
    def shutdown_computer(self):
        """关闭电脑（带重试和通知）"""
        task_name = "关闭电脑"
        self.send_notification('task_start', task_name=task_name)
        
        try:
            shutdown_script = self.script_dir / 'shutdown.py'
            if not shutdown_script.exists():
                raise Exception("关机脚本不存在")
            
            start_time = time.time()
            success = self.run_command_with_retry(
                f'python "{shutdown_script}"',
                task_name=task_name
            )
            duration = time.time() - start_time
            
            if success:
                self.send_notification('task_complete', 
                                     task_name=task_name, 
                                     duration=duration, 
                                     success=True)
            return success
            
        except Exception as e:
            self.logger.error(f"{task_name}失败: {e}")
            screenshot_path = self.capture_error_screenshot(task_name)
            self.send_notification('task_error', 
                                 task_name=task_name, 
                                 error_message=str(e),
                                 screenshot_path=screenshot_path)
            raise
    
    def run_full_automation(self):
        """运行完整的自动化流程"""
        self.logger.info("=" * 50)
        self.logger.info("开始米哈游游戏自动化流程")
        self.logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 50)
        
        # 发送系统状态通知
        self.send_notification('system_status', 
                             status="开始执行",
                             details="米哈游游戏自动化流程启动")
        
        steps = [
            ("远程唤醒", self.wake_computer),
            ("系统就绪检查", self.check_system_ready),
            ("原神自动化", self.run_genshin_automation),
            ("绝区零自动化", self.run_zzz_automation),
            ("关闭电脑", self.shutdown_computer)
        ]
        
        results = []
        overall_success = True
        
        for step_name, step_func in steps:
            self.logger.info(f"\n▶️ 开始步骤: {step_name}")
            start_time = time.time()
            
            try:
                success = step_func()
                elapsed = time.time() - start_time
                
                if success:
                    self.logger.info(f"✅ 步骤完成: {step_name} (耗时: {elapsed:.1f}秒)")
                else:
                    self.logger.error(f"❌ 步骤失败: {step_name} (耗时: {elapsed:.1f}秒)")
                    overall_success = False
                
                results.append({
                    'task': step_name,
                    'success': success,
                    'duration': elapsed,
                    'timestamp': datetime.now().isoformat()
                })
                
                # 如果步骤失败，决定是否继续
                if not success:
                    if step_name in ["远程唤醒", "系统就绪检查"]:
                        self.logger.error("关键步骤失败，停止自动化")
                        break
                    else:
                        self.logger.warning("非关键步骤失败，继续执行")
                
                # 步骤间的冷却时间
                if step_name != "关闭电脑":
                    cooldown = self.config.get('timing', {}).get('cooldown_between_games_seconds', 30)
                    self.logger.info(f"⏳ 冷却 {cooldown} 秒...")
                    time.sleep(cooldown)
                    
            except Exception as e:
                elapsed = time.time() - start_time
                self.logger.error(f"❌ 步骤异常: {step_name} - {e}")
                self.logger.debug(traceback.format_exc())
                
                results.append({
                    'task': step_name,
                    'success': False,
                    'duration': elapsed,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
                
                overall_success = False
                
                if step_name in ["远程唤醒", "系统就绪检查"]:
                    self.logger.error("关键步骤异常，停止自动化")
                    break
        
        # 生成报告
        report_data = self.generate_report(results)
        
        # 发送每日报告
        self.send_notification('daily_report', report_data=report_data)
        
        # 发送最终状态
        final_status = "成功完成" if overall_success else "部分完成或失败"
        self.send_notification('system_status',
                             status=final_status,
                             details=f"成功率: {report_data.get('success_rate', 0):.1f}%")
        
        if overall_success:
            self.logger.info("🎉 自动化流程完成！")
        else:
            self.logger.warning("⚠️  自动化流程部分完成")
        
        return overall_success
    
    def generate_report(self, results):
        """生成执行报告"""
        total_time = sum(r.get('duration', 0) for r in results)
        success_count = sum(1 for r in results if r.get('success'))
        total_count = len(results)
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        report_data = {
            'total_time': total_time,
            'success_count': success_count,
            'total_count': total_count,
            'success_rate': success_rate,
            'details': results,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat()
        }
        
        # 保存报告到文件
        report_file = self.script_dir / 'logs' / 'execution_reports' / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f        self.logger.info(f"执行报告已保存: {report_file}")
        
        return report_data

def main():
    """主函数"""
    print("=" * 50)
    print("米哈游游戏自动化主控制器 v2")
    print("=" * 50)
    
    # 检查新模块
    if not NEW_MODULES_AVAILABLE:
        print("⚠️  部分新模块不可用，部分功能受限")
        print("请安装依赖: pip install opencv-python pillow pyautogui numpy requests")
    
    # 检查配置文件
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # 创建控制器
    controller = EnhancedGameAutomationController(config_path)
    if not controller.config:
        print("❌ 初始化失败，请检查配置文件")
        return 1
    
    # 运行自动化
    print("\n🚀 开始自动化流程...")
    success = controller.run_full_automation()
    
    if success:
        print("\n🎉 自动化流程成功完成！")
        return 0
    else:
        print("\n⚠️  自动化流程部分完成或失败")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)