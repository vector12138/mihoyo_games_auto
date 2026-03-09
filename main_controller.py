#!/usr/bin/env python3
"""
米哈游游戏自动化主控制器
协调WOL唤醒、系统检查、游戏自动化和关机
"""

import os
import sys
import time
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(str(Path(__file__).parent))

class GameAutomationController:
    """游戏自动化控制器"""
    
    def __init__(self, config_path=None):
        """初始化控制器"""
        self.script_dir = Path(__file__).parent
        self.config = self.load_config(config_path)
        self.setup_logging()
        
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
    
    def run_command(self, command, timeout=None):
        """运行命令并返回结果"""
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
                self.logger.info(f"命令执行成功")
                if result.stdout.strip():
                    self.logger.debug(f"输出: {result.stdout.strip()}")
            else:
                self.logger.error(f"命令执行失败: {result.stderr}")
            
            return result.returncode == 0
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"命令执行超时: {command}")
            return False
        except Exception as e:
            self.logger.error(f"执行命令异常: {e}")
            return False
    
    def wake_computer(self):
        """唤醒电脑"""
        self.logger.info("=== 步骤1: 远程唤醒电脑 ===")
        
        wol_script = self.script_dir / 'wol_wake.py'
        if not wol_script.exists():
            self.logger.error("WOL唤醒脚本不存在")
            return False
        
        return self.run_command(f'python "{wol_script}"')
    
    def check_system_ready(self):
        """检查系统就绪"""
        self.logger.info("=== 步骤2: 检查系统就绪 ===")
        
        check_script = self.script_dir / 'check_system_ready.py'
        if not check_script.exists():
            self.logger.error("系统检查脚本不存在")
            return False
        
        # 获取等待时间配置
        wake_wait = self.config.get('timing', {}).get('wake_wait_seconds', 60)
        timeout = wake_wait + 300  # 额外5分钟
        
        return self.run_command(f'python "{check_script}"', timeout=timeout)
    
    def auto_login(self):
        """自动登录（如果需要）"""
        automation_config = self.config.get('automation', {})
        use_auto_login = automation_config.get('use_auto_login', False)
        
        if not use_auto_login:
            self.logger.info("跳过自动登录（未启用）")
            return True
        
        self.logger.info("=== 步骤3: 自动登录 ===")
        
        login_script = self.script_dir / 'auto_login.py'
        if not login_script.exists():
            self.logger.error("自动登录脚本不存在")
            return False
        
        return self.run_command(f'python "{login_script}"')
    
    def run_genshin_automation(self):
        """运行原神自动化"""
        self.logger.info("=== 步骤4: 原神自动化 ===")
        
        # 获取AutoHotkey路径
        paths_config = self.config.get('paths', {})
        ahk_path = paths_config.get('autohotkey')
        if not ahk_path or not Path(ahk_path).exists():
            self.logger.error(f"AutoHotkey路径不存在: {ahk_path}")
            return False
        
        # 原神自动化脚本
        genshin_script = self.script_dir / 'genshin_automation.ahk'
        if not genshin_script.exists():
            self.logger.error("原神自动化脚本不存在")
            return False
        
        # 获取等待时间
        timing_config = self.config.get('timing', {})
        launch_wait = timing_config.get('genshin_launch_wait_seconds', 120)
        task_wait = timing_config.get('genshin_task_wait_minutes', 15)
        
        timeout = launch_wait + (task_wait * 60) + 300  # 额外5分钟
        
        command = f'"{ahk_path}" "{genshin_script}" run'
        return self.run_command(command, timeout=timeout)
    
    def run_zzz_automation(self):
        """运行绝区零自动化"""
        self.logger.info("=== 步骤5: 绝区零自动化 ===")
        
        # 获取AutoHotkey路径
        paths_config = self.config.get('paths', {})
        ahk_path = paths_config.get('autohotkey')
        if not ahk_path or not Path(ahk_path).exists():
            self.logger.error(f"AutoHotkey路径不存在: {ahk_path}")
            return False
        
        # 绝区零自动化脚本
        zzz_script = self.script_dir / 'zzz_automation.ahk'
        if not zzz_script.exists():
            self.logger.error("绝区零自动化脚本不存在")
            return False
        
        # 获取等待时间
        timing_config = self.config.get('timing', {})
        launch_wait = timing_config.get('zzz_launch_wait_seconds', 90)
        task_wait = timing_config.get('zzz_task_wait_minutes', 15)
        
        timeout = launch_wait + (task_wait * 60) + 300  # 额外5分钟
        
        command = f'"{ahk_path}" "{zzz_script}" run'
        return self.run_command(command, timeout=timeout)
    
    def shutdown_computer(self):
        """关闭电脑"""
        self.logger.info("=== 步骤6: 关闭电脑 ===")
        
        shutdown_script = self.script_dir / 'shutdown.py'
        if not shutdown_script.exists():
            self.logger.error("关机脚本不存在")
            return False
        
        return self.run_command(f'python "{shutdown_script}"')
    
    def run_full_automation(self):
        """运行完整的自动化流程"""
        self.logger.info("=" * 50)
        self.logger.info("开始米哈游游戏自动化流程")
        self.logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 50)
        
        steps = [
            ("远程唤醒", self.wake_computer),
            ("系统就绪检查", self.check_system_ready),
            ("自动登录", self.auto_login),
            ("原神自动化", self.run_genshin_automation),
            ("绝区零自动化", self.run_zzz_automation),
            ("关闭电脑", self.shutdown_computer)
        ]
        
        results = []
        
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
                
                results.append((step_name, success, elapsed))
                
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
                self.logger.error(f"❌ 步骤异常: {step_name} - {e}")
                results.append((step_name, False, time.time() - start_time))
                break
        
        # 生成报告
        self.generate_report(results)
        
        # 检查整体结果
        overall_success = all(success for _, success, _ in results if _ not in ["自动登录"])  # 自动登录可选
        
        if overall_success:
            self.logger.info("🎉 自动化流程完成！")
        else:
            self.logger.warning("⚠️  自动化流程部分完成")
        
        return overall_success
    
    def generate_report(self, results):
        """生成执行报告"""
        report_file = self.script_dir / 'logs' / 'execution_report.txt'
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 50 + "\n")
            f.write("米哈游游戏自动化执行报告\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            
            total_time = 0
            for step_name, success, elapsed in results:
                status = "✅ 成功" if success else "❌ 失败"
                f.write(f"{step_name}: {status} (耗时: {elapsed:.1f}秒)\n")
                total_time += elapsed
            
            f.write(f"\n总计耗时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)\n")
            
            success_count = sum(1 for _, success, _ in results if success)
            total_count = len(results)
            f.write(f"成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)\n")
        
        self.logger.info(f"执行报告已保存: {report_file}")

def main():
    """主函数"""
    print("=" * 50)
    print("米哈游游戏自动化主控制器")
    print("=" * 50)
    
    # 检查配置文件
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # 创建控制器
    controller = GameAutomationController(config_path)
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