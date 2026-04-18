#!/bin/bash
# QQ和微信通知一键配置脚本

echo "🎯 QQ和微信通知系统配置"
echo "=========================="

# 检查必要工具
echo "🔧 检查系统工具..."
if ! command -v curl &> /dev/null; then
    echo "❌ 需要安装curl"
    echo "运行: sudo apt-get install curl"
    exit 1
fi

# 测试AI分析服务
echo "📡 测试AI分析服务..."
AI_STATUS=$(curl -s http://localhost:5000/api/status | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
if [ "$AI_STATUS" = "running" ]; then
    echo "✅ AI分析服务运行正常"
else
    echo "❌ AI分析服务未运行"
    echo "请先启动: cd crypto_analyzer && ./start_complete_system.sh"
    exit 1
fi

# 显示菜单
echo ""
echo "📱 请选择消息发送方式:"
echo "1. 📧 QQ邮箱（推荐，QQ直接通知）"
echo "2. 💬 微信 Server酱（微信直接接收）"
echo "3. 📲 PushPlus（支持微信/QQ/邮件）"
echo "4. 📋 查看配置指南"
echo "5. 🚀 测试当前系统"
echo "6. ⏰ 设置自动发送"
echo "0. ❌ 退出"
echo ""

read -p "请输入选择 (0-6): " CHOICE

case $CHOICE in
    1)
        echo ""
        echo "📧 配置QQ邮箱发送..."
        echo ""
        echo "需要以下信息:"
        echo "1. QQ邮箱地址（如: 123456789@qq.com）"
        echo "2. QQ邮箱授权码（16位，不是QQ密码）"
        echo ""
        read -p "请输入QQ邮箱地址: " QQ_EMAIL
        read -p "请输入QQ邮箱授权码: " QQ_AUTH_CODE
        
        # 配置QQ邮箱脚本
        sed -i "s/YOUR_QQ_NUMBER@qq.com/$QQ_EMAIL/g" send_via_qq_email.sh
        sed -i "s/YOUR_QQ_EMAIL_AUTH_CODE/$QQ_AUTH_CODE/g" send_via_qq_email.sh
        
        echo "✅ QQ邮箱配置完成"
        echo "测试发送: ./send_via_qq_email.sh"
        ;;
        
    2)
        echo ""
        echo "💬 配置微信 Server酱..."
        echo ""
        echo "需要以下信息:"
        echo "1. Server酱 SendKey"
        echo "  获取地址: https://sct.ftqq.com"
        echo ""
        read -p "请输入Server酱 SendKey: " SERVERCHAN_KEY
        
        # 配置Server酱脚本
        sed -i "s/YOUR_SERVERCHAN_SEND_KEY/$SERVERCHAN_KEY/g" send_via_wechat_serverchan.sh
        
        echo "✅ Server酱配置完成"
        echo "测试发送: ./send_via_wechat_serverchan.sh"
        ;;
        
    3)
        echo ""
        echo "📲 配置 PushPlus..."
        echo ""
        echo "需要以下信息:"
        echo "1. PushPlus Token"
        echo "  获取地址: https://www.pushplus.plus"
        echo ""
        read -p "请输入PushPlus Token: " PUSHPLUS_TOKEN
        
        # 配置PushPlus脚本
        sed -i "s/YOUR_PUSHPLUS_TOKEN/$PUSHPLUS_TOKEN/g" send_via_pushplus.sh
        
        echo "✅ PushPlus配置完成"
        echo "测试发送: ./send_via_pushplus.sh"
        ;;
        
    4)
        echo ""
        echo "📋 打开配置指南..."
        echo ""
        echo "QQ和微信配置指南:"
        cat QQ_WECHAT_SETUP_GUIDE.md | head -50
        echo ""
        echo "完整指南查看: cat QQ_WECHAT_SETUP_GUIDE.md"
        ;;
        
    5)
        echo ""
        echo "🚀 测试当前系统..."
        echo ""
        ./send_ai_analysis_to_phone.sh
        ;;
        
    6)
        echo ""
        echo "⏰ 设置自动发送..."
        echo ""
        echo "当前cron任务:"
        crontab -l 2>/dev/null || echo "暂无cron任务"
        echo ""
        echo "添加每小时自动发送任务..."
        
        # 创建自动发送脚本
        cat > auto_send_hourly.sh << 'EOF'
#!/bin/bash
# 每小时自动发送AI分析报告

cd /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer

# 生成报告
./send_ai_analysis_to_phone.sh > /dev/null 2>&1

# 发送到已配置的渠道
if [ -f "./send_via_qq_email.sh" ] && ! grep -q "YOUR_QQ_NUMBER" ./send_via_qq_email.sh; then
    ./send_via_qq_email.sh > /dev/null 2>&1
fi

if [ -f "./send_via_wechat_serverchan.sh" ] && ! grep -q "YOUR_SERVERCHAN_SEND_KEY" ./send_via_wechat_serverchan.sh; then
    ./send_via_wechat_serverchan.sh > /dev/null 2>&1
fi

if [ -f "./send_via_pushplus.sh" ] && ! grep -q "YOUR_PUSHPLUS_TOKEN" ./send_via_pushplus.sh; then
    ./send_via_pushplus.sh > /dev/null 2>&1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 自动发送完成" >> /tmp/ai_auto_send.log
EOF
        
        chmod +x auto_send_hourly.sh
        
        # 添加cron任务
        CRON_JOB="0 * * * * /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/auto_send_hourly.sh"
        (crontab -l 2>/dev/null | grep -v "auto_send_hourly.sh"; echo "$CRON_JOB") | crontab -
        
        echo "✅ 已设置每小时自动发送"
        echo "下次发送时间: $(date -d 'next hour' '+%H:00')"
        echo "查看日志: tail -f /tmp/ai_auto_send.log"
        ;;
        
    0)
        echo "退出配置"
        exit 0
        ;;
        
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "🎉 配置完成！"
echo ""
echo "📋 可用命令:"
echo "  ./send_ai_analysis_to_phone.sh    # 生成报告"
echo "  ./send_via_qq_email.sh           # 发送到QQ邮箱"
echo "  ./send_via_wechat_serverchan.sh  # 发送到微信"
echo "  ./send_via_pushplus.sh           # 发送到PushPlus"
echo "  crontab -l                       # 查看定时任务"
echo ""
echo "📊 查看日志:"
echo "  tail -f /tmp/ai_analysis_cron.log"
echo "  tail -f /tmp/ai_auto_send.log"
echo ""
echo "⏰ 系统将在每小时整点自动发送报告"