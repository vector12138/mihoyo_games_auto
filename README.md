# 米哈游游戏自动化工具

全新重构版本，去除了远程唤醒和AutoHotkey脚本，全Python实现，基于BitBlt高速截图 + PaddleOCR文本识别，框架化设计，添加新游戏只需要配置按钮文本和操作步骤即可。

## ✨ 特性
- 🚀 **高速截图**：基于Windows BitBlt API实现，比传统截图快10倍以上
- 🔍 **精准识别**：百度PaddleOCR中文识别准确率99%+，支持模糊匹配
- 🎮 **配置化设计**：新增游戏完全不需要写代码，只需编写YAML步骤配置文件即可
- ⌨️ **纯Python控制**：去除AutoHotkey依赖，全Python实现鼠标键盘控制
- 📱 **通知支持**：Telegram消息推送任务状态和执行结果，支持远程控制
- 🔄 **重试机制**：失败自动重试，支持单步骤自定义重试次数和超时时间
- ⚡ **GPU加速**：支持GPU加速OCR识别，速度更快
- 🌐 **远程WOL唤醒支持**：支持远程唤醒Windows设备执行任务，完成后自动关机
- 🛡️ **灵活的流程控制**：支持步骤失败后自定义动作（继续/终止流程），支持强制步骤
- 🧠 **智能任务调度**：自动跳过今日已执行的任务，无任务时不做任何额外操作（不静音、不发通知）
- 🔧 **多种WOL检测模式**：支持自动检测、强制WOL、强制本地三种模式，适配各种场景

## 📦 安装依赖
```bash
# 安装基础依赖
pip install -r requirements.txt
pip install paddlepaddle-gpu==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cu126/

# （可选）如果需要GPU加速，先安装CUDA版本的paddlepaddle
# 参考：https://www.paddlepaddle.org.cn/install/quick
```

## 🛠️ 配置
1. 复制配置文件：
```bash
cp config.example.yaml config.yaml
```
2. 编辑`config.yaml`，根据你的实际情况修改配置：
   - 配置游戏路径
   - 配置Telegram通知（可选）
   - 启用/禁用对应游戏

## 🎮 支持的游戏
| 游戏名称 | 配置key | 状态 |
|---------|---------|------|
| 原神 | genshin | ✅ 已支持 |
| 绝区零 | zzz | ✅ 已支持 |
| 崩坏：星穹铁道 | hsr | 待添加 |
| 崩坏3 | honkai3 | 待添加 |

## 🚀 运行
```bash
python main.py
```

## 🎯 新增游戏教程
1. 在`games/`目录下新建游戏文件，比如`hsr.py`
2. 继承`MultiAppBase`类
3. 配置`self.buttons`按钮文本
4. 配置`self.task_steps`操作步骤
5. 实现自定义方法（可选）
6. 在`config.example.yaml`添加对应游戏配置
7. 在`main.py`导入并添加到执行列表

### 示例：
```python
from src.core import MultiAppBase

class StarRail(MultiAppBase):
    def __init__(self, config, global_config=None):
        super().__init__(config)
        self.buttons = {
            'login': '登录',
            'enter': '进入游戏'
        }
        self.task_steps = [
            {'type': 'click', 'text': self.buttons['login']},
            {'type': 'click', 'text': self.buttons['enter']}
        ]
```

## ⚠️ 注意事项
1. 仅支持Windows系统（BitBlt是Windows专属API）
2. 游戏分辨率推荐设置为1920x1080，识别准确率最高
3. 游戏建议设置为窗口模式或者全屏无边框模式
4. 运行时不要遮挡游戏窗口
5. 支持 Python 3.9+ 版本（已修复类型注解兼容性）

## 📜 免责声明
本项目由 **OpenClaw AI 助手** 自动生成，仅用于技术学习、测试和交流用途：
- 禁止用于违反任何游戏用户协议、服务条款或相关法律法规的用途
- 使用者对使用本工具产生的所有后果自行承担全部责任
- 开发者、AI生成方不承担任何直接、间接、附带或衍生的损失和责任
- 下载、复制、使用本项目即表示您同意本免责声明的全部内容

## 📚 详细文档
完整的项目文档已创建在 `docs/` 目录中，包含：

### 项目概述
- 📖 [项目简介](docs/01-项目概述/01-项目简介.md) - 项目目标和特性
- ✨ [功能特性](docs/01-项目概述/02-功能特性.md) - 详细功能说明
- 🏗️ [架构设计](docs/01-项目概述/03-架构设计.md) - 系统架构和模块设计
- 💻 [平台支持](docs/01-项目概述/04-平台支持说明.md) - Windows专用说明

### 快速开始
- ⚙️ [环境要求](docs/02-快速开始/01-环境要求.md) - 系统要求和依赖
- 🚀 [安装指南](docs/02-快速开始/02-安装指南.md) - 详细安装步骤
- 📦 [依赖说明](docs/02-快速开始/03-依赖说明.md) - 依赖包详细说明

### 使用指南
- 🔌 [代理使用指南](docs/03-使用指南/01-代理使用指南.md) - Telegram代理配置

### 开发文档
- 🔧 [优化总结](docs/04-开发文档/01-优化总结.md) - 项目优化记录
- 🐛 [Bug修复总结](docs/04-开发文档/02-Bug修复总结.md) - 问题修复记录

## 📁 项目结构
```
mihoyo_games_auto/
├── docs/                   # 📚 详细文档目录
│   ├── 01-项目概述/        # 项目介绍和架构
│   │   ├── 01-项目简介.md
│   │   ├── 02-功能特性.md
│   │   ├── 03-架构设计.md
│   │   └── 04-平台支持说明.md
│   ├── 02-快速开始/        # 安装和配置指南
│   │   ├── 01-环境要求.md
│   │   ├── 02-安装指南.md
│   │   └── 03-依赖说明.md
│   ├── 03-使用指南/        # 使用教程
│   │   └── 01-代理使用指南.md
│   └── 04-开发文档/        # 开发相关文档
│       ├── 01-优化总结.md
│       └── 02-Bug修复总结.md
├── games/                  # 🎮 各个游戏实现目录
│   ├── genshin.py          # 原神实现
│   └── zzz.py              # 绝区零实现
├── src/                    # 🧱 核心源码目录
│   ├── core/               # 核心组件
│   │   ├── game_base.py    # 游戏基类 + 多应用基类
│   │   ├── screen_capture.py # BitBlt截图模块
│   │   ├── ocr_recognizer.py # PaddleOCR识别模块
│   │   ├── input_controller.py # 鼠标键盘控制模块
│   │   ├── retry_manager.py # 重试管理器
│   │   └── shutdown.py     # 关机模块
│   ├── config/             # 配置管理
│   │   ├── config.py       # 配置加载
│   │   └── logging_config.py # 日志配置
│   └── utils/              # 工具模块
│       └── telegram_notifier.py # Telegram通知模块
├── main.py                 # 🚀 主入口
├── requirements.txt        # 📦 依赖列表
├── config.example.yaml     # 📄 示例配置文件
└── logs/                   # 📝 日志目录
```
