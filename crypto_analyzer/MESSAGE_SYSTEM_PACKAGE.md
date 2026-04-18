# 📱 消息发送系统 - 完整打包

## 🎯 系统概述

这是一个完整的AI分析报告消息发送系统，支持通过多种渠道每小时自动发送BTC AI分析报告。

## 📦 包含的文件

### 1. 核心脚本
- `send_ai_analysis_to_phone.sh` - 主脚本，生成分析报告
- `send_via_qq_email.sh` - QQ邮箱发送脚本
- `send_via_wechat_serverchan.sh` - 微信Server酱发送脚本
- `send_via_pushplus.sh` - PushPlus多平台发送脚本
- `send_via_telegram.sh` - Telegram发送模板

### 2. 配置工具
- `setup_hourly_report.sh` - 设置每小时报告系统
- `setup_qq_wechat_notification.sh` - QQ/微信一键配置脚本

### 3. 文档指南
- `MESSAGE_SETUP_GUIDE.md` - 消息发送配置指南
- `QQ_WECHAT_SETUP_GUIDE.md` - QQ和微信专门配置指南
- `FMZ_STRATEGY_DEPLOY_GUIDE.md` - FMZ策略部署指南
- `FMZ_SYNTAX_FIX_GUIDE.md` - FMZ语法错误解决方案

### 4. FMZ策略文件
- `fmz_simple_strategy.js` - 简洁版FMZ策略
- `fmz_compatible_strategy.js` - 兼容版FMZ策略
- `fmz_strict_compatible.js` - 严格兼容版FMZ策略
- `fmz_minimal_test.js` - 最小测试版本
- `fmz_ai_advanced_strategy.js` - 高级FMZ策略
- `fmz_final_strategy.js` - 最终版FMZ策略

## 🚀 快速开始

### 1. 测试系统
```bash
./send_ai_analysis_to_phone.sh
```

### 2. 配置发送方式
```bash
# 一键配置
./setup_qq_wechat_notification.sh

# 或手动配置
# 编辑 send_via_qq_email.sh (QQ邮箱)
# 编辑 send_via_wechat_serverchan.sh (微信)
# 编辑 send_via_pushplus.sh (多平台)
```

### 3. 设置自动发送
```bash
# 设置每小时自动发送
./setup_hourly_report.sh
```

## ⚙️ 系统要求

### 依赖项
- Python 3.x
- curl
- sendemail (用于QQ邮箱发送)
- cron (用于定时任务)

### 服务要求
- AI分析服务运行在端口5000
- 网络连接正常

## 📊 功能特性

### 1. 报告生成
- 自动获取BTC AI分析数据
- 格式化消息生成
- 支持Markdown和HTML格式
- 包含价格、方向、置信度等关键信息

### 2. 多平台支持
- **QQ邮箱**: QQ客户端直接通知
- **微信(Server酱)**: 微信服务号推送
- **PushPlus**: 支持微信、QQ、邮件等多平台
- **Telegram**: 国际用户使用

### 3. 自动化
- 每小时自动运行
- 错误处理和日志记录
- 可配置的发送渠道

### 4. 可扩展性
- 模块化设计
- 易于添加新的发送渠道
- 支持自定义消息格式

## 🔧 配置说明

### QQ邮箱配置
1. 获取QQ邮箱授权码（不是密码）
2. 编辑 `send_via_qq_email.sh`
3. 设置QQ邮箱和授权码

### 微信配置
1. 注册Server酱或PushPlus
2. 获取Token/Key
3. 编辑对应的脚本文件
4. 关注服务号

### 定时任务配置
系统使用cron设置每小时自动发送：
```
0 * * * * /path/to/send_ai_analysis_to_phone.sh
```

## 📈 报告内容

每小时报告包含：
- BTC当前价格
- AI分析方向（看涨/看跌/中性）
- 置信度百分比
- 双模型一致性评分
- DeepSeek和MiniMax独立分析
- 简要市场分析
- 时间戳和日期
- 详细分析链接

## 🐛 故障排除

### 常见问题
1. **API连接失败**: 检查AI分析服务是否运行
2. **邮件发送失败**: 检查QQ邮箱授权码
3. **微信收不到消息**: 检查Token和是否关注服务号
4. **定时任务不运行**: 检查cron服务和日志

### 日志文件
- `/tmp/ai_analysis_cron.log` - 主脚本日志
- `/tmp/ai_auto_send.log` - 自动发送日志
- `/tmp/flask_output.log` - Flask服务日志

## 🔄 更新维护

### 添加新功能
1. 创建新的发送脚本
2. 更新配置指南
3. 测试发送功能
4. 更新打包文档

### 备份恢复
```bash
# 备份整个系统
tar -czf message_system_backup_$(date +%Y%m%d).tar.gz *.sh *.md

# 恢复系统
tar -xzf message_system_backup_YYYYMMDD.tar.gz
```

## 📝 版本历史

### v1.0 (2026-04-17)
- 初始版本发布
- 支持QQ邮箱、微信、PushPlus
- 每小时自动发送
- 完整的配置指南

### v1.1 (计划中)
- 添加短信通知支持
- 添加多语言支持
- 添加数据统计功能
- 优化错误处理

## 📞 支持

### 文档资源
- 本文件: `MESSAGE_SYSTEM_PACKAGE.md`
- 配置指南: `QQ_WECHAT_SETUP_GUIDE.md`
- FMZ指南: `FMZ_STRATEGY_DEPLOY_GUIDE.md`

### 在线资源
- Server酱: https://sct.ftqq.com
- PushPlus: https://www.pushplus.plus
- QQ邮箱帮助: https://service.mail.qq.com

## 🎉 成功部署标志

1. ✅ `send_ai_analysis_to_phone.sh` 能正常生成报告
2. ✅ 至少一种发送方式配置成功
3. ✅ 测试发送能收到消息
4. ✅ 定时任务设置正确
5. ✅ 日志文件正常记录

---

**系统已打包完成，可以部署到任何支持bash和cron的Linux环境。**

**使用前请确保:**
1. AI分析服务正常运行
2. 网络连接正常
3. 必要的依赖已安装
4. 发送渠道已配置

**祝使用愉快！** 🚀