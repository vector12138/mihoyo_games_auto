; 原神自动化脚本 (AutoHotkey)
; 控制bettergi和原神游戏，执行日常任务

#NoEnv
#SingleInstance Force
#Persistent
#WinActivateForce

SetTitleMatchMode, 2
SetControlDelay, -1
SetKeyDelay, 50, 50
SetMouseDelay, 50

; 配置变量
bettergiTitle := "BetterGI"
genshinTitle := "原神"
genshinWindowClass := "UnityWndClass"
timeoutSeconds := 300

; 日志函数
LogMessage(message) {
    FormatTime, currentTime,, yyyy-MM-dd HH:mm:ss
    FileAppend, [%currentTime%] %message%`n, logs/genshin_automation.log
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

; 启动BetterGI
StartBetterGI(bettergiPath) {
    LogMessage("启动BetterGI: " . bettergiPath)
    
    ; 检查是否已运行
    IfWinExist, %bettergiTitle%
    {
        LogMessage("BetterGI 已在运行")
        WinActivate, %bettergiTitle%
        return true
    }
    
    ; 启动BetterGI
    try {
        Run, %bettergiPath%
    } catch {
        LogMessage("启动BetterGI失败")
        return false
    }
    
    ; 等待BetterGI窗口
    windowId := WaitForWindow(bettergiTitle)
    if (windowId = 0) {
        return false
    }
    
    WinActivate, ahk_id %windowId%
    Sleep, 3000  ; 等待BetterGI完全加载
    
    return true
}

; 通过BetterGI启动原神
LaunchGenshinThroughBetterGI() {
    LogMessage("通过BetterGI启动原神")
    
    ; 激活BetterGI窗口
    IfWinNotExist, %bettergiTitle%
    {
        LogMessage("BetterGI 窗口不存在")
        return false
    }
    
    WinActivate, %bettergiTitle%
    Sleep, 1000
    
    ; 查找并点击"启动"按钮
    ; 注意：这里需要根据BetterGI的实际界面调整坐标或控件ID
    ; 这里使用相对坐标，假设"启动"按钮在窗口中的位置
    
    ; 获取BetterGI窗口位置
    WinGetPos, bgX, bgY, bgWidth, bgHeight, %bettergiTitle%
    
    if (bgWidth = 0 or bgHeight = 0) {
        LogMessage("无法获取BetterGI窗口位置")
        return false
    }
    
    ; 假设"启动"按钮在窗口中央偏下位置
    ; 实际使用时需要根据BetterGI界面调整
    buttonX := bgX + bgWidth // 2
    buttonY := bgY + bgHeight - 100
    
    ; 点击"启动"按钮
    Click, %buttonX%, %buttonY%
    LogMessage("点击启动按钮 (坐标: " . buttonX . ", " . buttonY . ")")
    
    return true
}

; 等待原神启动并进入游戏
WaitForGenshin() {
    LogMessage("等待原神启动...")
    
    ; 等待原神游戏窗口
    windowId := WaitForWindow(genshinTitle, genshinWindowClass, 180)  ; 3分钟超时
    if (windowId = 0) {
        LogMessage("原神启动失败")
        return false
    }
    
    WinActivate, ahk_id %windowId%
    Sleep, 5000  ; 等待游戏完全加载
    
    ; 检查是否在登录界面或主界面
    ; 这里可以添加图像识别或颜色检查来确认游戏状态
    ; 暂时使用简单的等待
    
    LogMessage("原神已启动，等待进入游戏界面...")
    Sleep, 15000  ; 等待15秒进入游戏
    
    return true
}

; 执行原神日常任务（一条龙）
ExecuteGenshinDailyTasks() {
    LogMessage("开始执行原神日常任务...")
    
    ; 这里需要根据你的日常任务流程编写具体的自动化步骤
    ; 以下是一个示例流程，需要根据实际情况调整
    
    ; 1. 打开日常任务界面（按F3或点击图标）
    Send, {F3}
    Sleep, 3000
    
    ; 2. 领取每日委托奖励
    ; 假设领取按钮在屏幕特定位置
    Click, 960, 600  ; 示例坐标，需要调整
    Sleep, 2000
    
    ; 3. 完成4个每日委托（自动传送和完成）
    Loop, 4 {
        LogMessage("完成每日委托 " . A_Index . "/4")
        
        ; 点击"前往"按钮
        Click, 1200, 700  ; 示例坐标
        Sleep, 5000  ; 等待传送
        
        ; 自动战斗（按F键开始战斗）
        Send, {F}
        Sleep, 30000  ; 等待战斗完成
        
        ; 返回委托界面
        Send, {F3}
        Sleep, 3000
    }
    
    ; 4. 领取委托奖励
    Click, 1400, 800  ; 领取奖励按钮
    Sleep, 2000
    
    ; 5. 完成树脂消耗（如刷副本）
    LogMessage("消耗树脂...")
    ; 这里可以添加刷副本的自动化
    
    ; 6. 完成其他日常（如派遣、锻造等）
    LogMessage("完成其他日常...")
    
    LogMessage("原神日常任务完成")
    return true
}

; 关闭BetterGI
CloseBetterGI() {
    LogMessage("关闭BetterGI")
    
    IfWinExist, %bettergiTitle%
    {
        ; 尝试正常关闭
        WinClose, %bettergiTitle%
        Sleep, 2000
        
        ; 检查是否已关闭
        IfWinNotExist, %bettergiTitle%
        {
            LogMessage("BetterGI 已关闭")
            return true
        }
        
        ; 强制关闭
        WinKill, %bettergiTitle%
        Sleep, 1000
        
        IfWinNotExist, %bettergiTitle%
        {
            LogMessage("BetterGI 已强制关闭")
            return true
        }
        
        LogMessage("关闭BetterGI失败")
        return false
    }
    
    LogMessage("BetterGI 未运行")
    return true
}

; 关闭原神
CloseGenshin() {
    LogMessage("关闭原神")
    
    IfWinExist, ahk_class %genshinWindowClass%
    {
        ; 先按ESC打开菜单
        Send, {Esc}
        Sleep, 1000
        
        ; 点击退出游戏按钮（假设在右下角）
        Click, 1800, 1000  ; 示例坐标
        Sleep, 2000
        
        ; 确认退出
        Click, 960, 700  ; 确认按钮
        Sleep, 5000
        
        ; 检查是否已关闭
        IfWinNotExist, ahk_class %genshinWindowClass%
        {
            LogMessage("原神已关闭")
            return true
        }
        
        ; 强制关闭
        WinKill, ahk_class %genshinWindowClass%
        Sleep, 2000
        
        IfWinNotExist, ahk_class %genshinWindowClass%
        {
            LogMessage("原神已强制关闭")
            return true
        }
        
        LogMessage("关闭原神失败")
        return false
    }
    
    LogMessage("原神未运行")
    return true
}

; 主函数
Main() {
    LogMessage("=== 原神自动化开始 ===")
    
    ; 读取配置文件
    configFile := A_ScriptDir . "\config.json"
    if (!FileExist(configFile)) {
        configFile := A_ScriptDir . "\config.example.json"
    }
    
    ; 这里可以添加读取配置的代码
    ; 暂时使用硬编码路径
    bettergiPath := "C:\Program Files\BetterGI\bettergi.exe"
    
    ; 1. 启动BetterGI
    if (!StartBetterGI(bettergiPath)) {
        LogMessage("启动BetterGI失败，退出")
        return false
    }
    
    ; 2. 通过BetterGI启动原神
    if (!LaunchGenshinThroughBetterGI()) {
        LogMessage("启动原神失败，退出")
        return false
    }
    
    ; 3. 等待原神启动
    if (!WaitForGenshin()) {
        LogMessage("等待原神启动失败，退出")
        return false
    }
    
    ; 4. 执行日常任务
    if (!ExecuteGenshinDailyTasks()) {
        LogMessage("执行日常任务失败")
        ; 继续执行关闭流程
    }
    
    ; 5. 关闭原神
    CloseGenshin()
    
    ; 6. 关闭BetterGI
    CloseBetterGI()
    
    LogMessage("=== 原神自动化完成 ===")
    return true
}

; 脚本入口
#z::  ; 按Win+Z开始自动化（测试用）
    Main()
return

; 紧急停止
#x::  ; 按Win+X停止所有操作
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