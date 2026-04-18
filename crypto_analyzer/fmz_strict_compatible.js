// AI量化交易策略 - FMZ平台严格兼容版
function main() {
    Log("AI量化交易策略启动");
    
    // 配置参数
    var config = {
        exchange: "binance",
        symbol: "BTC_USDT",
        aiApiUrl: "http://localhost:5000/api/analyze",
        checkInterval: 300,
        minConfidence: 60,
        tradeAmount: 0.001,
        maxPosition: 0.01,
        stopLoss: 5.0,
        takeProfit: 10.0
    };
    
    // 状态变量
    var state = {
        position: 0,
        entryPrice: 0,
        lastTradeTime: 0,
        tradeCount: 0
    };
    
    // 初始化
    Log("配置信息:");
    Log("交易所: " + config.exchange);
    Log("交易对: " + config.symbol);
    Log("检查间隔: " + config.checkInterval + "秒");
    
    // 设置交易所
    exchange.SetRate(config.exchange);
    exchange.SetCurrency(config.symbol.split('_')[0]);
    
    // 主循环
    while (true) {
        try {
            // 获取AI信号
            var signal = getAISignal(config.aiApiUrl);
            if (!signal) {
                Log("未获取到AI信号");
                Sleep(config.checkInterval * 1000);
                continue;
            }
            
            Log("AI信号方向: " + signal.direction);
            Log("AI信号置信度: " + signal.confidence + "%");
            
            // 检查置信度
            if (signal.confidence < config.minConfidence) {
                Log("置信度过低，跳过");
                Sleep(config.checkInterval * 1000);
                continue;
            }
            
            // 获取账户信息
            var account = exchange.GetAccount();
            if (!account) {
                Log("获取账户失败");
                Sleep(60000);
                continue;
            }
            
            // 获取当前价格
            var ticker = exchange.GetTicker();
            var currentPrice = ticker ? ticker.Last : 0;
            
            if (currentPrice === 0) {
                Log("获取价格失败");
                Sleep(config.checkInterval * 1000);
                continue;
            }
            
            // 检查持仓
            if (state.position !== 0) {
                checkPosition(currentPrice, state, config);
            } else {
                checkOpenPosition(signal, account, currentPrice, state, config);
            }
            
            // 等待下次检查
            Sleep(config.checkInterval * 1000);
            
        } catch (error) {
            Log("策略错误: " + error.toString());
            Sleep(60000);
        }
    }
}

// 获取AI信号
function getAISignal(apiUrl) {
    try {
        var response = HttpQuery(apiUrl, "POST", '{"symbol":"BTC"}', "Content-Type: application/json");
        
        if (!response) {
            Log("AI API无响应");
            return null;
        }
        
        var data;
        try {
            data = JSON.parse(response);
        } catch (e) {
            Log("JSON解析错误: " + e);
            return null;
        }
        
        if (data.error) {
            Log("AI API错误: " + data.error);
            return null;
        }
        
        var signal = {
            direction: "hold",
            confidence: 0,
            price: 0
        };
        
        if (data.signal) {
            signal.direction = data.signal.direction || "hold";
            signal.confidence = data.signal.confidence || 0;
        }
        
        if (data.current_price) {
            signal.price = data.current_price;
        }
        
        return signal;
        
    } catch (error) {
        Log("获取信号错误: " + error.toString());
        return null;
    }
}

// 检查持仓
function checkPosition(currentPrice, state, config) {
    if (state.position === 0) return;
    
    var profitPercent = ((currentPrice - state.entryPrice) / state.entryPrice) * 100;
    
    Log("持仓检查:");
    Log("持仓数量: " + state.position);
    Log("入场价格: " + state.entryPrice.toFixed(2));
    Log("当前价格: " + currentPrice.toFixed(2));
    Log("浮动盈亏: " + profitPercent.toFixed(2) + "%");
    
    // 止损检查
    if (profitPercent <= -config.stopLoss) {
        Log("触发止损");
        closePosition(currentPrice, state, "止损");
        return;
    }
    
    // 止盈检查
    if (profitPercent >= config.takeProfit) {
        Log("触发止盈");
        closePosition(currentPrice, state, "止盈");
        return;
    }
}

// 检查开仓机会
function checkOpenPosition(signal, account, currentPrice, state, config) {
    // 检查持仓限制
    if (Math.abs(state.position) >= config.maxPosition) {
        Log("达到最大持仓");
        return;
    }
    
    // 检查资金
    var requiredFunds = config.tradeAmount * currentPrice;
    if (account.Balance < requiredFunds) {
        Log("资金不足");
        return;
    }
    
    // 执行交易
    if (signal.direction === "buy") {
        openLongPosition(currentPrice, state, config);
    } else if (signal.direction === "sell") {
        openShortPosition(currentPrice, state, config);
    }
}

// 开多仓
function openLongPosition(price, state, config) {
    try {
        Log("执行买入: " + config.tradeAmount + " BTC");
        
        var order = exchange.Buy(-1, config.tradeAmount);
        
        if (order && order.id) {
            state.position += config.tradeAmount;
            state.entryPrice = price;
            state.lastTradeTime = Date.now();
            state.tradeCount++;
            
            Log("买入成功: 订单#" + order.id);
            Log("当前持仓: " + state.position + " BTC");
        }
        
    } catch (error) {
        Log("买入失败: " + error.toString());
    }
}

// 开空仓
function openShortPosition(price, state, config) {
    try {
        Log("执行卖出: " + config.tradeAmount + " BTC");
        
        var order = exchange.Sell(-1, config.tradeAmount);
        
        if (order && order.id) {
            state.position -= config.tradeAmount;
            state.entryPrice = price;
            state.lastTradeTime = Date.now();
            state.tradeCount++;
            
            Log("卖出成功: 订单#" + order.id);
            Log("当前持仓: " + state.position + " BTC");
        }
        
    } catch (error) {
        Log("卖出失败: " + error.toString());
    }
}

// 平仓
function closePosition(price, state, reason) {
    try {
        var closeAmount = Math.abs(state.position);
        
        if (state.position > 0) {
            Log("平多仓: " + closeAmount + " BTC");
            var order = exchange.Sell(-1, closeAmount);
        } else if (state.position < 0) {
            Log("平空仓: " + closeAmount + " BTC");
            var order = exchange.Buy(-1, closeAmount);
        } else {
            return;
        }
        
        if (order && order.id) {
            var profit = (price - state.entryPrice) * state.position;
            
            Log("平仓成功: 订单#" + order.id);
            Log("平仓原因: " + reason);
            Log("盈亏: $" + profit.toFixed(2));
            
            // 重置状态
            state.position = 0;
            state.entryPrice = 0;
        }
        
    } catch (error) {
        Log("平仓失败: " + error.toString());
    }
}