# FMZ发明者量化平台集成指南

## 📋 概述

本系统将你的AI分析系统与FMZ（发明者量化平台）对接，实现AI分析信号的自动交易执行。

## 🚀 快速开始

### 1. 准备工作

#### 1.1 获取FMZ API Key
1. 访问 [FMZ官网](https://www.fmz.com)
2. 注册并登录账号
3. 进入"控制中心" → "API管理"
4. 创建API Key，获取：
   - `api_key`
   - `secret_key`

#### 1.2 配置系统
```bash
# 进入项目目录
cd /home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer

# 编辑配置文件
vim config/fmz_config.yaml
```

修改配置文件中的以下部分：
```yaml
fmz:
  api_key: "你的FMZ_API_KEY"      # ← 修改这里
  secret_key: "你的FMZ_SECRET_KEY" # ← 修改这里
```

### 2. 启动系统

#### 方法一：使用启动脚本（推荐）
```bash
./start_fmz_integration.sh
```

#### 方法二：手动启动
```bash
# 1. 启动AI分析系统（如果未运行）
cd web_dashboard
python3 app.py &

# 2. 启动FMZ API服务
cd ..
python3 src/fmz/fmz_api.py &

# 3. 测试集成
python3 src/fmz/ai_fmz_integration.py
```

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI分析系统    │    │  FMZ集成层      │    │   FMZ平台       │
│  (Flask API)    │────│  (Flask API)    │────│  (量化交易)     │
│  Port: 5000     │    │  Port: 5001     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        │ 1. 获取AI分析          │ 2. 转换信号            │ 3. 执行交易
        │ 3. 返回结果            │ 4. 调用FMZ API         │ 5. 返回结果
        │                        │                        │
```

## 📊 核心功能

### 1. AI信号生成
- 实时获取AI分析结果（DeepSeek + MiniMax）
- 转换为标准交易信号
- 置信度评估和过滤

### 2. FMZ交易执行
- 自动执行买入/卖出信号
- 账户余额和持仓管理
- 订单状态监控

### 3. 风险管理
- 最小置信度过滤（默认60%）
- 交易频率限制
- 信号历史记录

### 4. 监控和统计
- 实时交易统计
- 信号执行历史
- 胜率和收益统计

## 🔧 API接口

### AI分析系统 (Port: 5000)
- `POST /api/analyze` - 获取AI分析
- `GET /api/status` - 系统状态

### FMZ集成服务 (Port: 5001)

#### 状态和账户
- `GET /api/fmz/status` - FMZ连接状态
- `GET /api/fmz/balance` - 账户余额
- `GET /api/fmz/positions` - 持仓信息

#### 策略管理
- `GET /api/fmz/strategies` - 策略列表
- `POST /api/fmz/create-ai-strategy` - 创建AI策略
- `GET /api/fmz/running-strategies` - 运行中的策略

#### 交易执行
- `POST /api/fmz/execute-signal` - 执行AI信号
- `POST /api/fmz/place-order` - 手动下单
- `POST /api/fmz/cancel-order` - 取消订单
- `GET /api/fmz/orders` - 订单列表

#### 监控和控制
- `GET /api/fmz/signal-history` - 信号历史
- `POST /api/fmz/trading-control` - 交易控制开关
- `GET /api/fmz/market-data` - 市场数据

## 💡 使用示例

### 1. 获取AI分析并执行
```bash
# 获取AI分析
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC","timeframe":"1h","ai_model":"both"}'

# 执行AI信号
curl -X POST http://localhost:5001/api/fmz/execute-signal \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC_USDT",
    "direction": "buy",
    "confidence": 75,
    "price": 75000,
    "amount": 0.001
  }'
```

### 2. Python代码集成
```python
from src.fmz.ai_fmz_integration import AIFMZIntegrator

# 创建集成器
integrator = AIFMZIntegrator(
    ai_api_url="http://localhost:5000",
    fmz_api_url="http://localhost:5001",
    min_confidence=60
)

# 分析并执行
result = integrator.analyze_and_execute("BTC", "1h")
print(f"执行结果: {result['status']}")

# 获取统计
stats = integrator.get_trade_stats()
print(f"胜率: {stats['win_rate']:.1f}%")
```

### 3. 自动交易机器人
```python
from src.fmz.ai_fmz_integration import AutoTradingBot, AIFMZIntegrator

# 创建集成器
integrator = AIFMZIntegrator()

# 创建自动交易机器人
bot = AutoTradingBot(
    integrator=integrator,
    interval=300,  # 5分钟检查一次
    symbols=["BTC", "ETH"],  # 监控的币种
    timeframe="1h"  # 时间框架
)

# 启动机器人
bot.start()

# 运行一段时间后停止
import time
time.sleep(3600)  # 运行1小时
bot.stop()
```

## ⚙️ 配置说明

### 主要配置项 (`config/fmz_config.yaml`)

```yaml
fmz:
  api_key: "your_api_key"           # FMZ API Key
  secret_key: "your_secret_key"     # FMZ Secret Key
  base_url: "https://api.fmz.com"   # FMZ API地址
  
  trading:
    min_confidence: 60              # 最小执行置信度
    default_amount:                 # 默认交易数量
      BTC: 0.001
      ETH: 0.01
    max_position_ratio: 0.5         # 最大持仓比例
    
  strategy:
    ai_strategy_name: "AI量化策略"   # 策略名称
    check_interval: 300             # 检查间隔(秒)
    auto_trading: false             # 是否自动交易
```

### 风险管理配置
```yaml
risk_management:
  daily_max_trades: 10              # 每日最大交易次数
  daily_max_loss_ratio: 0.05        # 单日最大亏损比例(5%)
  max_consecutive_losses: 3         # 最大连续亏损次数
  cooldown_minutes: 60              # 冷却时间(分钟)
```

## 🔍 监控和调试

### 日志文件
- AI分析系统: `/tmp/ai_server.log`
- FMZ API服务: `/tmp/fmz_api.log`
- 交易日志: `logs/fmz_trading.log` (如果启用)

### 监控命令
```bash
# 查看服务状态
curl http://localhost:5000/api/status
curl http://localhost:5001/api/fmz/status

# 查看账户余额
curl http://localhost:5001/api/fmz/balance?exchange=binance

# 查看信号历史
curl http://localhost:5001/api/fmz/signal-history?limit=10

# 查看运行中的策略
curl http://localhost:5001/api/fmz/running-strategies
```

### 调试技巧
1. **先测试AI分析**: 确保AI分析系统正常工作
2. **测试FMZ连接**: 检查API Key和网络连接
3. **小额测试**: 先用最小金额测试交易流程
4. **查看日志**: 遇到问题时查看详细日志

## 🛡️ 安全建议

### 1. API Key安全
- 不要将API Key提交到Git仓库
- 使用环境变量或配置文件管理
- 定期更换API Key

### 2. 交易安全
- 先使用模拟交易或小额测试
- 设置合理的止损止盈
- 监控交易频率和风险

### 3. 系统安全
- 使用防火墙限制访问
- 定期备份配置和数据
- 监控系统资源使用

## 🚨 故障排除

### 常见问题

#### 1. FMZ连接失败
```
错误: FMZ API错误: 签名验证失败
```
**解决方案**:
- 检查API Key和Secret Key是否正确
- 检查系统时间是否准确（FMZ使用时间戳签名）
- 检查网络连接

#### 2. 交易执行失败
```
错误: 余额不足
```
**解决方案**:
- 检查账户余额
- 调整交易数量
- 检查交易对是否正确

#### 3. AI分析获取失败
```
错误: AI API不可用
```
**解决方案**:
- 检查AI分析系统是否运行
- 检查网络连接
- 查看AI系统日志

#### 4. 信号置信度过低
```
状态: skipped, 原因: confidence_too_low
```
**解决方案**:
- 调整`min_confidence`配置
- 优化AI分析模型
- 检查市场数据质量

### 调试步骤
1. 检查所有服务是否运行
2. 测试API连接
3. 查看日志文件
4. 简化测试用例
5. 逐步排查问题

## 📈 高级功能

### 1. 自定义策略
修改`src/fmz/fmz_client.py`中的`create_ai_strategy`方法，创建自定义交易策略。

### 2. 多交易所支持
系统支持多个交易所，在配置中设置：
```yaml
exchanges:
  binance:
    api_key: ""
    secret_key: ""
  okex:
    api_key: ""
    secret_key: ""
```

### 3. 回测集成
使用FMZ的回测系统验证AI策略：
```python
# 在FMZ平台上创建回测任务
# 使用AI分析结果作为交易信号
```

### 4. 实时监控面板
可以扩展前端，添加FMZ交易监控面板：
- 实时持仓显示
- 交易信号图表
- 收益曲线

## 📚 相关资源

### 官方文档
- [FMZ API文档](https://www.fmz.com/api)
- [FMZ GitHub仓库](https://github.com/fmzquant)
- [FMZ社区论坛](https://www.fmz.com/bbs)

### 学习资源
- [量化交易入门教程](https://www.fmz.com/bbs-topic/4183)
- [Python量化交易实战](https://www.fmz.com/bbs-topic/463)
- [FMZ策略编写指南](https://www.fmz.com/bbs-topic/91)

### 工具推荐
- [FMZ策略编辑器](https://www.fmz.com/strategy)
- [FMZ回测系统](https://www.fmz.com/backtest)
- [FMZ移动端APP](https://www.fmz.com/mobile)

## 🎯 最佳实践

### 1. 开始阶段
1. 使用模拟账户测试
2. 小额实盘验证
3. 逐步增加资金

### 2. 运行阶段
1. 定期检查系统状态
2. 监控交易统计
3. 及时调整参数

### 3. 优化阶段
1. 分析交易历史
2. 优化AI模型
3. 调整风险参数

## 📞 支持与反馈

如有问题或建议，请：
1. 查看日志文件获取详细错误信息
2. 检查配置文件是否正确
3. 参考FMZ官方文档
4. 在GitHub提交Issue

---

**祝您交易顺利！** 🚀

*最后更新: 2026-04-17*