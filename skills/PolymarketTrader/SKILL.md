---
name: polymarket-trader
version: "1.0.0"
description: Polymarket BTC 5分钟三信号自动交易系统
author: user
license: MIT
---

# Polymarket BTC 自动交易系统

## 功能
- 三信号确认：技术指标 + AI分析 + 币安价差
- 仓位分级：2信号$2 / 3信号$3 / 3信号+AI≥65%$5
- 止盈止损：止损20% / 止盈30%
- Web控制面板
- 统一回测框架

## 启动交易系统
```bash
cd /home/billyqqq/.openclaw/workspace
python3 -u auto_trader.py
```

## 启动Dashboard
```bash
cd /home/billyqqq/.openclaw/workspace
python3 trading_dashboard.py
```

## Dashboard访问
http://localhost:5000

## 文件结构
- auto_trader.py - 自动交易机器人
- analyze_for_trading.py - 三信号分析
- polymarket_live_trader.py - 核心库
- trading_dashboard.py - Web控制面板
- backtest.py - 统一回测入口
- backtest_framework.py - 回测引擎核心

## 三信号说明
1. 技术指标 - BTC价格动量分析
2. AI分析 - DeepSeek置信度
3. 币安价差 - BTC价格偏离度
   - >+0.1% → 做多 YES
   - <-0.25% → 做空 NO

## 仓位规则
- 2信号一致 → $2
- 3信号一致 → $3
- 3信号 + AI≥65% → $5

## 回测框架
```bash
# 统一回测入口
python3 backtest.py --help

# 运行基本回测
python3 backtest.py --run

# 参数优化
python3 backtest.py --optimize

# 完整流程
python3 backtest.py --all
```
