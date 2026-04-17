#!/bin/bash

echo "🚀 启动修复版5000端口服务"
echo "=========================="

# 停止现有服务
echo "🛑 停止现有服务..."
pkill -f "python.*app\.py" 2>/dev/null
sleep 2

# 启动新服务
echo "▶️  启动服务..."
cd "$(dirname "$0")"
nohup python3 app.py > app_fixed.log 2>&1 &
PID=$!

echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo "🔍 检查服务状态..."
if curl -s http://localhost:5000/api/status > /dev/null; then
    echo "✅ 服务启动成功 (PID: $PID)"
    
    # 测试前端页面
    echo "🌐 测试前端页面..."
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/)
    if [ "$HTTP_STATUS" = "200" ]; then
        echo "✅ 前端页面正常 (HTTP 200)"
        
        # 获取页面标题
        TITLE=$(curl -s http://localhost:5000/ | grep -o '<title>[^<]*</title>' | sed 's/<title>//;s/<\/title>//')
        echo "📄 页面标题: $TITLE"
        
        echo ""
        echo "🎉 服务启动完成！"
        echo "=================="
        echo "访问地址: http://localhost:5000/"
        echo "API状态: http://localhost:5000/api/status"
        echo "增强版: http://localhost:5000/enhanced"
        echo "简单版: http://localhost:5000/simple"
        echo "测试页: http://localhost:5000/test"
        echo "原始版: http://localhost:5000/original"
        echo "=================="
        echo "日志文件: app_fixed.log"
        echo "停止命令: pkill -f \"python.*app\.py\""
    else
        echo "❌ 前端页面异常 (HTTP $HTTP_STATUS)"
        echo "查看日志: tail -f app_fixed.log"
    fi
else
    echo "❌ 服务启动失败"
    echo "查看日志: tail -f app_fixed.log"
fi