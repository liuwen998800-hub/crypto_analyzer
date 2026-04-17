#!/bin/bash
# Web仪表板启动脚本

set -e

echo "================================================================"
echo "虚拟币分析仪表板 - 启动脚本"
echo "================================================================"

# 检查Python
echo "检查Python环境..."
python3 --version || { echo "❌ 需要Python 3.8或更高版本"; exit 1; }

# 检查Flask
echo "检查Flask..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "安装Flask..."
    python3 -m pip install --user flask || { echo "❌ Flask安装失败"; exit 1; }
fi

# 检查Chart.js依赖
echo "检查前端依赖..."
if ! python3 -c "import requests" 2>/dev/null; then
    echo "安装requests..."
    python3 -m pip install --user requests || { echo "❌ requests安装失败"; exit 1; }
fi

# 创建必要的目录
echo "创建目录结构..."
mkdir -p ../results
mkdir -p ../logs

# 检查是否有分析结果
if [ ! -f "../results/latest.json" ]; then
    echo "⚠️  未找到分析结果，正在运行一次分析..."
    cd ..
    python3 simple_analysis.py
    cd web_dashboard
fi

# 启动Web服务器
echo "启动Web服务器..."
echo ""
echo "================================================================"
echo "仪表板已启动！"
echo ""
echo "访问地址: http://localhost:5000"
echo "API地址:  http://localhost:5000/api/latest"
echo ""
echo "功能说明:"
echo "1. 市场总结 - 查看整体市场情绪和信号分布"
echo "2. 币种分析 - 查看各币种详细信号和价格"
echo "3. 价格图表 - 可视化价格走势和变化"
echo "4. 系统状态 - 查看分析次数和数据大小"
echo "5. 币种详情 - 点击币种卡片查看详细分析"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "================================================================"

python3 app.py