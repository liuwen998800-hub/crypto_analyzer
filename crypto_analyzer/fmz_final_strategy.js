// ============================================
// AI智能量化交易策略 - FMZ平台专用
// 版本: 3.0 (完整版)
// 功能: 连接AI分析系统，自动执行交易信号
// 配置: 需要设置AI_API_URL为你的AI分析系统地址
// ============================================

function main() {
    Log("🚀 AI智能量化交易策略启动");
    Log("============================================");
    
    // ========== 策略配置 ==========
    // ⚠️ 重要：请根据你的实际情况修改以下配置
    
    var config = {
        // 交易所配置
        EXCHANGE: "binance",           // 交易所: binance, okex, huobi等
        SYMBOL: "BTC_USDT",            // 交易对: BTC_USDT, ETH_USDT等
        
        // AI分析系统配置
        AI_API_URL: "http://localhost:5000/api/analyze",  // AI分析API地址
        
        // 交易参数
        CHECK_INTERVAL: 300,           // 检查间隔（秒），建议300-600
        MIN_CONFIDENCE: 60,            // 最小置信度（%），低于此值不交易
        MAX_CONFIDENCE: 90,            // 最大置信度（%），高于此值可能过拟合
        
        // 仓位管理
        BASE_TRADE_AMOUNT: 0.001,      // 基础交易数量（BTC）
        MAX_POSITION: 0.01,            // 最大持仓（BTC）
        POSITION_SCALE: 0.5,           // 仓位缩放系数（0-1）
        
        // 风险管理
        STOP_LOSS: 5.0,                // 止损百分比
        TAKE_PROFIT: 10.0,             // 止盈百分比
        TRAILING_STOP: 2.0,            // 移动止损百分比
        
        // 交易控制
        MAX_DAILY_TRADES: 10,          // 每日最大交易次数
        COOLDOWN_MINUTES: 30,          // 冷却时间（分钟）
        
        // 高级设置
        ENABLE_SHORT_SELLING: false,   // 是否允许做空
        USE_MARKET_ORDERS: true,       // 使用市价单（true）还是限价单（false）
        ORDER_PRICE_OFFSET: 0.001,     // 限价单价格偏移（0.1%）
        
        // 日志设置
        LOG_LEVEL: "info"              // debug, info, warning, error
    };
    
    // ========== 状态管理 ==========
    var state = {
        // 时间相关
        lastTradeTime: 0,
        dailyTradeCount: 0,
        lastTradeDate: 0,
        strategyStartTime: Date.now(),
        
        // 持仓相关
        currentPosition: 0,
        entryPrice: 0,
        highestPrice: 0,
        lowestPrice: 0,
        positionDirection: "none", // none, long, short
        
        // 统计相关
        totalTrades: 0,
        winningTrades: 0,
        losingTrades: 0,
        totalProfit: 0,
        maxDrawdown: 0,
        currentDrawdown: 0,
        peakBalance: 0,
        
        // 风险控制
        consecutiveLosses: 0,
        consecutiveWins: 0,
        riskLevel: "normal" // low, normal, high
    };
    
    // ========== 初始化 ==========
    Log("📋 策略配置:");
    Log("   交易所: " + config.EXCHANGE);
    Log("   交易对: " + config.SYMBOL);
    Log("   AI API: " + config.AI_API_URL);
    Log("   检查间隔: " + config.CHECK_INTERVAL + "秒");
    Log("   最小置信度: " + config.MIN_CONFIDENCE + "%");
    Log("   最大持仓: " + config.MAX_POSITION + " BTC");
    Log("   止损: " + config.STOP_LOSS + "%");
    Log("   止盈: " + config.TAKE_PROFIT + "%");
    
    if (config.ENABLE_SHORT_SELLING) {
        Log("   允许做空: 是");
    } else {
        Log("   允许做空: 否");
    }
    
    // 设置交易所
    exchange.SetRate(config.EXCHANGE);
    exchange.SetCurrency(config.SYMBOL.split('_')[0]);
    
    // 获取初始账户信息
    var initAccount = exchange.GetAccount();
    if (initAccount && initAccount.Balance) {
        state.peakBalance = initAccount.Balance;
        Log("💰 初始余额: " + initAccount.Balance + " " + config.SYMBOL.split('_')[1]);
    }
    
    // ========== 主循环 ==========
    Log("🔄 进入主循环...");
    
    while (true) {
        try {
            // 1. 检查日期重置
            checkDateReset();
            
            // 2. 检查交易限制
            if (!checkTradeLimits()) {
                Sleep(config.CHECK_INTERVAL * 1000);
                continue;
            }
            
            // 3. 获取市场数据
            var marketData = getMarketData();
            if (!marketData.available) {
                Log("⚠️  市场数据不可用，等待重试");
                Sleep(60000);
                continue;
            }
            
            // 4. 获取AI分析信号
            var aiSignal = getAISignal();
            if (!aiSignal) {
                Log("⏭️  未获取到AI信号，等待下次检查");
                Sleep(config.CHECK_INTERVAL * 1000);
                continue;
            }
            
            // 5. 分析信号并生成决策
            var decision = analyzeAndDecide(aiSignal, marketData);
            
            // 6. 执行交易
            if (decision.action !== "hold") {
                executeTrade(decision, marketData);
            } else {
                if (config.LOG_LEVEL === "debug") {
                    Log("⏸️  决策: 持仓不动 - " + decision.reason);
                }
            }
            
            // 7. 更新统计信息
            updateStatistics();
            
            // 8. 等待下次检查
            if (config.LOG_LEVEL === "debug") {
                Log("⏰ 等待下次检查 (" + config.CHECK_INTERVAL + "秒)...");
            }
            Sleep(config.CHECK_INTERVAL * 1000);
            
        } catch (error) {
            Log("❌ 策略执行异常: " + error);
            Log("🔄 等待60秒后重试...");
            Sleep(60000);
        }
    }
    
    // ========== 核心功能函数 ==========
    
    // 检查日期重置
    function checkDateReset() {
        var today = new Date().getDate();
        if (state.lastTradeDate !== today) {
            Log("📅 新的一天开始，重置交易计数");
            state.dailyTradeCount = 0;
            state.lastTradeDate = today;
            state.consecutiveLosses = 0;
            state.consecutiveWins = 0;
        }
    }
    
    // 检查交易限制
    function checkTradeLimits() {
        // 检查每日交易次数
        if (state.dailyTradeCount >= config.MAX_DAILY_TRADES) {
            Log("⏹️  达到每日交易限制: " + state.dailyTradeCount + "/" + config.MAX_DAILY_TRADES);
            return false;
        }
        
        // 检查冷却时间
        var now = Date.now();
        var cooldownMs = config.COOLDOWN_MINUTES * 60 * 1000;
        if (state.lastTradeTime > 0 && (now - state.lastTradeTime) < cooldownMs) {
            if (config.LOG_LEVEL === "debug") {
                var remaining = Math.ceil((cooldownMs - (now - state.lastTradeTime)) / 60000);
                Log("⏳ 冷却时间剩余: " + remaining + "分钟");
            }
            return false;
        }
        
        // 检查连续亏损
        if (state.consecutiveLosses >= 3) {
            Log("⚠️  连续亏损" + state.consecutiveLosses + "次，暂停交易30分钟");
            Sleep(30 * 60 * 1000);
            state.consecutiveLosses = 0;
            return false;
        }
        
        // 检查回撤控制
        if (state.currentDrawdown >= 20) {
            Log("⚠️  当前回撤" + state.currentDrawdown.toFixed(2) + "%，暂停交易");
            Sleep(60 * 60 * 1000); // 暂停1小时
            return false;
        }
        
        return true;
    }
    
    // 获取市场数据
    function getMarketData() {
        try {
            var ticker = exchange.GetTicker();
            var depth = exchange.GetDepth();
            var account = exchange.GetAccount();
            
            if (!ticker || !depth || !account) {
                return { available: false };
            }
            
            return {
                available: true,
                price: ticker.Last,
                bid: ticker.Buy,
                ask: ticker.Sell,
                high: ticker.High,
                low: ticker.Low,
                volume: ticker.Volume,
                bidSize: depth.Bids[0] ? depth.Bids[0].Amount : 0,
                askSize: depth.Asks[0] ? depth.Asks[0].Amount : 0,
                balance: account.Balance,
                frozen: account.FrozenBalance,
                total: account.Balance + account.FrozenBalance
            };
            
        } catch (error) {
            Log("❌ 获取市场数据失败: " + error);
            return { available: false };
        }
    }
    
    // 获取AI分析信号
    function getAISignal() {
        try {
            if (config.LOG_LEVEL === "debug") {
                Log("📡 正在获取AI分析信号...");
            }
            
            // 调用AI分析API
            var response = HttpQuery(config.AI_API_URL, "POST", 
                JSON.stringify({symbol: "BTC"}), 
                "Content-Type: application/json"
            );
            
            if (!response) {
                Log("⚠️  AI API无响应");
                return null;
            }
            
            var data = JSON.parse(response);
            
            if (data.error) {
                Log("❌ AI API错误: " + data.error);
                return null;
            }
            
            // 解析信号
            var signal = {
                symbol: config.SYMBOL,
                direction: data.signal ? data.signal.direction : "hold",
                confidence: data.signal ? data.signal.confidence : 0,
                price: data.current_price || 0,
                timestamp: Date.now(),
                reasoning: data.signal ? data.signal.reasoning : "无信号",
                rawData: data
            };
            
            if (config.LOG_LEVEL === "debug") {
                Log("📊 AI信号详情:");
                Log("   方向: " + signal.direction);
                Log("   置信度: " + signal.confidence + "%");
                Log("   价格: $" + signal.price.toFixed(2));
                Log("   时间: " + new Date(signal.timestamp).toLocaleTimeString());
            }
            
            return signal;
            
        } catch (error) {
            Log("❌ 获取AI信号异常: " + error);
            return null;
        }
    }
    
    // 分析信号并生成决策
    function analyzeAndDecide(signal, market) {
        var decision = {
            action: "hold",
            symbol: config.SYMBOL,
            amount: 0,
            price: market.price,
            reason: "",
            type: config.USE_MARKET_ORDERS ? "market" : "limit",
            confidence: signal.confidence
        };
        
        // 1. 检查信号有效性
        if (signal.confidence < config.MIN_CONFIDENCE) {
            decision.reason = "置信度过低: " + signal.confidence + "%";
            return decision;
        }
        
        if (signal.confidence > config.MAX_CONFIDENCE) {
            decision.reason = "置信度过高: " + signal.confidence + "%";
            return decision;
        }
        
        // 2. 检查当前持仓
        if (state.currentPosition !== 0) {
            return handleExistingPosition(signal, market, decision);
        }
        
        // 3. 新开仓决策
        return handleNewPosition(signal, market, decision);
    }
    
    // 处理已有持仓
    function handleExistingPosition(signal, market, decision) {
        var positionProfit = 0;
        var positionProfitPercent = 0;
        
        if (state.positionDirection === "long") {
            positionProfit = (market.price - state.entryPrice) * state.currentPosition;
            positionProfitPercent = ((market.price - state.entryPrice) / state.entryPrice) * 100;
        } else if (state.positionDirection === "short") {
            positionProfit = (state.entryPrice - market.price) * Math.abs(state.currentPosition);
            positionProfitPercent = ((state.entryPrice - market.price) / state.entryPrice) * 100;
        }
        
        // 更新最高价/最低价
        if (state.positionDirection === "long") {
            if (market.price > state.highestPrice) state.highestPrice = market.price;
        } else if (state.positionDirection === "short") {
            if (market.price < state.lowestPrice) state.lowestPrice = market.price;
        }
        
        // 检查止损止盈
        var stopLossTriggered = false;
        var takeProfitTriggered = false;
        var trailingStopTriggered = false;
        
        // 止损检查
        if (positionProfitPercent <= -config.STOP_LOSS) {
            stopLossTriggered = true;
            decision.action = "close";
            decision.amount = Math.abs(state.currentPosition);
            decision.reason = "触发止损: " + positionProfitPercent.toFixed(2) + "%";
        }
        
        // 止盈检查
        if (positionProfitPercent >= config.TAKE_PROFIT) {
            takeProfitTriggered = true;
            decision.action = "close";
            decision.amount = Math.abs(state.currentPosition);
            decision.reason = "触发止盈: " + positionProfitPercent.toFixed(2) + "%";
        }
        
        // 移动止损检查
        if (config.TRAILING_STOP > 0) {
            var trailingStopPrice = 0;
            if (state.positionDirection === "long") {
                trailingStopPrice = state.highestPrice * (1 - config.TRAILING_STOP / 100);
                if (market.price <= trailingStopPrice) {
                    trailingStopTriggered = true;
                    decision.action = "close";
                    decision.amount = Math.abs(state.currentPosition);
                    decision.reason = "触发移动止损: $" + market.price.toFixed(2) + " <= $" + trailingStopPrice.toFixed(2);
                }
            }
        }
        
        if (stopLossTriggered || takeProfitTriggered || trailingStopTriggered) {
            return decision;
        }
        
        // 检查反向信号
        if (signal.direction === "buy" && state.positionDirection === "short") {
            // 做空时收到买入信号
            if (positionProfitPercent > 2) {
                decision.action = "close";
                decision.amount = Math.abs(state.currentPosition);
                decision.reason = "做空盈利时收到买入信号，平仓止盈";
            } else if (positionProfitPercent < -2) {
                decision.action = "close";
                decision.amount = Math.abs(state.currentPosition);
                decision.reason = "做空亏损时收到买入信号，平仓止损";
            }
        } else if (signal.direction === "sell" && state.positionDirection === "long") {
            // 做多时收到卖出信号
            if (positionProfitPercent > 2) {
                decision.action = "close";
                decision.amount = Math.abs(state.currentPosition);
                decision.reason = "做多盈利时收到卖出信号，平仓止盈";
            } else if (positionProfitPercent < -2) {
                decision.action = "close";
                decision.amount = Math.abs(state.currentPosition);
                decision.reason = "做多亏损时收到卖出信号，平仓止损";
            }
        }
        
        return decision;
    }
    
    // 处理新开仓
    function handleNewPosition(signal, market, decision) {
        // 检查做空是否允许
        if (signal.direction === "sell" && !config.ENABLE_SHORT_SELLING) {
            decision.reason = "做空功能已禁用";
            return decision;
        }
        
        // 计算交易数量
        var confidenceFactor = signal.confidence / 100;
        var baseAmount = config.BASE_TRADE_AMOUNT;
        var scaledAmount = baseAmount * confidenceFactor * config.POSITION_SCALE;
        
        // 限制最大持仓
        scaledAmount = Math.min(scaledAmount, config.MAX_POSITION);
        
        // 检查资金是否足够
        var requiredFunds = scaledAmount * market.price;
        if (market.balance < requiredFunds) {
            decision.reason = "资金不足: 需要$" + requiredFunds.toFixed(2) + 
                            "，可用$" + market.balance.toFixed(2);
            return decision;
        }
        
        // 设置决策
        decision.action = signal.direction;
        decision.amount = scaledAmount;
        decision.reason = "AI信号: " + signal.confidence + "%置信度";
        
        // 设置限价单价格
        if (!config.USE_MARKET_ORDERS) {
            if (signal.direction === "buy") {
                decision.price = market.price * (1 - config.ORDER_PRICE_OFFSET);
            } else {
                decision.price = market.price * (1 +