#!/bin/bash
# 通过Server酱发送微信消息
# Server酱官网: https://sct.ftqq.com

# Server酱配置
SERVERCHAN_KEY="YOUR_SERVERCHAN_SEND_KEY"  # 在Server酱官网获取
SERVERCHAN_TITLE="🤖 BTC AI分析报告 - $(date '+%m-%d %H:%M')"

# 获取AI分析消息
MESSAGE_FILE="/tmp/latest_ai_analysis.txt"
if [ ! -f "$MESSAGE_FILE" ]; then
    echo "❌ 未找到分析数据，请先运行 send_ai_analysis_to_phone.sh"
    exit 1
fi

MESSAGE=$(cat "$MESSAGE_FILE")

# 提取关键信息用于摘要
PRICE=$(echo "$MESSAGE" | grep "价格:" | sed 's/.*价格: //')
DIRECTION=$(echo "$MESSAGE" | grep "方向:" | sed 's/.*方向: //')
CONFIDENCE=$(echo "$MESSAGE" | grep "置信度:" | sed 's/.*置信度: //')

# 构建Server酱消息
# Server酱支持Markdown格式
SERVERCHAN_CONTENT="## 📊 BTC AI分析报告
**📅 时间:** $(date '+%Y-%m-%d %H:%M:%S')
**💰 价格:** $PRICE
**📈 方向:** $DIRECTION
**🎯 置信度:** $CONFIDENCE

### 🤖 AI模型分析
$(echo "$MESSAGE" | grep -A2 "AI模型分析:")

### 📝 简要分析
$(echo "$MESSAGE" | grep -A1 "简要分析:" | tail -1)

### 🔗 详细查看
[点击查看完整分析面板](http://localhost:5000)

---
*此消息由AI量化交易系统自动发送*
*下次报告: $(date -d '+1 hour' '+%H:%M')*"

echo "📱 准备发送微信消息 via Server酱..."
echo "🔑 使用的Key: ${SERVERCHAN_KEY:0:8}..."

# 发送到Server酱
RESPONSE=$(curl -s -X POST "https://sctapi.ftqq.com/${SERVERCHAN_KEY}.send" \
  -d "title=${SERVERCHAN_TITLE}" \
  -d "desp=${SERVERCHAN_CONTENT}")

# 检查响应
if echo "$RESPONSE" | grep -q '"code":0'; then
    echo "✅ 微信消息发送成功！"
    echo "💡 请查看微信Server酱服务号"
else
    echo "❌ 微信消息发送失败"
    echo "响应: $RESPONSE"
    echo ""
    echo "🔧 故障排除:"
    echo "1. 检查Server酱Key是否正确"
    echo "2. 访问 https://sct.ftqq.com 查看配置"
    echo "3. 确保已关注Server酱服务号"
fi

echo ""
echo "📋 Server酱配置步骤:"
echo "1. 访问 https://sct.ftqq.com"
echo "2. 微信扫码登录"
echo "3. 获取SendKey"
echo "4. 关注Server酱服务号"
echo "5. 修改本脚本中的SERVERCHAN_KEY"
echo ""
echo "🎯 特点:"
echo "• 免费使用"
echo "• 微信直接接收"
echo "• 支持Markdown格式"
echo "• 有发送频率限制"