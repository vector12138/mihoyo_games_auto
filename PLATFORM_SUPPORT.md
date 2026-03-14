# 平台支持说明

## 通知平台支持

### ✅ 支持的平台
- **Telegram**: 本项目完全支持 Telegram 通知功能
  - 支持消息推送
  - 支持图片发送
  - 支持代理配置
  - 支持任务状态报告

### ❌ 不支持的平台
本项目**不**支持以下通知平台：
- Discord
- Slack
- WhatsApp
- Signal
- Line
- 微信/WeChat
- 钉钉
- 其他第三方消息平台

## 技术决策说明

### 为什么只支持 Telegram？
1. **API 稳定性**: Telegram Bot API 稳定且功能完善
2. **代理友好**: Telegram 在需要科学上网的环境中表现良好
3. **功能丰富**: 支持 Markdown、图片、文件等多种消息格式
4. **配置简单**: 只需要 Bot Token 和 Chat ID 即可使用
5. **社区支持**: 有完善的文档和社区支持

### 未来扩展可能性
虽然当前版本只支持 Telegram，但项目架构设计允许未来扩展其他平台：
- 可以通过继承 `BaseNotifier` 类实现新的通知器
- 配置文件结构支持多平台配置
- 核心通知逻辑与平台解耦

## 配置示例

### Telegram 配置
```yaml
# 全局配置
global:
  telegram_notify: true         # 启用Telegram通知
  telegram_token: "YOUR_BOT_TOKEN"
  telegram_chat_id: "YOUR_CHAT_ID"

# Telegram代理配置（可选）
telegram_proxy:
  enabled: false                # 是否启用代理
  url: "http://127.0.0.1:7890" # 代理服务器地址
```

## 常见问题

### Q: 能否添加 Discord/Slack 支持？
**A**: 当前版本不支持。如果需要其他平台支持，可以考虑：
1. 使用 IFTTT/Zapier 等工具将 Telegram 消息转发到其他平台
2. 自行扩展代码，实现新的通知器类
3. 提交功能请求到项目 Issue

### Q: 为什么选择 Telegram 而不是其他平台？
**A**: Telegram 具有以下优势：
- 免费且无消息数量限制
- 支持完善的 Bot API
- 跨平台支持良好
- 代理配置简单
- 消息推送及时

### Q: 能否同时支持多个通知平台？
**A**: 当前架构不支持，但可以通过修改代码实现。主要限制是：
1. 配置复杂度增加
2. 错误处理更复杂
3. 需要维护多个平台的 API 集成

## 技术实现

### 通知器架构
```
BaseNotifier (抽象类)
    └── TelegramNotifier (具体实现)
```

### 扩展新平台
如需添加新平台支持，需要：
1. 创建新的通知器类，继承自 `BaseNotifier`
2. 实现 `send_message()`、`send_photo()` 等方法
3. 更新配置加载逻辑
4. 添加相应的测试

## 总结
本项目专注于 Telegram 通知功能，提供了完整的代理支持和丰富的消息类型。虽然不支持其他平台，但 Telegram 的功能已经足够满足大多数自动化任务的通知需求。

如需其他平台支持，建议使用消息转发工具或自行扩展代码。