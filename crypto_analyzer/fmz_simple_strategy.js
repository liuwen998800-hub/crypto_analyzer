// ============================================
// AI量化交易策略 - FMZ平台专用（简洁版）
// 功能: 连接AI分析系统，自动执行交易信号
// 使用方法: 
// 1. 复制此代码到FMZ策略编辑器
// 2. 修改AI_API_URL为你的AI分析系统地址
// 3. 配置交易所和交易参数
// 4. 保存并运行策略
// ============================================

function main() {
    Log("🤖 AI量化交易策略启动");
    
    // ========== 配置参数 ==========
    // ⚠️ 请根据你的实际情况修改以下参数
    
    var config = {
        // 基本配置
        EXCHANGE: "binance",           // 交易所
        SYMBOL: "BTC_USDT",            // 交易对
        
        // AI分析系统
        AI_API_URL: "http://localhost:5000/api/analyze",  // AI分析API
        
        // 交易设置
        CHECK_INTERVAL: 300,           // 检查间隔（秒）
        MIN_CONFIDENCE: 60,            // 最小置信度
        
        // 仓位管理
        TRADE_AMOUNT: 0.001,           // 每次交易数量（BTC）
        MAX_POSITION: 0.01,            // 最大持仓（BTC）
        
        // 风险管理
        STOP_LOSS: 5.0,                // 止损百分比
        TAKE_PROFIT: 10.0,             // 止盈百分比
    };
    
    // ========== 状态变量 ==========
    var state = {
        position: 0,                    // 当前持仓
        entryPrice: 0,                  // 入场价格
        lastTradeTime: 0,               // 上次交易时间
        tradeCount: 0                   // 交易次数
    };
    
    // ========== 初始化 ==========
    Log("配置信息:");
    Log("交易所: " + config.EXCHANGE);
    Log("交易对: " + config.SYMBOL);
    Log("AI API: " + config.AI_API_URL);
    Log("检查间隔: " + config.CHECK_INTERVAL + "秒");
    Log("最小置信度: " + config.MIN_CONFIDENCE + "%");
    Log("交易数量: " + config.TRADE_AMOUNT + " BTC");
    
    // 设置交易所
    exchange.SetRate(config.EXCHANGE);
    exchange.SetCurrency(config.SYMBOL.split('_')[0]);
    
    // ========== 主循环 ==========
    while (true) {
        try {
            // 1. 获取AI信号
            var signal = getAISignal();
            if (!signal) {
                Log("未获取到AI信号，等待下次检查");
                Sleep(config.CHECK_INTERVAL * 1000);
                continue;
            }
            
            Log("AI信号: " + signal.direction + " (" + signal.confidence + "%)");
            
            // 2. 检查置信度
            if (signal.confidence < config.MIN_CONFIDENCE) {
                Log("置信度过低，跳过交易");
                Sleep(config.CHECK_INTERVAL * 1000);
                continue;
            }
            
            // 3. 获取账户信息
            var account = exchange.GetAccount();
            if (!account) {
                Log("获取账户信息失败");
                Sleep(60000);
                continue;
            }
            
            // 4. 检查当前持仓
            var ticker = exchange.GetTicker();
            var currentPrice = ticker.Last;
            
            if (state.position !== 0) {
                // 有持仓，检查是否需要平仓
                checkPosition(currentPrice);
            } else {
                // 无持仓，检查是否需要开仓
                checkOpenPosition(signal, account, currentPrice);
            }
            
            // 5. 等待下次检查
            Sleep(config.CHECK_INTERVAL * 1000);
            
        } catch (error) {
            Log("策略执行错误: " + error);
            Sleep(60000); // 错误后等待1分钟
        }
    }
    
    // ========== 功能函数 ==========
    
    // 获取AI信号
    function getAISignal() {
        try {
            var response = HttpQuery(config.AI_API_URL, "POST", 
                JSON.stringify({symbol: "BTC"}), 
                "Content-Type: application/json"
            );
            
            if (!response) return null;
            
            var data = JSON.parse(response);
            
            if (data.error) {
                Log("AI API错误: " + data.error);
                return null;
            }
            
            return {
                direction: data.signal ? data.signal.direction : "hold",
                confidence: data.signal ? data.signal.confidence : 0,
                price: data.current_price || 0,
                reasoning: data.signal ? data.signal.reasoning : "无信号"
            };
            
        } catch (error) {
            Log("获取AI信号失败: " + error);
            return null;
        }
    }
    
    // 检查持仓状态
    function checkPosition(currentPrice) {
        if (state.position === 0) return;
        
        // 计算盈亏百分比
        var profitPercent = ((currentPrice - state.entryPrice) / state.entryPrice) * 100;
        
        Log("持仓状态:");
        Log("  持仓数量: " + state.position + " BTC");
        Log("  入场价格: $" + state.entryPrice.toFixed(2));
        Log("  当前价格: $" + currentPrice.toFixed(2));
        Log("  浮动盈亏: " + profitPercent.toFixed(2) + "%");
        
        // 检查止损
        if (profitPercent <= -config.STOP_LOSS) {
            Log("触发止损: " + profitPercent.toFixed(2) + "% <= -" + config.STOP_LOSS + "%");
            closePosition(currentPrice, "止损");
            return;
        }
        
        // 检查止盈
        if (profitPercent >= config.TAKE_PROFIT) {
            Log("触发止盈: " + profitPercent.toFixed(2) + "% >= " + config.TAKE_PROFIT + "%");
            closePosition(currentPrice, "止盈");
            return;
        }
    }
    
    // 检查开仓机会
    function checkOpenPosition(signal, account, currentPrice) {
        // 检查持仓限制
        if (Math.abs(state.position) >= config.MAX_POSITION) {
            Log("达到最大持仓限制");
            return;
        }
        
        // 检查资金是否足够
        var requiredFunds = config.TRADE_AMOUNT * currentPrice;
        if (account.Balance < requiredFunds) {
            Log("资金不足: 需要$" + requiredFunds.toFixed(2) + 
                "，可用$" + account.Balance.toFixed(2));
            return;
        }
        
        // 执行交易
        if (signal.direction === "buy") {
            openLongPosition(currentPrice, signal.confidence);
        } else if (signal.direction === "sell") {
            openShortPosition(currentPrice, signal.confidence);
        }
    }
    
    // 开多仓
    function openLongPosition(price, confidence) {
        try {
            Log("执行买入: " + config.TRADE_AMOUNT + " BTC @ $" + price.toFixed(2));
            
            var order = exchange.Buy(-1, config.TRADE_AMOUNT);
            
            if (order && order.id) {
                state.position += config.TRADE_AMOUNT;
                state.entryPrice = price;
                state.lastTradeTime = Date.now();
                state.tradeCount++;
                
                Log("买入成功: 订单#" + order.id);
                Log("成交价: $" + (order.price || price).toFixed(2));
                Log("成交数量: " + (order.amount || config.TRADE_AMOUNT) + " BTC");
                Log("当前持仓: " + state.position + " BTC");
                
                // 记录交易
                recordTrade("buy", price, config.TRADE_AMOUNT, confidence);
            }
            
        } catch (error) {
            Log("买入失败: " + error);
        }
    }
    
    // 开空仓（如果支持）
    function openShortPosition(price, confidence) {
        try {
            Log("执行卖出: " + config.TRADE_AMOUNT + " BTC @ $" + price.toFixed(2));
            
            var order = exchange.Sell(-1, config.TRADE_AMOUNT);
            
            if (order && order.id) {
                state.position -= config.TRADE_AMOUNT; // 做空，持仓为负
                state.entryPrice = price;
                state.lastTradeTime = Date.now();
                state.tradeCount++;
                
                Log("卖出成功: 订单#" + order.id);
                Log("成交价: $" + (order.price || price).toFixed(2));
                Log("成交数量: " + (order.amount || config.TRADE_AMOUNT) + " BTC");
                Log("当前持仓: " + state.position + " BTC");
                
                // 记录交易
                recordTrade("sell", price, config.TRADE_AMOUNT, confidence);
            }
            
        } catch (error) {
            Log("卖出失败: " + error);
        }
    }
    
    // 平仓
    function closePosition(price, reason) {
        try {
            var closeAmount = Math.abs(state.position);
            
            if (state.position > 0) {
                // 平多仓
                Log("平多仓: " + closeAmount + " BTC @ $" + price.toFixed(2));
                var order = exchange.Sell(-1, closeAmount);
            } else if (state.position < 0) {
                // 平空仓
                Log("平空仓: " + closeAmount + " BTC @ $" + price.toFixed(2));
                var order = exchange.Buy(-1, closeAmount);
            } else {
                return;
            }
            
            if (order && order.id) {
                // 计算盈亏
                var profit = (price - state.entryPrice) * state.position;
                var profitPercent = ((price - state.entryPrice) / state.entryPrice) * 100;
                
                Log("平仓成功: 订单#" + order.id);
                Log("平仓原因: " + reason);
                Log("盈亏: $" + profit.toFixed(2) + " (" + profitPercent.toFixed(2) + "%)");
                
                // 重置持仓状态
                state.position = 0;
                state.entryPrice = 0;
                
                // 记录平仓
                recordClose(price, closeAmount, profit, profitPercent, reason);
            }
            
        } catch (error) {
            Log("平仓失败: " + error);
        }
    }
    
    // 记录交易
    function recordTrade(direction, price, amount, confidence) {
        Log("📝 交易记录:");
        Log("   方向: " + direction.toUpperCase());
        Log("   价格: $" + price.toFixed(2));
        Log("   数量: " + amount + " BTC");
        Log("   价值: $" + (price * amount).toFixed(2));
        Log("   置信度: " + confidence + "%");
        Log("   时间: " + new Date().toLocaleString());
        Log("   总交易次数: " + state.tradeCount);
    }
    
    // 记录平仓
    function recordClose(price, amount, profit, profitPercent, reason) {
        Log("📝 平仓记录:");
        Log("   价格: $" + price.toFixed(2));
        Log("   数量: " + amount + " BTC");
        Log("   盈亏: $" + profit.toFixed(2));
        Log("   盈亏率: " + profitPercent.toFixed(2) + "%");
        Log("   原因: " + reason);
        Log("   时间: " + new Date().toLocaleString());
    }
    
    // 显示统计信息
    function showStats() {
        Log("📊 策略统计:");
        Log("   运行时间: " + Math.floor((Date.now() - state.strategyStartTime) / 3600000) + "小时");
        Log("   总交易次数: " + state.tradeCount);
        Log("   当前持仓: " + state.position + " BTC");
        if (state.position !== 0) {
            Log("   入场价格: $" + state.entryPrice.toFixed(2));
        }
    }
}

// ============================================
// 使用说明:
// 1. 将此代码复制到FMZ策略编辑器
// 2. 修改AI_API_URL为你的AI分析系统地址
// 3. 根据需要调整交易参数
// 4. 保存策略并运行
// 5. 监控日志查看交易执行情况
// ============================================