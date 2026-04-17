# 虚拟币分析指标产品 - 项目结构

## 目录结构

```
crypto_analyzer/
├── README.md                    # 项目说明
├── PROJECT_STRUCTURE.md         # 项目结构文档
├── requirements.txt             # Python依赖
├── setup.sh                     # 安装脚本
├── run.sh                       # 运行脚本
│
├── config/                      # 配置文件
│   ├── api_keys.example.yaml   # API密钥示例
│   ├── api_keys.yaml           # API密钥配置（安装后创建）
│   └── scoring_rules.yaml      # 评分规则配置
│
├── src/                         # 源代码
│   ├── data_fetchers/          # 数据获取模块
│   │   └── binance_fetcher.py  # Binance数据获取
│   │
│   ├── technical/              # 技术分析模块
│   │   └── indicators_calculator.py  # 技术指标计算
│   │
│   ├── ai_models/              # AI分析模块
│   │   └── dual_ai_analyzer.py # 双模型AI分析
│   │
│   ├── sentiment/              # 情绪分析模块
│   │   └── fear_greed_analyzer.py  # 恐慌贪婪指数
│   │
│   └── signals/                # 信号生成模块
│       └── composite_signal_generator.py  # 综合信号生成
│
├── scripts/                     # 运行脚本
│   ├── hourly_analysis.py      # 每小时分析主脚本
│   ├── scheduler_service.py    # 调度服务
│   └── test_connection.py      # 连接测试
│
├── logs/                        # 日志目录（自动创建）
├── results/                     # 分析结果（自动创建）
├── reports/                     # 报告文件（自动创建）
└── data/                        # 数据缓存（自动创建）
```

## 模块说明

### 1. 数据获取模块 (`src/data_fetchers/`)
- **功能**: 从Binance获取实时价格和历史数据
- **支持币种**: BTC, ETH, SOL
- **数据包括**: 价格、成交量、24小时变化、订单簿等
- **特点**: 无需API密钥（免费层），支持模拟数据

### 2. 技术分析模块 (`src/technical/`)
- **功能**: 计算技术指标并评分
- **指标包括**: RSI, MACD, 移动平均线, 布林带, 成交量
- **评分体系**: 基于现有Polymarket交易系统
- **输出**: 技术评分、支撑阻力位、置信度

### 3. AI分析模块 (`src/ai_models/`)
- **功能**: 使用DeepSeek和MiniMax双模型分析
- **特点**: 双模型互补，提高分析可靠性
- **输出**: AI评分、趋势判断、交易建议、一致性评分

### 4. 情绪分析模块 (`src/sentiment/`)
- **功能**: 计算市场恐慌贪婪指数
- **数据源**: Alternative.me API + 模拟数据
- **输出**: 情绪分数、市场情绪、对技术分析的影响权重

### 5. 信号生成模块 (`src/signals/`)
- **功能**: 综合技术+AI+情绪生成交易信号
- **权重分配**: 技术40% + AI40% + 情绪20%
- **输出**: 交易信号、置信度、目标价位、止损位、风险评估

## 运行流程

### 单次分析流程
```
数据获取 → 技术分析 → AI分析 → 情绪分析 → 信号生成 → 结果保存
   ↓          ↓          ↓          ↓          ↓          ↓
Binance    指标计算  双模型分析  恐慌指数  综合信号   JSON/CSV
```

### 调度服务流程
```
启动调度 → 每小时分析 → 结果保存 → 每日报告 → 持续运行
   ↓          ↓          ↓          ↓          ↓
Background  定时任务  本地存储  汇总分析  7x24小时
Scheduler
```

## 输出格式

### 每小时分析结果 (`results/analysis_YYYYMMDD_HHMMSS.json`)
```json
{
  "timestamp": "2026-04-16T03:00:00",
  "symbols_analyzed": ["BTC", "ETH", "SOL"],
  "results": {
    "BTC": {
      "market_data": { ... },
      "technical_analysis": { ... },
      "ai_analysis": { ... },
      "sentiment_analysis": { ... },
      "trading_signal": {
        "signal": "BUY",
        "score": 75,
        "confidence": 0.8,
        "trading_advice": { ... }
      }
    }
  },
  "market_summary": { ... }
}
```

### 交易信号详情
```json
{
  "signal": "STRONG_BUY",
  "score": 85,
  "confidence": 0.9,
  "description": "强烈买入 - 技术、AI、情绪指标均显示强烈看涨",
  "trading_advice": {
    "action": "积极买入",
    "position_sizing": "可重仓",
    "timing": "立即或分批买入",
    "target_prices": [67000, 68500],
    "stop_loss": 61400
  },
  "key_levels": {
    "supports": [61400, 60000],
    "resistances": [67000, 68500]
  },
  "risk_assessment": {
    "risk_level": "低风险",
    "recommended_position_pct": 75
  }
}
```

## 配置说明

### API密钥配置 (`config/api_keys.yaml`)
```yaml
# Binance API (可选)
binance:
  api_key: ""
  api_secret: ""

# DeepSeek API (必需)
deepseek:
  api_key: "sk-xxxxxxxxxxxx"
  model: "deepseek-chat"

# MiniMax API (必需)
minimax:
  api_key: "xxxxxxxxxxxx"
  model: "MiniMax-M2.7"
```

### 评分规则配置 (`config/scoring_rules.yaml`)
```yaml
# 权重分配
scoring_weights:
  technical: 0.4
  ai_analysis: 0.4
  sentiment: 0.2

# 信号阈值
signal_thresholds:
  strong_buy: 80
  buy: 60
  neutral: 40
  sell: 20
  strong_sell: 0
```

## 部署说明

### 开发环境
```bash
# 1. 克隆项目
git clone <repository>
cd crypto_analyzer

# 2. 安装依赖
./setup.sh

# 3. 配置API密钥
vim config/api_keys.yaml

# 4. 测试运行
./run.sh
```

### 生产环境
```bash
# 使用systemd服务
sudo cp crypto_analyzer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable crypto_analyzer
sudo systemctl start crypto_analyzer

# 查看日志
sudo journalctl -u crypto_analyzer -f
```

## 扩展说明

### 添加新币种
1. 在 `src/data_fetchers/binance_fetcher.py` 的 `symbol_map` 中添加映射
2. 在 `scripts/hourly_analysis.py` 的 `analyze_all_symbols` 中添加币种

### 添加新指标
1. 在 `src/technical/indicators_calculator.py` 中添加计算函数
2. 在 `config/scoring_rules.yaml` 中添加评分规则
3. 更新权重分配

### 集成新数据源
1. 在 `src/data_fetchers/` 中添加新的数据获取类
2. 在 `src/sentiment/` 中添加新的情绪分析类
3. 更新主分析流程

## 故障排除

### 常见问题
1. **Binance API连接失败**: 检查网络连接，可能需要代理
2. **AI分析失败**: 检查API密钥配置和余额
3. **TA-Lib安装失败**: 使用 `pip install ta` 作为备选
4. **内存不足**: 减少历史数据天数或分析频率

### 日志查看
```bash
# 查看分析日志
tail -f logs/analysis.log

# 查看调度日志
tail -f logs/scheduler.log

# 查看错误日志
grep -i error logs/*.log
```

## 性能优化

### 数据缓存
- 价格数据缓存5分钟
- 技术指标计算结果缓存
- 情绪指数缓存5分钟

### 资源控制
- 限制历史数据天数（默认30天）
- 控制API调用频率
- 使用异步请求（可扩展）

### 内存管理
- 及时清理临时数据
- 使用生成器处理大数据
- 分块处理历史数据