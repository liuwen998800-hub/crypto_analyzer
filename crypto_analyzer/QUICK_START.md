# 🚀 增强版虚拟币分析系统 - 快速开始指南

## 📋 系统状态

✅ **系统已部署并运行正常**
- **服务状态**: 运行中
- **访问地址**: http://localhost:5003/enhanced
- **API端口**: 5003
- **启动时间**: 2026-04-16 07:00

## 🔧 立即使用

### 1. 访问Web界面
```bash
# 直接在浏览器打开
http://localhost:5003/enhanced
```

### 2. 使用步骤
1. **选择币种**: BTC / ETH / SOL
2. **选择时间框架**: 1小时 / 4小时 / 24小时
3. **选择AI模型**: 双模型 / DeepSeek / MiniMax
4. **点击分析**: "开始AI分析"按钮
5. **查看结果**: 实时显示分析结果

### 3. API调用示例
```bash
# 分析BTC
curl -X POST http://localhost:5003/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC","timeframe":"1h","ai_model":"both"}'

# 批量分析所有币种
curl -X POST http://localhost:5003/api/analyze/batch \
  -H "Content-Type: application/json" \
  -d '{"symbols":["BTC","ETH","SOL"],"timeframe":"1h"}'
```

## 📊 当前分析示例

### BTC分析结果 (示例)
```
📈 BTC - 比特币
当前价格: $76,304.57 (+1.93%)
综合评分: 68/100 (BUY信号)
AI共识: bullish (61%置信度)

🔧 技术指标:
- RSI: 55.79 (中性)
- MACD: -15.34 (看跌)
- 移动平均线: 多头排列
- 布林带位置: 63.11%

🎯 关键价位:
- 支撑位: $74,000 (强)
- 阻力位: $78,000 (中)
- 当前价格位置: 中部偏上

💡 操作建议:
基于技术分析和AI共识，建议考虑买入或持有。
市场情绪偏向积极，但需注意阻力位突破情况。
```

## 🛠️ 管理命令

### 启动服务
```bash
cd /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/web_dashboard
./start_simple.sh
```

### 停止服务
```bash
pkill -f "python.*app_simple.py"
```

### 查看日志
```bash
tail -f /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/web_dashboard/app_simple.log
```

### 重启服务
```bash
cd /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/web_dashboard
pkill -f "python.*app_simple.py"
sleep 2
nohup python3 app_simple.py > app_simple.log 2>&1 &
```

## 🔍 系统验证

### 测试API状态
```bash
curl http://localhost:5003/api/status
```
预期响应: `{"status": "running", ...}`

### 测试分析功能
```bash
curl -X POST http://localhost:5003/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"ETH","timeframe":"4h"}' | jq '.signal.signal'
```
预期响应: `"BUY"` 或 `"SELL"` 等信号

### 测试Web界面
```bash
curl -I http://localhost:5003/enhanced
```
预期响应: `HTTP/1.1 200 OK`

## ⚙️ 配置说明

### 1. API密钥配置 (可选)
如需使用真实的AI分析，编辑配置文件:
```bash
nano /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/config/api_keys.yaml
```
填入:
- DeepSeek API密钥
- MiniMax API密钥和Group ID

### 2. 评分规则调整
编辑评分权重:
```bash
nano /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/config/scoring_rules.yaml
```
调整:
- 技术指标权重
- AI分析权重
- 信号阈值

## 📈 功能特点

### ✅ 已实现功能
1. **双AI模型分析** - DeepSeek + MiniMax
2. **多时间框架** - 1h/4h/24h分析
3. **详细技术指标** - 20+种指标计算
4. **支撑阻力位** - 智能识别关键价位
5. **综合评分系统** - 技术+AI+情绪综合评分
6. **实时数据** - 价格和涨跌幅监控
7. **美观界面** - 响应式Web界面
8. **完整API** - RESTful API接口

### 🎯 使用场景
- **实时监控**: 监控币种价格和技术指标
- **交易决策**: 基于综合评分做出买卖决定
- **风险管理**: 识别支撑阻力位设置止损
- **策略研究**: 分析历史数据和信号准确率

## 🚨 注意事项

### 1. 数据来源
- 当前使用模拟数据演示
- 配置真实API密钥后可使用实时数据
- 历史数据为模拟生成

### 2. 分析频率
- 手动分析: 随时点击分析
- 自动分析: 每小时自动运行
- 数据更新: 每5分钟价格更新

### 3. 系统限制
- 同时分析: 支持最多3个币种
- 历史数据: 保留最近30天
- 并发请求: 支持多用户同时访问

## 🔄 备份与恢复

### 备份系统
```bash
cd /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/web_dashboard
./backup_system.sh
```

### 恢复系统
```bash
# 从备份恢复
tar -xzf backups/enhanced_crypto_analyzer_*.tar.gz -C ..
```

## 📞 技术支持

### 问题排查
1. **服务无法启动**: 检查端口5003是否被占用
2. **API无响应**: 检查服务进程是否运行
3. **界面无法访问**: 检查网络连接和防火墙
4. **分析结果异常**: 检查配置文件和依赖

### 日志查看
```bash
# 查看错误日志
tail -100 /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/web_dashboard/app_simple.log

# 查看系统日志
journalctl -u 相关服务名
```

## 🎉 开始使用

系统已准备就绪！立即访问:
**http://localhost:5003/enhanced**

开始您的虚拟币分析之旅！🚀

---
*系统版本: 增强版 v1.0*
*最后更新: 2026-04-16*
*状态: ✅ 运行正常*