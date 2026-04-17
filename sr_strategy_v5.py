#!/usr/bin/env python3
"""
支撑压力做单策略 V5 - 双周期趋势确认版
核心升级:
1. 日线趋势过滤 (EMA50 on Daily)
2. 1H信号 + 日线确认
3. 只在日线趋势方向交易
4. ATR止损1倍 + 盈亏比3:1
"""

import pandas as pd
import numpy as np
import requests
import json
import time
import os

INITIAL_CAPITAL = 10000
RISK_PCT = 0.015
SYMBOL = 'BTCUSDT'
INTERVAL = '1h'
START_DATE = '2024-04-16'
END_DATE = '2025-04-16'
TRADE_FEE = 0.0004
ATR_PERIOD = 14
SR_LOOKBACK = 24
MAX_POSITIONS = 2
REBALANCE_HOURS = 1
SL_ATR = 1.0
TP_RATIO = 3.0

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

def calc_levels(df, lookback=24):
    recent = df.tail(lookback)
    current = df['close'].iloc[-1]
    atr = df['atr'].iloc[-1]
    
    ema20 = df['ema20'].iloc[-1]
    ema60 = df['ema60'].iloc[-1]
    
    swing_high = recent['high'].max()
    swing_low = recent['low'].min()
    
    bb_std = df['close'].tail(20).std()
    bb_upper = current + 2 * bb_std
    bb_lower = current - 2 * bb_std
    
    # 1H趋势
    if current > ema60 and ema20 > ema60:
        trend_1h = 'bullish'
    elif current < ema60 and ema20 < ema60:
        trend_1h = 'bearish'
    else:
        trend_1h = 'neutral'
    
    rsi = df['rsi'].iloc[-1]
    
    dist_sup = (current - swing_low) / current * 100
    dist_res = (swing_high - current) / current * 100
    
    return {
        'current': current, 'atr': atr,
        'trend_1h': trend_1h,
        'rsi': rsi,
        'ema20': ema20, 'ema60': ema60,
        'swing_high': swing_high, 'swing_low': swing_low,
        'bb_upper': bb_upper, 'bb_lower': bb_lower,
        'dist_sup': dist_sup, 'dist_res': dist_res,
    }

class StrategyV5:
    def __init__(self):
        self.capital = INITIAL_CAPITAL
        self.positions = []
        self.closed = []
        self.equity_curve = []
        self.trades = []
        self.wins = self.losses = 0
        self.win_amt = []
        self.loss_amt = []
        self.last_entry = {}
    
    def size_calc(self, entry, sl):
        risk = self.capital * RISK_PCT
        dist = abs(entry - sl)
        if dist == 0: return 0
        return min(risk / dist, self.capital * 0.25)
    
    def check_open_long(self, sr, daily_trend):
        score = 0
        
        # 日线趋势确认
        if daily_trend == 'bull':
            score += 3
        elif daily_trend == 'neutral':
            score += 1
        else:  # 日线也看空，不做多
            return False
        
        # 1H趋势配合
        if sr['trend_1h'] in ['bullish']:
            score += 2
        elif sr['trend_1h'] == 'neutral':
            score += 1
        
        # RSI超卖
        if sr['rsi'] < 30:
            score += 4
        elif sr['rsi'] < 38:
            score += 3
        elif sr['rsi'] < 45:
            score += 2
        elif sr['rsi'] < 50:
            score += 1
        
        # 布林带支撑
        if sr['current'] < sr['bb_lower']:
            score += 3
        elif sr['current'] < sr['bb_lower'] * 1.005:
            score += 1
        
        # 距支撑近
        if sr['dist_sup'] < 2:
            score += 2
        elif sr['dist_sup'] < 4:
            score += 1
        
        return score >= 7, score
    
    def check_open_short(self, sr, daily_trend):
        # 日线熊市才做空
        if daily_trend != 'bear':
            return False, 0
        
        score = 0
        
        # 1H趋势配合
        if sr['trend_1h'] in ['bearish']:
            score += 3
        elif sr['trend_1h'] == 'neutral':
            score += 1
        
        # RSI超买 (必要条件)
        if sr['rsi'] > 70:
            score += 4
        elif sr['rsi'] > 65:
            score += 3
        elif sr['rsi'] > 60:
            score += 2
        
        # 布林带上轨
        if sr['current'] > sr['bb_upper']:
            score += 3
        elif sr['current'] > sr['bb_upper'] * 0.995:
            score += 1
        
        # 距压力近
        if sr['dist_res'] < 2:
            score += 2
        elif sr['dist_res'] < 4:
            score += 1
        
        return score >= 8, score
    
    def open_pos(self, ptype, entry, sl, tp, info, atr, ts):
        key = (ptype, ts.strftime('%Y-%m-%d %H'))
        if key in self.last_entry:
            return
        if len(self.positions) >= MAX_POSITIONS:
            return
        
        size = self.size_calc(entry, sl)
        if size <= 0: return
        
        if ptype == 'long':
            cost = size * entry * (1 + TRADE_FEE)
            if cost > self.capital: return
        else:
            margin = size * entry / 10
            if margin > self.capital * 0.5: return
        
        pos = {
            'type': ptype, 'size': size,
            'entry': entry, 'sl': sl, 'tp': tp,
            'atr': atr, 'info': info,
            'open_time': ts, 'pnl': 0
        }
        self.positions.append(pos)
        self.last_entry[key] = True
        
        self.trades.append({
            'timestamp': ts, 'type': f'OPEN_{ptype.upper()}',
            'price': entry, 'size': size, 'sl': sl, 'tp': tp,
            'atr': atr, 'info': info,
            'trend_1h': self.trend_1h, 'trend_d': self.daily_trend,
            'rsi': self.rsi, 'capital': self.capital
        })
    
    def close_pos(self, pos, price, ts, reason):
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
            self.win_amt.append(pnl)
        else:
            self.losses += 1
            self.loss_amt.append(pnl)
        
        hold_h = (ts - pos['open_time']).total_seconds() / 3600
        
        self.closed.append({
            **pos, 'close_price': price, 'close_time': ts,
            'pnl': pnl, 'reason': reason, 'hold_h': hold_h
        })
        
        self.trades.append({
            'timestamp': ts, 'type': f'CLOSE_{pos["type"].upper()}',
            'price': price, 'size': pos['size'],
            'pnl': pnl, 'reason': reason, 'hold_h': hold_h,
            'capital_after': self.capital
        })
    
    def check_stops(self, price, ts):
        for pos in self.positions[:]:
            hit = reason = None
            if pos['type'] == 'long':
                if price <= pos['sl']: hit, reason = 'SL', 'STOP_LOSS'
                elif price >= pos['tp']: hit, reason = 'TP', 'TAKE_PROFIT'
            else:
                if price >= pos['sl']: hit, reason = 'SL', 'STOP_LOSS'
                elif price <= pos['tp']: hit, reason = 'TP', 'TAKE_PROFIT'
            
            if hit:
                self.close_pos(pos, price, ts, reason)
                self.positions.remove(pos)
    
    def update_eq(self, ts, price, sr):
        ppnl = sum(
            p['size'] * ((price - p['entry']) if p['type'] == 'long' else (p['entry'] - price))
            for p in self.positions
        )
        self.equity_curve.append({
            'timestamp': ts, 'date': ts.strftime('%Y-%m-%d'),
            'close': price, 'capital': self.capital,
            'total_equity': self.capital + ppnl,
            'n_pos': len(self.positions),
            'trend_1h': self.trend_1h, 'trend_d': self.daily_trend,
            'rsi': self.rsi, 'atr': sr['atr'],
        })

def get_daily_trend(df_1h):
    """从1H数据中计算日线趋势"""
    df_daily = df_1h.groupby(df_1h.index.date).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    df_daily.index = pd.to_datetime(df_daily.index)
    
    ema50 = df_daily['close'].ewm(span=50, adjust=False).mean()
    ema20d = df_daily['close'].ewm(span=20, adjust=False).mean()
    
    trends = {}
    for dt in df_daily.index:
        if dt not in ema50.index:
            continue
        c = df_daily.loc[dt, 'close']
        e50 = ema50.loc[dt]
        e20d = ema20d.loc[dt] if dt in ema20d.index else c
        
        if c > e50 and e20d > e50:
            trends[dt] = 'bull'
        elif c < e50 and e20d < e50:
            trends[dt] = 'bear'
        else:
            trends[dt] = 'neutral'
    
    return trends

def run():
    print("=" * 70)
    print("  支撑压力做单策略 V5 - 双周期趋势确认版")
    print("=" * 70)
    print(f"本金: ${INITIAL_CAPITAL:,.2f} | 每笔风险: {RISK_PCT*100:.1f}%")
    print(f"止损: ATR×{SL_ATR} | 盈亏比: {TP_RATIO}:1")
    print(f"日线趋势过滤: 日EMA50确认方向 | 1H信号入场")
    print(f"做多: 日线bull + 1H信号(score≥7)")
    print(f"做空: 日线bear + 1H信号(score≥8)")
    print("=" * 70)
    
    # 数据
    print(f"\n[1/6] 获取数据...")
    cache = "/tmp/binance_BTCUSDT_1y.json"
    if os.path.exists(cache):
        with open(cache) as f: raw = json.load(f)
    else:
        raw = get_binance_klines(SYMBOL, INTERVAL, START_DATE, END_DATE)
        if raw:
            with open(cache, 'w') as f: json.dump(raw, f)
    if not raw: return
    
    df = parse_klines(raw)
    print(f"  {len(df)} 根1H K线")
    
    # 日线趋势
    print("\n[2/6] 计算日线趋势...")
    df['atr'] = calc_atr(df, ATR_PERIOD)
    df['ema20'] = calc_ema(df['close'], 20)
    df['ema60'] = calc_ema(df['close'], 60)
    df['rsi'] = calc_rsi(df['close'], 14)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['close'] + 2 * df['bb_std']
    df['bb_lower'] = df['close'] - 2 * df['bb_std']
    df = df.dropna()
    
    daily_trends = get_daily_trend(df)
    print(f"  日线趋势样本: {len(daily_trends)}")
    bull_days = sum(1 for v in daily_trends.values() if v == 'bull')
    bear_days = sum(1 for v in daily_trends.values() if v == 'bear')
    print(f"  牛市天数: {bull_days} | 熊市天数: {bear_days} | 中性: {len(daily_trends)-bull_days-bear_days}")
    
    # 回测
    print("\n[3/6] 运行回测...")
    strat = StrategyV5()
    
    for i in range(SR_LOOKBACK + 1, len(df)):
        row = df.iloc[i]
        ts = row.name
        price = row['close']
        
        # 日线趋势
        day_key = ts.date()
        strat.daily_trend = daily_trends.get(day_key, 'neutral')
        
        sr = calc_levels(df.iloc[:i+1], SR_LOOKBACK)
        strat.trend_1h = sr['trend_1h']
        strat.rsi = sr['rsi']
        
        # 平仓检查
        strat.check_stops(price, ts)
        
        # 每小时决策
        if i % REBALANCE_HOURS == 0:
            cutoff = ts - pd.Timedelta(hours=2)
            strat.last_entry = {
                k: v for k, v in strat.last_entry.items()
                if pd.Timestamp(k[1]) > cutoff
            }
            
            # 尝试做多
            long_ok, long_score = strat.check_open_long(sr, strat.daily_trend)
            if long_ok and len(strat.positions) < MAX_POSITIONS:
                sl = price - sr['atr'] * SL_ATR
                tp = price + sr['atr'] * SL_ATR * TP_RATIO
                strat.open_pos('long', price, sl, tp,
                             f"score={long_score},d={strat.daily_trend},1h={strat.trend_1h},RSI={sr['rsi']:.1f}",
                             sr['atr'], ts)
            
            # 尝试做空
            short_ok, short_score = strat.check_open_short(sr, strat.daily_trend)
            if short_ok and len(strat.positions) < MAX_POSITIONS:
                sl = price + sr['atr'] * SL_ATR
                tp = price - sr['atr'] * SL_ATR * TP_RATIO
                strat.open_pos('short', price, sl, tp,
                             f"score={short_score},d={strat.daily_trend},1h={strat.trend_1h},RSI={sr['rsi']:.1f}",
                             sr['atr'], ts)
        
        strat.update_eq(ts, price, sr)
    
    # 平仓
    fp = df.iloc[-1]['close']
    for pos in strat.positions[:]:
        strat.close_pos(pos, fp, df.iloc[-1].name, 'END')
        strat.positions.remove(pos)
    
    # 报告
    print("\n[4/6] 生成报告...")
    eq = pd.DataFrame(strat.equity_curve)
    trades = pd.DataFrame(strat.trades)
    closed = pd.DataFrame(strat.closed) if len(strat.closed) > 0 else pd.DataFrame()
    
    fc = strat.capital
    tr_pct = (fc - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    tr_amt = fc - INITIAL_CAPITAL
    
    n = len(closed)
    wr = strat.wins / (strat.wins + strat.losses) * 100 if (strat.wins + strat.losses) > 0 else 0
    aw = np.mean(strat.win_amt) if strat.win_amt else 0
    al = np.mean(strat.loss_amt) if strat.loss_amt else 0
    pf = abs(sum(strat.win_amt) / sum(strat.loss_amt)) if strat.loss_amt and sum(strat.loss_amt) != 0 else 0
    
    if len(eq) > 0:
        eq['peak'] = eq['total_equity'].cummax()
        eq['dd'] = (eq['total_equity'] - eq['peak']) / eq['peak'] * 100
        max_dd = abs(eq['dd'].min())
        hrs = len(eq)
        ann = ((fc / INITIAL_CAPITAL) ** (365 * 24 / hrs) - 1) * 100 if hrs > 0 and fc > 0 else 0
        rets = eq['total_equity'].pct_change().dropna()
        sharpe = rets.mean() / rets.std() * np.sqrt(365 * 24) if rets.std() > 0 else 0
    else:
        max_dd = ann = sharpe = 0
    
    opens = trades[trades['type'].str.startswith('OPEN')] if len(trades) > 0 else pd.DataFrame()
    closes = trades[trades['type'].str.startswith('CLOSE')] if len(trades) > 0 else pd.DataFrame()
    
    n_long = len(opens[opens['type'] == 'OPEN_LONG']) if len(opens) > 0 else 0
    n_short = len(opens[opens['type'] == 'OPEN_SHORT']) if len(opens) > 0 else 0
    tp_n = len(closes[closes['reason'] == 'TAKE_PROFIT']) if len(closes) > 0 else 0
    sl_n = len(closes[closes['reason'] == 'STOP_LOSS']) if len(closes) > 0 else 0
    
    print(f"""
{'='*70}
        📊 回测报告 V5 - 双周期趋势确认 (BTC 1年)
{'='*70}

┌─ 【账户概览】 ──────────────────────────────────────────────────────────────
│  初始本金:        ${INITIAL_CAPITAL:,.2f}
│  最终权益:        ${fc:,.2f}
│  总收益:          ${tr_amt:,.2f}
│  总收益率:        {tr_pct:.2f}%
│  年化收益率:      {ann:.2f}%
│  夏普比率:        {sharpe:.2f}
│  最大回撤:        {max_dd:.2f}%
└──────────────────────────────────────────────────────────────────────────────

┌─ 【交易统计】 ──────────────────────────────────────────────────────────────
│  总开仓次数:      {n}
│  做多次数:        {n_long}    做空次数: {n_short}
│  盈利交易:        {strat.wins}    亏损交易: {strat.losses}
│  胜率:            {wr:.2f}%
│  平均盈利:        ${aw:,.2f}
│  平均亏损:        ${al:,.2f}
│  盈亏比:          {pf:.2f}
│  止盈次数:        {tp_n} ({tp_n/n*100:.1f}%)  止损次数: {sl_n} ({sl_n/n*100:.1f}%)
└──────────────────────────────────────────────────────────────────────────────
""")
    
    if len(opens) > 0:
        d_trend = opens['trend_d'].value_counts()
        print(f"┌─ 【日线趋势分布】 ─────────────────────────────────────────────────────────")
        for t in ['bull', 'neutral', 'bear']:
            c = d_trend.get(t, 0)
            pct = c / len(opens) * 100
            bar = '█' * int(pct / 2)
            print(f"│  日线{t:7s}: {c:3d} ({pct:5.1f}%) {bar}")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    if len(eq) > 0:
        print(f"\n┌─ 【月度收益】 ──────────────────────────────────────────────────────────────")
        eq['month'] = eq['date'].str[:7]
        mo = eq.groupby('month').agg({'total_equity': ['first', 'last']})
        mo.columns = ['s', 'e']
        mo['r'] = (mo['e'] - mo['s']) / mo['s'] * 100
        for m, row in mo.iterrows():
            r = row['r']
            c = '🟢' if r >= 0 else '🔴'
            print(f"│  {m}: {'+' if r >= 0 else ''}{r:6.2f}%  {c}")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    if len(closes) > 0:
        print(f"\n┌─ 【平仓原因】 ──────────────────────────────────────────────────────────────")
        for r, cnt in closes['reason'].value_counts().items():
            pct = cnt / len(closes) * 100
            print(f"│  {r:20s}: {cnt:3d} ({pct:5.1f}%)")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 保存
    print("\n[5/6] 保存数据...")
    od = '/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/backtest_results'
    os.makedirs(od, exist_ok=True)
    eq.to_csv(f'{od}/sr_v5_equity.csv', index=False)
    trades.to_csv(f'{od}/sr_v5_trades.csv', index=False)
    with open(f'{od}/sr_v5_summary.json', 'w') as f:
        json.dump({
            'strategy': 'SR_V5_DualPeriod',
            'initial': INITIAL_CAPITAL, 'final': fc,
            'total_return_pct': tr_pct, 'annual_return_pct': ann,
            'sharpe': sharpe, 'max_drawdown_pct': max_dd,
            'total_trades': n, 'win_rate': wr, 'profit_factor': pf,
        }, f, indent=2)
    print(f"\n[6/6] 完成!")
    print(f"📁 {od}/sr_v5_*.csv")

if __name__ == '__main__':
    run()
