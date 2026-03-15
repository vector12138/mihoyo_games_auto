# MultiAppBase 基类API参考

## 概述
MultiAppBase是所有游戏自动化脚本的基类，提供了应用管理、屏幕操作、OCR识别、Win32消息发送等核心功能。本文档记录最新新增的Win32消息/控件操作相关API。

---

## 一、Win32消息发送API（应用级）

### 1. send_app_message
给指定应用发送Win32 API消息
```python
def send_app_message(self, msg: int, wparam: int = 0, lparam: int = 0, 
                    app_name: Optional[str] = None, use_post: bool = False) -> bool:
```
| 参数 | 类型 | 说明 |
|------|------|------|
| msg | int | 消息类型，如`win32con.WM_CLOSE`/`WM_KEYDOWN`等 |
| wparam | int | WPARAM参数，默认0 |
| lparam | int | LPARAM参数，默认0 |
| app_name | str | 应用名称，不传则使用当前活跃应用 |
| use_post | bool | 是否使用PostMessage（异步，不等待返回），默认SendMessage（同步） |
| **返回值** | bool | 是否发送成功 |

### 2. send_app_key
给应用发送键盘按键消息
```python
def send_app_key(self, key_code: int, app_name: Optional[str] = None, press: bool = True) -> bool:
```
| 参数 | 类型 | 说明 |
|------|------|------|
| key_code | int | 按键码，如`win32con.VK_RETURN`/`VK_SPACE`等 |
| app_name | str | 应用名称，不传则使用当前活跃应用 |
| press | bool | True为按下（WM_KEYDOWN），False为松开（WM_KEYUP），默认True |
| **返回值** | bool | 是否发送成功 |

### 3. close_app_by_message
通过发送WM_CLOSE消息关闭应用（比原关闭方法更稳定）
```python
def close_app_by_message(self, app_name: Optional[str] = None, force: bool = False) -> bool:
```
| 参数 | 类型 | 说明 |
|------|------|------|
| app_name | str | 应用名称，不传则使用当前活跃应用 |
| force | bool | 是否强制关闭（发送WM_DESTROY），默认False |
| **返回值** | bool | 是否发送成功 |

---

## 二、控件操作API（控件级）

### 1. find_child_control
查找应用内的子控件句柄
```python
def find_child_control(self, app_name: Optional[str] = None, 
                      class_name: Optional[str] = None, 
                      window_title: Optional[str] = None,
                      control_id: Optional[int] = None) -> Optional[int]:
```
| 参数 | 类型 | 说明 |
|------|------|------|
| app_name | str | 应用名称，不传则使用当前活跃应用 |
| class_name | str | 控件类名（如"Edit"、"Button"） |
| window_title | str | 控件标题/文本 |
| control_id | int | 控件ID（可通过Spy++等工具获取） |
| **返回值** | int/None | 找到的控件句柄，找不到返回None |

### 2. send_control_message
给指定控件发送Win32消息
```python
def send_control_message(self, control_hwnd: int, msg: int, 
                       wparam: int = 0, lparam: int = 0, 
                       use_post: bool = False) -> bool:
```
| 参数 | 类型 | 说明 |
|------|------|------|
| control_hwnd | int | 控件句柄（通过find_child_control获取） |
| msg | int | 消息类型 |
| wparam | int | WPARAM参数，默认0 |
| lparam | int | LPARAM参数，默认0 |
| use_post | bool | 是否使用PostMessage异步发送，默认False |
| **返回值** | bool | 是否发送成功 |

### 3. set_control_text
设置输入框/文本控件的内容
```python
def set_control_text(self, control_hwnd: int, text: str) -> bool:
```
| 参数 | 类型 | 说明 |
|------|------|------|
| control_hwnd | int | 控件句柄 |
| text | str | 要设置的文本 |
| **返回值** | bool | 是否设置成功 |

### 4. click_control
点击按钮控件
```python
def click_control(self, control_hwnd: int) -> bool:
```
| 参数 | 类型 | 说明 |
|------|------|------|
| control_hwnd | int | 按钮控件句柄 |
| **返回值** | bool | 是否点击成功 |

---

## 三、步骤配置支持
在`task_steps`中可直接使用以下新增步骤类型，无需编写代码：

| 步骤类型 | 功能 | 配置参数 |
|----------|------|----------|
| `send_app_message` | 给应用发Win32消息 | msg, wparam(可选), lparam(可选), app_name(可选), use_post(可选) |
| `send_app_key` | 给应用发按键 | key_code, app_name(可选), press(可选) |
| `find_control` | 查找应用内控件 | app_name(可选), class_name(可选), window_title(可选), control_id(可选) |
| `send_control_message` | 给控件发消息 | msg, wparam(可选), lparam(可选), use_post(可选), control_hwnd(可选，默认使用上一步结果) |
| `set_control_text` | 设置控件文本 | text, control_hwnd(可选，默认使用上一步结果) |
| `click_control` | 点击控件 | control_hwnd(可选，默认使用上一步结果) |

### 配置示例（自动登录场景）
```python
self.task_steps = [
    {"type": "launch_app", "app_name": "genshin", "name": "启动原神"},
    # 查找账号输入框（控件ID=1001）
    {"type": "find_control", "control_id": 1001, "name": "查找账号输入框"},
    # 输入账号（自动使用上一步找到的控件句柄）
    {"type": "set_control_text", "text": "123456789", "name": "输入账号"},
    # 查找密码输入框
    {"type": "find_control", "class_name": "Edit", "control_id": 1002, "name": "查找密码输入框"},
    {"type": "set_control_text", "text": "password123", "name": "输入密码"},
    # 查找登录按钮
    {"type": "find_control", "window_title": "登录", "name": "查找登录按钮"},
    {"type": "click_control", "name": "点击登录"},
    # 给应用发送回车键确认
    {"type": "send_app_key", "key_code": win32con.VK_RETURN, "name": "按回车确认"}
]
```

---

## 四、代码示例
```python
from src.core.game_base import MultiAppBase
import win32con

class ExampleAutomation(MultiAppBase):
    def __init__(self, config, global_config):
        super().__init__(config, global_config)
        self.task_steps = [
            {"type": "launch_app", "app_name": "notepad", "name": "启动记事本"},
            # 查找记事本编辑框
            {"type": "find_control", "class_name": "Edit", "name": "查找编辑框"},
            # 输入文本
            {"type": "set_control_text", "text": "Hello World!", "name": "输入文本"},
            # 发送Ctrl+S保存
            {"type": "send_app_key", "key_code": ord('S'), "name": "保存文件"},
        ]

if __name__ == '__main__':
    # 加载配置并运行
    ...
```
