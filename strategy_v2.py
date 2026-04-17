#!/usr/bin/env python3
"""
优化版多策略回测系统
本金: $10,000 | 首仓: $1,000 | 止损: 3% | 止盈: 5%
"""
import json
import numpy as np
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ========== 加载数据 ==========
with open('/tmp/binance_BTCUSDT_1y.json') as f:
    raw = json.load(f)

df = pd.DataFrame(raw, columns=['t', 'o', 'h', 'l', 'c', 'v', 'ct', 'qv', 'trades', 'tbb', 'tbq', 'ign'])
df['t'] = pd.to_datetime(df['t'], unit='ms')
df = df.set_index('t')
df = df.sort_index()

for col in ['o', 'h', 'l', 'c', 'v', 'qv']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

df_1h = df[['o','h','l','c','v']].resample('1h').agg({
    'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
}).dropna()

df_daily = df[['o','h','l','c','v']].resample('1d').agg({
    'o': 'first', 'h': 'max', 'l': 'min', 'c': 'last', 'v': 'sum'
}).dropna()

print(f"数据范围: {df_1h.index[0]} 至 {df_1h.index[-1]}")
print(f"1H: {len(df_1h)} | 日线: {len(df_daily)}")

# ========== 指标 ==========
def add_indicators(df):
    df = df.copy()
    df['ema20'] = df['c'].ewm(span=20).mean()
    df['ema50'] = df['c'].ewm(span=50).mean()
    df['ema200'] = df['c'].ewm(span=200).mean()
    
    delta = df['c'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    df['bb_mid'] = df['c'].rolling(20).mean()
    bb_std = df['c'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * bb_std
    df['bb_lower'] = df['bb_mid'] - 2 * bb_std
    
    high_low = df['h'] - df['l']
    high_close = np.abs(df['h'] - df['c'].shift())
    low_close = np.abs(df['l'] - df['c'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    
    return df

df_1h = add_indicators(df_1h)
df_daily = add_indicators(df_daily)

# ========== 策略A: 趋势突破 + 动态仓位 ==========
def strategy_trend_breakout():
    """
    日线EMA50在EMA200上方 = 多头趋势
    1H突破20日高点入场，回调至EMA20附近加仓
    首仓$1500，允许加仓2次($1000+$500)
    止损3%，止盈6%
    """
    CAPITAL = 10000
    STOP_LOSS = 0.03
    TAKE_PROFIT = 0.06
    
    trades = []
    positions = []
    equity = [CAPITAL]
    
    for i in range(200, len(df_1h)):
        dt = df_1h.index[i]
        price = df_1h.iloc[i]['c']
        
        daily_data = df_daily[df_daily.index < dt]
        if len(daily_data) < 200:
            continue
        
        daily_curr = daily_data.iloc[-1]
        daily_bull = daily_curr['ema50'] > daily_curr['ema200']
        
        row = df_1h.iloc[i]
        rsi = row['rsi']
        ema20_1h = row['ema20']
        bb_mid = row['bb_mid']
        bb_lower = row['bb_lower']
        
        # 计算前20日高点
        prev_20_high = df_1h.iloc[i-20:i]['h'].max() if i >= 20 else price
        prev_20_low = df_1h.iloc[i-20:i]['l'].min() if i >= 20 else price
        
        # 开仓
        if not positions and len(positions) == 0:
            if daily_bull and price > prev_20_high and rsi < 75:
                # 突破做多
                positions.append({
                    'entry': price,
                    'sl': price * (1 - STOP_LOSS),
                    'tp': price * (1 + TAKE_PROFIT),
                    'size': 1500,
                    'side': 'long',
                    'entry_idx': i,
                    'add_level': price * 0.97  # 加仓位
                })
            elif not daily_bull and price < prev_20_low and rsi > 25:
                positions.append({
                    'entry': price,
                    'sl': price * (1 + STOP_LOSS),
                    'tp': price * (1 - TAKE_PROFIT),
                    'size': 1500,
                    'side': 'short',
                    'entry_idx': i,
                    'add_level': price * 1.03
                })
        
        # 检查加仓
        if positions and len(positions) < 3:
            pos = positions[-1]
            if pos['side'] == 'long' and price <= pos['add_level'] and price > pos['sl']:
                new_size = 1000 if len(positions) == 1 else 500
                new_sl = min(pos['sl'], price * (1 - STOP_LOSS))
                positions.append({
                    'entry': price,
                    'sl': new_sl,
                    'tp': pos['tp'],
                    'size': new_size,
                    'side': 'long',
                    'entry_idx': i,
                    'add_level': price * 0.97
                })
            elif pos['side'] == 'short' and price >= pos['add_level'] and price < pos['sl']:
                new_size = 1000 if len(positions) == 1 else 500
                new_sl = max(pos['sl'], price * (1 + STOP_LOSS))
                positions.append({
                    'entry': price,
                    'sl': new_sl,
                    'tp': pos['tp'],
                    'size': new_size,
                    'side': 'short',
                    'entry_idx': i,
                    'add_level': price * 1.03
                })
        
        # 检查止损止盈
        for pos in positions[:]:
            if pos['side'] == 'long':
                pnl_pct = (price - pos['entry']) / pos['entry']
                hit = price <= pos['sl'] or price >= pos['tp']
            else:
                pnl_pct = (pos['entry'] - price) / pos['entry']
                hit = price >= pos['sl'] or price <= pos['tp']
            
            if hit:
                pnl = pos['size'] * pnl_pct
                fee = pos['size'] * 0.0004
                CAPITAL += pnl - fee
                trades.append({
                    'entry': pos['entry'],
                    'exit': price,
                    'side': pos['side'],
                    'size': pos['size'],
                    'pnl': pnl - fee,
                    'pnl_pct': pnl_pct * 100
                })
                positions.remove(pos)
        
        equity.append(CAPTAL)
    
    return trades, CAPITAL, equity

# ========== 策略B: 均线金叉 + ATR止损 ==========
def strategy_ma_crossover():
    """
    日线EMA20>EMA50确认趋势
    1H EMA20上穿EMA50金叉做多，下穿死叉做空
    首仓$2000，ATR动态止损(1.5倍ATR)，止盈2倍ATR
    """
    CAPITAL = 10000
    ATR_MULT_SL = 1.5
    ATR_MULT_TP = 2.0
    
    trades = []
    positions = []
    equity = [CAPITAL]
    prev_ema20_1h = None
    
    for i in range(200, len(df_1h)):
        dt = df_1h.index[i]
        price = df_1h.iloc[i]['c']
        
        daily_data = df_daily[df_daily.index < dt]
        if len(daily_data) < 50:
            continue
        
        daily_curr = daily_data.iloc[-1]
        daily_bull = daily_curr['ema20'] > daily_curr['ema50']
        
        row = df_1h.iloc[i]
        rsi = row['rsi']
        atr = row['atr']
        ema20_1h = row['ema20']
        ema50_1h = row['ema50']
        
        # 均线交叉检测
        if prev_ema20_1h is not None:
            golden_cross = prev_ema20_1h < ema50_1h and ema20_1h >= ema50_1h
            death_cross = prev_ema20_1h > ema50_1h and ema20_1h <= ema50_1h
        else:
            golden_cross = death_cross = False
        
        prev_ema20_1h = ema20_1h
        
        # 开仓
        if not positions:
            if daily_bull and golden_cross and rsi < 60:
                sl = price - atr * ATR_MULT_SL
                tp = price + atr * ATR_MULT_TP
                positions.append({
                    'entry': price, 'sl': sl, 'tp': tp,
                    'size': 2000, 'side': 'long', 'entry_idx': i
                })
            elif not daily_bull and death_cross and rsi > 40:
                sl = price + atr * ATR_MULT_SL
                tp = price - atr * ATR_MULT_TP
                positions.append({
                    'entry': price, 'sl': sl, 'tp': tp,
                    'size': 2000, 'side': 'short', 'entry_idx': i
                })
        
        # 检查止损止盈
        for pos in positions[:]:
            if pos['side'] == 'long':
                hit = price <= pos['sl'] or price >= pos['tp']
            else:
                hit = price >= pos['sl'] or price <= pos['tp']
            
            if hit:
                pnl_pct = (price - pos['entry']) / pos['entry'] if pos['side'] == 'long' else (pos['entry'] - price) / pos['entry']
                pnl = pos['size'] * pnl_pct
                fee = pos['size'] * 0.0004
                CAPITAL += pnl - fee
                trades.append({
                    'entry': pos['entry'], 'exit': price,
                    'side': pos['side'], 'size': pos['size'],
                    'pnl': pnl - fee, 'pnl_pct': pnl_pct * 100
                })
                positions.remove(pos)
        
        equity.append(CAPITAL)
    
    return trades, CAPITAL, equity

# ========== 策略C: 日内支撑阻力 + RSI极限 ==========
def strategy_sr_reversal():
    """
    日线定方向，1H RSI极值反转
    RSI<30且价格触及布林下轨 = 做多
    RSI>70且价格触及布林上轨 = 做空
    首仓$2000，止损2%，止盈4%
    """
    CAPITAL = 10000
    STOP_LOSS = 0.02
    TAKE_PROFIT = 0.04
    
    trades = []
    positions = []
    equity = [CAPITAL]
    
    for i in range(200, len(df_1h)):
        dt = df_1h.index[i]
        price = df_1h.iloc[i]['c']
        
        daily_data = df_daily[df_daily.index < dt]
        if len(daily_data) < 50:
            continue
        
        daily_curr = daily_data.iloc[-1]
        daily_bull = daily_curr['ema50'] > daily_curr['ema20']
        
        row = df_1h.iloc[i]
        rsi = row['rsi']
        bb_lower = row['bb_lower']
        bb_upper = row['bb_upper']
        bb_mid = row['bb_mid']
        atr = row['atr']
        
        if not positions:
            if daily_bull and rsi < 30 and price <= bb_mid:
                sl = price * (1 - STOP_LOSS)
                tp = price * (1 + TAKE_PROFIT)
                positions.append({
                    'entry': price, 'sl': sl, 'tp': tp,
                    'size': 2000, 'side': 'long', 'entry_idx': i
                })
            elif not daily_bull and rsi > 70 and price >= bb_mid:
                sl = price * (1 + STOP_LOSS)
                tp = price * (1 - TAKE_PROFIT)
                positions.append({
                    'entry': price, 'sl': sl, 'tp': tp,
                    'size': 2000, 'side': 'short', 'entry_idx': i
                })
        
        for pos in positions[:]:
            if pos['side'] == 'long':
                hit = price <= pos['sl'] or price >= pos['tp']
            else:
                hit = price >= pos['sl'] or price <= pos['tp']
            
            if hit:
                pnl_pct = (price - pos['entry']) / pos['entry'] if pos['side'] == 'long' else (pos['entry'] - price) / pos['entry']
                pnl = pos['size'] * pnl_pct
                fee = pos['size'] * 0.0004
                CAPITAL += pnl - fee
                trades.append({
                    'entry': pos['entry'], 'exit': price,
                    'side': pos['side'], 'size': pos['size'],
                    'pnl': pnl - fee, 'pnl_pct': pnl_pct * 100
                })
                positions.remove(pos)
        
        equity.append(CAPITAL)
    
    return trades, CAPITAL, equity

# ========== 策略D: 纯趋势 + 大止损大止盈 ==========
def strategy_trend_pure():
    """
    只做日线趋势方向，忽略短期波动
    首仓$3000，止损5%，止盈15%
    允许最大持仓$5000
    """
    CAPITAL = 10000
    STOP_LOSS = 0.05
    TAKE_PROFIT = 0.15
    
    trades = []
    positions = []
    equity = [CAPITAL]
    
    for i in range(200, len(df_1h)):
        dt = df_1h.index[i]
        price = df_1h.iloc[i]['c']
        
        daily_data = df_daily[df_daily.index < dt]
        if len(daily_data) < 50:
            continue
        
        daily_curr = daily_data.iloc[-1]
        daily_bull = daily_curr['ema50'] > daily_curr['ema200']
        
        row = df_1h.iloc[i]
        rsi = row['rsi']
        bb_mid = row['bb_mid']
        
        total_size = sum(p['size'] for p in positions)
        
        if not positions:
            if daily_bull and price > bb_mid and rsi < 60:
                positions.append({
                    'entry': price,
                    'sl': price * (1 - STOP_LOSS),
                    'tp': price * (1 + TAKE_PROFIT),
                    'size': 3000,
                    'side': 'long',
                    'entry_idx': i
                })
            elif not daily_bull and price < bb_mid and rsi > 40:
                positions.append({
                    'entry': price,
                    'sl': price * (1 + STOP_LOSS),
                    'tp': price * (1 - TAKE_PROFIT),
                    'size': 3000,
                    'side': 'short',
                    'entry_idx': i
                })
        elif len(positions) == 1 and total_size < 5000:
            last = positions[-1]
            if last['side'] == 'long' and price < last['entry'] * 0.98:
                positions.append({
                    'entry': price,
                    'sl': price * (1 - STOP_LOSS),
                    'tp': last['tp'],
                    'size': 2000,
                    'side': 'long',
                    'entry_idx': i
                })
            elif last['side'] == 'short' and price > last['entry'] * 1.02:
                positions.append({
                    'entry': price,
                    'sl': price * (1 + STOP_LOSS),
                    'tp': last['tp'],
                    'size': 2000,
                    'side': 'short',
                    'entry_idx': i
                })
        
        for pos in positions[:]:
            if pos['side'] == 'long':
                hit = price <= pos['sl'] or price >= pos['tp']
            else:
                hit = price >= pos['sl'] or price <= pos['tp']
            
            if hit:
                pnl_pct = (price - pos['entry']) / pos['entry'] if pos['side'] == 'long' else (pos['entry'] - price) / pos['entry']
                pnl = pos['size'] * pnl_pct
                fee = pos['size'] * 0.0004
                CAPITAL += pnl - fee
                trades.append({
                    'entry': pos['entry'], 'exit': price,
                    'side': pos['side'], 'size': pos['size'],
                    'pnl': pnl - fee, 'pnl_pct': pnl_pct * 100
                })
                positions.remove(pos)
        
        equity.append(CAPITAL)
    
    return trades, CAPITAL, equity

# ========== 策略E: 波段交易 + 分批止盈 ==========
def strategy_swing():
    """
    日线趋势 + 1H波段
    首仓$2000，止损3%
    止盈分三批: 5%, 10%, 15%
    """
    CAPITAL = 10000
    STOP_LOSS = 0.03
    
    trades = []
    positions = []
    equity = [CAPITAL]
    
    for i in range(200, len(df_1h)):
        dt = df_1h.index[i]
        price = df_1h.iloc[i]['c']
        
        daily_data = df_daily[df_daily.index < dt]
        if len(daily_data) < 50:
            continue
        
        daily_curr = daily_data.iloc[-1]
        daily_bull = daily_curr['ema50'] > daily_curr['ema20']
        
        row = df_1h.iloc[i]
        rsi = row['rsi']
        bb_lower = row['bb_lower']
        bb_upper = row['bb_upper']
        atr = row['atr']
        
        if not positions:
            if daily_bull and price <= bb_lower and rsi < 35:
                sl = price * (1 - STOP_LOSS)
                positions.append({
                    'entry': price,
                    'sl': sl,
                    'tp1': price * 1.05,
                    'tp2': price * 1.10,
                    'tp3': price * 1.15,
                    'size': 2000,
                    'side': 'long',
                    'entry_idx': i,
                    'closed_size': 0
                })
            elif not daily_bull and price >= bb_upper and rsi > 65:
                sl = price * (1 + STOP_LOSS)
                positions.append({
                    'entry': price,
                    'sl': sl,
                    'tp1': price * 0.95,
                    'tp2': price * 0.90,
                    'tp3': price * 0.85,
                    'size': 2000,
                    'side': 'short',
                    'entry_idx': i,
                    'closed_size': 0
                })
        
        for pos in positions[:]:
            pnl_pct = (price - pos['entry']) / pos['entry'] if pos['side'] == 'long' else (pos['entry'] - price) / pos['entry']
            
            # 分批止盈
            exit_size = 0
            if pos['side'] == 'long':
                if price >= pos['tp3'] and pos['closed_size'] < pos['size']:
                    exit_size = pos['size']
                elif price >= pos['tp2'] and pos['closed_size'] < pos['size'] * 0.66:
                    exit_size = pos['size'] * 0.5
                elif price >= pos['tp1'] and pos['closed_size'] < pos['size'] * 0.33:
                    exit_size = pos['size'] * 0.33
                hit_sl = price <= pos['sl']
            else:
                if price <= pos['tp3'] and pos['closed_size'] < pos['size']:
                    exit_size = pos['size']
                elif price <= pos['tp2'] and pos['closed_size'] < pos['size'] * 0.66:
                    exit_size = pos['size'] * 0.5
                elif price <= pos['tp1'] and pos['closed_size'] < pos['size'] * 0.33:
                    exit_size = pos['size'] * 0.33
                hit_sl = price >= pos['sl']
            
            if exit_size > 0 or hit_sl:
                actual_exit_size = exit_size if exit_size > 0 else pos['size']
                pnl = actual_exit_size * pnl_pct
                fee = actual_exit_size * 0.0004
                CAPITAL += pnl - fee
                trades.append({
                    'entry': pos['entry'], 'exit': price,
                    'side': pos['side'], 'size': actual_exit_size,
                    'pnl': pnl - fee, 'pnl_pct': pnl_pct * 100
                })
                if exit_size >= pos['size']:
                    positions.remove(pos)
                else:
                    pos['closed_size'] += exit_size
        
        equity.append(CAPITAL)
    
    return trades, CAPITAL, equity

# ========== 运行 ==========
print("\n" + "="*80)
print("优化策略回测结果")
print("="*80)

strategies = [
    ("A. 趋势突破+动态仓位", strategy_trend_breakout),
    ("B. 均线金叉+ATR止损", strategy_ma_crossover),
    ("C. 支撑阻力RSI极限", strategy_sr_reversal),
    ("D. 纯趋势+大止盈", strategy_trend_pure),
    ("E. 波段+分批止盈", strategy_swing),
]

all_results = []

for name, func in strategies:
    try:
        trades, final_cap, equity = func()
        
        if trades:
            wins = [t for t in trades if t['pnl'] > 0]
            losses = [t for t in trades if t['pnl'] <= 0]
            winrate = len(wins) / len(trades) * 100
            
            peak = equity[0]
            max_dd = 0
            for e in equity:
                peak = max(peak, e)
                dd = (peak - e) / peak * 100
                max_dd = max(max_dd, dd)
            
            roi = (final_cap - 10000) / 10000 * 100
            avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
            avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
            
            all_results.append({
                'name': name,
                'final': final_cap,
                'roi': roi,
                'trades': len(trades),
                'winrate': winrate,
                'max_dd': max_dd,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
            })
        else:
            all_results.append({
                'name': name, 'final': 10000, 'roi': 0, 'trades': 0,
                'winrate': 0, 'max_dd': 0, 'avg_win': 0, 'avg_loss': 0
            })
    except Exception as e:
        all_results.append({'name': name, 'error': str(e)})

all_results.sort(key=lambda x: x.get('roi', 0), reverse=True)

print(f"\n{'策略':<28} {'最终资金':>12} {'收益率':>10} {'交易数':>8} {'胜率':>8} {'最大回撤':>10}")
print("-"*80)

for r in all_results:
    emoji = "🏆" if r.get('roi', 0) > 20 else ("✅" if r.get('roi', 0) > 0 else "❌")
    print(f"{emoji}{r['name']:<26} ${r['final']:>11,.2f} {r.get('roi',0):>+9.1f}% {r['trades']:>8} {r.get('winrate',0):>7.1f}% {r.get('max_dd',0):>9.1f}%")

# 保存
with open('/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/strategy_results_v2.json', 'w') as f:
    json.dump(all_results, f, indent=2, default=str)

print(f"\n✅ 结果已保存到 strategy_results_v2.json")