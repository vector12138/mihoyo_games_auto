# 米哈游游戏自动化工具

全新重构版本，去除了远程唤醒和AutoHotkey脚本，全Python实现，基于BitBlt高速截图 + PaddleOCR文本识别，框架化设计，添加新游戏只需要配置按钮文本和操作步骤即可。

## ✨ 特性
- 🚀 **高速截图**：基于Windows BitBlt API实现，比传统截图快10倍以上
- 🔍 **精准识别**：百度PaddleOCR中文识别准确率99%+，支持模糊匹配
- 🎮 **框架化设计**：新增游戏只需要继承基类，配置按钮和步骤，无需修改核心代码
- ⌨️ **纯Python控制**：去除AutoHotkey依赖，全Python实现鼠标键盘控制
- 📱 **通知支持**：Telegram消息推送任务状态
- 🔄 **重试机制**：失败自动重试，提高成功率
- ⚡ **GPU加速**：支持GPU加速OCR识别，速度更快

## 📦 安装依赖
```bash
# 安装基础依赖
pip install -r requirements.txt

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
2. 继承`GameBase`类
3. 配置`self.buttons`按钮文本
4. 配置`self.steps`操作步骤
5. 实现自定义方法（可选）
6. 在`config.example.yaml`添加对应游戏配置
7. 在`main.py`导入并添加到执行列表

### 示例：
```python
from game_base import GameBase

class StarRail(GameBase):
    def __init__(self, config):
        super().__init__(config)
        self.buttons = {
            'login': '登录',
            'enter': '进入游戏'
        }
        self.steps = [
            {'type': 'click', 'text': self.buttons['login']},
            {'type': 'click', 'text': self.buttons['enter']}
        ]
```

## ⚠️ 注意事项
1. 仅支持Windows系统（BitBlt是Windows专属API）
2. 游戏分辨率推荐设置为1920x1080，识别准确率最高
3. 游戏建议设置为窗口模式或者全屏无边框模式
4. 运行时不要遮挡游戏窗口
5. 本工具仅用于学习交流，请勿用于违规用途，使用风险自负

## 📁 项目结构
```
mihoyo_games_auto/
├── games/                  # 各个游戏实现目录
│   ├── genshin.py          # 原神实现
│   └── zzz.py              # 绝区零实现
├── screen_capture.py       # BitBlt截图模块
├── ocr_recognizer.py       # PaddleOCR识别模块
├── input_controller.py     # 鼠标键盘控制模块
├── game_base.py            # 游戏基类（核心框架）
├── config.py               # 配置管理
├── main.py                 # 主入口
├── retry_manager.py        # 重试管理器
├── telegram_notifier.py    # Telegram通知模块
├── shutdown.py             # 关机模块
├── requirements.txt        # 依赖列表
├── config.example.yaml     # 示例配置文件
└── logs/                   # 日志目录
```
