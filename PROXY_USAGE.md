# Telegram 代理配置指南

## 概述
米哈游游戏自动化工具现在支持通过代理发送 Telegram 通知。这对于需要科学上网的环境非常有用。

## 支持的代理类型
- HTTP 代理
- HTTPS 代理
- SOCKS5 代理（通过 HTTP 代理转发）

## 配置方法

### 1. 编辑配置文件
在 `config.yaml` 中添加以下配置：

```yaml
# Telegram代理配置（可选）
telegram_proxy:
  enabled: true                  # 启用代理
  url: "http://127.0.0.1:1080"  # 代理服务器地址
  auth:                          # 代理认证（如果需要）
    username: "your_username"
    password: "your_password"
```

### 2. 代理地址格式
- HTTP/HTTPS 代理：`http://127.0.0.1:1080` 或 `https://proxy.example.com:8080`
- SOCKS5 代理：`socks5://127.0.0.1:1080`
- 带认证的代理：`http://username:password@proxy.example.com:8080`

### 3. 常见代理配置示例

#### 示例 1：本地 HTTP 代理（Clash/V2Ray）
```yaml
telegram_proxy:
  enabled: true
  url: "http://127.0.0.1:7890"
  auth:
    username: ""
    password: ""
```

#### 示例 2：SOCKS5 代理
```yaml
telegram_proxy:
  enabled: true
  url: "socks5://127.0.0.1:10808"
  auth:
    username: ""
    password: ""
```

#### 示例 3：带认证的代理
```yaml
telegram_proxy:
  enabled: true
  url: "http://proxy.example.com:8080"
  auth:
    username: "myuser"
    password: "mypass"
```

## 测试代理连接

### 1. 使用测试脚本
```bash
cd /path/to/mihoyo_games_auto
python -c "
from telegram_notifier import TelegramNotifier, load_config
config = load_config()
telegram_config = config.get('telegram', {})
telegram_config['proxy'] = config.get('telegram_proxy', {})
notifier = TelegramNotifier(telegram_config)
if notifier.test_connection():
    print('✅ 代理连接测试成功')
else:
    print('❌ 代理连接测试失败')
"
```

### 2. 运行完整测试
```bash
python telegram_notifier.py
```

## 故障排除

### 1. 连接失败
**问题**: `ConnectionError` 或 `Timeout`
**解决方案**:
- 检查代理服务器是否运行
- 检查代理地址和端口是否正确
- 尝试关闭防火墙或安全软件

### 2. 认证失败
**问题**: `ProxyError` 或 `407 Proxy Authentication Required`
**解决方案**:
- 检查用户名和密码是否正确
- 确认代理服务器支持认证
- 尝试在 URL 中直接包含认证信息：`http://user:pass@proxy:port`

### 3. SSL/TLS 错误
**问题**: `SSLError` 或证书验证失败
**解决方案**:
- 对于自签名证书，可以尝试禁用验证（不推荐）
- 确保代理支持 HTTPS 连接
- 检查系统时间是否正确

### 4. 代理不支持 SOCKS5
**问题**: SOCKS5 代理连接失败
**解决方案**:
- 使用 HTTP 代理转发 SOCKS5 流量
- 或者使用支持 SOCKS5 的代理客户端

## 高级配置

### 1. 环境变量覆盖
可以通过环境变量临时覆盖配置：
```bash
export TELEGRAM_PROXY_URL="http://127.0.0.1:7890"
export TELEGRAM_PROXY_ENABLED="true"
python main.py
```

### 2. 动态代理切换
在代码中动态切换代理：
```python
from telegram_notifier import TelegramNotifier

# 创建不带代理的通知器
notifier1 = TelegramNotifier({
    'bot_token': 'YOUR_TOKEN',
    'chat_id': 'YOUR_CHAT_ID',
    'enabled': True
})

# 创建带代理的通知器
notifier2 = TelegramNotifier({
    'bot_token': 'YOUR_TOKEN',
    'chat_id': 'YOUR_CHAT_ID',
    'enabled': True,
    'proxy': {
        'enabled': True,
        'url': 'http://127.0.0.1:7890'
    }
})
```

## 安全注意事项

1. **不要提交敏感信息**: 确保 `config.yaml` 文件不包含真实的代理认证信息
2. **使用环境变量**: 对于生产环境，建议使用环境变量存储敏感信息
3. **定期更换密码**: 如果使用带认证的代理，定期更换密码
4. **限制代理访问**: 确保代理服务器只允许受信任的客户端连接

## 性能影响
- 代理会增加网络延迟，但通常影响不大
- 建议使用本地代理服务器以减少延迟
- 如果代理不稳定，可以配置重试机制

## 相关链接
- [Requests 代理文档](https://docs.python-requests.org/en/latest/user/advanced/#proxies)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Python 网络编程](https://docs.python.org/3/library/urllib.request.html#urllib.request.ProxyHandler)