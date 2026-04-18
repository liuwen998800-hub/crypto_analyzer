#!/bin/bash
# 发送AI分析数据到手机 - 增强版

# 获取当前时间
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DAY_OF_WEEK=$(date '+%A')

echo "🔄 开始生成AI分析报告..."
echo "⏰ 时间: $TIMESTAMP"

# 获取AI分析数据
echo "📡 获取AI分析数据..."
ANALYSIS_JSON=$(curl -s -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC"}')

# 检查API响应
if [ -z "$ANALYSIS_JSON" ] || [ "$ANALYSIS_JSON" = "null" ]; then
    echo "❌ 无法获取AI分析数据"
    echo "💡 请检查:"
    echo "1. AI分析服务是否运行: curl http://localhost:5000/api/status"
    echo "2. 网络连接是否正常"
    exit 1
fi

# 使用Python解析JSON数据
read -r -d '' PYTHON_CODE << 'EOF'
import sys, json

try:
    data = json.loads(sys.stdin.read())
    
    # 获取价格 - 尝试多个可能的字段
    price = None
    price_fields = ['current_price', 'price', 'last_price', 'close']
    
    for field in price_fields:
        if field in data:
            price = data[field]
            break
    
    # 如果还没找到，尝试从嵌套结构中找
    if price is None and 'market_data' in data:
        market_data = data['market_data']
        for field in price_fields:
            if field in market_data:
                price = market_data[field]
                break
    
    # 获取AI分析结果
    ai_analysis = data.get('ai_analysis', {})
    consensus = ai_analysis.get('consensus', {})
    
    # 获取详细分析
    deepseek = ai_analysis.get('deepseek', {})
    minimax = ai_analysis.get('minimax', {})
    
    # 构建结果
    result = {
        'price': f"{price:,.2f}" if price else 'N/A',
        'direction': consensus.get('direction', 'N/A'),
        'confidence': consensus.get('confidence', 0),
        'deepseek_view': consensus.get('deepseek_view', 'N/A'),
        'minimax_view': consensus.get('minimax_view', 'N/A'),
        'agreement_score': consensus.get('agreement_score', 0),
        'reasoning': consensus.get('reasoning', ''),
        'deepseek_recommendation': deepseek.get('recommendation', 'N/A'),
        'minimax_recommendation': minimax.get('recommendation', 'N/A')
    }
    
    # 输出为易于解析的格式
    for key, value in result.items():
        print(f"{key}:{value}")
        
except Exception as e:
    print(f"error:{str(e)}")
EOF

# 执行Python代码解析数据
PARSED_DATA=$(echo "$ANALYSIS_JSON" | python3 -c "$PYTHON_CODE")

# 检查解析是否成功
if echo "$PARSED_DATA" | grep -q "^error:"; then
    ERROR_MSG=$(echo "$PARSED_DATA" | grep "^error:" | cut -d: -f2-)
    echo "❌ 数据解析失败: $ERROR_MSG"
    exit 1
fi

# 提取解析后的数据
PRICE=$(echo "$PARSED_DATA" | grep "^price:" | cut -d: -f2-)
DIRECTION=$(echo "$PARSED_DATA" | grep "^direction:" | cut -d: -f2-)
CONFIDENCE=$(echo "$PARSED_DATA" | grep "^confidence:" | cut -d: -f2-)
DEEPSEEK_VIEW=$(echo "$PARSED_DATA" | grep "^deepseek_view:" | cut -d: -f2-)
MINIMAX_VIEW=$(echo "$PARSED_DATA" | grep "^minimax_view:" | cut -d: -f2-)
AGREEMENT_SCORE=$(echo "$PARSED_DATA" | grep "^agreement_score:" | cut -d: -f2-)
REASONING=$(echo "$PARSED_DATA" | grep "^reasoning:" | cut -d: -f2-)
DEEPSEEK_REC=$(echo "$PARSED_DATA" | grep "^deepseek_recommendation:" | cut -d: -f2-)
MINIMAX_REC=$(echo "$PARSED_DATA" | grep "^minimax_recommendation:" | cut -d: -f2-)

# 设置方向表情符号和颜色
case $DIRECTION in
    "bullish") 
        DIRECTION_EMOJI="📈"
        DIRECTION_COLOR="#2ecc71"  # 绿色
        ;;
    "bearish") 
        DIRECTION_EMOJI="📉"
        DIRECTION_COLOR="#e74c3c"  # 红色
        ;;
    "neutral") 
        DIRECTION_EMOJI="➡️"
        DIRECTION_COLOR="#3498db"  # 蓝色
        ;;
    *) 
        DIRECTION_EMOJI="❓"
        DIRECTION_COLOR="#95a5a6"  # 灰色
        ;;
esac

# 构建消息
MESSAGE="🤖 *BTC AI分析报告*
━━━━━━━━━━━━━━━━
📅 $DAY_OF_WEEK
⏰ $TIMESTAMP

💰 *价格:* \$$PRICE
$DIRECTION_EMOJI *方向:* $DIRECTION
🎯 *置信度:* ${CONFIDENCE}%
🤝 *模型一致度:* ${AGREEMENT_SCORE}%

*🤖 AI模型分析:*
▸ DeepSeek: $DEEPSEEK_VIEW
  建议: $DEEPSEEK_REC
▸ MiniMax: $MINIMAX_VIEW
  建议: $MINIMAX_REC

*📝 市场分析:*
${REASONING:0:120}...

📊 *详细分析:* 
http://localhost:5000
━━━━━━━━━━━━━━━━
#BTC #AI分析 #加密货币"

# 保存消息到文件
echo "$MESSAGE" > /tmp/latest_ai_analysis.txt
echo "✅ 分析报告已生成"

# 输出到控制台
echo ""
echo "=== 📋 报告内容 ==="
echo "$MESSAGE"
echo "=================="
echo ""

# 记录日志
echo "[$(date '+%Y-%m-%d %H:%M:%S')] AI分析报告生成完成 - 方向:$DIRECTION 价格:\$$PRICE" >> /tmp/ai_analysis_cron.log

# 自动发送选项
echo "📱 发送选项:"
echo "1. 📧 QQ邮箱: ./send_via_qq_email.sh"
echo "2. 💬 微信(Server酱): ./send_via_wechat_serverchan.sh"
echo "3. 📲 微信/QQ(PushPlus): ./send_via_pushplus.sh"
echo "4. 📋 手动复制: cat /tmp/latest_ai_analysis.txt"
echo ""

# 检查是否有配置好的发送方式
if [ -f "./send_via_qq_email.sh" ] && grep -q "YOUR_QQ_NUMBER" ./send_via_qq_email.sh; then
    echo "⚠️  QQ邮箱未配置，请编辑 send_via_qq_email.sh"
fi

if [ -f "./send_via_wechat_serverchan.sh" ] && grep -q "YOUR_SERVERCHAN_SEND_KEY" ./send_via_wechat_serverchan.sh; then
    echo "⚠️  Server酱未配置，请编辑 send_via_wechat_serverchan.sh"
fi

if [ -f "./send_via_pushplus.sh" ] && grep -q "YOUR_PUSHPLUS_TOKEN" ./send_via_pushplus.sh; then
    echo "⚠️  PushPlus未配置，请编辑 send_via_pushplus.sh"
fi

echo ""
echo "⏰ 下次自动发送: 每小时整点"
echo "📊 查看日志: tail -f /tmp/ai_analysis_cron.log"