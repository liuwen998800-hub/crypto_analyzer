# 🚀 虚拟币AI分析系统 - 使用说明

## 📦 备份文件说明

本备份包含完整的虚拟币AI分析系统，包含：
- ✅ 后端API服务 (Flask)
- ✅ 前端Web界面 
- ✅ 配置文件
- ✅ 启动脚本

## 🌐 访问地址

**前端界面**: http://localhost:5000/

## 🚀 启动命令

```bash
# 方法1: 使用启动脚本
cd /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/backups/web_dashboard
./start_crypto_analyzer.sh

# 方法2: 手动启动
cd /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/backups/web_dashboard
python3 app.py

# 方法3: 后台运行
nohup python3 app.py > app.log 2>&1 &
```

## 📊 功能列表

### 1. 双AI模型分析
- **DeepSeek**: 专业技术分析，提供多空置信率和关键支撑阻力位
- **MiniMax**: 市场情绪分析，提供恐慌指数和风险评估
- **双模型比对**: 计算共识方向和一致性评分

### 2. 实时数据
- Binance实时市场价格
- 24小时涨跌幅度
- 恐惧贪婪指数

### 3. 技术指标
- RSI (相对强弱指标)
- MACD (指数平滑异同移动平均线)
- 移动平均线
- 布林带

### 4. 支撑阻力位
- 3个级别的支撑位 (强/中/弱)
- 3个级别的阻力位 (强/中/弱)
- 每个位置包含强度评分

### 5. 信号系统
- STRONG_BUY (≥80分): 强烈买入
- BUY (≥60分): 买入
- NEUTRAL (≥40分): 观望
- SELL (≥20分): 卖出
- STRONG_SELL (<20分): 强烈卖出

## 📡 API接口

### 主要接口

```bash
# 分析单个币种
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC","timeframe":"1h","ai_model":"both"}'

# 批量分析
curl -X POST http://localhost:5000/api/analyze/batch \
  -H "Content-Type: application/json" \
  -d '{"symbols":["BTC","ETH","SOL"],"timeframe":"1h"}'

# 系统状态
curl http://localhost:5000/api/status
```

### 参数说明
- `symbol`: BTC / ETH / SOL
- `timeframe`: 1h / 4h / 24h
- `ai_model`: both / deepseek / minimax

## 🔧 配置文件

配置文件位于 `config/api_keys.yaml`：

```yaml
deepseek:
  api_key: "sk_live_xxxxx"  # DeepSeek API密钥

minimax:
  api_key: "sk-cp-xxxxx"      # MiniMax API密钥
  group_id: ""               # Group ID (如需要)
```

## 📁 文件结构

```
backups/
├── web_dashboard/
│   ├── app.py              # 主程序 (使用这个启动)
│   ├── start_crypto_analyzer.sh  # 启动脚本
│   ├── templates/
│   │   └── final_dashboard.html  # 前端页面
│   └── config/
│       └── api_keys.yaml   # API密钥配置
└── README.md               # 本说明文件
```

## ⚠️ 注意事项

1. **API密钥**: 如需使用真实AI分析，请配置DeepSeek/MiniMax的API密钥
2. **端口占用**: 确保5000端口未被占用
3. **依赖**: 需要Python3和Flask框架

## 🔄 常用命令

```bash
# 停止服务
pkill -f "python.*app\.py"

# 查看日志
tail -f app.log

# 重启服务
./start_crypto_analyzer.sh

# 检查服务状态
curl http://localhost:5000/api/status
```

## 📞 技术支持

如有问题，请检查：
1. app.log 日志文件
2. 端口5000是否被占用
3. Python3是否安装
4. 防火墙设置

---

*最后更新: 2026-04-16*
*版本: v2.0 双模型版*