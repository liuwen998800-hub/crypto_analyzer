#!/bin/bash
# Telegram消息发送脚本模板
# 需要先配置TELEGRAM_BOT_TOKEN和TELEGRAM_CHAT_ID

TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID="YOUR_CHAT_ID_HERE"

MESSAGE_FILE="/tmp/latest_ai_analysis.txt"
MESSAGE=$(cat "$MESSAGE_FILE")

# 发送到Telegram
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d chat_id="${TELEGRAM_CHAT_ID}" \
  -d text="${MESSAGE}" \
  -d parse_mode="Markdown"
