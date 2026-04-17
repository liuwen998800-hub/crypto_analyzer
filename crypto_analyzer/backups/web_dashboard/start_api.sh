#!/bin/bash
cd /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/web_dashboard
pkill -f "python.*app\.py" 2>/dev/null
sleep 1
python3 app.py > app.log 2>&1 &
sleep 3
echo "API服务已启动"
curl -s http://localhost:5000/api/status | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'状态: {d[\"status\"]}, 分析次数: {d[\"results_count\"]}')"
