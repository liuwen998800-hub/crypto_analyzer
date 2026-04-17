#!/bin/bash
# =========================================
# 虚拟币AI分析系统 - 启动脚本
# =========================================
# 
# 功能：
#   - DeepSeek + MiniMax 双AI模型独立分析
#   - 实时市场价格获取 (Binance)
#   - 恐惧贪婪指数
#   - 技术指标分析
#   - 支撑阻力位计算
#   - 多空置信率分析
#
# 启动后访问: http://localhost:5000/
#
# =========================================

echo "============================================"
echo "🚀 虚拟币AI分析系统启动中..."
echo "============================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: Python3 未安装"
    exit 1
fi

echo "📂 工作目录: $SCRIPT_DIR"
echo ""

# 停止已有服务
echo "🛑 停止已有服务..."
pkill -f "python.*app\.py" 2>/dev/null
sleep 2

# 启动服务
echo "▶️  启动服务..."
nohup python3 app.py > app.log 2>&1 &
APP_PID=$!

echo "⏳ 等待服务启动..."
sleep 4

# 检查服务是否启动成功
if curl -s http://localhost:5000/api/status > /dev/null 2>&1; then
    echo ""
    echo "============================================"
    echo "✅ 服务启动成功！"
    echo "============================================"
    echo ""
    echo "🌐 前端地址: http://localhost:5000/"
    echo "📡 API状态:  http://localhost:5000/api/status"
    echo "📊 分析接口: http://localhost:5000/api/analyze"
    echo ""
    echo "📝 常用操作:"
    echo "   查看日志: tail -f $SCRIPT_DIR/app.log"
    echo "   停止服务: pkill -f \"python.*app\.py\""
    echo "   重启服务: ./start_crypto_analyzer.sh"
    echo ""
    echo "PID: $APP_PID"
    echo "============================================"
else
    echo ""
    echo "❌ 服务启动失败！"
    echo "查看日志: tail -f $SCRIPT_DIR/app.log"
    exit 1
fi