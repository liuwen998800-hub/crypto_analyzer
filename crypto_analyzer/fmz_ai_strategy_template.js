// AI量化策略 - 自动执行AI分析信号
function main() {
    Log("🤖 AI量化策略启动");
    
    // 配置参数
    var exchange = "binance";
    var symbol = "BTC_USDT";
    var checkInterval = 300; // 检查间隔（秒）
    var minConfidence = 60;  // 最小置信度
    var maxPosition = 0.01;  // 最大持仓（BTC）
    var tradeAmount = 0.001; // 每次交易数量
    
    // AI信号API配置
    var aiApiUrl = "http://localhost:5000/api/analyze";
    
    while (true) {
        try {
            Log("📡 获取AI分析信号...");
            
            // 从AI分析系统获取信号
            var aiSignal = HttpQuery(aiApiUrl);
            var signalData = JSON.parse(aiSignal);
            
            if (signalData && signalData.signal) {
                var direction = signalData.signal.direction;
                var confidence = signalData.signal.confidence;
                var price = signalData.signal.price;
                
                Log("📊 AI信号分析:");
                Log("   方向: " + direction);
                Log("   置信度: " + confidence + "%");
                Log("   价格: " + price);
                
                // 检查置信度
                if (confidence >= minConfidence) {
                    Log("✅ 信号置信度足够，准备执行交易");
                    
                    // 获取账户余额
                    var account = exchange.GetAccount();
                    var balance = account.Balance;
                    var frozen = account.FrozenBalance;
                    
                    Log("💰 账户余额:");
                    Log("   可用: " + balance);
                    Log("   冻结: " + frozen);
                    
                    if (direction === "buy" && balance > price * tradeAmount) {
                        // 执行买入
                        Log("🟢 执行买入订单...");
                        var order = exchange.Buy(-1, tradeAmount);
                        if (order && order.id) {
                            Log("✅ 买入订单成功: #" + order.id);
                        }
                    } else if (direction === "sell") {
                        // 执行卖出
                        Log("🔴 执行卖出订单...");
                        var order = exchange.Sell(-1, tradeAmount);
                        if (order && order.id) {
                            Log("✅ 卖出订单成功: #" + order.id);
                        }
                    }
                } else {
                    Log("⏸️  信号置信度不足，跳过交易");
                }
            } else {
                Log("⚠️  未获取到有效AI信号");
            }
            
            // 等待下次检查
            Log("⏰ 等待下次检查 (" + checkInterval + "秒)...");
            Sleep(checkInterval * 1000);
            
        } catch (error) {
            Log("❌ 发生错误: " + error);
            Sleep(60000); // 错误后等待1分钟
        }
    }
}
