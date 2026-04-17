#!/usr/bin/env python3
"""
币安BTC策略 - 策略H (收益率最高 +25.7%)
日线EMA20>EMA50确认趋势 + 1H放量突破布林上轨入场

使用方法:
1. 安装: pip install pandas numpy requests
2. 配置: 设置API_KEY和SECRET_KEY (仅用于查询，信号计算不需要)
3. 运行: python binance_strategy.py
4. 或导入: from binance_strategy import get_signal
"""
import requests
import time
from datetime import datetime

# ========== 配置 ==========
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
LIMIT = 200  # 1H数据量
DAILY_LIMIT = 50  # 日线数据量

# 策略参数
STOP_LOSS_PCT = 0.04  # 4%止损
TAKE_PROFIT_PCT = 0.08  # 8%止盈
FIRST_POSITION = 1000  # 首仓$1000
VOLUME_MULTIPLIER = 1.5  # 放量倍数

# ========== 币安API ==========
def get_klines(symbol, interval, limit=100):
    """获取K线数据"""
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()
    
    result = []
    for k in data:
        result.append({
            't': int(k[0]),
            'o': float(k[1]),
            'h': float(k[2]),
            'l': float(k[3]),
            'c': float(k[4]),
            'v': float(k[5])
        })
    return result

# ========== 技术指标计算 ==========
def calc_ema(prices, period):
    """计算EMA"""
    ema = []
    k = 2 / (period + 1)
    
    for i, price in enumerate(prices):
        if i == 0:
            ema.append(price)
        else:
            ema.append(price * k + ema[-1] * (1 - k))
    return ema

def calc_rsi(prices, period=14):
    """计算RSI"""
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    rsi = []
    for i in range(len(prices)):
        if i < period:
            rsi.append(50)
        elif i == period:
            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi.append(100 - (100 / (1 + rs)))
        else:
            avg_gain = (avg_gain * (period - 1) + gains[i-1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i-1]) / period
            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi.append(100 - (100 / (1 + rs)))
    return rsi

def calc_bollinger(prices, period=20, std_dev=2):
    """计算布林带"""
    mid = []
    upper = []
    lower = []
    
    for i in range(len(prices)):
        if i < period - 1:
            mid.append(prices[i])
            upper.append(prices[i])
            lower.append(prices[i])
        else:
            window = prices[i-period+1:i+1]
            m = sum(window) / period
            variance = sum((x - m) ** 2 for x in window) / period
            s = variance ** 0.5
            
            mid.append(m)
            upper.append(m + std_dev * s)
            lower.append(m - std_dev * s)
    
    return upper, mid, lower

# ========== 核心策略逻辑 ==========
def analyze(symbol=SYMBOL):
    """
    分析市场并返回交易信号
    返回: {
        'action': 'BUY' / 'SELL' / 'HOLD',
        'price': 当前价格,
        'entry': 入场价,
        'sl': 止损价,
        'tp': 止盈价,
        'confidence': 置信度 0-100,
        'reason': 信号原因
    }
    """
    # 获取数据
    klines_1h = get_klines(symbol, "1h", LIMIT)
    klines_daily = get_klines(symbol, "1d", DAILY_LIMIT)
    
    # 提取价格
    closes_1h = [k['c'] for k in klines_1h]
    closes_daily = [k['c'] for k in klines_daily]
    highs_1h = [k['h'] for k in klines_1h]
    volumes_1h = [k['v'] for k in klines_1h]
    
    current_price = closes_1h[-1]
    
    # === 日线趋势判断 ===
    ema20_daily = calc_ema(closes_daily, 20)
    ema50_daily = calc_ema(closes_daily, 50)
    
    daily_bullish = ema20_daily[-1] > ema50_daily[-1]
    
    # === 1H指标 ===
    ema20_1h = calc_ema(closes_1h, 20)
    bb_upper, bb_mid, bb_lower = calc_bollinger(closes_1h, 20)
    rsi_1h = calc_rsi(closes_1h, 14)
    
    # 放量检测
    avg_volume_20 = sum(volumes_1h[-21:-1]) / 20
    current_volume = volumes_1h[-1]
    volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 0
    
    # 突破检测
    bb_upper_last = bb_upper[-1]
    bb_mid_last = bb_mid[-1]
    rsi_last = rsi_1h[-1]
    
    # === 入场信号 ===
    if daily_bullish and current_price > bb_upper_last and volume_ratio > VOLUME_MULTIPLIER:
        # 做多信号
        entry = current_price
        sl = current_price * (1 - STOP_LOSS_PCT)
        tp = current_price * (1 + TAKE_PROFIT_PCT)
        
        confidence = min(90, 50 + volume_ratio * 10 + (current_price - bb_mid_last) / bb_mid_last * 100)
        
        return {
            'action': 'BUY',
            'price': current_price,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'position_size': FIRST_POSITION,
            'confidence': round(confidence, 1),
            'reason': f'放量突破布林上轨 | 放量倍数: {volume_ratio:.1f}x | RSI: {rsi_last:.1f}'
        }
    
    elif not daily_bullish and current_price < bb_lower[-1] and volume_ratio > VOLUME_MULTIPLIER:
        # 做空信号
        entry = current_price
        sl = current_price * (1 + STOP_LOSS_PCT)
        tp = current_price * (1 - TAKE_PROFIT_PCT)
        
        confidence = min(90, 50 + volume_ratio * 10)
        
        return {
            'action': 'SELL',
            'price': current_price,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'position_size': FIRST_POSITION,
            'confidence': round(confidence, 1),
            'reason': f'放量跌破布林下轨 | 放量倍数: {volume_ratio:.1f}x | RSI: {rsi_last:.1f}'
        }
    
    else:
        return {
            'action': 'HOLD',
            'price': current_price,
            'entry': None,
            'sl': None,
            'tp': None,
            'position_size': 0,
            'confidence': 0,
            'reason': f'趋势{"多头" if daily_bullish else "空头"}但无放量突破 | RSI: {rsi_last:.1f}'
        }

# ========== 打印分析结果 ==========
def print_signal():
    """打印当前信号"""
    print("="*60)
    print(f"📊 币安 {SYMBOL} 策略分析")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    result = analyze()
    
    print(f"\n当前价格: ${result['price']:,.2f}")
    print(f"信号: {'🟢 买入' if result['action']=='BUY' else ('🔴 卖出' if result['action']=='SELL' else '⚪ 观望')}")
    print(f"置信度: {result['confidence']}%")
    print(f"信号原因: {result['reason']}")
    
    if result['action'] != 'HOLD':
        print(f"\n📋 入场计划:")
        print(f"  入场价: ${result['entry']:,.2f}")
        print(f"  止损价: ${result['sl']:,.2f} ({STOP_LOSS_PCT*100}%)")
        print(f"  止盈价: ${result['tp']:,.2f} ({TAKE_PROFIT_PCT*100}%)")
        print(f"  仓位: ${result['position_size']}")
        
        # 盈亏预估
        potential_profit = (result['tp'] - result['entry']) / result['entry'] * result['position_size']
        potential_loss = (result['entry'] - result['sl']) / result['entry'] * result['position_size']
        print(f"  预期盈利: ${potential_profit:,.2f}")
        print(f"  预期亏损: ${potential_loss:,.2f}")
    
    print("="*60)
    return result

# ========== 策略D实现 (首仓1000 + 3次加仓) ==========
def analyze_strategy_d():
    """
    策略D: 日线EMA趋势 + RSI超卖 + 金字塔加仓
    - 首仓: $1000
    - 加仓: 3次 ($1000 + $500 + $250)
    - 止损: 3%
    - 止盈: 6%
    """
    klines_1h = get_klines(SYMBOL, "1h", LIMIT)
    klines_daily = get_klines(SYMBOL, "1d", DAILY_LIMIT)
    
    closes_1h = [k['c'] for k in klines_1h]
    closes_daily = [k['c'] for k in klines_daily]
    volumes_1h = [k['v'] for k in klines_1h]
    
    current_price = closes_1h[-1]
    
    # 日线趋势
    ema20_daily = calc_ema(closes_daily, 20)
    ema50_daily = calc_ema(closes_daily, 50)
    daily_bullish = ema20_daily[-1] > ema50_daily[-1]
    
    # 1H指标
    bb_upper, bb_mid, bb_lower = calc_bollinger(closes_1h, 20)
    rsi_1h = calc_rsi(closes_1h, 14)
    
    rsi_last = rsi_1h[-1]
    bb_mid_last = bb_mid[-1]
    
    print("\n" + "="*60)
    print("📊 策略D: RSI超卖 + 金字塔加仓")
    print("="*60)
    print(f"日线趋势: {'🟢 多头' if daily_bullish else '🔴 空头'}")
    print(f"当前价格: ${current_price:,.2f}")
    print(f"布林中轨: ${bb_mid_last:,.2f}")
    print(f"RSI: {rsi_last:.1f}")
    
    if daily_bullish and rsi_last < 35 and current_price <= bb_mid_last:
        print(f"\n🟢 买入信号!")
        print(f"  入场价: ${current_price:,.2f}")
        print(f"  止损: ${current_price * 0.97:,.2f} (3%)")
        print(f"  止盈: ${current_price * 1.06:,.2f} (6%)")
        print(f"\n📋 加仓计划:")
        print(f"  首仓: $1000 @ ${current_price:,.2f}")
        print(f"  加仓1: $1000 @ ${current_price * 0.97:,.2f} (跌3%)")
        print(f"  加仓2: $500 @ ${current_price * 0.94:,.2f} (再跌3%)")
        print(f"  加仓3: $250 @ ${current_price * 0.91:,.2f} (再跌3%)")
        print(f"  总仓位: $2750")
        
        total_cost = 1000 + 1000 + 500 + 250
        avg_price = (1000*current_price + 1000*current_price*0.97 + 500*current_price*0.94 + 250*current_price*0.91) / total_cost
        print(f"  均价: ${avg_price:,.2f}")
    else:
        print(f"\n⚪ 观望信号")
        print(f"原因: 需要日线多头 + RSI<35 + 价格在布林中轨下方")

# ========== 主函数 ==========
if __name__ == "__main__":
    # 打印策略H结果
    print_signal()
    
    # 打印策略D结果
    analyze_strategy_d()
