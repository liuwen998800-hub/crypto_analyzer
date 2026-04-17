#!/bin/bash
# 增强版虚拟币分析系统启动脚本

echo "🚀 启动增强版虚拟币分析系统"
echo "================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查依赖
echo "📦 检查Python依赖..."
REQUIREMENTS_FILE="../requirements.txt"
if [ -f "$REQUIREMENTS_FILE" ]; then
    pip3 install -r "$REQUIREMENTS_FILE" --quiet
else
    pip3 install flask flask-cors numpy pandas pyyaml requests aiohttp schedule --quiet
fi

# 检查配置文件
CONFIG_FILE="../config/api_keys.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️  配置文件不存在，创建示例配置..."
    cp "../config/api_keys.example.yaml" "$CONFIG_FILE"
    echo "📝 请编辑 $CONFIG_FILE 配置API密钥"
fi

# 停止可能存在的旧进程
echo "🛑 停止旧服务..."
pkill -f "python.*app_enhanced.py" 2>/dev/null
sleep 2

# 创建日志目录
mkdir -p logs

# 启动服务
echo "🚀 启动增强版Web服务..."
cd "$(dirname "$0")"
nohup python3 app_enhanced.py > logs/app_enhanced.log 2>&1 &
ENHANCED_PID=$!

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo "🔍 检查服务状态..."
if curl -s http://localhost:5001/api/status > /dev/null; then
    echo "✅ 增强版服务已启动 (PID: $ENHANCED_PID)"
    echo "🌐 访问地址: http://localhost:5001"
    echo "📊 增强版仪表板: http://localhost:5001/enhanced"
    
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
    echo $ENHANCED_PID > logs/enhanced.pid
    
    # 显示日志文件位置
    echo ""
    echo "📝 日志文件:"
    echo "  - 应用日志: logs/app_enhanced.log"
    echo "  - PID文件: logs/enhanced.pid"
    
    # 显示启动命令
    echo ""
    echo "🔧 管理命令:"
    echo "  停止服务: pkill -f 'python.*app_enhanced.py'"
    echo "  查看日志: tail -f logs/app_enhanced.log"
    echo "  重启服务: ./start_enhanced.sh"
    
else
    echo "❌ 服务启动失败，请检查日志"
    echo "📝 查看日志: tail -f logs/app_enhanced.log"
    exit 1
fi

echo ""
echo "🎉 增强版虚拟币分析系统启动完成！"
echo "================================"