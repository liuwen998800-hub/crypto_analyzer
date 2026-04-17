#!/bin/bash
# 简化版虚拟币分析系统启动脚本

echo "🚀 启动简化版虚拟币分析系统"
echo "================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查Flask是否安装
if ! python3 -c "import flask" 2>/dev/null; then
    echo "📦 安装Flask..."
    python3 -m pip install flask --quiet --break-system-packages
fi

# 停止可能存在的旧进程
echo "🛑 停止旧服务..."
pkill -f "python.*app_simple.py" 2>/dev/null
sleep 2

# 创建日志目录
mkdir -p logs

# 启动服务
echo "🚀 启动简化版Web服务..."
cd "$(dirname "$0")"
nohup python3 app_simple.py > logs/app_simple.log 2>&1 &
SIMPLE_PID=$!

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo "🔍 检查服务状态..."
if curl -s http://localhost:5003/api/status > /dev/null; then
    echo "✅ 简化版服务已启动 (PID: $SIMPLE_PID)"
    echo "🌐 访问地址: http://localhost:5003"
    echo "📊 增强版仪表板: http://localhost:5003/enhanced"
    
    # 显示API端点
    echo ""
    echo "📡 API端点:"
    echo "  POST /api/analyze      - 分析单个币种"
    echo "  POST /api/analyze/batch - 批量分析"
    echo "  GET  /api/symbols      - 获取币种列表"
    echo "  GET  /api/status       - 系统状态"
    echo "  GET  /api/history/<symbol> - 分析历史"
    echo "  GET  /api/config       - 系统配置"
    
    # 保存PID
    echo $SIMPLE_PID > logs/simple.pid
    
    # 显示日志文件位置
    echo ""
    echo "📝 日志文件:"
    echo "  - 应用日志: logs/app_simple.log"
    echo "  - PID文件: logs/simple.pid"
    
    # 显示启动命令
    echo ""
    echo "🔧 管理命令:"
    echo "  停止服务: pkill -f 'python.*app_simple.py'"
    echo "  查看日志: tail -f logs/app_simple.log"
    echo "  重启服务: ./start_simple.sh"
    
else
    echo "❌ 服务启动失败，请检查日志"
    echo "📝 查看日志: tail -f logs/app_simple.log"
    exit 1
fi

echo ""
echo "🎉 简化版虚拟币分析系统启动完成！"
echo "================================"