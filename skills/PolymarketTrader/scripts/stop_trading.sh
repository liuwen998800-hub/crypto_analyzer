#!/bin/bash
# 停止 Polymarket BTC 自动交易系统

echo "============================================"
echo "⏹️  停止 Polymarket BTC 交易系统"
echo "============================================"

# 停止自动交易机器人
echo "📊 停止自动交易机器人..."
pkill -f auto_trader.py

# 停止Dashboard
echo "🌐 停止Dashboard..."
pkill -f trading_dashboard.py

echo ""
echo "✅ 已全部停止"
echo "============================================"
