#!/bin/bash
# 通过QQ邮箱发送AI分析报告
# QQ邮箱格式: QQ号码@qq.com
# 例如: 123456789@qq.com

# 配置QQ邮箱信息
QQ_EMAIL="YOUR_QQ_NUMBER@qq.com"  # 修改为你的QQ邮箱
EMAIL_SUBJECT="🤖 BTC AI分析报告 - $(date '+%Y-%m-%d %H:%M')"

# 邮件服务器配置（QQ邮箱SMTP）
SMTP_SERVER="smtp.qq.com"
SMTP_PORT="587"
SMTP_USER="$QQ_EMAIL"
SMTP_PASSWORD="YOUR_QQ_EMAIL_AUTH_CODE"  # QQ邮箱授权码，不是QQ密码

# 检查是否安装了邮件发送工具
if ! command -v sendemail &> /dev/null && ! command -v mail &> /dev/null; then
    echo "❌ 需要安装邮件发送工具"
    echo "安装方法:"
    echo "Ubuntu/Debian: sudo apt-get install sendemail"
    echo "或使用其他邮件客户端"
    exit 1
fi

# 获取AI分析消息
MESSAGE_FILE="/tmp/latest_ai_analysis.txt"
if [ ! -f "$MESSAGE_FILE" ]; then
    echo "❌ 未找到分析数据，请先运行 send_ai_analysis_to_phone.sh"
    exit 1
fi

MESSAGE=$(cat "$MESSAGE_FILE")

# 转换为HTML格式（QQ邮箱支持HTML）
HTML_MESSAGE=$(echo "$MESSAGE" | sed 's/\\n/<br>/g' | sed 's/\*\([^*]*\)\*/<strong>\1<\/strong>/g')

# 构建完整HTML邮件
HTML_CONTENT="<!DOCTYPE html>
<html>
<head>
    <meta charset=\"UTF-8\">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; }
        .content { background: #f5f5f5; padding: 20px; border-radius: 10px; margin-top: 20px; }
        .section { margin-bottom: 15px; }
        .label { font-weight: bold; color: #333; }
        .value { color: #666; }
        .ai-model { display: inline-block; background: white; padding: 10px; border-radius: 5px; margin: 5px; }
        .footer { margin-top: 20px; font-size: 12px; color: #999; text-align: center; }
    </style>
</head>
<body>
    <div class=\"header\">
        <h1>🤖 BTC AI分析报告</h1>
        <p>📅 $(date '+%Y年%m月%d日 %A') ⏰ $(date '+%H:%M:%S')</p>
    </div>
    
    <div class=\"content\">
        <div class=\"section\">
            <span class=\"label\">💰 当前价格:</span>
            <span class=\"value\">$(echo "$MESSAGE" | grep "价格:" | sed 's/.*价格: //' | sed 's/\$//')</span>
        </div>
        
        <div class=\"section\">
            <span class=\"label\">📈 分析方向:</span>
            <span class=\"value\">$(echo "$MESSAGE" | grep "方向:" | sed 's/.*方向: //')</span>
        </div>
        
        <div class=\"section\">
            <span class=\"label\">🎯 置信度:</span>
            <span class=\"value\">$(echo "$MESSAGE" | grep "置信度:" | sed 's/.*置信度: //')</span>
        </div>
        
        <div class=\"section\">
            <span class=\"label\">🤖 AI模型分析:</span><br>
            <div class=\"ai-model\">$(echo "$MESSAGE" | grep "DeepSeek:" | sed 's/.*DeepSeek: //')</div>
            <div class=\"ai-model\">$(echo "$MESSAGE" | grep "MiniMax:" | sed 's/.*MiniMax: //')</div>
        </div>
        
        <div class=\"section\">
            <span class=\"label\">📊 详细分析:</span>
            <span class=\"value\"><a href=\"http://localhost:5000\">点击查看完整分析面板</a></span>
        </div>
    </div>
    
    <div class=\"footer\">
        <p>此邮件由AI量化交易系统自动发送</p>
        <p>下次报告时间: $(date -d '+1 hour' '+%H:%M')</p>
    </div>
</body>
</html>"

# 保存HTML内容到临时文件
HTML_FILE="/tmp/ai_report_$(date '+%Y%m%d_%H%M%S').html"
echo "$HTML_CONTENT" > "$HTML_FILE"

echo "📧 准备发送QQ邮件到: $QQ_EMAIL"
echo "📋 邮件主题: $EMAIL_SUBJECT"

# 方法1: 使用sendemail（推荐）
if command -v sendemail &> /dev/null; then
    echo "📤 使用sendemail发送..."
    sendemail \
        -f "$SMTP_USER" \
        -t "$QQ_EMAIL" \
        -u "$EMAIL_SUBJECT" \
        -m "$MESSAGE" \
        -s "$SMTP_SERVER:$SMTP_PORT" \
        -xu "$SMTP_USER" \
        -xp "$SMTP_PASSWORD" \
        -o tls=yes \
        -o message-content-type=html \
        -o message-file="$HTML_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✅ 邮件发送成功！"
        echo "💡 提示：QQ邮箱收到邮件后，QQ客户端会有通知"
    else
        echo "❌ 邮件发送失败"
        echo "💡 请检查："
        echo "1. QQ邮箱是否正确"
        echo "2. 授权码是否正确（不是QQ密码）"
        echo "3. 是否开启了SMTP服务"
    fi

# 方法2: 使用mail命令（简单但功能有限）
elif command -v mail &> /dev/null; then
    echo "📤 使用mail命令发送..."
    echo "$MESSAGE" | mail -s "$EMAIL_SUBJECT" "$QQ_EMAIL"
    
    if [ $? -eq 0 ]; then
        echo "✅ 邮件已排队发送"
    else
        echo "❌ 邮件发送失败"
    fi
fi

# 清理临时文件
rm -f "$HTML_FILE"

echo ""
echo "🔧 QQ邮箱配置说明:"
echo "1. 登录QQ邮箱网页版"
echo "2. 设置 → 账户 → 开启SMTP服务"
echo "3. 生成授权码（16位字母数字）"
echo "4. 修改本脚本中的QQ邮箱和授权码"
echo ""
echo "📱 手机QQ会收到邮件到达通知"