#!/bin/bash
# 虚拟币分析指标产品 - 运行脚本

set -e

echo "================================================================"
echo "虚拟币分析指标产品 - 运行脚本"
echo "================================================================"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行 ./setup.sh"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查配置文件
if [ ! -f "config/api_keys.yaml" ]; then
    echo "⚠️  配置文件不存在，正在创建..."
    cp config/api_keys.example.yaml config/api_keys.yaml
    echo "✅ 已创建配置文件，请编辑 config/api_keys.yaml 配置API密钥"
    exit 1
fi

# 显示菜单
echo ""
echo "请选择运行模式:"
echo "1. 测试连接"
echo "2. 运行一次分析"
echo "3. 启动调度服务"
echo "4. 生成每日报告"
echo "5. 查看最新结果"
echo "6. 退出"
echo ""

read -p "请输入选择 (1-6): " choice

case $choice in
    1)
        echo "运行连接测试..."
        python scripts/test_connection.py
        ;;
    2)
        echo "运行分析..."
        python scripts/hourly_analysis.py
        ;;
    3)
        echo "启动调度服务..."
        echo "按 Ctrl+C 停止服务"
        python scripts/scheduler_service.py
        ;;
    4)
        echo "生成每日报告..."
        # 这里可以调用专门的报告生成脚本
        echo "功能开发中..."
        ;;
    5)
        echo "查看最新结果..."
        if [ -f "results/latest.json" ]; then
            python -c "
import json
with open('results/latest.json', 'r') as f:
    data = json.load(f)
    
print('最新分析结果:')
print('=' * 60)
print(f'时间: {data.get(\"timestamp\", \"未知\")}')
print(f'分析币种: {len(data.get(\"results\", {}))}个')

market_summary = data.get('market_summary', {})
print(f'市场情绪: {market_summary.get(\"market_sentiment\", \"未知\").upper()}')

print('\\n各币种信号:')
for symbol, result in data.get('results', {}).items():
    if result.get('error', False):
        print(f'  {symbol}: ❌ 分析失败')
    else:
        signal = result.get('trading_signal', {})
        price = result.get('market_data', {}).get('price', 0)
        print(f'  {symbol}: {signal.get(\"signal\", \"UNKNOWN\")} (分数: {signal.get(\"score\", 0)}, 价格: \${price:,.2f})')

print('=' * 60)
            "
        else
            echo "❌ 未找到最新结果，请先运行分析"
        fi
        ;;
    6)
        echo "退出"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "================================================================"
echo "运行完成"
echo "================================================================"