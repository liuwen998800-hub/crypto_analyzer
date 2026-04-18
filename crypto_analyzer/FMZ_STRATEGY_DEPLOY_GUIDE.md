# 🚀 FMZ策略部署指南

## 📋 概述

本指南将帮助你将AI量化交易策略部署到FMZ平台。我们已经创建了完整的策略代码，你只需要按照步骤操作即可。

## 🎯 已创建的策略文件

1. **`fmz_simple_strategy.js`** - 简洁版策略（推荐初学者）
2. **`fmz_ai_advanced_strategy.js`** - 高级版策略（完整功能）
3. **`fmz_final_strategy.js`** - 最终版策略（最完整）

## 🔧 部署步骤

### 步骤1: 登录FMZ平台
1. 访问 https://www.fmz.com
2. 使用你的账户登录

### 步骤2: 配置交易所
1. 进入"控制中心" → "交易所"
2. 点击"添加交易所"
3. 选择"Binance"
4. 输入你的币安API Key:
   - **API Key**: `B4oYgaYvdPja31cjbYScexOCKiMgNjqKOIjyNK71iD3Zo7IssK1TOdHeUIGN0xXQ`
   - **Secret Key**: `uxJsSX8lpBWSQZnvfKO33jkSO5kj60KBnlYzHWeddl6v0jXHrbJDYgZXUxUdMKeJ`
5. 保存配置

### 步骤3: 创建策略
1. 进入"策略库" → "新建策略"
2. 填写策略信息:
   - **策略名称**: `AI量化交易策略`
   - **编程语言**: `JavaScript`
   - **策略类型**: `现货`
3. 复制策略代码:
   ```bash
   # 复制简洁版策略
   cat /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/fmz_simple_strategy.js
   ```
4. 粘贴到FMZ策略编辑器
5. **重要**: 修改AI_API_URL配置:
   ```javascript
   AI_API_URL: "http://YOUR_SERVER_IP:5000/api/analyze",
   ```
   - 将 `YOUR_SERVER_IP` 替换为你的服务器IP地址
   - 如果是本地测试，使用 `http://localhost:5000/api/analyze`

### 步骤4: 配置策略参数
根据你的需求调整以下参数:

```javascript
// 基本配置
EXCHANGE: "binance",           // 交易所
SYMBOL: "BTC_USDT",            // 交易对

// 交易设置
CHECK_INTERVAL: 300,           // 检查间隔（秒）
MIN_CONFIDENCE: 60,            // 最小置信度

// 仓位管理
TRADE_AMOUNT: 0.001,           // 每次交易数量（BTC）
MAX_POSITION: 0.01,            // 最大持仓（BTC）

// 风险管理
STOP_LOSS: 5.0,                // 止损百分比
TAKE_PROFIT: 10.0,             // 止盈百分比
```

### 步骤5: 保存并测试策略
1. 点击"保存"按钮
2. 点击"回测"进行策略测试
3. 检查回测结果是否符合预期

### 步骤6: 启动FMZ托管者
策略需要在FMZ托管者上运行:

```bash
# 启动FMZ托管者（Docker）
docker run -d --name fmz-worker \
  -e ACCESS_KEY=74c1c98076616ccb54015c18c5ae7950 \
  -e SECRET_KEY=a4418a9b969650012682b54f5b578933 \
  fmzquant/worker:latest

# 查看日志
docker logs -f fmz-worker
```

### 步骤7: 运行策略
1. 在FMZ平台选择你创建的策略
2. 点击"实盘"
3. 选择配置的交易所（Binance）
4. 设置初始参数
5. 点击"运行"

## 🛠️ 策略代码详解

### 核心功能
1. **AI信号获取**: 定期调用AI分析API获取交易信号
2. **信号验证**: 检查置信度是否达到阈值
3. **仓位管理**: 控制每次交易数量和最大持仓
4. **风险管理**: 自动执行止损止盈
5. **交易执行**: 调用交易所API执行买卖操作

### 工作流程
```
1. 获取AI分析信号
   ↓
2. 验证信号置信度
   ↓
3. 检查账户余额和持仓
   ↓
4. 生成交易决策
   ↓
5. 执行交易订单
   ↓
6. 更新持仓状态
   ↓
7. 等待下次检查
```

## 🔍 监控和调试

### 查看日志
1. 在FMZ平台查看策略运行日志
2. 监控AI分析系统日志:
   ```bash
   tail -f /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/logs/ai_system.log
   ```

### 测试AI信号
```bash
# 测试AI分析API
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC"}'

# 预期响应
{
  "signal": {
    "direction": "buy",
    "confidence": 75,
    "reasoning": "技术分析显示看涨信号"
  },
  "current_price": 75234.50
}
```

### 检查服务状态
```bash
# 检查所有服务
cd /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer
./start_complete_system.sh

# 测试完整系统
python3 test_strategy_system.py
```

## ⚠️ 注意事项

### 安全设置
1. **API权限**: 确保币安API只启用交易权限，禁用提现权限
2. **IP白名单**: 在币安设置API IP白名单
3. **资金安全**: 从小额开始，逐步增加

### 网络配置
1. **公网访问**: 如果AI分析系统在服务器上，需要配置公网访问
2. **防火墙**: 确保端口5000对外开放
3. **HTTPS**: 生产环境建议使用HTTPS

### 参数优化
1. **起始资金**: 根据账户余额调整交易数量
2. **风险参数**: 根据风险承受能力调整止损止盈
3. **检查频率**: 根据市场波动调整检查间隔

## 🚨 故障排除

### 常见问题

#### 1. AI API连接失败
```bash
# 检查AI分析服务是否运行
curl http://localhost:5000/api/status

# 检查防火墙
sudo ufw status
sudo ufw allow 5000
```

#### 2. FMZ托管者无法连接
```bash
# 检查Docker容器
docker ps | grep fmz-worker

# 查看日志
docker logs fmz-worker

# 重启容器
docker restart fmz-worker
```

#### 3. 交易所API错误
- 检查API Key和Secret Key是否正确
- 检查API权限设置
- 检查IP白名单配置

#### 4. 策略不执行交易
- 检查AI信号置信度是否达到阈值
- 检查账户余额是否足够
- 检查持仓是否达到上限

### 调试方法
1. **增加日志级别**: 修改策略中的 `LOG_LEVEL: "debug"`
2. **手动测试**: 使用curl测试各个API接口
3. **分步调试**: 先测试AI信号，再测试交易执行

## 📈 性能优化建议

### 策略优化
1. **动态仓位**: 根据市场波动率调整仓位
2. **多时间框架**: 结合不同时间框架的信号
3. **信号过滤**: 添加额外的技术指标过滤
4. **机器学习**: 使用历史数据训练信号模型

### 系统优化
1. **缓存机制**: 缓存AI分析结果，减少API调用
2. **异步处理**: 使用消息队列处理交易信号
3. **监控告警**: 设置交易异常告警
4. **备份恢复**: 定期备份策略配置和交易数据

## 🔄 更新和维护

### 定期检查
1. **每日**: 检查交易日志和账户余额
2. **每周**: 分析策略性能，调整参数
3. **每月**: 全面检查系统安全性和稳定性

### 版本管理
1. **策略版本**: 记录策略代码的版本变化
2. **配置备份**: 备份重要的配置文件
3. **数据备份**: 定期备份交易历史数据

## 🎉 成功部署的标志

1. ✅ AI分析系统正常运行
2. ✅ FMZ策略成功创建并保存
3. ✅ FMZ托管者正常运行
4. ✅ 策略能够获取AI信号
5. ✅ 策略能够执行交易
6. ✅ 交易记录正确无误
7. ✅ 风险控制正常运作

## 📞 支持资源

- FMZ官方文档: https://www.fmz.com/bbs
- FMZ GitHub: https://github.com/fmzquant
- 币安API文档: https://binance-docs.github.io/apidocs/
- AI分析系统代码: 当前目录

---

**🎯 现在你已经准备好将AI量化交易策略部署到FMZ平台了！**

**建议流程:**
1. 先在模拟账户测试
2. 小额真实资金测试
3. 逐步优化策略参数
4. 监控交易表现
5. 定期调整和优化

**记住: 量化交易有风险，请谨慎操作，从小额开始！**