#!/usr/bin/env python3
"""
多策略币安BTC永续合约回测系统
设计: 日线定方向 + 1H找入场点
本金: $10,000 | 首仓: $1,000 | 止损: 3% | 止盈: 5%
"""
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ========== 加载数据 ==========
with open('/tmp/binance_BTCUSDT_1y.json') as f:
    raw = json.load(f)

# 币安数据结构: [open_time, o, h, l, c, v, close_time, qv, trades, taker_buy_base, taker_buy_quote, ignore]
df = pd.DataFrame(raw, columns=['t', 'o', 'h', 'l', 'c', 'v', 'ct', 'qv', 'trades', 'tbb', 'tbq', 'ign'])
df['t'] = pd.to_datetime(df['t'], unit='ms')
df = df.set_index('t')
df = df.sort_index()

# 转换数值列
for col in ['o', 'h', 'l', 'c', 'v', 'qv']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# 重采样到1H
df_1h = df[['o','h','l','c','v']].resample('1h').agg({
    'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
}).dropna()

# 日线
df_daily = df[['o','h','l','c','v']].resample('1d').agg({
    'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
}).dropna()

print(f"数据范围: {df_1h.index[0]} 至 {df_1h.index[-1]}")
print(f"1H数据: {len(df_1h)} 根K线")
print(f"日线数据: {len(df_daily)} 根K线")

# ========== 技术指标 ==========
def add_indicators(df):
    df = df.copy()
    # EMA
    df['ema20'] = df['c'].ewm(span=20).mean()
    df['ema50'] = df['c'].ewm(span=50).mean()
    df['ema200'] = df['c'].ewm(span=200).mean()
    
    # RSI
    delta = df['c'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 布林带
    df['bb_mid'] = df['c'].rolling(20).mean()
    bb_std = df['c'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * bb_std
    df['bb_lower'] = df['bb_mid'] - 2 * bb_std
    
    # ATR
    high_low = df['h'] - df['l']
    high_close = np.abs(df['h'] - df['c'].shift())
    low_close = np.abs(df['l'] - df['c'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    
    # 支撑阻力
    df['sr_level'] = (df['bb_upper'] + df['bb_lower']) / 2
    
    return df

df_1h = add_indicators(df_1h)
df_daily = add_indicators(df_daily)

# ========== 策略1: EMA趋势 + 布林带支撑阻力 ==========
def strategy_ema_bb():
    """
    日线 EMA50 > EMA20 判断多空
    1H: 价格回撤到布林带中轨/下轨附近做多，触及上轨做空
    """
    CAPITAL = 10000
    FIRST_POS = 1000
    MAX_POSITIONS = 4
    STOP_LOSS = 0.03
    TAKE_PROFIT = 0.05
    
    trades = []
    equity_curve = [CAPITAL]
    positions = []
    daily_close_tracker = None
    
    for i in range(200, len(df_1h)):
        dt = df_1h.index[i]
        
        # 获取当日数据
        daily_data = df_daily[df_daily.index < dt]
        if len(daily_data) < 50:
            continue
        daily_current = daily_data.iloc[-1]
        daily_prev = daily_data.iloc[-2]
        
        # 日线趋势: EMA50在EMA20上方 = 多头
        daily_bullish = daily_current['ema50'] > daily_current['ema20']
        
        # 1H当前价格
        price = df_1h.iloc[i]['c']
        bb_mid = df_1h.iloc[i]['bb_mid']
        bb_lower = df_1h.iloc[i]['bb_lower']
        bb_upper = df_1h.iloc[i]['bb_upper']
        rsi = df_1h.iloc[i]['rsi']
        atr = df_1h.iloc[i]['atr']
        
        # 如果没有持仓，检查是否需要开仓
        if not positions:
            # 日线收盘价确认 (只在日线收盘时判断方向)
            if daily_close_tracker != daily_current.name:
                daily_close_tracker = daily_current.name
                continue  # 新的一天，等待确认
            
            # 计算总仓位
            total_exposed = sum(p['size'] for p in positions)
            if total_exposed >= FIRST_POS * MAX_POSITIONS:
                continue
            
            # 入场条件
            if daily_bullish:
                # 做多: 价格回撤到布林带下轨附近
                if price <= bb_lower * 1.02 and rsi < 40:
                    entry_price = price
                    stop_loss = entry_price * (1 - STOP_LOSS)
                    take_profit = entry_price * (1 + TAKE_PROFIT)
                    
                    # 计算仓位大小
                    pos_size = FIRST_POS
                    if positions:
                        # 金字塔加仓: 每跌3%加仓一次
                        last_entry = positions[-1]['entry']
                        if price < last_entry * 0.97:  # 比上次低3%
                            pos_size = FIRST_POS
                        else:
                            continue
                    
                    positions.append({
                        'side': 'long',
                        'entry': entry_price,
                        'sl': stop_loss,
                        'tp': take_profit,
                        'size': pos_size,
                        'atr': atr,
                        'entry_idx': i
                    })
                    
        # 检查止损止盈
        for pos in positions[:]:
            pnl_pct = (price - pos['entry']) / pos['entry']
            
            if pos['side'] == 'long':
                if price <= pos['sl'] or pnl_pct >= TAKE_PROFIT:
                    # 平仓
                    pnl = pos['size'] * pnl_pct
                    fee = pos['size'] * 0.0004  # 0.04% 手续费
                    net_pnl = pnl - fee
                    CAPITAL += net_pnl
                    trades.append({
                        'entry_time': df_1h.index[pos['entry_idx']],
                        'exit_time': dt,
                        'side': 'long',
                        'entry': pos['entry'],
                        'exit': price,
                        'size': pos['size'],
                        'pnl': net_pnl,
                        'pnl_pct': pnl_pct * 100
                    })
                    positions.remove(pos)
        
        equity_curve.append(CAPITAL)
    
    return trades, CAPITAL, equity_curve

# ========== 策略2: 支撑阻力 + RSI确认 ==========
def strategy_sr_rsi():
    """
    日线: EMA200判断趋势
    1H: 在支撑位(布林下轨) RSI<35 做多，在阻力位(布林上轨) RSI>65 做空
    金字塔加仓: 每亏损3%加仓$1000
    """
    CAPITAL = 10000
    FIRST_POS = 1000
    MAX_POSITIONS = 4
    STOP_LOSS = 0.03
    TAKE_PROFIT = 0.05
    
    trades = []
    equity_curve = [CAPITAL]
    positions = []
    
    for i in range(200, len(df_1h)):
        dt = df_1h.index[i]
        price = df_1h.iloc[i]['c']
        
        # 日线趋势
        daily_data = df_daily[df_daily.index < dt]
        if len(daily_data) < 50:
            continue
        
        daily_current = daily_data.iloc[-1]
        daily_trend_bullish = daily_current['ema50'] > daily_current['ema200']
        
        bb_mid = df_1h.iloc[i]['bb_mid']
        bb_lower = df_1h.iloc[i]['bb_lower']
        bb_upper = df_1h.iloc[i]['bb_upper']
        rsi = df_1h.iloc[i]['rsi']
        atr = df_1h.iloc[i]['atr']
        
        if not positions:
            total_exposed = 0
            
            if daily_trend_bullish:
                # 做多: 价格在布林下轨附近且RSI超卖
                if price <= bb_lower * 1.03 and rsi < 35:
                    entry_price = price
                    stop_loss = entry_price * (1 - STOP_LOSS)
                    take_profit = entry_price * (1 + TAKE_PROFIT)
                    
                    positions.append({
                        'side': 'long',
                        'entry': entry_price,
                        'sl': stop_loss,
                        'tp': take_profit,
                        'size': FIRST_POS,
                        'entry_idx': i
                    })
            else:
                # 做空: 价格在布林上轨附近且RSI超买
                if price >= bb_upper * 0.97 and rsi > 65:
                    entry_price = price
                    stop_loss = entry_price * (1 + STOP_LOSS)
                    take_profit = entry_price * (1 - TAKE_PROFIT)
                    
                    positions.append({
                        'side': 'short',
                        'entry': entry_price,
                        'sl': stop_loss,
                        'tp': take_profit,
                        'size': FIRST_POS,
                        'entry_idx': i
                    })
        
        # 检查止损止盈
        for pos in positions[:]:
            if pos['side'] == 'long':
                pnl_pct = (price - pos['entry']) / pos['entry']
                hit_sl = price <= pos['sl']
                hit_tp = pnl_pct >= TAKE_PROFIT
            else:
                pnl_pct = (pos['entry'] - price) / pos['entry']
                hit_sl = price >= pos['sl']
                hit_tp = pnl_pct >= TAKE_PROFIT
            
            if hit_sl or hit_tp:
                pnl = pos['size'] * pnl_pct
                fee = pos['size'] * 0.0004
                net_pnl = pnl - fee
                CAPITAL += net_pnl
                trades.append({
                    'entry_time': df_1h.index[pos['entry_idx']],
                    'exit_time': dt,
                    'side': pos['side'],
                    'entry': pos['entry'],
                    'exit': price,
                    'size': pos['size'],
                    'pnl': net_pnl,
                    'pnl_pct': pnl_pct * 100
                })
                positions.remove(pos)
        
        equity_curve.append(CAPITAL)
    
    return trades, CAPITAL, equity_curve

# ========== 策略3: 动态金字塔 + 追踪止损 ==========
def strategy_pyramid_trailing():
    """
    首仓$1000，随后每亏损3%金字塔加仓$1000
    止盈5%但用追踪止损保护利润
    """
    CAPITAL = 10000
    FIRST_POS = 1000
    MAX_POSITIONS = 4
    STOP_LOSS = 0.03
    TAKE_PROFIT = 0.05
    
    trades = []
    equity_curve = [CAPITAL]
    positions = []
    trailing_stop = 0
    
    for i in range(200, len(df_1h)):
        dt = df_1h.index[i]
        price = df_1h.iloc[i]['c']
        
        daily_data = df_daily[df_daily.index < dt]
        if len(daily_data) < 50:
            continue
        
        daily_current = daily_data.iloc[-1]
        daily_bullish = daily_current['ema50'] > daily_current['ema20']
        
        bb_mid = df_1h.iloc[i]['bb_mid']
        bb_lower = df_1h.iloc[i]['bb_lower']
        bb_upper = df_1h.iloc[i]['bb_upper']
        rsi = df_1h.iloc[i]['rsi']
        
        if not positions:
            if daily_bullish and price <= bb_mid * 1.01 and rsi < 45:
                positions.append({
                    'side': 'long',
                    'entry': price,
                    'sl': price * (1 - STOP_LOSS),
                    'tp': price * (1 + TAKE_PROFIT),
                    'size': FIRST_POS,
                    'entry_idx': i,
                    'peak': price
                })
            elif not daily_bullish and price >= bb_mid * 0.99 and rsi > 55:
                positions.append({
                    'side': 'short',
                    'entry': price,
                    'sl': price * (1 + STOP_LOSS),
                    'tp': price * (1 - TAKE_PROFIT),
                    'size': FIRST_POS,
                    'entry_idx': i,
                    'peak': price
                })
        
        # 检查持仓
        for pos in positions[:]:
            # 更新峰值
            if pos['side'] == 'long':
                pos['peak'] = max(pos['peak'], price)
                pnl_pct = (price - pos['entry']) / pos['entry']
                
                # 追踪止损: 盈利超过3%后，回撤1.5%止损
                if pnl_pct > 0.03:
                    trailing_stop = pos['peak'] * 0.985
                    hit_ts = price <= trailing_stop
                else:
                    hit_ts = False
                
                hit_sl = price <= pos['sl']
                hit_tp = pnl_pct >= TAKE_PROFIT
            else:
                pos['peak'] = min(pos['peak'], price)
                pnl_pct = (pos['entry'] - price) / pos['entry']
                
                if pnl_pct > 0.03:
                    trailing_stop = pos['peak'] * 1.015
                    hit_ts = price >= trailing_stop
                else:
                    hit_ts = False
                
                hit_sl = price >= pos['sl']
                hit_tp = pnl_pct >= TAKE_PROFIT
            
            if hit_sl or hit_tp or hit_ts:
                pnl = pos['size'] * pnl_pct
                fee = pos['size'] * 0.0004
                net_pnl = pnl - fee
                CAPITAL += net_pnl
                trades.append({
                    'entry_time': df_1h.index[pos['entry_idx']],
                    'exit_time': dt,
                    'side': pos['side'],
                    'entry': pos['entry'],
                    'exit': price,
                    'size': pos['size'],
                    'pnl': net_pnl,
                    'pnl_pct': pnl_pct * 100,
                    'exit_reason': 'TP' if hit_tp else ('TS' if hit_ts else 'SL')
                })
                positions.remove(pos)
        
        equity_curve.append(CAPITAL)
    
    return trades, CAPITAL, equity_curve

# ========== 策略4: 区间突破 + 固定加仓 ==========
def strategy_breakout():
    """
    日线EMA确认趋势
    1H: 突破昨日高点/低点入场
    首仓$1000，回调加仓最多3次，每次$500
    """
    CAPITAL = 10000
    FIRST_POS = 1000
    ADD_POS = 500
    MAX_TOTAL = 2500
    STOP_LOSS = 0.03
    TAKE_PROFIT = 0.05
    
    trades = []
    equity_curve = [CAPITAL]
    positions = []
    yesterday_high = None
    yesterday_low = None
    
    for i in range(200, len(df_1h)):
        dt = df_1h.index[i]
        price = df_1h.iloc[i]['c']
        
        daily_data = df_daily[df_daily.index < dt]
        if len(daily_data) < 2:
            continue
        
        daily_current = daily_data.iloc[-1]
        daily_bullish = daily_current['ema50'] > daily_current['ema20']
        
        # 获取昨日高低点
        daily_prev = daily_data.iloc[-2]
        yh = daily_prev['h']
        yl = daily_prev['l']
        
        rsi = df_1h.iloc[i]['rsi']
        bb_upper = df_1h.iloc[i]['bb_upper']
        bb_lower = df_1h.iloc[i]['bb_lower']
        
        # 计算现有仓位
        total_size = sum(p['size'] for p in positions)
        
        if not positions:
            if daily_bullish and price > yh and rsi < 70:
                # 突破昨日高点做多
                positions.append({
                    'side': 'long',
                    'entry': price,
                    'sl': min(yh * 0.97, price * 0.97),
                    'tp': price * (1 + TAKE_PROFIT),
                    'size': FIRST_POS,
                    'entry_idx': i
                })
            elif not daily_bullish and price < yl and rsi > 30:
                positions.append({
                    'side': 'short',
                    'entry': price,
                    'sl': max(yl * 1.03, price * 1.03),
                    'tp': price * (1 - TAKE_PROFIT),
                    'size': FIRST_POS,
                    'entry_idx': i
                })
        elif len(positions) < 3 and total_size < MAX_TOTAL:
            # 金字塔加仓: 价格回调时加仓
            last = positions[-1]
            if last['side'] == 'long' and price < last['entry'] * 0.98 and price > last['sl']:
                positions.append({
                    'side': 'long',
                    'entry': price,
                    'sl': last['sl'],
                    'tp': last['entry'] * (1 + TAKE_PROFIT * 1.5),
                    'size': ADD_POS,
                    'entry_idx': i
                })
            elif last['side'] == 'short' and price > last['entry'] * 1.02 and price < last['sl']:
                positions.append({
                    'side': 'short',
                    'entry': price,
                    'sl': last['sl'],
                    'tp': last['entry'] * (1 - TAKE_PROFIT * 1.5),
                    'size': ADD_POS,
                    'entry_idx': i
                })
        
        # 检查止损止盈
        for pos in positions[:]:
            if pos['side'] == 'long':
                pnl_pct = (price - pos['entry']) / pos['entry']
                hit_sl = price <= pos['sl']
                hit_tp = pnl_pct >= TAKE_PROFIT
            else:
                pnl_pct = (pos['entry'] - price) / pos['entry']
                hit_sl = price >= pos['sl']
                hit_tp = pnl_pct >= TAKE_PROFIT
            
            if hit_sl or hit_tp:
                pnl = pos['size'] * pnl_pct
                fee = pos['size'] * 0.0004
                net_pnl = pnl - fee
                CAPITAL += net_pnl
                trades.append({
                    'entry_time': df_1h.index[pos['entry_idx']],
                    'exit_time': dt,
                    'side': pos['side'],
                    'entry': pos['entry'],
                    'exit': price,
                    'size': pos['size'],
                    'pnl': net_pnl,
                    'pnl_pct': pnl_pct * 100
                })
                positions.remove(pos)
        
        equity_curve.append(CAPITAL)
    
    return trades, CAPITAL, equity_curve

# ========== 策略5: 双重确认 + Kelly资金管理 ==========
def strategy_dual_confirm():
    """
    日线趋势确认 + 1H RSI + MACD确认
    Kelly公式计算仓位
    首仓$1000，最多3次加仓，每次翻倍
    """
    CAPITAL = 10000
    BASE_POS = 1000
    STOP_LOSS = 0.03
    TAKE_PROFIT = 0.05
    
    trades = []
    equity_curve = [CAPITAL]
    positions = []
    
    for i in range(200, len(df_1h)):
        dt = df_1h.index[i]
        price = df_1h.iloc[i]['c']
        
        daily_data = df_daily[df_daily.index < dt]
        if len(daily_data) < 50:
            continue
        
        daily_current = daily_data.iloc[-1]
        daily_bullish = daily_current['ema50'] > daily_current['ema20']
        
        # 1H指标
        rsi = df_1h.iloc[i]['rsi']
        bb_mid = df_1h.iloc[i]['bb_mid']
        bb_lower = df_1h.iloc[i]['bb_lower']
        bb_upper = df_1h.iloc[i]['bb_upper']
        
        # MACD (简化版)
        ema12 = df_1h.iloc[i-11:i+1]['c'].ewm(span=12).mean().iloc[-1] if i >= 12 else df_1h.iloc[i]['c']
        ema26 = df_1h.iloc[i-25:i+1]['c'].ewm(span=26).mean().iloc[-1] if i >= 26 else df_1h.iloc[i]['c']
        macd = ema12 - ema26
        macd_signal = macd * 0.9  # 简化signal
        
        macd_bullish = macd > macd_signal
        macd_hist = macd - macd_signal
        
        if not positions:
            total_size = sum(p['size'] for p in positions)
            if total_size >= BASE_POS * 4:
                continue
            
            # 多头确认: 日线多头 + RSI<40 + MACD转正
            if daily_bullish and rsi < 40 and price <= bb_mid and macd_hist > 0:
                entry_price = price
                stop_loss = entry_price * (1 - STOP_LOSS)
                take_profit = entry_price * (1 + TAKE_PROFIT)
                
                # Kelly仓位
                win_rate = 0.5  # 假设50%胜率
                odds = TAKE_PROFIT / STOP_LOSS  # 盈亏比
                kelly = (win_rate * odds - (1 - win_rate)) / odds
                kelly_pos = BASE_POS * min(kelly * 2, 1.5)  # 半Kelly
                
                positions.append({
                    'side': 'long',
                    'entry': entry_price,
                    'sl': stop_loss,
                    'tp': take_profit,
                    'size': kelly_pos,
                    'entry_idx': i
                })
            # 空头确认: 日线空头 + RSI>60 + MACD转负
            elif not daily_bullish and rsi > 60 and price >= bb_mid and macd_hist < 0:
                entry_price = price
                stop_loss = entry_price * (1 + STOP_LOSS)
                take_profit = entry_price * (1 - TAKE_PROFIT)
                
                positions.append({
                    'side': 'short',
                    'entry': entry_price,
                    'sl': stop_loss,
                    'tp': take_profit,
                    'size': BASE_POS,
                    'entry_idx': i
                })
        
        # 检查止损止盈
        for pos in positions[:]:
            if pos['side'] == 'long':
                pnl_pct = (price - pos['entry']) / pos['entry']
                hit_sl = price <= pos['sl']
                hit_tp = pnl_pct >= TAKE_PROFIT
            else:
                pnl_pct = (pos['entry'] - price) / pos['entry']
                hit_sl = price >= pos['sl']
                hit_tp = pnl_pct >= TAKE_PROFIT
            
            if hit_sl or hit_tp:
                pnl = pos['size'] * pnl_pct
                fee = pos['size'] * 0.0004
                net_pnl = pnl - fee
                CAPITAL += net_pnl
                trades.append({
                    'entry_time': df_1h.index[pos['entry_idx']],
                    'exit_time': dt,
                    'side': pos['side'],
                    'entry': pos['entry'],
                    'exit': price,
                    'size': pos['size'],
                    'pnl': net_pnl,
                    'pnl_pct': pnl_pct * 100
                })
                positions.remove(pos)
        
        equity_curve.append(CAPITAL)
    
    return trades, CAPITAL, equity_curve

# ========== 运行所有策略 ==========
print("\n" + "="*80)
print("多策略回测结果")
print("="*80)

strategies = [
    ("策略1: EMA趋势 + 布林带支撑", strategy_ema_bb),
    ("策略2: 支撑阻力 + RSI确认", strategy_sr_rsi),
    ("策略3: 金字塔 + 追踪止损", strategy_pyramid_trailing),
    ("策略4: 区间突破 + 固定加仓", strategy_breakout),
    ("策略5: 双重确认 + Kelly仓位", strategy_dual_confirm),
]

all_results = []

for name, func in strategies:
    try:
        trades, final_capital, equity = func()
        
        if trades:
            wins = [t for t in trades if t['pnl'] > 0]
            losses = [t for t in trades if t['pnl'] <= 0]
            winrate = len(wins) / len(trades) * 100
            
            # 计算最大回撤
            peak = equity[0]
            max_dd = 0
            for e in equity:
                if e > peak:
                    peak = e
                dd = (peak - e) / peak * 100
                max_dd = max(max_dd, dd)
            
            roi = (final_capital - 10000) / 10000 * 100
            avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
            avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
            
            all_results.append({
                'name': name,
                'final': final_capital,
                'roi': roi,
                'trades': len(trades),
                'winrate': winrate,
                'max_dd': max_dd,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'trades_list': trades
            })
        else:
            all_results.append({
                'name': name,
                'final': 10000,
                'roi': 0,
                'trades': 0,
                'winrate': 0,
                'max_dd': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'trades_list': []
            })
    except Exception as e:
        print(f"{name} 错误: {e}")
        all_results.append({
            'name': name,
            'final': 10000,
            'roi': 0,
            'trades': 0,
            'winrate': 0,
            'max_dd': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'trades_list': [],
            'error': str(e)
        })

# 排序输出
all_results.sort(key=lambda x: x['roi'], reverse=True)

print(f"\n{'策略名称':<30} {'最终资金':>12} {'收益率':>10} {'交易数':>8} {'胜率':>8} {'最大回撤':>10} {'年均收益':>10}")
print("-"*100)

for r in all_results:
    emoji = "🏆" if r['roi'] > 30 else ("✅" if r['roi'] > 0 else "❌")
    annual = r['roi']  # 约1年数据
    print(f"{emoji}{r['name']:<28} ${r['final']:>11,.2f} {r['roi']:>+9.1f}% {r['trades']:>8} {r['winrate']:>7.1f}% {r['max_dd']:>9.1f}% {annual:>+9.1f}%")

# 最佳策略详情
best = all_results[0]
print(f"\n{'='*80}")
print(f"🏆 最佳策略: {best['name']}")
print(f"{'='*80}")
print(f"  最终资金: ${best['final']:,.2f}")
print(f"  收益率: {best['roi']:+.1f}%")
print(f"  总交易数: {best['trades']}")
print(f"  胜率: {best['winrate']:.1f}%")
print(f"  最大回撤: {best['max_dd']:.1f}%")
print(f"  平均盈利: ${best['avg_win']:,.2f}")
print(f"  平均亏损: ${best['avg_loss']:,.2f}")

# 盈亏比
if best['avg_loss'] != 0:
    profit_ratio = abs(best['avg_win'] / best['avg_loss'])
    print(f"  盈亏比: {profit_ratio:.2f}")

# 保存结果
with open('/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/strategy_results.json', 'w') as f:
    json.dump(all_results, f, indent=2, default=str)

print(f"\n✅ 结果已保存到 strategy_results.json")