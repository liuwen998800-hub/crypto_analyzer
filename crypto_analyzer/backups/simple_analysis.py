#!/usr/bin/env python3
"""
简化分析脚本 - 不依赖复杂库
"""

import requests
import json
import time
from datetime import datetime

def get_crypto_prices():
    """获取加密货币价格"""
    print("获取加密货币价格...")
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    prices = {}
    
    for symbol in symbols:
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr"
            params = {"symbol": symbol}
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                coin = symbol.replace('USDT', '')
                
                prices[coin] = {
                    'price': float(data['lastPrice']),
                    'change': float(data['priceChange']),
                    'change_percent': float(data['priceChangePercent']),
                    'high': float(data['highPrice']),
                    'low': float(data['lowPrice']),
                    'volume': float(data['volume'])
                }
                
                print(f"  {coin}: ${prices[coin]['price']:,.2f} ({prices[coin]['change_percent']:+.2f}%)")
            else:
                print(f"  ❌ {symbol}: 获取失败")
                
        except Exception as e:
            print(f"  ❌ {symbol}: 错误 - {e}")
    
    return prices

def get_fear_greed_index():
    """获取恐慌贪婪指数"""
    print("\n获取市场情绪...")
    
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                fgi = data['data'][0]
                value = int(fgi['value'])
                classification = fgi['value_classification']
                
                print(f"  恐慌贪婪指数: {value} ({classification})")
                
                # 转换为交易分数 (恐慌=高分，贪婪=低分)
                sentiment_score = 100 - value  # 恐慌时分数高
                
                if value <= 25:
                    sentiment = "极度恐慌 - 强烈买入信号"
                    trading_action = "积极买入"
                elif value <= 45:
                    sentiment = "恐惧 - 买入机会"
                    trading_action = "考虑买入"
                elif value <= 55:
                    sentiment = "中性 - 观望"
                    trading_action = "观望"
                elif value <= 75:
                    sentiment = "贪婪 - 卖出信号"
                    trading_action = "考虑卖出"
                else:
                    sentiment = "极度贪婪 - 强烈卖出信号"
                    trading_action = "积极卖出"
                
                print(f"  市场情绪: {sentiment}")
                print(f"  情绪分数: {sentiment_score}/100")
                
                return {
                    'value': value,
                    'classification': classification,
                    'sentiment_score': sentiment_score,
                    'trading_action': trading_action,
                    'description': sentiment
                }
    
    except Exception as e:
        print(f"  ⚠️  获取情绪指数失败: {e}")
    
    # 使用默认值
    print("  使用默认情绪分析")
    return {
        'value': 50,
        'classification': 'Neutral',
        'sentiment_score': 50,
        'trading_action': '观望',
        'description': '中性 - 等待明确信号'
    }

def analyze_technical_simple(price_data):
    """简化技术分析"""
    print("\n技术分析...")
    
    results = {}
    
    for coin, data in price_data.items():
        price = data['price']
        change_24h = data['change_percent']
        volume = data['volume']
        
        # 简单技术评分 (0-100)
        score = 50  # 基础分
        
        # 价格变化加分
        if change_24h > 5:
            score += 20  # 大幅上涨
        elif change_24h > 2:
            score += 10  # 上涨
        elif change_24h < -5:
            score -= 20  # 大幅下跌
        elif change_24h < -2:
            score -= 10  # 下跌
        
        # 成交量分析
        avg_volume = 1000000000  # 假设的平均成交量
        if volume > avg_volume * 2:
            score += 10  # 放量
        elif volume < avg_volume * 0.5:
            score -= 5   # 缩量
        
        # 确保在0-100范围内
        score = max(0, min(100, score))
        
        # 确定信号
        if score >= 70:
            signal = "看涨"
            action = "买入"
        elif score >= 40:
            signal = "中性"
            action = "观望"
        else:
            signal = "看跌"
            action = "卖出"
        
        results[coin] = {
            'technical_score': score,
            'signal': signal,
            'action': action,
            'price': price,
            'change_24h': change_24h
        }
        
        print(f"  {coin}: {signal} ({score}/100) - {action}")
    
    return results

def generate_composite_signals(technical_results, sentiment_data):
    """生成综合信号"""
    print("\n生成综合交易信号...")
    
    composite_signals = {}
    
    for coin, tech_data in technical_results.items():
        tech_score = tech_data['technical_score']
        sentiment_score = sentiment_data['sentiment_score']
        
        # 综合评分 (技术60% + 情绪40%)
        composite_score = int(tech_score * 0.6 + sentiment_score * 0.4)
        
        # 确定综合信号
        if composite_score >= 80:
            signal = "STRONG_BUY"
            description = "强烈买入 - 技术面和情绪面均强烈看涨"
            color = "🟢"
        elif composite_score >= 60:
            signal = "BUY"
            description = "买入 - 多数指标显示看涨"
            color = "🟡"
        elif composite_score >= 40:
            signal = "NEUTRAL"
            description = "观望 - 指标矛盾或无明确趋势"
            color = "⚪"
        elif composite_score >= 20:
            signal = "SELL"
            description = "卖出 - 多数指标显示看跌"
            color = "🟠"
        else:
            signal = "STRONG_SELL"
            description = "强烈卖出 - 技术面和情绪面均强烈看跌"
            color = "🔴"
        
        # 支撑阻力位 (简化)
        price = tech_data['price']
        support = price * 0.95  # 下方5%作为支撑
        resistance = price * 1.05  # 上方5%作为阻力
        
        composite_signals[coin] = {
            'signal': signal,
            'composite_score': composite_score,
            'description': description,
            'color': color,
            'price': price,
            'support': support,
            'resistance': resistance,
            'breakdown': {
                'technical_score': tech_score,
                'sentiment_score': sentiment_score
            }
        }
        
        print(f"  {color} {coin}: {signal} (综合分数: {composite_score}/100)")
        print(f"     描述: {description}")
        print(f"     价格: ${price:,.2f}")
        print(f"     支撑: ${support:,.2f}")
        print(f"     阻力: ${resistance:,.2f}")
    
    return composite_signals

def generate_market_summary(composite_signals, sentiment_data):
    """生成市场总结"""
    print("\n" + "=" * 60)
    print("市场总结")
    print("=" * 60)
    
    # 统计信号
    signal_counts = {
        'STRONG_BUY': 0,
        'BUY': 0,
        'NEUTRAL': 0,
        'SELL': 0,
        'STRONG_SELL': 0
    }
    
    for coin, signal_data in composite_signals.items():
        signal = signal_data['signal']
        signal_counts[signal] += 1
    
    # 确定市场情绪
    total_coins = len(composite_signals)
    buy_signals = signal_counts['STRONG_BUY'] + signal_counts['BUY']
    sell_signals = signal_counts['STRONG_SELL'] + signal_counts['SELL']
    
    if buy_signals > sell_signals:
        market_sentiment = "看涨"
    elif sell_signals > buy_signals:
        market_sentiment = "看跌"
    else:
        market_sentiment = "震荡"
    
    # 寻找最强和最弱币种
    if composite_signals:
        strongest = max(composite_signals.items(), key=lambda x: x[1]['composite_score'])
        weakest = min(composite_signals.items(), key=lambda x: x[1]['composite_score'])
    else:
        strongest = weakest = (None, None)
    
    print(f"市场情绪: {market_sentiment}")
    print(f"恐慌贪婪指数: {sentiment_data['value']} ({sentiment_data['classification']})")
    print(f"情绪建议: {sentiment_data['trading_action']}")
    
    print(f"\n信号分布:")
    for signal, count in signal_counts.items():
        if count > 0:
            print(f"  {signal}: {count}个币种")
    
    if strongest[0]:
        print(f"\n最强币种: {strongest[0]} ({strongest[1]['signal']}, {strongest[1]['composite_score']}分)")
    if weakest[0]:
        print(f"最弱币种: {weakest[0]} ({weakest[1]['signal']}, {weakest[1]['composite_score']}分)")
    
    print(f"\n交易建议:")
    if market_sentiment == "看涨" and sentiment_data['value'] <= 45:
        print("  ✅ 市场整体看涨且情绪恐慌，是良好的买入机会")
    elif market_sentiment == "看跌" and sentiment_data['value'] >= 55:
        print("  ⚠️  市场看跌且情绪贪婪，注意风险控制")
    else:
        print("  🔄 市场方向不明，建议谨慎操作，等待明确信号")

def save_results(price_data, sentiment_data, composite_signals):
    """保存分析结果"""
    print("\n" + "=" * 60)
    print("保存分析结果")
    print("=" * 60)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 创建结果字典
    results = {
        'timestamp': datetime.now().isoformat(),
        'price_data': price_data,
        'sentiment_data': sentiment_data,
        'composite_signals': composite_signals,
        'summary': {
            'total_coins_analyzed': len(price_data),
            'analysis_time': timestamp
        }
    }
    
    # 保存为JSON
    import os
    os.makedirs('results', exist_ok=True)
    
    json_file = f'results/analysis_{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # 保存为CSV
    csv_file = f'results/summary_{timestamp}.csv'
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write('symbol,signal,score,price,change_24h,support,resistance\n')
        for coin, signal_data in composite_signals.items():
            price_info = price_data.get(coin, {})
            f.write(f"{coin},{signal_data['signal']},{signal_data['composite_score']},"
                   f"{price_info.get('price', 0)},{price_info.get('change_percent', 0)},"
                   f"{signal_data['support']},{signal_data['resistance']}\n")
    
    print(f"✅ 结果已保存:")
    print(f"  JSON文件: {json_file}")
    print(f"  CSV文件: {csv_file}")
    
    # 更新最新结果
    latest_file = 'results/latest.json'
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"  最新结果: {latest_file}")

def main():
    """主函数"""
    print("=" * 60)
    print("虚拟币分析指标产品 - 简化分析系统")
    print("=" * 60)
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("分析币种: BTC, ETH, SOL")
    print("=" * 60)
    
    try:
        # 1. 获取价格数据
        price_data = get_crypto_prices()
        if not price_data:
            print("❌ 无法获取价格数据，分析终止")
            return
        
        # 2. 获取市场情绪
        sentiment_data = get_fear_greed_index()
        
        # 3. 技术分析
        technical_results = analyze_technical_simple(price_data)
        
        # 4. 生成综合信号
        composite_signals = generate_composite_signals(technical_results, sentiment_data)
        
        # 5. 市场总结
        generate_market_summary(composite_signals, sentiment_data)
        
        # 6. 保存结果
        save_results(price_data, sentiment_data, composite_signals)
        
        print("\n" + "=" * 60)
        print("分析完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 分析过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()