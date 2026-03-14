# 依赖包说明

## 核心依赖

### 1. OCR 相关
- **paddlepaddle>=2.6.0** - 百度飞桨深度学习框架
- **paddleocr>=2.7.3** - PaddleOCR 文字识别库
- **shapely>=2.0.0** - 几何图形处理库
- **pyclipper>=1.3.0** - 多边形裁剪库

### 2. Windows API 相关
- **pywin32>=306** - Windows API 接口
  - 包含 `win32gui`、`win32ui`、`win32api` 等模块
  - 用于窗口捕获、鼠标键盘模拟等

### 3. 自动化控制
- **pyautogui>=0.9.54** - 自动点击、键盘输入
- **pynput>=1.7.6** - 键盘鼠标监听和控制

### 4. 图像处理
- **opencv-python>=4.8.0** - OpenCV 计算机视觉库
- **pillow>=10.0.0** - Python 图像处理库
- **numpy>=1.24.0** - 数值计算库

### 5. 系统工具
- **psutil>=5.9.0** - 系统进程和资源监控

### 6. 通知和配置
- **python-telegram-bot>=20.0** - Telegram 机器人通知
- **pyyaml>=6.0** - YAML 配置文件解析
- **loguru>=0.7.0** - 日志记录库

## 安装说明

### 基本安装
```bash
pip install -r requirements.txt
```

### Windows 特定依赖
在 Windows 系统上，还需要确保：
1. 安装 Visual C++ Redistributable
2. 对于 `pywin32`，可能需要以管理员权限运行：
   ```bash
   pip install pywin32
   ```

### 可选依赖
- **CUDA 支持**：如需 GPU 加速，安装 CUDA 版本的 paddlepaddle
- **中文支持**：确保系统字体包含中文字体，用于 OCR 识别

## 常见问题

### 1. 编码问题
如果遇到编码错误，请确保：
- 使用 UTF-8 编码
- 在 Windows 上设置正确的代码页：`chcp 65001`

### 2. 权限问题
- `pywin32` 可能需要管理员权限
- 游戏自动化需要以管理员身份运行脚本

### 3. 版本兼容性
- Python 3.9+ 推荐
- Windows 10/11 系统

## 开发环境
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```