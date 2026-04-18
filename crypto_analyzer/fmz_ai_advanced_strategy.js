// ============================================
// AI智能量化交易策略 - FMZ平台专用
// 版本: 2.0
// 作者: AI量化交易系统
// ============================================

function main() {
    Log("🚀 AI智能量化交易策略启动");
    Log("============================================");
    
    // ========== 策略配置 ==========
    var config = {
        // 交易所配置
        exchange: "binance",      // 交易所名称
        symbol: "BTC_USDT",       // 交易对
        
        // AI API配置
        aiApiUrl: "http://localhost:5000/api/analyze",  // AI分析API地址
        strategyApiUrl: "http://localhost:5002/api/strategy/process-signal", // 策略API地址
        
        // 交易参数
        checkInterval: 300,       // 检查间隔（秒）
        minConfidence: 60,        // 最小置信度（%）
        maxConfidence: 90,        // 最大置信度（%）
        
        // 仓位管理
        baseTradeAmount: 0.001,   // 基础交易数量（BTC）
        maxPosition: 0.01,        // 最大持仓（BTC）
        positionScale: 0.5,       // 仓位缩放系数（根据置信度）
        
        // 风险管理
        stopLoss: 5.0,            // 止损百分比
        takeProfit: 10.0,         // 止盈百分比
        trailingStop: 2.0,        // 移动止损百分比
        
        // 交易控制
        maxDailyTrades: 10,       // 每日最大交易次数
        cooldownMinutes: 30,      // 冷却时间（分钟）
        
        // 日志级别
        logLevel: "info"          // debug, info, warning, error
    };
    
    // ========== 状态变量 ==========
    var state = {
        lastTradeTime: 0,         // 上次交易时间
        dailyTradeCount: 0,       // 今日交易次数
        lastTradeDate: 0,         // 上次交易日期
        currentPosition: 0,       // 当前持仓数量
        entryPrice: 0,            // 入场价格
        highestPrice: 0,          // 最高价（用于移动止损）
        lowestPrice: 0,           // 最低价（用于移动止损）
        totalTrades: 0,           // 总交易次数
        totalProfit: 0,           // 总盈亏
        consecutiveLosses: 0      // 连续亏损次数
    };
    
    // ========== 初始化 ==========
    Log("📋 策略配置:");
    Log("   交易所: " + config.exchange);
    Log("   交易对: " + config.symbol);
    Log("   检查间隔: " + config.checkInterval + "秒");
    Log("   最小置信度: " + config.minConfidence + "%");
    Log("   最大持仓: " + config.maxPosition + " BTC");
    Log("   止损: " + config.stopLoss + "%");
    Log("   止盈: " + config.takeProfit + "%");
    
    // 设置交易所
    exchange.SetRate(config.exchange);
    exchange.SetCurrency(config.symbol.split('_')[0]);
    
    // ========== 主循环 ==========
    while (true) {
        try {
            // 检查日期重置
            checkDateReset();
            
            // 检查交易限制
            if (!checkTradeLimits()) {
                Sleep(config.checkInterval * 1000);
                continue;
            }
            
            // 获取AI分析信号
            var aiSignal = getAISignal();
            if (!aiSignal) {
                Log("⏭️  未获取到AI信号，等待下次检查");
                Sleep(config.checkInterval * 1000);
                continue;
            }
            
            // 分析信号
            var analysis = analyzeSignal(aiSignal);
            if (!analysis.valid) {
                Log("⏭️  信号无效，跳过交易");
                Sleep(config.checkInterval * 1000);
                continue;
            }
            
            // 获取账户信息
            var account = getAccountInfo();
            if (!account.available) {
                Log("⚠️  账户不可用，等待重试");
                Sleep(60000);
                continue;
            }
            
            // 检查当前持仓
            var positionInfo = checkPosition(account);
            
            // 生成交易决策
            var decision = makeTradingDecision(analysis, account, positionInfo);
            
            // 执行交易
            if (decision.action !== "hold") {
                executeTrade(decision, account);
            } else {
                Log("⏸️  决策: 持仓不动");
            }
            
            // 等待下次检查
            Log("⏰ 等待下次检查 (" + config.checkInterval + "秒)...");
            Sleep(config.checkInterval * 1000);
            
        } catch (error) {
            Log("❌ 策略执行异常: " + error);
            Log("🔄 等待60秒后重试...");
            Sleep(60000);
        }
    }
    
    // ========== 功能函数 ==========
    
    // 检查日期重置
    function checkDateReset() {
        var today = new Date().getDate();
        if (state.lastTradeDate !== today) {
            Log("📅 新的一天开始，重置交易计数");
            state.dailyTradeCount = 0;
            state.lastTradeDate = today;
            state.consecutiveLosses = 0;
        }
    }
    
    // 检查交易限制
    function checkTradeLimits() {
        // 检查每日交易次数
        if (state.dailyTradeCount >= config.maxDailyTrades) {
            Log("⏹️  达到每日交易限制: " + state.dailyTradeCount + "/" + config.maxDailyTrades);
            return false;
        }
        
        // 检查冷却时间
        var now = Date.now();
        var cooldownMs = config.cooldownMinutes * 60 * 1000;
        if (state.lastTradeTime > 0 && (now - state.lastTradeTime) < cooldownMs) {
            var remaining = Math.ceil((cooldownMs - (now - state.lastTradeTime)) / 60000);
            Log("⏳ 冷却时间剩余: " + remaining + "分钟");
            return false;
        }
        
        // 检查连续亏损
        if (state.consecutiveLosses >= 3) {
            Log("⚠️  连续亏损" + state.consecutiveLosses + "次，暂停交易30分钟");
            Sleep(30 * 60 * 1000);
            state.consecutiveLosses = 0;
            return false;
        }
        
        return true;
    }
    
    // 获取AI分析信号
    function getAISignal() {
        try {
            Log("📡 获取AI分析信号...");
            
            var response = HttpQuery(config.aiApiUrl, "POST", 
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
            
            // 提取信号信息
            var signal = {
                symbol: config.symbol,
                direction: data.signal ? data.signal.direction : "hold",
                confidence: data.signal ? data.signal.confidence : 0,
                price: data.current_price || 0,
                timestamp: Date.now(),
                reasoning: data.signal ? data.signal.reasoning : "无信号"
            };
            
            Log("📊 AI信号分析:");
            Log("   方向: " + signal.direction);
            Log("   置信度: " + signal.confidence + "%");
            Log("   价格: $" + signal.price.toFixed(2));
            Log("   推理: " + signal.reasoning);
            
            return signal;
            
        } catch (error) {
            Log("❌ 获取AI信号失败: " + error);
            return null;
        }
    }
    
    // 分析信号
    function analyzeSignal(signal) {
        var analysis = {
            valid: false,
            direction: signal.direction,
            confidence: signal.confidence,
            price: signal.price,
            action: "hold",
            reason: ""
        };
        
        // 检查置信度
        if (signal.confidence < config.minConfidence) {
            analysis.reason = "置信度过低: " + signal.confidence + "% < " + config.minConfidence + "%";
            return analysis;
        }
        
        if (signal.confidence > config.maxConfidence) {
            analysis.reason = "置信度过高，可能过拟合: " + signal.confidence + "% > " + config.maxConfidence + "%";
            return analysis;
        }
        
        // 检查价格有效性
        if (signal.price <= 0) {
            analysis.reason = "无效价格: " + signal.price;
            return analysis;
        }
        
        analysis.valid = true;
        
        // 根据置信度确定行动
        if (signal.confidence >= 80) {
            analysis.action = signal.direction;  // 高置信度，直接执行
            analysis.reason = "高置信度信号 (" + signal.confidence + "%)";
        } else if (signal.confidence >= 70) {
            analysis.action = signal.direction;  // 中等置信度
            analysis.reason = "中等置信度信号 (" + signal.confidence + "%)";
        } else if (signal.confidence >= config.minConfidence) {
            analysis.action = "hold";  // 低置信度，持仓观察
            analysis.reason = "低置信度信号，观察 (" + signal.confidence + "%)";
        }
        
        return analysis;
    }
    
    // 获取账户信息
    function getAccountInfo() {
        try {
            var account = exchange.GetAccount();
            
            if (!account) {
                Log("❌ 获取账户信息失败");
                return { available: false };
            }
            
            var info = {
                available: true,
                balance: account.Balance || 0,
                frozen: account.FrozenBalance || 0,
                total: (account.Balance || 0) + (account.FrozenBalance || 0),
                currency: config.symbol.split('_')[1]  // USDT
            };
            
            if (config.logLevel === "debug") {
                Log("💰 账户详情:");
                Log("   总余额: " + info.total + " " + info.currency);
                Log("   可用余额: " + info.balance + " " + info.currency);
                Log("   冻结余额: " + info.frozen + " " + info.currency);
            }
            
            return info;
            
        } catch (error) {
            Log("❌ 获取账户信息异常: " + error);
            return { available: false };
        }
    }
    
    // 检查持仓
    function checkPosition(account) {
        try {
            var ticker = exchange.GetTicker();
            var currentPrice = ticker.Last;
            
            var position = {
                hasPosition: state.currentPosition > 0,
                amount: state.currentPosition,
                entryPrice: state.entryPrice,
                currentPrice: currentPrice,
                profitLoss: 0,
                profitLossPercent: 0
            };
            
            if (position.hasPosition) {
                position.profitLoss = (currentPrice - position.entryPrice) * position.amount;
                position.profitLossPercent = ((currentPrice - position.entryPrice) / position.entryPrice) * 100;
                
                // 更新最高最低价
                if (currentPrice > state.highestPrice || state.highestPrice === 0) {
                    state.highestPrice = currentPrice;
                }
                if (currentPrice < state.lowestPrice || state.lowestPrice === 0) {
                    state.lowestPrice = currentPrice;
                }
                
                Log("📊 持仓状态:");
                Log("   持仓数量: " + position.amount + " BTC");
                Log("   入场价格: $" + position.entryPrice.toFixed(2));
                Log("   当前价格: $" + currentPrice.toFixed(2));
                Log("   浮动盈亏: $" + position.profitLoss.toFixed(2) + 
                    " (" + position.profitLossPercent.toFixed(2) + "%)");
                
                // 检查止损止盈
                checkStopLossTakeProfit(position);
            }
            
            return position;
            
        } catch (error) {
            Log("❌ 检查持仓异常: " + error);
            return { hasPosition: false };
        }
    }
    
    // 检查止损止盈
    function checkStopLossTakeProfit(position) {
        if (!position.hasPosition) return;
        
        var shouldClose = false;
        var reason = "";
        
        // 检查止损
        if (position.profitLossPercent <= -config.stopLoss) {
            shouldClose = true;
            reason = "触发止损: " + position.profitLossPercent.toFixed(2) + "% <= -" + config.stopLoss + "%";
        }
        
        // 检查止盈
        if (position.profitLossPercent >= config.takeProfit) {
            shouldClose = true;
            reason = "触发止盈: " + position.profitLossPercent.toFixed(2) + "% >= " + config.takeProfit + "%";
        }
        
        // 检查移动止损
        if (config.trailingStop > 0 && state.highestPrice > 0) {
            var trailingStopPrice = state.highestPrice * (1 - config.trailingStop / 100);
            if (position.currentPrice <= trailingStopPrice) {
                shouldClose = true;
                reason = "触发移动止损: 当前价$" + position.currentPrice.toFixed(2) + 
                        " <= 移动止损价$" + trailingStopPrice.toFixed(2);
            }
        }
        
        if (shouldClose) {
            Log("🚨 " + reason);
            
            var decision = {
                action: "close",
                symbol: config.symbol,
                amount: position.amount,
                price: position.currentPrice,
                reason: reason,
                type: "market"
            };
            
            executeTrade(decision, { balance: position.amount * position.currentPrice });
        }
    }
    
    // 生成交易决策
    function makeTradingDecision(analysis, account, position) {
        var decision = {
            action: "hold",
            symbol: config.symbol,
            amount: 0,
            price: analysis.price,
            reason: analysis.reason,
            type: "market"
        };
        
        // 如果有持仓，优先处理持仓
        if (position.hasPosition) {
            // 检查是否需要反向操作
            if (analysis.action === "buy" && position.profitLossPercent < -2) {
                // 亏损时收到买入信号，考虑平仓
                decision.action = "close";
                decision.amount = position.amount;
                decision.reason = "亏损时收到反向信号，平仓止损";
            } else if (analysis.action === "sell" && position.profitLossPercent > 2) {
                // 盈利时收到卖出信号，考虑止盈
                decision.action = "close";
                decision.amount = position.amount;
                decision.reason = "盈利时收到反向信号，止盈离场";
            }
            return decision;
        }
        
        // 新开仓决策
        if (analysis.action !== "hold") {
            // 计算交易数量（根据置信度缩放）
            var confidenceFactor = analysis.confidence / 100;
            var scaledAmount = config.baseTradeAmount * confidenceFactor * config.positionScale;
            
            // 确保不超过最大持仓
            scaledAmount = Math.min(scaledAmount, config.maxPosition);
            
            // 检查资金是否足够
            var requiredFunds = scaledAmount * analysis.price;
            if (account.balance >= requiredFunds) {
                decision.action = analysis.action;
                decision.amount = scaledAmount;
                decision.reason = analysis.reason + " | 仓位: " + (confidenceFactor * 100).toFixed(1) + "%";
            } else {
                decision.reason = "资金不足: 需要$" + requiredFunds.toFixed(2) + 
                                "，可用$" + account.balance.toFixed(2);
            }
        }
        
        return decision;
    }
    
    // 执行交易
    function executeTrade(decision, account) {
        try {
            Log("🎯 执行交易决策:");
            Log("   行动: " + decision.action.toUpperCase());
            Log("   数量: " + decision.amount + " BTC");
            Log("   价格: $" + decision.price.toFixed(2));
            Log("   原因: " + decision.reason);
            
            var order = null;
            
            if (decision.action === "buy") {
                Log("🟢 执行买入订单...");
                order = exchange.Buy(-1, decision.amount);
                
                if (order && order.id) {
                    // 更新状态
                    state.currentPosition += decision.amount;
                    state.entryPrice = decision.price;
                    state.highestPrice = decision.price;
                    state.lowestPrice = decision.price;
                    
                    Log("✅ 买入订单成功: #" + order.id);
                    Log("   成交价: $" + (order.price || decision.price).toFixed(2));
                    Log("   成交数量: " + (order.amount || decision.amount) + " BTC");
                }
                
            } else if (decision.action === "sell") {
                Log("🔴 执行卖出订单...");
                order = exchange.Sell(-1, decision.amount);
                
                if (order && order.id) {
                    // 更新状态（做空，持仓为负）
                    state.currentPosition -= decision.amount;
                    state.entryPrice = decision.price;
                    state.highestPrice = decision.price;
                    state.lowestPrice = decision.price;
                    
                    Log("✅ 卖出订单成功: #" + order.id);
                    Log("   成交价: $" + (order.price || decision.price).toFixed(2));
                    Log("   成交数量