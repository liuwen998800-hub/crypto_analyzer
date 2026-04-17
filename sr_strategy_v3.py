#!/usr/bin/env python3
"""
支撑压力做单策略 V3 - 市场内直接入场版
核心理念:
1. 不等价格回落/反弹到精确支撑压力位，而是在当前价直接入场
2. 支撑压力位用于计算止损(止损在支撑下方/压力上方)
3. 趋势跟随 + 反向保护
4. ATR动态止损 + 固定2:1盈亏比
5. Kelly仓位管理
"""

import pandas as pd
import numpy as np
import requests
import json
import time
import os
from datetime import datetime

# ========== 配置 ==========
INITIAL_CAPITAL = 10000
RISK_PCT = 0.02            # 每笔风险 2%账户
SYMBOL = 'BTCUSDT'
INTERVAL = '1h'
START_DATE = '2024-04-16'
END_DATE = '2025-04-16'
TRADE_FEE = 0.0004
ATR_PERIOD = 14
SR_LOOKBACK = 24
MAX_POSITIONS = 3          # 最多同时3个方向
REBALANCE_HOURS = 1        # 每1小时检查
TP_RISK_RATIO = 2.0        # 2:1盈亏比
ATR_SL_MULT = 1.5           # ATR止损倍数
KELLY_USE = True
KELLY_MAX = 0.25           # Kelly最高25%

# ========== 数据获取 ==========
def get_binance_klines(symbol, interval, start_str, end_str=None, limit=1500):
    url = "https://api.binance.com/api/v3/klines"
    params = {'symbol': symbol, 'interval': interval,
              'startTime': int(pd.Timestamp(start_str).timestamp() * 1000), 'limit': limit}
    if end_str:
        params['endTime'] = int(pd.Timestamp(end_str).timestamp() * 1000)
    all_klines = []
    while True:
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            if isinstance(data, dict) and 'code' in data: break
            all_klines.extend(data)
            if len(data) < limit: break
            params['startTime'] = int(data[-1][0]) + 1
            time.sleep(0.25)
        except: break
    return all_klines

def parse_klines(klines):
    df = pd.DataFrame(klines, columns=[
        'open_time','open','high','low','close','volume',
        'close_time','quote_volume','trades','taker_buy_base','taker_buy_quote','ignore'
    ])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    for c in ['open','high','low','close','volume','quote_volume']:
        df[c] = df[c].astype(float)
    return df.set_index('open_time')

# ========== 指标 ==========
def calc_atr(df, period=14):
    hl = df['high'] - df['low']
    hc = np.abs(df['high'] - df['close'].shift())
    lc = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calc_ema(p, n):
    return p.ewm(span=n, adjust=False).mean()

def calc_rsi(p, n=14):
    d = p.diff()
    g = d.where(d>0, 0).rolling(n).mean()
    l = (-d.where(d<0, 0)).rolling(n).mean()
    return 100 - (100 / (1 + g / (l + 1e-10)))

# ========== 支撑压力分析 ==========
def analyze_levels(df, lookback=24):
    """DeepSeek式支撑压力分析"""
    recent = df.tail(lookback)
    current = df['close'].iloc[-1]
    atr = df['atr'].iloc[-1] if 'atr' in df.columns else current * 0.01
    
    # 基本位
    swing_high = recent['high'].max()
    swing_low = recent['low'].min()
    ema20 = df['ema20'].iloc[-1]
    ema60 = df['ema60'].iloc[-1]
    
    # 布林带
    bb_std = df['close'].tail(20).std()
    bb_upper = current + 2 * bb_std
    bb_lower = current - 2 * bb_std
    
    # 斐波那契
    fib_diff = swing_high - swing_low
    r1 = swing_low + fib_diff * 0.382
    r2 = swing_low + fib_diff * 0.618
    s1 = swing_high - fib_diff * 0.382
    s2 = swing_high - fib_diff * 0.618
    
    # 整数关口
    round_level = round(current / 1000) * 1000
    
    # 趋势
    if current > ema60 and ema20 > ema60:
        trend = 'bullish'
    elif current < ema60 and ema20 < ema60:
        trend = 'bearish'
    else:
        trend = 'neutral'
    
    # RSI
    rsi = df['rsi'].iloc[-1] if 'rsi' in df.columns else 50
    
    # 距离支撑/压力的百分比
    dist_to_support = (current - swing_low) / current * 100
    dist_to_resistance = (swing_high - current) / current * 100
    
    return {
        'current': current,
        'atr': atr,
        'trend': trend,
        'rsi': rsi,
        'swing_high': swing_high,
        'swing_low': swing_low,
        'bb_upper': bb_upper,
        'bb_lower': bb_lower,
        'ema20': ema20,
        'ema60': ema60,
        'fib_r1': r1, 'fib_r2': r2,
        'fib_s1': s1, 'fib_s2': s2,
        'round_level': round_level,
        'dist_to_support': dist_to_support,
        'dist_to_resistance': dist_to_resistance,
    }

# ========== Kelly仓位 ==========
def kelly_size(win_rate, avg_win, avg_loss, max_cap_pct=0.25):
    if avg_loss == 0 or avg_win == 0:
        return max_cap_pct
    b = abs(avg_win / avg_loss)
    q = 1 - win_rate
    kelly = (b * win_rate - q) / b
    return min(max(kelly * 0.3, 0.05), max_cap_pct)  # 保守启用30%

# ========== 模拟器 ==========
class StrategyV3:
    def __init__(self):
        self.capital = INITIAL_CAPITAL
        self.positions = []
        self.closed = []
        self.equity_curve = []
        self.trades = []
        self.wins = 0
        self.losses = 0
        self.win_amounts = []
        self.loss_amounts = []
        self.kelly = 0.15
        self.last_entry_hour = {}  # 每小时最多开一次
        
    def calc_position_size(self, entry, stop):
        risk_amt = self.capital * RISK_PCT
        risk_per_unit = abs(entry - stop)
        if risk_per_unit == 0:
            return 0
        size = risk_amt / risk_per_unit
        return min(size, self.capital * self.kelly)
    
    def open_position(self, pos_type, entry, sl, tp, level_info, atr, ts, price):
        # 检查是否已经开过
        hour_key = (pos_type, ts.strftime('%Y-%m-%d %H'))
        if hour_key in self.last_entry_hour:
            return None
        
        # 止损计算
        if pos_type == 'long':
            sl_price = entry - atr * ATR_SL_MULT
            tp_price = entry + atr * ATR_SL_MULT * TP_RISK_RATIO
        else:
            sl_price = entry + atr * ATR_SL_MULT
            tp_price = entry - atr * ATR_SL_MULT * TP_RISK_RATIO
        
        # 最小止损距离
        min_stop_dist = entry * 0.005  # 0.5%
        if abs(entry - sl_price) < min_stop_dist:
            sl_price = entry - min_stop_dist if pos_type == 'long' else entry + min_stop_dist
            tp_price = entry + min_stop_dist * TP_RISK_RATIO if pos_type == 'long' else entry - min_stop_dist * TP_RISK_RATIO
        
        size = self.calc_position_size(entry, sl_price)
        if size <= 0:
            return None
        
        notional = size * entry
        
        if pos_type == 'long':
            cost = notional * (1 + TRADE_FEE)
            if cost > self.capital:
                return None
        else:
            margin = notional / 10
            if margin > self.capital * 0.4:
                return None
        
        pos = {
            'type': pos_type,
            'size': size,
            'entry': entry,
            'sl': sl_price,
            'tp': tp_price,
            'atr': atr,
            'level': level_info,
            'open_time': ts,
            'notional': notional,
            'pnl': 0
        }
        
        self.positions.append(pos)
        self.last_entry_hour[hour_key] = True
        
        self.trades.append({
            'timestamp': ts,
            'type': f'OPEN_{pos_type.upper()}',
            'price': entry,
            'size': size,
            'sl': sl_price,
            'tp': tp_price,
            'atr': atr,
            'level': level_info,
            'trend': self.current_trend,
            'rsi': self.current_rsi,
            'capital': self.capital
        })
        
        return pos
    
    def check_and_close(self, price, ts):
        for pos in self.positions[:]:
            should_close = False
            reason = ''
            
            if pos['type'] == 'long':
                if price <= pos['sl']:
                    should_close = True
                    reason = 'STOP_LOSS'
                elif price >= pos['tp']:
                    should_close = True
                    reason = 'TAKE_PROFIT'
            else:
                if price >= pos['sl']:
                    should_close = True
                    reason = 'STOP_LOSS'
                elif price <= pos['tp']:
                    should_close = True
                    reason = 'TAKE_PROFIT'
            
            if should_close:
                if pos['type'] == 'long':
                    proceeds = pos['size'] * price * (1 - TRADE_FEE)
                    cost = pos['size'] * pos['entry'] * (1 + TRADE_FEE)
                    pnl = proceeds - cost
                else:
                    cost = pos['size'] * price * (1 + TRADE_FEE)
                    proceeds = pos['size'] * pos['entry'] * (1 - TRADE_FEE)
                    pnl = proceeds - cost
                
                self.capital += pnl
                
                if pnl > 0:
                    self.wins += 1
                    self.win_amounts.append(pnl)
                else:
                    self.losses += 1
                    self.loss_amounts.append(pnl)
                
                hold_h = (ts - pos['open_time']).total_seconds() / 3600
                
                self.closed.append({
                    **pos,
                    'close_price': price,
                    'close_time': ts,
                    'pnl': pnl,
                    'reason': reason,
                    'holding_hours': hold_h
                })
                
                self.trades.append({
                    'timestamp': ts,
                    'type': f'CLOSE_{pos["type"].upper()}',
                    'price': price,
                    'size': pos['size'],
                    'pnl': pnl,
                    'reason': reason,
                    'holding_hours': hold_h,
                    'capital_after': self.capital
                })
                
                self.positions.remove(pos)
    
    def update_kelly(self):
        if self.wins < 5 or self.losses < 5:
            return
        wins_arr = np.array(self.win_amounts)
        losses_arr = np.array(self.loss_amounts)
        wr = self.wins / (self.wins + self.losses)
        aw = wins_arr.mean()
        al = abs(losses_arr.mean())
        self.kelly = kelly_size(wr, aw, al)
    
    def decide_entry(self, sr):
        """决定是否开仓"""
        decisions = []
        trend = sr['trend']
        rsi = sr['rsi']
        current = sr['current']
        atr = sr['atr']
        
        # ===== 多头信号 =====
        long_score = 0
        
        # 趋势看多
        if trend == 'bullish':
            long_score += 3
        elif trend == 'neutral':
            long_score += 1
        
        # RSI处于合理区间
        if 35 < rsi < 60:
            long_score += 2
        elif rsi < 30:
            long_score += 3  # 超卖
        
        # 距离支撑近
        if sr['dist_to_support'] < 3:
            long_score += 2
        
        # 布林下轨支撑
        if current < sr['bb_upper'] and current > sr['bb_lower']:
            if current - sr['bb_lower'] < atr:
                long_score += 2
        
        # 均线支撑
        if current > sr['ema20']:
            long_score += 1
        
        # 开多条件
        if long_score >= 5:
            level = f"bullish_s{long_score}_RSI{int(rsi)}"
            tp = current + atr * ATR_SL_MULT * TP_RISK_RATIO
            decisions.append(('long', current, tp, level))
        
        # ===== 空头信号 =====
        short_score = 0
        
        # 趋势看空
        if trend == 'bearish':
            short_score += 3
        elif trend == 'neutral':
            short_score += 1
        
        # RSI过高
        if 40 < rsi < 70:
            short_score += 2
        elif rsi > 70:
            short_score += 3
        
        # 距离压力近
        if sr['dist_to_resistance'] < 3:
            short_score += 2
        
        # 布林上轨压力
        if current < sr['bb_upper'] and current > sr['bb_lower']:
            if sr['bb_upper'] - current < atr:
                short_score += 2
        
        # 均线压力
        if current < sr['ema20']:
            short_score += 1
        
        # 开空条件
        if short_score >= 5:
            level = f"bearish_s{short_score}_RSI{int(rsi)}"
            tp = current - atr * ATR_SL_MULT * TP_RISK_RATIO
            decisions.append(('short', current, tp, level))
        
        return decisions

# ========== 主程序 ==========
def run():
    print("=" * 70)
    print("  支撑压力做单策略 V3 - 市场内直接入场")
    print("=" * 70)
    print(f"本金: ${INITIAL_CAPITAL:,.2f}")
    print(f"每笔风险: {RISK_PCT*100:.0f}%账户 | ATR止损×{ATR_SL_MULT} | 盈亏比{TP_RISK_RATIO}:1")
    print(f"Kelly仓位: {'启用(最高25%)' if KELLY_USE else '关闭'}")
    print(f"最大同时持仓: {MAX_POSITIONS}")
    print("=" * 70)
    
    # 数据
    print(f"\n[1/6] 获取 {SYMBOL} 数据...")
    cache = "/tmp/binance_BTCUSDT_1y.json"
    if os.path.exists(cache):
        with open(cache) as f: raw = json.load(f)
    else:
        raw = get_binance_klines(SYMBOL, INTERVAL, START_DATE, END_DATE)
        if raw:
            with open(cache, 'w') as f: json.dump(raw, f)
    if not raw: print("失败"); return
    
    df = parse_klines(raw)
    print(f"  {len(df)} 根K线")
    
    # 指标
    print("\n[2/6] 计算指标...")
    df['atr'] = calc_atr(df, ATR_PERIOD)
    df['ema20'] = calc_ema(df['close'], 20)
    df['ema60'] = calc_ema(df['close'], 60)
    df['rsi'] = calc_rsi(df['close'], 14)
    df['bb_sma'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_sma'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_sma'] - 2 * df['bb_std']
    df = df.dropna()
    print(f"  有效数据: {len(df)}")
    
    # 回测
    print("\n[3/6] 运行回测...")
    strat = StrategyV3()
    
    for i in range(SR_LOOKBACK + 1, len(df)):
        row = df.iloc[i]
        ts = row.name
        price = row['close']
        
        lookback = df.iloc[:i+1]
        sr = analyze_levels(lookback, SR_LOOKBACK)
        strat.current_trend = sr['trend']
        strat.current_rsi = sr['rsi']
        
        # 每小时检查一次
        if i % REBALANCE_HOURS == 0:
            # 清理过时的entry记录 (保留最近2小时的)
            cutoff = ts - pd.Timedelta(hours=2)
            strat.last_entry_hour = {
                k: v for k, v in strat.last_entry_hour.items()
                if pd.Timestamp(k[1]) > cutoff
            }
        
        # 检查平仓
        strat.check_and_close(price, ts)
        
        # 限制最大持仓
        if len(strat.positions) < MAX_POSITIONS:
            decisions = strat.decide_entry(sr)
            for pos_type, entry, tp, level in decisions:
                sl = entry - (tp - entry) / TP_RISK_RATIO  # 反推止损
                pos = strat.open_position(pos_type, entry, sl, tp, level, sr['atr'], ts, price)
                if pos is None:
                    break  # 资金不够
        
        # Kelly更新 (每24小时)
        if i % 24 == 0:
            strat.update_kelly()
        
        # 记录权益
        pos_pnl = 0
        for p in strat.positions:
            if p['type'] == 'long':
                pos_pnl += p['size'] * (price - p['entry'])
            else:
                pos_pnl += p['size'] * (p['entry'] - price)
        
        strat.equity_curve.append({
            'timestamp': ts,
            'hour': ts.strftime('%Y-%m-%d %H:00'),
            'date': ts.strftime('%Y-%m-%d'),
            'close': price,
            'capital': strat.capital,
            'position_pnl': pos_pnl,
            'total_equity': strat.capital + pos_pnl,
            'n_positions': len(strat.positions),
            'trend': strat.current_trend,
            'rsi': strat.current_rsi,
            'atr': sr['atr'],
            'kelly': strat.kelly,
            'support': sr['swing_low'],
            'resistance': sr['swing_high'],
        })
    
    # 最终平仓
    final_price = df.iloc[-1]['close']
    for pos in strat.positions[:]:
        if pos['type'] == 'long':
            proceeds = pos['size'] * final_price * (1 - TRADE_FEE)
            cost = pos['size'] * pos['entry'] * (1 + TRADE_FEE)
            pnl = proceeds - cost
        else:
            cost = pos['size'] * final_price * (1 + TRADE_FEE)
            proceeds = pos['size'] * pos['entry'] * (1 - TRADE_FEE)
            pnl = proceeds - cost
        strat.capital += pnl
        strat.closed.append({**pos, 'close_price': final_price, 'pnl': pnl, 'reason': 'END'})
        strat.positions.remove(pos)
    
    # 报告
    print("\n[4/6] 生成报告...")
    eq = pd.DataFrame(strat.equity_curve)
    trades = pd.DataFrame(strat.trades)
    closed = pd.DataFrame(strat.closed)
    
    final_cap = strat.capital
    total_ret = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    total_pnl = final_cap - INITIAL_CAPITAL
    
    n_trades = len(closed)
    wr = strat.wins / (strat.wins + strat.losses) * 100 if (strat.wins + strat.losses) > 0 else 0
    avg_w = np.mean(strat.win_amounts) if strat.win_amounts else 0
    avg_l = np.mean(strat.loss_amounts) if strat.loss_amounts else 0
    pf = abs(sum(strat.win_amounts) / sum(strat.loss_amounts)) if strat.loss_amounts and sum(strat.loss_amounts) != 0 else 0
    
    if len(eq) > 0:
        eq['peak'] = eq['total_equity'].cummax()
        eq['dd'] = (eq['total_equity'] - eq['peak']) / eq['peak'] * 100
        max_dd = abs(eq['dd'].min())
        hours = len(eq)
        ann_ret = ((final_cap / INITIAL_CAPITAL) ** (365 * 24 / hours) - 1) * 100 if hours > 0 and final_cap > 0 else 0
        rets = eq['total_equity'].pct_change().dropna()
        sharpe = rets.mean() / rets.std() * np.sqrt(365 * 24) if rets.std() > 0 else 0
    else:
        max_dd = ann_ret = sharpe = 0
    
    open_trades = trades[trades['type'].str.startswith('OPEN')]
    close_trades = trades[trades['type'].str.startswith('CLOSE')]
    
    n_long = len(open_trades[open_trades['type'] == 'OPEN_LONG'])
    n_short = len(open_trades[open_trades['type'] == 'OPEN_SHORT'])
    tp_count = len(close_trades[close_trades['reason'] == 'TAKE_PROFIT']) if len(close_trades) > 0 else 0
    sl_count = len(close_trades[close_trades['reason'] == 'STOP_LOSS']) if len(close_trades) > 0 else 0
    
    print(f"""
{'='*70}
        📊 回测报告 V3 - 支撑压力直接入场策略 (BTC 1年)
{'='*70}

┌─ 【账户概览】 ──────────────────────────────────────────────────────────────
│  初始本金:        ${INITIAL_CAPITAL:,.2f}
│  最终权益:        ${final_cap:,.2f}
│  总收益:          ${total_pnl:,.2f}
│  总收益率:        {total_ret:.2f}%
│  年化收益率:      {ann_ret:.2f}%
│  夏普比率:        {sharpe:.2f}
│  最大回撤:        {max_dd:.2f}%
└──────────────────────────────────────────────────────────────────────────────

┌─ 【交易统计】 ──────────────────────────────────────────────────────────────
│  总开仓次数:      {n_trades}
│  做多次数:        {n_long}    做空次数: {n_short}
│  盈利交易:        {strat.wins}    亏损交易: {strat.losses}
│  胜率:            {wr:.2f}%
│  平均盈利:        ${avg_w:,.2f}
│  平均亏损:        ${avg_l:,.2f}
│  盈亏比:          {pf:.2f}
│  止盈次数:        {tp_count} ({tp_count/n_trades*100:.1f}%)
│  止损次数:        {sl_count} ({sl_count/n_trades*100:.1f}%)
│  最终Kelly:       {strat.kelly:.1%}
└──────────────────────────────────────────────────────────────────────────────
""")
    
    # 趋势分析
    if len(open_trades) > 0:
        trend_bull = len(open_trades[open_trades['trend'] == 'bullish'])
        trend_bear = len(open_trades[open_trades['trend'] == 'bearish'])
        trend_neut = len(open_trades[open_trades['trend'] == 'neutral'])
        print(f"┌─ 【趋势分布】 ──────────────────────────────────────────────────────────────")
        print(f"│  牛市(做多):    {trend_bull:3d} ({trend_bull/len(open_trades)*100:5.1f}%)")
        print(f"│  熊市(做空):    {trend_bear:3d} ({trend_bear/len(open_trades)*100:5.1f}%)")
        print(f"│  中性:          {trend_neut:3d} ({trend_neut/len(open_trades)*100:5.1f}%)")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 月度
    if len(eq) > 0:
        print(f"\n┌─ 【月度收益】 ──────────────────────────────────────────────────────────────")
        eq['month'] = eq['date'].str[:7]
        monthly = eq.groupby('month').agg({'total_equity': ['first', 'last']})
        monthly.columns = ['s', 'e']
        monthly['r'] = (monthly['e'] - monthly['s']) / monthly['s'] * 100
        for m, row in monthly.iterrows():
            r = row['r']
            c = '🟢' if r >= 0 else '🔴'
            print(f"│  {m}: {'+' if r >= 0 else ''}{r:6.2f}%  {c}")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 平仓原因
    if len(close_trades) > 0:
        print(f"\n┌─ 【平仓原因】 ──────────────────────────────────────────────────────────────")
        for r, cnt in close_trades['reason'].value_counts().items():
            pct = cnt / len(close_trades) * 100
            print(f"│  {r:20s}: {cnt:3d} ({pct:5.1f}%)")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # RSI分布
    if len(open_trades) > 0:
        print(f"\n┌─ 【入场RSI分布】 ──────────────────────────────────────────────────────────")
        bins = [(20, 35), (35, 45), (45, 55), (55, 65), (65, 80)]
        for lo, hi in bins:
            cnt = len(open_trades[(open_trades['rsi'] >= lo) & (open_trades['rsi'] < hi)])
            if cnt > 0:
                pct = cnt / len(open_trades) * 100
                bar = '█' * int(pct / 2)
                print(f"│  RSI {lo:2d}-{hi:2d}: {cnt:3d} ({pct:5.1f}%) {bar}")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 保存
    print("\n[5/6] 保存数据...")
    od = '/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/backtest_results'
    os.makedirs(od, exist_ok=True)
    eq.to_csv(f'{od}/sr_v3_equity.csv', index=False)
    trades.to_csv(f'{od}/sr_v3_trades.csv', index=False)
    
    summary = {
        'strategy': 'SR_V3_DirectEntry',
        'initial_capital': INITIAL_CAPITAL,
        'final_equity': final_cap,
        'total_return_pct': total_ret,
        'annual_return_pct': ann_ret,
        'sharpe': sharpe,
        'max_drawdown_pct': max_dd,
        'total_trades': n_trades,
        'win_rate': wr,
        'profit_factor': pf,
        'final_kelly': strat.kelly,
    }
    with open(f'{od}/sr_v3_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n[6/6] 完成!")
    print(f"📁 数据已保存: {od}/sr_v3_*.csv")
    
    return strat, eq, closed

if __name__ == '__main__':
    run()
