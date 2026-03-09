; 绝区零自动化脚本 (AutoHotkey)
; 控制绝区零游戏，执行日常任务

#NoEnv
#SingleInstance Force
#Persistent
#WinActivateForce

SetTitleMatchMode, 2
SetControlDelay, -1
SetKeyDelay, 50, 50
SetMouseDelay, 50

; 配置变量
zzzTitle := "绝区零"
zzzWindowClass := "UnityWndClass"
timeoutSeconds := 300

; 日志函数
LogMessage(message) {
    FormatTime, currentTime,, yyyy-MM-dd HH:mm:ss
    FileAppend, [%currentTime%] %message%`n, logs/zzz_automation.log
    ToolTip, %message%
    Sleep, 1000
    ToolTip
}

; 等待窗口函数
WaitForWindow(windowTitle, windowClass := "", timeout := timeoutSeconds) {
    LogMessage("等待窗口: " . windowTitle)
    startTime := A_TickCount
    
    Loop {
        if (windowClass = "") {
            WinWait, %windowTitle%, , 1
        } else {
            WinWait, ahk_class %windowClass%, , 1
        }
        
        if (ErrorLevel = 0) {
            WinGet, windowId, ID, %windowTitle%
            if (windowId) {
                LogMessage("窗口找到: " . windowTitle)
                return windowId
            }
        }
        
        ; 检查超时
        if ((A_TickCount - startTime) > (timeout * 1000)) {
            LogMessage("等待窗口超时: " . windowTitle)
            return 0
        }
        
        Sleep, 1000
    }
}

; 启动绝区零
LaunchZZZ(zzzPath) {
    LogMessage("启动绝区零: " . zzzPath)
    
    ; 检查是否已运行
    IfWinExist, %zzzTitle%
    {
        LogMessage("绝区零 已在运行")
        WinActivate, %zzzTitle%
        return true
    }
    
    ; 启动绝区零
    try {
        Run, %zzzPath%
    } catch {
        LogMessage("启动绝区零失败")
        return false
    }
    
    ; 等待绝区零窗口
    windowId := WaitForWindow(zzzTitle, zzzWindowClass, 180)  ; 3分钟超时
    if (windowId = 0) {
        return false
    }
    
    WinActivate, ahk_id %windowId%
    Sleep, 5000  ; 等待游戏完全加载
    
    return true
}

; 等待绝区零进入游戏界面
WaitForZZZGame() {
    LogMessage("等待绝区零进入游戏界面...")
    
    ; 这里可以添加图像识别或颜色检查来确认游戏状态
    ; 暂时使用简单的等待
    
    Sleep, 20000  ; 等待20秒进入游戏
    
    ; 按ESC跳过可能的开场动画
    Send, {Esc}
    Sleep, 1000
    
    LogMessage("绝区零已进入游戏界面")
    return true
}

; 执行绝区零日常任务（一条龙）
ExecuteZZZDailyTasks() {
    LogMessage("开始执行绝区零日常任务...")
    
    ; 这里需要根据绝区零的日常任务流程编写具体的自动化步骤
    ; 以下是一个示例流程，需要根据实际情况调整
    
    ; 1. 打开日常任务界面（假设按J键）
    Send, {j}
    Sleep, 3000
    
    ; 2. 领取每日活跃奖励
    ; 假设领取按钮在屏幕特定位置
    Click, 1000, 600  ; 示例坐标，需要调整
    Sleep, 2000
    
    ; 3. 完成日常任务
    Loop, 5 {
        LogMessage("完成日常任务 " . A_Index . "/5")
        
        ; 点击"前往"按钮
        Click, 1200, 700  ; 示例坐标
        Sleep, 5000  ; 等待加载
        
        ; 自动战斗（按F键开始）
        Send, {f}
        Sleep, 20000  ; 等待战斗完成
        
        ; 返回任务界面
        Send, {j}
        Sleep, 3000
    }
    
    ; 4. 领取任务奖励
    Click, 1400, 800  ; 领取奖励按钮
    Sleep, 2000
    
    ; 5. 完成资源关卡
    LogMessage("完成资源关卡...")
    
    ; 打开关卡界面（假设按K键）
    Send, {k}
    Sleep, 3000
    
    ; 选择第一个资源关卡
    Click, 800, 400  ; 示例坐标
    Sleep, 2000
    
    ; 开始挑战
    Click, 1200, 800
    Sleep, 10000  ; 等待加载
    
    ; 自动战斗
    Send, {f}
    Sleep, 30000  ; 等待战斗完成
    
    ; 6. 完成其他日常（如派遣、商店等）
    LogMessage("完成其他日常...")
    
    LogMessage("绝区零日常任务完成")
    return true
}

; 关闭绝区零
CloseZZZ() {
    LogMessage("关闭绝区零")
    
    IfWinExist, ahk_class %zzzWindowClass%
    {
        ; 先按ESC打开菜单
        Send, {Esc}
        Sleep, 1000
        
        ; 点击设置按钮（假设在右上角）
        Click, 1850, 50  ; 示例坐标
        Sleep, 2000
        
        ; 点击退出游戏
        Click, 1600, 900  ; 退出按钮
        Sleep, 2000
        
        ; 确认退出
        Click, 960, 700  ; 确认按钮
        Sleep, 5000
        
        ; 检查是否已关闭
        IfWinNotExist, ahk_class %zzzWindowClass%
        {
            LogMessage("绝区零已关闭")
            return true
        }
        
        ; 强制关闭
        WinKill, ahk_class %zzzWindowClass%
        Sleep, 2000
        
        IfWinNotExist, ahk_class %zzzWindowClass%
        {
            LogMessage("绝区零已强制关闭")
            return true
        }
        
        LogMessage("关闭绝区零失败")
        return false
    }
    
    LogMessage("绝区零未运行")
    return true
}

; 主函数
Main() {
    LogMessage("=== 绝区零自动化开始 ===")
    
    ; 读取配置文件
    configFile := A_ScriptDir . "\config.json"
    if (!FileExist(configFile)) {
        configFile := A_ScriptDir . "\config.example.json"
    }
    
    ; 这里可以添加读取配置的代码
    ; 暂时使用硬编码路径
    zzzPath := "C:\Program Files\Zenless Zone Zero\Game\ZenlessZoneZero.exe"
    
    ; 1. 启动绝区零
    if (!LaunchZZZ(zzzPath)) {
        LogMessage("启动绝区零失败，退出")
        return false
    }
    
    ; 2. 等待进入游戏界面
    if (!WaitForZZZGame()) {
        LogMessage("等待绝区零启动失败，退出")
        return false
    }
    
    ; 3. 执行日常任务
    if (!ExecuteZZZDailyTasks()) {
        LogMessage("执行日常任务失败")
        ; 继续执行关闭流程
    }
    
    ; 4. 关闭绝区零
    CloseZZZ()
    
    LogMessage("=== 绝区零自动化完成 ===")
    return true
}

; 脚本入口
#c::  ; 按Win+C开始自动化（测试用）
    Main()
return

; 紧急停止
#v::  ; 按Win+V停止所有操作
    LogMessage("紧急停止")
    ExitApp
return

; 如果通过命令行调用
if (0 = 0) {  ; 总是执行
    if (A_Args.Length() > 0) {
        if (A_Args[1] = "run") {
            Main()
        }
    }
}