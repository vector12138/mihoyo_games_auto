# 米哈游游戏自动化工程 (mihoyo_games_auto)

自动化执行原神和绝区零的日常任务，支持远程唤醒、自动登录、任务执行和自动关机。

## 功能概述

### 核心功能
1. **远程唤醒**：通过WOL（Wake-on-LAN）远程唤醒电脑
2. **自动登录**：系统就绪后自动登录（可选）
3. **原神自动化**：
   - 打开bettergi程序
   - 点击启动原神
   - 等待游戏进入界面
   - 执行"一条龙"日常任务
   - 关闭bettergi
4. **绝区零自动化**：
   - 启动绝区零游戏
   - 等待游戏进入界面
   - 执行"一条龙"日常任务
5. **自动关机**：所有任务完成后自动关闭电脑

### 增强功能
6. **Telegram通知**：实时发送任务状态到Telegram
7. **图像识别**：使用OpenCV进行游戏界面识别和状态检测
8. **错误重试**：智能重试机制，支持指数退避
9. **详细报告**：生成执行报告和错误截图

## 系统要求

- **操作系统**：Windows 10/11（推荐）
- **网络**：支持WOL的主板和网络配置
- **软件依赖**：
  - Python 3.8+
  - bettergi（原神启动器）
  - 原神游戏客户端
  - 绝区零游戏客户端
  - AutoHotkey（用于Windows自动化）

## 工程结构

```
mihoyo_games_auto/
├── README.md                 # 说明文档
├── config.json               # 配置文件
├── wol_wake.py              # WOL唤醒脚本
├── check_system_ready.py    # 系统就绪检查
├── auto_login.py            # 自动登录脚本（可选）
├── genshin_automation.ahk   # 原神自动化脚本（AutoHotkey）
├── zzz_automation.ahk       # 绝区零自动化脚本（AutoHotkey）
├── main_controller.py       # 主控制脚本（基础版）
├── main_controller_enhanced.py # 主控制脚本（增强版）
├── telegram_notifier.py     # Telegram通知模块
├── image_recognizer.py      # 图像识别模块
├── retry_manager.py         # 重试管理模块
├── shutdown.py              # 关机脚本
├── logs/                    # 日志目录
│   ├── automation.log       # 运行日志
│   ├── screenshots/         # 错误截图
│   └── execution_reports/   # 执行报告
└── templates/               # 图像模板目录（用于图像识别）
```

## 快速开始

### 1. 配置WOL
- 在主板BIOS中启用Wake-on-LAN
- 在Windows网络适配器中启用"魔术包唤醒"
- 获取电脑的MAC地址和IP地址

### 2. 编辑配置文件
复制 `config.example.json` 为 `config.json` 并填写你的配置：
```json
{
  "wol": {
    "mac_address": "XX:XX:XX:XX:XX:XX",
    "ip_address": "192.168.1.100",
    "broadcast_address": "192.168.1.255"
  },
  "paths": {
    "bettergi": "C:\\Program Files\\BetterGI\\bettergi.exe",
    "genshin": "C:\\Program Files\\Genshin Impact\\Genshin Impact Game\\YuanShen.exe",
    "zzz": "C:\\Program Files\\Zenless Zone Zero\\Game\\ZenlessZoneZero.exe"
  },
  "timing": {
    "wake_wait_seconds": 60,
    "login_wait_seconds": 30,
    "genshin_launch_wait_seconds": 120,
    "zzz_launch_wait_seconds": 90,
    "task_wait_minutes": 30
  },
  "automation": {
    "use_auto_login": false,
    "username": "",
    "password": ""
  }
}
```

### 3. 安装依赖
```bash
pip install wakeonlan psutil pyautogui
```

### 4. 运行自动化
```bash
python main_controller.py
```

## 详细说明

### WOL唤醒
使用 `wol_wake.py` 发送魔术包唤醒电脑。需要配置正确的MAC地址和广播地址。

### 系统就绪检查
`check_system_ready.py` 会检查：
- 网络连接
- 系统启动完成
- 关键服务运行状态

### 自动登录（可选）
如果启用自动登录，`auto_login.py` 会模拟键盘输入用户名和密码。
**注意**：密码以明文存储，建议仅在安全环境下使用。

### 游戏自动化
使用AutoHotkey脚本控制游戏：
- `genshin_automation.ahk`：控制bettergi和原神
- `zzz_automation.ahk`：控制绝区零

自动化脚本会：
1. 启动游戏程序
2. 等待游戏加载
3. 执行预设的日常任务序列
4. 关闭游戏

### 主控制器
`main_controller.py` 协调整个流程：
1. 唤醒电脑
2. 等待系统就绪
3. 自动登录（如果启用）
4. 执行原神自动化
5. 执行绝区零自动化
6. 关机

## 安全注意事项

1. **密码安全**：不建议在配置文件中存储明文密码
2. **网络安全**：确保WOL仅在可信网络中使用
3. **游戏安全**：遵守游戏服务条款，避免使用违规自动化

## 故障排除

### WOL不工作
- 检查BIOS设置
- 检查网络适配器电源管理设置
- 确认防火墙未阻止魔术包

### 自动化失败
- 检查游戏窗口标题是否正确
- 调整等待时间参数
- 查看日志文件中的错误信息

### 关机失败
- 检查是否有未保存的工作
- 确认用户有关机权限

## 扩展功能

- 添加邮件/Telegram通知
- 支持多账号切换
- 添加错误重试机制
- 集成到OpenClaw定时任务

## 许可证

仅供个人学习使用，请遵守游戏服务条款。