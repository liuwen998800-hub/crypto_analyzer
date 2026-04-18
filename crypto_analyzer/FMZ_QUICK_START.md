# 🚀 FMZ平台快速入门指南

## 📋 系统状态

✅ **AI分析系统**: 运行正常 (端口5000)  
✅ **FMZ集成API**: 运行正常 (端口5001)  
✅ **FMZ API Key**: 已验证有效  
✅ **策略模板**: 已创建  

## 🔑 你的FMZ API Key

```
AccessKey: 74c1c98076616ccb54015c18c5ae7950
SecretKey: a4418a9b969650012682b54f5b578933
```

## 🎯 一键启动所有服务

```bash
cd /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer
./start_all_services.sh
```

## 🌐 服务访问地址

1. **AI分析面板**: http://localhost:5000
   - 实时市场分析
   - 双AI模型预测
   - 技术指标图表

2. **FMZ集成API**: http://localhost:5001
   - 状态检查: `/api/fmz/status`
   - 余额查询: `/api/fmz/balance`
   - 信号执行: `/api/fmz/execute-signal`

## 📝 配置步骤

### 步骤1: 配置FMZ平台

1. **登录FMZ平台**: https://www.fmz.com
2. **添加交易所API**:
   - 进入"控制中心" → "交易所"
   - 添加币安(Binance)或其他交易所
   - 获取交易所的API Key和Secret Key
   - ⚠️ **重要**: 启用只读权限，禁用提现权限

3. **创建策略**:
   - 进入"策略库" → "新建策略"
   - 策略名称: `AI量化策略`
   - 编程语言: JavaScript
   - 复制策略模板代码: `fmz_ai_strategy_template.js`

### 步骤2: 启动FMZ托管者

FMZ策略需要在托管者(Docker容器)上运行:

```bash
# 安装Docker (如果未安装)
# 参考: https://docs.docker.com/get-docker/

# 运行FMZ托管者
docker run -d --name fmz-worker \
  -e ACCESS_KEY=74c1c98076616ccb54015c18c5ae7950 \
  -e SECRET_KEY=a4418a9b969650012682b54f5b578933 \
  fmzquant/worker:latest

# 查看托管者日志
docker logs -f fmz-worker
```

### 步骤3: 运行策略

1. 在FMZ平台选择创建的策略
2. 点击"回测"测试策略
3. 点击"实盘"运行策略
4. 选择配置的交易所
5. 设置交易参数

## 🧪 测试流程

### 测试1: AI分析系统
```bash
curl http://localhost:5000/api/analyze
```

### 测试2: FMZ集成API
```bash
curl http://localhost:5001/api/fmz/status
```

### 测试3: 完整集成测试
```bash
python3 test_fmz_simple.py
```

### 测试4: 详细集成测试
```bash
python3 test_fmz_integration.py
```

## ⚙️ 配置说明

### AI分析系统配置
- 端口: 5000
- 数据源: 币安实时数据
- AI模型: DeepSeek + MiniMax双模型
- 分析频率: 每小时自动分析

### FMZ集成配置
- 端口: 5001
- 最小置信度: 60%
- 交易对: BTC_USDT (默认)
- 交易所: binance (默认)

### 风险控制参数
```yaml
# 在 config/fmz_config.yaml 中配置
min_confidence: 60      # 最小置信度
max_daily_trades: 10    # 每日最大交易次数
position_size: 0.001    # 每次交易仓位
stop_loss: 5           # 止损百分比
take_profit: 10        # 止盈百分比
```

## 🔄 工作流程

```
AI分析系统 (5000)
       ↓
   分析市场数据
       ↓
   生成交易信号
       ↓
FMZ集成API (5001)
       ↓
   验证信号置信度
       ↓
   执行FMZ API调用
       ↓
FMZ平台
       ↓
   执行实际交易
       ↓
   返回交易结果
```

## 📊 监控和日志

### 日志文件
- `logs/ai_system.log` - AI分析系统日志
- `logs/fmz_api.log` - FMZ集成API日志
- `logs/fmz_integration.log` - 集成测试日志

### 实时监控
```bash
# 查看所有日志
tail -f logs/*.log

# 查看AI分析日志
tail -f logs/ai_system.log

# 查看FMZ API日志
tail -f logs/fmz_api.log
```

## 🛑 停止服务

```bash
# 方法1: 使用停止脚本
./stop_all_services.sh

# 方法2: 手动停止
pkill -f "python3 web_dashboard/app.py"
pkill -f "python3 src/fmz/fmz_api.py"
pkill -f "python3 src/fmz/ai_fmz_integration.py"

# 停止FMZ托管者
docker stop fmz-worker
docker rm fmz-worker
```

## ⚠️ 重要提醒

1. **风险提示**: 加密货币交易存在高风险，可能损失全部资金
2. **测试优先**: 先用模拟账户测试，再用小额真实资金
3. **监控仓位**: 严格控制仓位大小，避免过度交易
4. **定期备份**: 定期备份配置文件和策略代码
5. **更新维护**: 定期更新系统和策略

## 🆘 故障排除

### 问题1: API连接失败
```bash
# 检查网络连接
ping www.fmz.com

# 检查API Key
python3 -c "
import requests
r = requests.get('https://www.fmz.com/api/v1', timeout=5)
print('状态码:', r.status_code)
"
```

### 问题2: 服务无法启动
```bash
# 检查端口占用
lsof -i :5000
lsof -i :5001

# 查看错误日志
cat logs/ai_system.log | tail -20
cat logs/fmz_api.log | tail -20
```

### 问题3: 交易未执行
1. 检查FMZ托管者是否运行: `docker ps | grep fmz-worker`
2. 检查交易所API配置是否正确
3. 检查账户是否有足够余额
4. 查看FMZ平台交易日志

## 📞 支持资源

- FMZ官方文档: https://www.fmz.com/bbs
- FMZ GitHub: https://github.com/fmzquant
- AI分析系统代码: 当前目录
- 问题反馈: 查看日志文件

---

**🎉 配置完成！现在你可以开始使用AI驱动的量化交易系统了。**

**建议流程:**
1. 运行 `./start_all_services.sh`
2. 访问 http://localhost:5000 查看AI分析
3. 配置FMZ平台交易所API
4. 启动FMZ托管者
5. 创建并运行AI策略
6. 从小额交易开始，逐步优化