# 📱 QQ和微信消息发送配置指南

## 🎯 快速开始

### 步骤1: 测试基础系统
```bash
cd /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer
./send_ai_analysis_to_phone.sh
```

### 步骤2: 选择发送方式
- **QQ邮箱** → 配置 `send_via_qq_email.sh`
- **微信(Server酱)** → 配置 `send_via_wechat_serverchan.sh`
- **微信/QQ(PushPlus)** → 配置 `send_via_pushplus.sh`

### 步骤3: 配置并测试
```bash
# 编辑配置文件后测试
./send_via_qq_email.sh
# 或
./send_via_wechat_serverchan.sh
# 或
./send_via_pushplus.sh
```

## 📧 方案1: QQ邮箱（推荐给QQ用户）

### 优点：
- ✅ 直接发送到QQ邮箱
- ✅ QQ客户端会有通知
- ✅ 支持HTML富文本
- ✅ 免费使用

### 配置步骤：

#### 1. 获取QQ邮箱授权码
1. 登录QQ邮箱网页版 (mail.qq.com)
2. 点击"设置" → "账户"
3. 找到"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
4. 开启"IMAP/SMTP服务"
5. 生成16位授权码（**不是QQ密码**）
6. 保存授权码

#### 2. 配置脚本
编辑 `send_via_qq_email.sh`：
```bash
QQ_EMAIL="123456789@qq.com"  # 你的QQ邮箱
SMTP_PASSWORD="你的16位授权码"  # 上一步获取的授权码
```

#### 3. 安装发送工具
```bash
# Ubuntu/Debian
sudo apt-get install sendemail

# CentOS/RHEL
sudo yum install sendemail
```

#### 4. 测试发送
```bash
./send_via_qq_email.sh
```

#### 5. 设置自动发送
编辑cron任务，添加发送命令：
```bash
# 编辑cron
crontab -e

# 添加（每小时运行主脚本后发送邮件）
0 * * * * /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/send_ai_analysis_to_phone.sh && /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/send_via_qq_email.sh
```

## 💬 方案2: 微信 - Server酱

### 优点：
- ✅ 微信直接接收
- ✅ 免费使用
- ✅ 设置简单
- ✅ 支持Markdown

### 配置步骤：

#### 1. 注册Server酱
1. 访问 https://sct.ftqq.com
2. 微信扫码登录
3. 获取SendKey（在"发送消息"页面）

#### 2. 配置脚本
编辑 `send_via_wechat_serverchan.sh`：
```bash
SERVERCHAN_KEY="SCT123456ABCDEFG"  # 你的SendKey
```

#### 3. 关注服务号
1. 扫描页面上的二维码
2. 关注"Server酱"服务号

#### 4. 测试发送
```bash
./send_via_wechat_serverchan.sh
```

## 📲 方案3: 微信/QQ - PushPlus

### 优点：
- ✅ 支持微信、QQ、短信等多种渠道
- ✅ 免费额度充足
- ✅ 支持HTML富文本
- ✅ 可绑定多个接收方式

### 配置步骤：

#### 1. 注册PushPlus
1. 访问 https://www.pushplus.plus
2. 微信扫码登录
3. 获取Token（在"一对一消息"页面）

#### 2. 配置脚本
编辑 `send_via_pushplus.sh`：
```bash
PUSHPLUS_TOKEN="1234567890abcdef"  # 你的Token
```

#### 3. 绑定接收方式
1. 在PushPlus后台绑定微信
2. 可选：绑定QQ、邮箱等

#### 4. 测试发送
```bash
./send_via_pushplus.sh
```

## ⚙️ 自动化配置

### 创建自动发送脚本
```bash
#!/bin/bash
# auto_send_all.sh - 自动发送到所有配置的渠道

# 生成报告
./send_ai_analysis_to_phone.sh

# 发送到QQ邮箱（如果已配置）
if [ -f "./send_via_qq_email.sh" ] && ! grep -q "YOUR_QQ_NUMBER" ./send_via_qq_email.sh; then
    echo "发送到QQ邮箱..."
    ./send_via_qq_email.sh
fi

# 发送到微信Server酱（如果已配置）
if [ -f "./send_via_wechat_serverchan.sh" ] && ! grep -q "YOUR_SERVERCHAN_SEND_KEY" ./send_via_wechat_serverchan.sh; then
    echo "发送到微信Server酱..."
    ./send_via_wechat_serverchan.sh
fi

# 发送到PushPlus（如果已配置）
if [ -f "./send_via_pushplus.sh" ] && ! grep -q "YOUR_PUSHPLUS_TOKEN" ./send_via_pushplus.sh; then
    echo "发送到PushPlus..."
    ./send_via_pushplus.sh
fi
```

### 设置每小时自动发送
```bash
# 编辑cron
crontab -e

# 添加（每小时运行自动发送脚本）
0 * * * * cd /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer && ./auto_send_all.sh >> /tmp/ai_auto_send.log 2>&1
```

## 🔧 故障排除

### 常见问题1: QQ邮箱发送失败
```bash
# 检查授权码
echo "检查QQ邮箱配置..."

# 测试SMTP连接
sendemail -f "test@qq.com" -t "你的QQ邮箱" -u "测试" -m "测试消息" \
  -s smtp.qq.com:587 -xu "你的QQ邮箱" -xp "你的授权码" -o tls=yes
```

### 常见问题2: 微信收不到消息
1. 检查是否关注了服务号（Server酱/PushPlus）
2. 检查Token/Key是否正确
3. 查看服务号后台是否有发送记录

### 常见问题3: 脚本权限问题
```bash
# 添加执行权限
chmod +x *.sh

# 检查权限
ls -la *.sh
```

### 常见问题4: 网络连接问题
```bash
# 测试AI分析服务
curl http://localhost:5000/api/status

# 测试外部API
curl -s https://api.telegram.org
curl -s https://sctapi.ftqq.com
curl -s https://www.pushplus.plus
```

## 📊 消息格式示例

### QQ邮箱接收效果：
- 📧 邮件主题带表情符号
- 📊 HTML格式的漂亮排版
- 📈 颜色区分涨跌
- 🔗 可点击的链接

### 微信接收效果：
- 🤖 标题带表情符号
- 📋 清晰的段落分隔
- 🎯 关键信息突出显示
- 📊 支持Markdown格式

## 🎯 推荐方案

### 个人使用：
1. **首选QQ邮箱** - 设置简单，QQ直接通知
2. **备选PushPlus** - 功能丰富，支持多平台

### 多平台需求：
1. **PushPlus** - 可同时发送到微信、QQ、邮件
2. **自定义脚本** - 结合多种方式

### 最小配置：
1. **QQ邮箱** - 只需QQ号和授权码
2. **Server酱** - 只需微信扫码

## 📞 支持

### 获取帮助：
1. **QQ邮箱问题** - 查看QQ邮箱帮助中心
2. **Server酱问题** - 访问 https://sct.ftqq.com
3. **PushPlus问题** - 访问 https://www.pushplus.plus
4. **脚本问题** - 查看脚本内的注释

### 紧急联系：
如果系统停止工作：
```bash
# 查看日志
tail -f /tmp/ai_analysis_cron.log
tail -f /tmp/ai_auto_send.log

# 手动运行
cd /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer
./send_ai_analysis_to_phone.sh
```

---

**现在选择你喜欢的方案，配置后就可以每小时收到BTC AI分析报告了！** 🎉

建议先配置QQ邮箱，这是最直接的方式。配置好后，QQ客户端每小时都会收到分析报告通知。 📱⏰