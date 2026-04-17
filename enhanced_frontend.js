// 增强版前端显示逻辑

function displayEnhancedResults(data) {
    // 隐藏等待卡，显示所有结果卡片
    document.getElementById('waitCard').style.display = 'none';
    document.getElementById('resultsCard').style.display = 'block';
    document.getElementById('aiModelsCard').style.display = 'block';
    document.getElementById('techCard').style.display = 'block';
    document.getElementById('maCard').style.display = 'block';
    document.getElementById('bbCard').style.display = 'block';
    document.getElementById('adviceCard').style.display = 'block';
    document.getElementById('levelsCard').style.display = 'block';
    document.getElementById('logCard').style.display = 'block';
    
    // 价格数据
    var price = data.price_data.current_price;
    var change = data.price_data.price_change_pct_24h;
    document.getElementById('resPrice').textContent = '$' + price.toLocaleString();
    var changeEl = document.getElementById('resChange');
    changeEl.textContent = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';
    changeEl.className = 'change ' + (change >= 0 ? 'up' : 'down');
    
    // 信号
    var signal = data.signal.signal;
    var signalEl = document.getElementById('resSignal');
    signalEl.textContent = signal;
    signalEl.className = 'signal-badge';
    if (signal.indexOf('BUY') >= 0) {
        signalEl.classList.add('signal-buy');
    } else if (signal.indexOf('SELL') >= 0) {
        signalEl.classList.add('signal-sell');
    } else {
        signalEl.classList.add('signal-neutral');
    }
    
    // 评分
    document.getElementById('resScore').textContent = data.composite_score.composite + '/100';
    
    // 时间
    var timestamp = new Date(data.timestamp);
    document.getElementById('resTime').textContent = timestamp.toLocaleString('zh-CN', {hour12: false});
    
    // 双模型共识
    var ai = data.ai_analysis.consensus;
    document.getElementById('resDirection').textContent = 
        ai.direction === 'bullish' ? '看涨' : 
        ai.direction === 'bearish' ? '看跌' : '中性';
    document.getElementById('resConfidence').textContent = ai.confidence + '%';
    document.getElementById('resAgreement').textContent = (ai.agreement_score || 0) + '%';
    
    // 显示双模型并排分析
    displayAIModels(data.ai_analysis);
    
    // 显示详细技术指标
    displayTechnicalIndicators(data.technical_indicators, data.price_data.current_price);
    
    // 显示移动平均线
    displayMovingAverages(data.technical_indicators.detailed_indicators, data.price_data.current_price);
    
    // 显示布林带
    displayBollingerBands(data.technical_indicators.detailed_indicators);
    
    // 显示交易建议
    displayTradingAdvice(data.ai_analysis, data.technical_indicators, data.price_data.current_price);
    
    // 显示关键价位
    displayKeyLevels(data.support_resistance);
}

// 显示双模型并排分析
function displayAIModels(aiAnalysis) {
    var html = '';
    
    // DeepSeek分析
    if (aiAnalysis.deepseek) {
        var ds = aiAnalysis.deepseek;
        var dsDirection = ds.direction === 'bullish' ? '看涨' : ds.direction === 'bearish' ? '看跌' : '中性';
        var dsColor = ds.direction === 'bullish' ? '#28a745' : ds.direction === 'bearish' ? '#dc3545' : '#ffc107';
        
        html += '<div class="ai-model-card deepseek">';
        html += '<div class="ai-model-title"><span style="color:#28a745">🤖</span> DeepSeek分析</div>';
        html += '<div style="margin-bottom: 10px;">';
        html += '<p><strong>建议信号:</strong> <span style="color:' + dsColor + ';font-weight:bold;">' + dsDirection + '</span></p>';
        html += '<p><strong>涨的置信度:</strong> <span style="color:#28a745">' + ds.bullish_confidence + '%</span></p>';
        html += '<p><strong>跌的置信度:</strong> <span style="color:#dc3545">' + ds.bearish_confidence + '%</span></p>';
        html += '<p><strong>综合置信度:</strong> ' + ds.confidence + '%</p>';
        html += '</div>';
        
        // 分析详情
        if (ds.analysis_details) {
            html += '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 10px;">';
            html += '<p style="margin: 5px 0;"><strong>震荡指标分析:</strong></p>';
            for (var key in ds.analysis_details) {
                html += '<p style="margin: 3px 0; font-size: 13px;">' + ds.analysis_details[key] + '</p>';
            }
            html += '</div>';
        }
        
        html += '</div>';
    }
    
    // MiniMax分析
    if (aiAnalysis.minimax) {
        var mm = aiAnalysis.minimax;
        var mmDirection = mm.direction === 'bullish' ? '看涨' : mm.direction === 'bearish' ? '看跌' : '中性';
        var mmColor = mm.direction === 'bullish' ? '#28a745' : mm.direction === 'bearish' ? '#dc3545' : '#ffc107';
        var sentiment = mm.sentiment_details || {};
        
        html += '<div class="ai-model-card minimax">';
        html += '<div class="ai-model-title"><span style="color:#dc3545">🧠</span> MiniMax分析</div>';
        html += '<div style="margin-bottom: 10px;">';
        html += '<p><strong>建议信号:</strong> <span style="color:' + mmColor + ';font-weight:bold;">' + mmDirection + '</span></p>';
        html += '<p><strong>涨的置信度:</strong> <span style="color:#28a745">' + mm.bullish_confidence + '%</span></p>';
        html += '<p><strong>跌的置信度:</strong> <span style="color:#dc3545">' + mm.bearish_confidence + '%</span></p>';
        html += '<p><strong>综合置信度:</strong> ' + mm.confidence + '%</p>';
        html += '</div>';
        
        // 情绪分析详情
        if (sentiment) {
            html += '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 10px;">';
            html += '<p style="margin: 5px 0;"><strong>市场情绪分析:</strong></p>';
            html += '<p style="margin: 3px 0; font-size: 13px;">恐慌指数: ' + (sentiment.fear_greed_index || '--') + ' (' + (sentiment.fear_greed_classification || '--') + ')</p>';
            html += '<p style="margin: 3px 0; font-size: 13px;">风险等级: ' + (sentiment.risk_level || '--') + '</p>';
            html += '<p style="margin: 3px 0; font-size: 13px;">价格动能: ' + (sentiment.price_momentum || '--') + ' (' + (sentiment.price_change_pct || 0).toFixed(2) + '%)</p>';
            html += '</div>';
        }
        
        html += '</div>';
    }
    
    document.getElementById('aiModelsGrid').innerHTML = html;
}

// 显示详细技术指标
function displayTechnicalIndicators(techIndicators, currentPrice) {
    var detailed = techIndicators.detailed_indicators || {};
    var html = '<table class="tech-table">';
    html += '<thead><tr><th>指标</th><th>数值</th><th>判断</th></tr></thead><tbody>';
    
    // RSI6
    var rsi6 = detailed.rsi6 || 0;
    var rsi6Judgment = getRSIJudgment(rsi6);
    html += '<tr><td>RSI6</td><td class="indicator-value">' + rsi6.toFixed(2) + '</td><td class="' + getIndicatorClass(rsi6Judgment) + '">' + rsi6Judgment + '</td></tr>';
    
    // RSI14
    var rsi14 = detailed.rsi14 || 0;
    var rsi14Judgment = getRSIJudgment(rsi14);
    html += '<tr><td>RSI14</td><td class="indicator-value">' + rsi14.toFixed(2) + '</td><td class="' + getIndicatorClass(rsi14Judgment) + '">' + rsi14Judgment + '</td></tr>';
    
    // MACD
    var macd = detailed.macd || 0;
    var macdJudgment = getMACDJudgment(macd);
    html += '<tr><td>MACD</td><td class="indicator-value">' + macd.toFixed(4) + '</td><td class="' + getIndicatorClass(macdJudgment) + '">' + macdJudgment + '</td></tr>';
    
    // KDJ K
    var kdj_k = detailed.kdj_k || 0;
    var kdjJudgment = getKDJJudgment(kdj_k);
    html += '<tr><td>KDJ K</td><td class="indicator-value">' + kdj_k.toFixed(2) + '</td><td class="' + getIndicatorClass(kdjJudgment) + '">' + kdjJudgment + '</td></tr>';
    
    // 威廉指标
    var williams = detailed.williams || 0;
    var williamsJudgment = getWilliamsJudgment(williams);
    html += '<tr><td>威廉指标</td><td class="indicator-value">' + williams.toFixed(2) + '</td><td class="' + getIndicatorClass(williamsJudgment) + '">' + williamsJudgment + '</td></tr>';
    
    // ATR波动率
    var atr = detailed.atr || 0;
    var atrJudgment = getATRJudgment(atr, currentPrice);
    html += '<tr><td>ATR波动率</td><td class="indicator-value">' + atr.toFixed(2) + '</td><td class="' + getIndicatorClass(atrJudgment) + '">' + atrJudgment + '</td></tr>';
    
    // 成交量
    var volume = detailed.volume || {};
    var volumeCurrent = volume.current || 0;
    var volumeMA20 = volume.ma20 || 0;
    var volumeRatio = volume.ratio || 0;
    var volumeJudgment = getVolumeJudgment(volumeRatio);
    
    html += '<tr><td>当前成交量</td><td class="indicator-value">' + volumeCurrent.toFixed(0) + ' BTC</td><td>-</td></tr>';
    html += '<tr><td>20均成交量</td><td class="indicator-value">' + volumeMA20.toFixed(0) + ' BTC</td><td>-</td></tr>';
    html += '<tr><td>量比</td><td class="indicator-value">' + volumeRatio.toFixed(2) + 'x</td><td class="' + getIndicatorClass(volumeJudgment) + '">' + volumeJudgment + '</td></tr>';
    
    html += '</tbody></table>';
    document.getElementById('techContent').innerHTML = html;
}

// 显示移动平均线
function displayMovingAverages(detailedIndicators, currentPrice) {
    var ma = detailedIndicators.moving_averages || {};
    var html = '<div class="ma-section">';
    
    // 当前价格
    html += '<div class="ma-row"><span>当前价格</span><span style="font-weight:bold;">$' + currentPrice.toLocaleString() + '</span><span>-</span></div>';
    
    // EMA5
    var ema5 = ma.ema5 || 0;
    var ema5Diff = ((currentPrice - ema5) / ema5 * 100).toFixed(2);
    var ema5Status = currentPrice > ema5 ? '高于价格' : '低于价格';
    html += '<div class="ma-row"><span>EMA5</span><span>$' + ema5.toLocaleString() + '</span><span>' + (currentPrice > ema5 ? '🟢 ' : '🔴 ') + ema5Status + ' (' + ema5Diff + '%)</span></div>';
    
    // EMA10
    var ema10 = ma.ema10 || 0;
    var ema10Status = currentPrice > ema10 ? '多头排列' : '空头排列';
    html += '<div class="ma-row"><span>EMA10</span><span>$' + ema10.toLocaleString() + '</span><span>' + (currentPrice > ema10 ? '🟢 ' : '🔴 ') + ema10Status + '</span></div>';
    
    // EMA20
    var ema20 = ma.ema20 || 0;
    html += '<div class="ma-row"><span>EMA20</span><span>$' + ema20.toLocaleString() + '</span><span>-</span></div>';
    
    // EMA50
    var ema50 = ma.ema50 || 0;
    html += '<div class="ma-row"><span>EMA50</span><span>$' + ema50.toLocaleString() + '</span><span>-</span></div>';
    
    // EMA200
    var ema200 = ma.ema200 || 0;
    html += '<div class="ma-row"><span>EMA200</span><span>$' + ema200.toLocaleString() + '</span><span>-</span></div>';
    
    html += '</div>';
    document.getElementById('maContent').innerHTML = html;
}

// 显示布林带
function displayBollingerBands(detailedIndicators) {
    var bb = detailedIndicators.bollinger_bands || {};
    var html = '<div class="bb-section">';
    
    html += '<div class="bb-row"><span>位置</span><span>价格</span></div>';
    html += '<div class="bb-row"><span>上轨</span><span style="color:#dc3545;font-weight:bold;">$' + (bb.upper || 0).toLocaleString() + '</span></div>';
    html += '<div class="bb-row"><span>中轨</span><span style="color:#ffc107;font-weight:bold;">$' + (bb.middle || 0).toLocaleString() + '</span></div>';
    html += '<div class="bb-row"><span>下轨</span><span style="color:#28a745;font-weight:bold;">$' + (bb.lower || 0).toLocaleString() + '</span></div>';
    
    html += '</div>';
    document.getElementById('bbContent').innerHTML = html;
}

// 显示交易建议
function displayTradingAdvice(aiAnalysis, techIndicators, currentPrice) {
    var html = '<div class="trading-advice">';
    
    // 短期分析 (1-4h)
    html += '<div style="margin-bottom: 15px;">';
    html += '<p><strong>短期(1-4h):</strong> ';
    
    var macdValue = techIndicators.core_indicators?.macd?.value || 0;
    if (macdValue > 0) {
        html += '上涨动能强劲，MACD柱状图上升';
    } else if (macdValue > -5) {
        html += '上涨动能减弱，MACD柱状图下降';
    } else {
        html += '下跌动能，MACD负值';
    }
    html += '</p>';
    html += '</div>';
    
    // 中期分析 (1-3天)
    html += '<div style="margin-bottom: 15px;">';
    html += '<p><strong>中期(1-3天):</strong> ';
    
    var maSignal = techIndicators.core_indicators?.moving_averages?.signal || 'neutral';
    if (maSignal === 'bullish') {
        html += '均线多头排列，趋势向上，逢低做多';
    } else if (maSignal === 'bearish') {
        html += '均线空头排列，趋势向下，逢高做空';
    } else {
        html += '均线纠缠，震荡行情，高抛低吸';
    }
    html += '</p>';
    html += '</div>';
    
    // 交易建议表格
    html += '<table class="tech-table" style="margin-top: 15px;">';
    html += '<thead><tr><th>操作</th><th>条件</th><th>价位</th></tr></thead><tbody>';
    
    // 做多建议
    var rsi14 = techIndicators.detailed_indicators?.rsi14 || 50;
    if (rsi14 < 40) {
        html += '<tr><td><span style="color:#28a745">🟢 做多</span></td><td>等待回调 + RSI&lt;40</td><td>$' + (currentPrice