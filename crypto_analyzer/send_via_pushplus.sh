#!/bin/bash
# 通过PushPlus发送消息到微信/QQ
# PushPlus官网: https://www.pushplus.plus

# PushPlus配置
PUSHPLUS_TOKEN="YOUR_PUSHPLUS_TOKEN"  # 在PushPlus官网获取
PUSHPLUS_TITLE="🤖 BTC AI分析报告 - $(date '+%m-%d %H:%M')"
PUSHPLUS_TEMPLATE="html"  # html, txt, json, markdown, cloudMonitor

# 获取AI分析消息
MESSAGE_FILE="/tmp/latest_ai_analysis.txt"
if [ ! -f "$MESSAGE_FILE" ]; then
    echo "❌ 未找到分析数据，请先运行 send_ai_analysis_to_phone.sh"
    exit 1
fi

MESSAGE=$(cat "$MESSAGE_FILE")

# 转换为HTML格式
HTML_CONTENT="<div style='font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;'>
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px 10px 0 0; text-align: center;'>
        <h1 style='margin: 0;'>🤖 BTC AI分析报告</h1>
        <p style='margin: 5px 0 0 0; opacity: 0.9;'>$(date '+%Y年%m月%d日 %A %H:%M:%S')</p>
    </div>
    
    <div style='background: #f8f9fa; padding: 20px; border-radius: 0 0 10px 10px;'>
        <div style='margin-bottom: 15px;'>
            <span style='font-weight: bold; color: #333;'>💰 当前价格:</span>
            <span style='color: #e74c3c; font-size: 18px; font-weight: bold;'>$(echo "$MESSAGE" | grep '价格:' | sed 's/.*价格: //')</span>
        </div>
        
        <div style='margin-bottom: 15px;'>
            <span style='font-weight: bold; color: #333;'>📈 分析方向:</span>
            <span style='color: #2ecc71; font-weight: bold;'>$(echo "$MESSAGE" | grep '方向:' | sed 's/.*方向: //')</span>
        </div>
        
        <div style='margin-bottom: 15px;'>
            <span style='font-weight: bold; color: #333;'>🎯 置信度:</span>
            <span style='color: #3498db;'>$(echo "$MESSAGE" | grep '置信度:' | sed 's/.*置信度: //')</span>
        </div>
        
        <div style='margin-bottom: 20px; background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db;'>
            <div style='font-weight: bold; color: #333; margin-bottom: 10px;'>🤖 AI模型分析</div>
            <div style='display: flex; gap: 10px;'>
                <div style='flex: 1; background: #e8f4fc; padding: 10px; border-radius: 5px;'>
                    <div style='font-weight: bold; color: #2980b9;'>DeepSeek</div>
                    <div>$(echo "$MESSAGE" | grep 'DeepSeek:' | sed 's/.*DeepSeek: //')</div>
                </div>
                <div style='flex: 1; background: #f0f7f0; padding: 10px; border-radius: 5px;'>
                    <div style='font-weight: bold; color: #27ae60;'>MiniMax</div>
                    <div>$(echo "$MESSAGE" | grep 'MiniMax:' | sed 's/.*MiniMax: //')</div>
                </div>
            </div>
        </div>
        
        <div style='margin-bottom: 20px; background: #fff8e1; padding: 15px; border-radius: 8px; border-left: 4px solid #f39c12;'>
            <div style='font-weight: bold; color: #333; margin-bottom: 5px;'>📝 市场分析</div>
            <div style='color: #666; line-height: 1.5;'>$(echo "$MESSAGE" | grep '简要分析:' -A1 | tail -1)</div>
        </div>
        
        <div style='text-align: center; margin-top: 20px;'>
            <a href='http://localhost:5000' style='display: inline-block; background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;'>
                📊 查看完整分析面板
            </a>
        </div>
        
        <div style='margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee; text-align: center; color: #999; font-size: 12px;'>
            <p>此消息由AI量化交易系统自动发送</p>
            <p>下次报告时间: $(date -d '+1 hour' '+%H:%M')</p>
        </div>
    </div>
</div>"

echo "📱 准备通过PushPlus发送消息..."
echo "🔑 使用的Token: ${PUSHPLUS_TOKEN:0:8}..."

# 发送到PushPlus
RESPONSE=$(curl -s -X POST "https://www.pushplus.plus/send" \
  -H "Content-Type: application/json" \
  -d "{
    \"token\": \"$PUSHPLUS_TOKEN\",
    \"title\": \"$PUSHPLUS_TITLE\",
    \"content\": \"$HTML_CONTENT\",
    \"template\": \"$PUSHPLUS_TEMPLATE\",
    \"channel\": \"wechat\"  # wechat, webhook, cp, sms, mail, voice
  }")

# 检查响应
if echo "$RESPONSE" | grep -q '"code":200'; then
    echo "✅ PushPlus消息发送成功！"
    echo "💡 请查看微信PushPlus服务号"
else
    echo "❌ PushPlus消息发送失败"
    echo "响应: $RESPONSE"
    echo ""
    echo "🔧 故障排除:"
    echo "1. 检查PushPlus Token是否正确"
    echo "2. 访问 https://www.pushplus.plus 查看配置"
    echo "3. 确保已关注PushPlus服务号"
fi

echo ""
echo "📋 PushPlus配置步骤:"
echo "1. 访问 https://www.pushplus.plus"
echo "2. 微信扫码登录"
echo "3. 获取Token"
echo "4. 关注PushPlus服务号"
echo "5. 修改本脚本中的PUSHPLUS_TOKEN"
echo ""
echo "🎯 特点:"
echo "• 支持微信、邮件、短信等多种渠道"
echo "• 免费额度充足"
echo "• 支持HTML富文本"
echo "• 可绑定多个接收方式"