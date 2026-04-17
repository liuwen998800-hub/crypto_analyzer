#!/bin/bash
# Polymarket BTC 自动交易系统启动器

echo "============================================"
echo "🚀 Polymarket BTC 交易系统"
echo "============================================"
echo ""

# 启动自动交易机器人
echo "📊 启动自动交易机器人..."
cd /home/billyqqq/.openclaw/workspace
nohup python3 -u auto_trader.py > logs/auto_trader_$(date +%Y%m%d_%H%M%S).log 2>&1 &
TRADER_PID=$!
echo "   PID: $TRADER_PID"

sleep 1

# 启动Dashboard
echo "🌐 启动Dashboard..."
nohup python3 trading_dashboard.py > /dev/null 2>&1 &
DASH_PID=$!
echo "   PID: $DASH_PID"
echo ""
echo "============================================"
echo "✅ 交易系统已启动!"
echo "   Dashboard: http://localhost:5000"
echo "   日志: /home/billyqqq/.openclaw/workspace/logs/"
echo "============================================"
