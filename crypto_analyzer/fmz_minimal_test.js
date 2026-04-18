// FMZ策略最小测试版本
function main() {
    Log("FMZ策略测试启动");
    
    // 基本配置
    var exchangeName = "binance";
    var symbol = "BTC_USDT";
    
    // 设置交易所
    exchange.SetRate(exchangeName);
    exchange.SetCurrency(symbol.split('_')[0]);
    
    Log("交易所: " + exchangeName);
    Log("交易对: " + symbol);
    
    // 主循环
    while (true) {
        try {
            // 获取市场数据
            var ticker = exchange.GetTicker();
            if (ticker) {
                Log("当前价格: $" + ticker.Last.toFixed(2));
            }
            
            // 获取账户信息
            var account = exchange.GetAccount();
            if (account) {
                Log("账户余额: $" + account.Balance.toFixed(2));
            }
            
            // 简单交易逻辑
            if (ticker && account) {
                // 这里可以添加简单的交易逻辑
                // 例如：价格低于某个值时买入
                if (ticker.Last < 70000 && account.Balance > 100) {
                    Log("价格低于70000，考虑买入");
                    // exchange.Buy(-1, 0.001);
                }
            }
            
            // 等待5分钟
            Sleep(300000);
            
        } catch (error) {
            Log("错误: " + error);
            Sleep(60000);
        }
    }
}