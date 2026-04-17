
## Polymarket Trading 经验 (2026-04-14)

### 关键发现：amount参数含义

Polymarket市价单的`amount`参数含义：
- **BUY市价单**：`amount` = 花费的USD金额（如`amount: 2` = 花$2）
- **SELL市价单**：`amount` = 卖出的shares数量

### 自动交易脚本

- 位置：`/home/billyqqq/.openclaw/workspace/auto_trader.py`
- 配置：$2/次，价格>75%不下单
- 启动：`cd /home/billyqqq/.openclaw/workspace && ./start_auto_trader.sh`
- 停止：`pkill -f auto_trader.py`
- 统计：`python3 /home/billyqqq/.openclaw/workspace/trade_stats.py`

### 教训

之前错误地将amount设置为shares数量，导致实际花费远超预期。
修复后使用正确的USD金额控制。
