# 📱 消息发送配置指南

## 选项1: 使用Telegram（推荐）

### 步骤1: 创建Telegram Bot
1. 在Telegram中搜索 @BotFather
2. 发送 `/newbot` 创建新机器人
3. 设置机器人名称和用户名
4. 保存Bot Token（类似: `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ`）

### 步骤2: 获取Chat ID
1. 给你的机器人发送消息 `/start`
2. 访问: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
3. 查找 `chat.id` 字段

### 步骤3: 配置脚本
编辑 `send_via_telegram.sh`:
```bash
TELEGRAM_BOT_TOKEN="你的Bot Token"
TELEGRAM_CHAT_ID="你的Chat ID"
```

### 步骤4: 测试发送
```bash
./send_via_telegram.sh
```

## 选项2: 使用OpenClaw内置消息

如果你已经配置了OpenClaw的消息通道（如WhatsApp、Signal），可以修改 `send_ai_analysis_to_phone.sh` 脚本，添加OpenClaw消息发送代码。

## 选项3: 使用邮件

创建 `send_via_email.sh` 脚本，使用 `mail` 或 `sendmail` 命令发送邮件。

## 选项4: 手动查看

每小时的分析数据会自动保存到:
- `/tmp/latest_ai_analysis.txt` - 最新分析结果
- `/tmp/ai_analysis_cron.log` - 执行日志

## 测试当前系统
```bash
# 手动运行一次
./send_ai_analysis_to_phone.sh

# 查看生成的消息
cat /tmp/latest_ai_analysis.txt
```

## 管理Cron任务
```bash
# 查看当前cron任务
crontab -l

# 编辑cron任务
crontab -e

# 删除所有cron任务
crontab -r
```

## 故障排除
1. 确保AI分析服务运行: `curl http://localhost:5000/api/status`
2. 检查cron日志: `tail -f /tmp/ai_analysis_cron.log`
3. 手动测试脚本: `./send_ai_analysis_to_phone.sh`
