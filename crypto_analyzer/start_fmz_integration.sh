#!/bin/bash
# FMZ集成系统启动脚本

set -e

echo "=========================================="
echo "FMZ发明者量化平台集成系统启动"
echo "=========================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到python3，请先安装Python3"
    exit 1
fi

# 检查依赖
echo "检查Python依赖..."
python3 -c "import flask, requests, yaml" 2>/dev/null || {
    echo "安装Python依赖..."
    pip install -r requirements_fmz.txt 2>/dev/null || {
        echo "创建requirements_fmz.txt..."
        cat > requirements_fmz.txt << EOF
flask>=2.3.0
flask-cors>=4.0.0
requests>=2.31.0
pyyaml>=6.0
EOF
        pip install -r requirements_fmz.txt
    }
}

# 检查配置文件
CONFIG_FILE="config/fmz_config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "配置文件不存在，已创建模板: $CONFIG_FILE"
    echo "请编辑配置文件，填写你的FMZ API Key和Secret Key"
    read -p "按回车键继续..." </dev/tty
fi

# 启动AI分析系统（如果未运行）
echo "检查AI分析系统..."
if ! curl -s http://localhost:5000/api/status >/dev/null 2>&1; then
    echo "AI分析系统未运行，正在启动..."
    cd web_dashboard
    python3 app.py > /tmp/ai_server.log 2>&1 &
    AI_PID=$!
    echo "AI分析系统启动中(PID: $AI_PID)..."
    sleep 5
    
    # 检查是否启动成功
    if curl -s http://localhost:5000/api/status >/dev/null 2>&1; then
        echo "✓ AI分析系统启动成功"
    else
        echo "✗ AI分析系统启动失败，请检查日志: /tmp/ai_server.log"
        exit 1
    fi
    cd ..
else
    echo "✓ AI分析系统已在运行"
fi

# 启动FMZ API服务
echo "启动FMZ API服务..."
python3 src/fmz/fmz_api.py > /tmp/fmz_api.log 2>&1 &
FMZ_API_PID=$!
echo "FMZ API服务启动中(PID: $FMZ_API_PID)..."
sleep 3

# 检查FMZ API是否启动成功
if curl -s http://localhost:5001/api/fmz/status >/dev/null 2>&1; then
    echo "✓ FMZ API服务启动成功"
else
    echo "✗ FMZ API服务启动失败，请检查日志: /tmp/fmz_api.log"
    exit 1
fi

# 测试集成
echo "测试AI-FMZ集成..."
python3 -c "
import sys
sys.path.append('.')
from src.fmz.ai_fmz_integration import AIFMZIntegrator

integrator = AIFMZIntegrator(
    ai_api_url='http://localhost:5000',
    fmz_api_url='http://localhost:5001',
    min_confidence=60
)

ai_ok = integrator.check_ai_api_status()
fmz_ok = integrator.check_fmz_api_status()

if ai_ok and fmz_ok:
    print('✓ AI-FMZ集成测试通过')
else:
    print('✗ AI-FMZ集成测试失败')
    print(f'  AI API: {\"正常\" if ai_ok else \"异常\"}')
    print(f'  FMZ API: {\"正常\" if fmz_ok else \"异常\"}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✓ 集成测试通过"
else
    echo "✗ 集成测试失败"
    exit 1
fi

# 显示服务信息
echo ""
echo "=========================================="
echo "服务启动完成"
echo "=========================================="
echo "AI分析系统: http://localhost:5000"
echo "FMZ API服务: http://localhost:5001"
echo ""
echo "可用端点:"
echo "  GET  http://localhost:5001/api/fmz/status"
echo "  GET  http://localhost:5001/api/fmz/balance"
echo "  POST http://localhost:5001/api/fmz/execute-signal"
echo ""
echo "测试命令:"
echo "  获取AI分析: curl -X POST http://localhost:5000/api/analyze -H 'Content-Type: application/json' -d '{\"symbol\":\"BTC\",\"timeframe\":\"1h\",\"ai_model\":\"both\"}'"
echo "  执行信号: curl -X POST http://localhost:5001/api/fmz/execute-signal -H 'Content-Type: application/json' -d '{\"symbol\":\"BTC_USDT\",\"direction\":\"buy\",\"confidence\":75}'"
echo ""
echo "日志文件:"
echo "  AI分析系统: /tmp/ai_server.log"
echo "  FMZ API服务: /tmp/fmz_api.log"
echo ""
echo "按Ctrl+C停止所有服务"
echo "=========================================="

# 等待用户中断
trap 'echo "停止服务..."; kill $AI_PID $FMZ_API_PID 2>/dev/null; exit 0' INT TERM
wait