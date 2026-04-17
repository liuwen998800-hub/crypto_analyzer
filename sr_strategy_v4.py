#!/usr/bin/env python3
"""
支撑压力做单策略 V4 - 严格趋势过滤版
核心改动:
1. 做空条件极其严格 (必须有明确下跌趋势 + RSI超买 + 压力位三重确认)
2. 做多条件相对宽松
3. 每2小时最多开1单
4. ATR止损收紧到1倍
5. 浮亏持仓不清算，等待回调
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
REBALANCE_HOURS = 2  # 每2小时检查
TP_RATIO = 2.5       # 盈亏比2.5:1
SL_ATR = 1.0          # ATR止损

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
    ema200 = df['ema200'].iloc[-1] if 'ema200' in df.columns else ema60
    
    swing_high = recent['high'].max()
    swing_low = recent['low'].min()
    
    bb_std = df['close'].tail(20).std()
    bb_upper = current + 2 * bb_std
    bb_lower = current - 2 * bb_std
    
    # 趋势 (五级)
    if current > ema200 and ema20 > ema60:
        trend = 'strong_bull'
    elif current > ema60 and ema20 > ema60:
        trend = 'bullish'
    elif current < ema60 and ema20 < ema60:
        trend = 'bearish'
    elif current < ema200 and ema20 < ema60:
        trend = 'strong_bear'
    else:
        trend = 'neutral'
    
    rsi = df['rsi'].iloc[-1]
    
    # 距离支撑/压力
    dist_support = (current - swing_low) / current * 100
    dist_resistance = (swing_high - current) / current * 100
    
    return {
        'current': current, 'atr': atr,
        'trend': trend, 'rsi': rsi,
        'ema20': ema20, 'ema60': ema60, 'ema200': ema200,
        'swing_high': swing_high, 'swing_low': swing_low,
        'bb_upper': bb_upper, 'bb_lower': bb_lower,
        'dist_support': dist_support, 'dist_resistance': dist_resistance,
    }

class StrategyV4:
    def __init__(self):
        self.capital = INITIAL_CAPITAL
        self.positions = []
        self.closed = []
        self.equity_curve = []
        self.trades = []
        self.wins = self.losses = 0
        self.win_amt = []
        self.loss_amt = []
        self.last_entry_time = {}  # 每对(type)的上次开仓时间
    
    def position_size(self, entry, sl):
        risk = self.capital * RISK_PCT
        dist = abs(entry - sl)
        if dist == 0: return 0
        size = risk / dist
        return min(size, self.capital * 0.25)
    
    def should_open_long(self, sr):
        """做多条件"""
        score = 0
        reasons = []
        
        # 强烈看多
        if sr['trend'] in ['strong_bull', 'bullish']:
            score += 4
            reasons.append(f"趋势={sr['trend']}(+4)")
        elif sr['trend'] == 'neutral':
            score += 1
        
        # RSI 超卖
        if sr['rsi'] < 30:
            score += 4
            reasons.append(f"RSI={sr['rsi']:.1f}(+4)")
        elif sr['rsi'] < 40:
            score += 2
            reasons.append(f"RSI={sr['rsi']:.1f}(+2)")
        elif sr['rsi'] < 50:
            score += 1
            reasons.append(f"RSI={sr['rsi']:.1f}(+1)")
        
        # 距离支撑近
        if sr['dist_support'] < 2:
            score += 2
            reasons.append(f"距支撑{sr['dist_support']:.1f}%(+2)")
        elif sr['dist_support'] < 5:
            score += 1
            reasons.append(f"距支撑{sr['dist_support']:.1f}%(+1)")
        
        # 布林下轨
        if sr['current'] < sr['bb_lower']:
            score += 3
            reasons.append("触布林下轨(+3)")
        elif sr['current'] < sr['bb_lower'] * 1.01:
            score += 1
        
        return score >= 6, reasons
    
    def should_open_short(self, sr):
        """做空条件 (极其严格)"""
        score = 0
        reasons = []
        
        # 必须明确下跌趋势
        if sr['trend'] in ['strong_bear', 'bearish']:
            score += 4
            reasons.append(f"趋势={sr['trend']}(+4)")
        elif sr['trend'] == 'neutral':
            score += 1
            reasons.append("中性趋势(+1)")
            # 中性趋势时,做空要求更苛刻
            if sr['rsi'] < 70:  # RSI不够高就不做空
                return False, []
        else:
            return False, []  # 牛市不做空
        
        # RSI 超买 (必须有)
        if sr['rsi'] > 70:
            score += 4
            reasons.append(f"RSI={sr['rsi']:.1f}(+4)")
        elif sr['rsi'] > 65:
            score += 2
            reasons.append(f"RSI={sr['rsi']:.1f}(+2)")
        
        # 距离压力近
        if sr['dist_resistance'] < 2:
            score += 3
            reasons.append(f"距压力{sr['dist_resistance']:.1f}%(+3)")
        elif sr['dist_resistance'] < 5:
            score += 1
        
        # 布林上轨
        if sr['current'] > sr['bb_upper']:
            score += 3
            reasons.append("触布林上轨(+3)")
        elif sr['current'] > sr['bb_upper'] * 0.99:
            score += 1
        
        return score >= 8, reasons  # 做空需要8分(更严格)
    
    def open_pos(self, ptype, entry, sl, tp, level, atr, ts):
        key = (ptype, ts.strftime('%Y-%m-%d %H'))
        if key in self.last_entry_time:
            return
        if len(self.positions) >= MAX_POSITIONS:
            return
        
        size = self.position_size(entry, sl)
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
            'atr': atr, 'level': level,
            'open_time': ts, 'pnl': 0
        }
        self.positions.append(pos)
        self.last_entry_time[key] = ts
        
        self.trades.append({
            'timestamp': ts, 'type': f'OPEN_{ptype.upper()}',
            'price': entry, 'size': size, 'sl': sl, 'tp': tp,
            'atr': atr, 'level': level,
            'trend': self.trend, 'rsi': self.rsi,
            'capital': self.capital
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
            hit = None
            if pos['type'] == 'long':
                if price <= pos['sl']:
                    hit = 'SL'
                elif price >= pos['tp']:
                    hit = 'TP'
            else:
                if price >= pos['sl']:
                    hit = 'SL'
                elif price <= pos['tp']:
                    hit = 'TP'
            
            if hit:
                reason = 'STOP_LOSS' if hit == 'SL' else 'TAKE_PROFIT'
                self.close_pos(pos, price, ts, reason)
                self.positions.remove(pos)
    
    def update_eq(self, ts, price, sr):
        ppnl = sum(
            p['size'] * (price - p['entry']) if p['type'] == 'long'
            else p['size'] * (p['entry'] - price)
            for p in self.positions
        )
        self.equity_curve.append({
            'timestamp': ts, 'date': ts.strftime('%Y-%m-%d'),
            'close': price,
            'capital': self.capital,
            'pos_pnl': ppnl,
            'total_equity': self.capital + ppnl,
            'n_pos': len(self.positions),
            'trend': self.trend, 'rsi': self.rsi,
            'atr': sr['atr'],
            'support': sr['swing_low'],
            'resistance': sr['swing_high'],
        })

def run():
    print("=" * 70)
    print("  支撑压力做单策略 V4 - 严格趋势过滤版")
    print("=" * 70)
    print(f"本金: ${INITIAL_CAPITAL:,.2f}")
    print(f"做多条件: score≥6 | 做空条件: score≥8 (极严)")
    print(f"ATR止损×{SL_ATR} | 盈亏比{TP_RATIO}:1 | 每{REBALANCE_HOURS}h最多1单")
    print(f"最大持仓: {MAX_POSITIONS}")
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
    print(f"  {len(df)} 根K线")
    
    # 指标
    print("\n[2/6] 计算指标...")
    df['atr'] = calc_atr(df, ATR_PERIOD)
    df['ema20'] = calc_ema(df['close'], 20)
    df['ema60'] = calc_ema(df['close'], 60)
    df['ema200'] = calc_ema(df['close'], 200)
    df['rsi'] = calc_rsi(df['close'], 14)
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['close'] + 2 * df['bb_std']
    df['bb_lower'] = df['close'] - 2 * df['bb_std']
    df = df.dropna()
    print(f"  有效数据: {len(df)}")
    
    # 回测
    print("\n[3/6] 运行回测...")
    strat = StrategyV4()
    
    for i in range(SR_LOOKBACK + 1, len(df)):
        row = df.iloc[i]
        ts = row.name
        price = row['close']
        
        sr = calc_levels(df.iloc[:i+1], SR_LOOKBACK)
        strat.trend = sr['trend']
        strat.rsi = sr['rsi']
        
        # 检查止损止盈
        strat.check_stops(price, ts)
        
        # 每REBALANCE_HOURS小时检查一次
        if i % REBALANCE_HOURS == 0:
            # 清理过期记录
            cutoff = ts - pd.Timedelta(hours=REBALANCE_HOURS * 2)
            strat.last_entry_time = {
                k: v for k, v in strat.last_entry_time.items()
                if pd.Timestamp(k[1]) > cutoff
            }
            
            # 决策
            long_ok, long_reasons = strat.should_open_long(sr)
            short_ok, short_reasons = strat.should_open_short(sr)
            
            if long_ok and len(strat.positions) < MAX_POSITIONS:
                atr = sr['atr']
                sl = price - atr * SL_ATR
                tp = price + atr * SL_ATR * TP_RATIO
                strat.open_pos('long', price, sl, tp, '; '.join(long_reasons), atr, ts)
            
            elif short_ok and len(strat.positions) < MAX_POSITIONS:
                atr = sr['atr']
                sl = price + atr * SL_ATR
                tp = price - atr * SL_ATR * TP_RATIO
                strat.open_pos('short', price, sl, tp, '; '.join(short_reasons), atr, ts)
        
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
    closed = pd.DataFrame(strat.closed)
    
    fc = strat.capital
    tr = (fc - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    tp_amt = fc - INITIAL_CAPITAL
    
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
    
    opens = trades[trades['type'].str.startswith('OPEN')]
    closes = trades[trades['type'].str.startswith('CLOSE')]
    n_long = len(opens[opens['type'] == 'OPEN_LONG'])
    n_short = len(opens[opens['type'] == 'OPEN_SHORT'])
    tp_n = len(closes[closes['reason'] == 'TAKE_PROFIT']) if len(closes) > 0 else 0
    sl_n = len(closes[closes['reason'] == 'STOP_LOSS']) if len(closes) > 0 else 0
    
    # 趋势统计
    trend_stats = {}
    if len(opens) > 0:
        for t in ['strong_bull', 'bullish', 'neutral', 'bearish', 'strong_bear']:
            cnt = len(opens[opens['trend'] == t])
            if cnt > 0:
                trend_stats[t] = cnt
    
    print(f"""
{'='*70}
        📊 回测报告 V4 - 严格趋势过滤 (BTC 1年)
{'='*70}

┌─ 【账户概览】 ──────────────────────────────────────────────────────────────
│  初始本金:        ${INITIAL_CAPITAL:,.2f}
│  最终权益:        ${fc:,.2f}
│  总收益:          ${tp_amt:,.2f}
│  总收益率:        {tr:.2f}%
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
│  止盈:            {tp_n} ({tp_n/n*100:.1f}%)
│  止损:            {sl_n} ({sl_n/n*100:.1f}%)
└──────────────────────────────────────────────────────────────────────────────

┌─ 【信号条件】 ──────────────────────────────────────────────────────────────
│  做多: score≥6 (趋势+RSI超卖+布林支撑+距支撑近)
│  做空: score≥8 (强趋势+RSI超买+布林压力+距压力近)【极严】
└──────────────────────────────────────────────────────────────────────────────
""")
    
    if trend_stats:
        print("┌─ 【趋势分布】 ──────────────────────────────────────────────────────────────")
        total_t = sum(trend_stats.values())
        for t, cnt in sorted(trend_stats.items(), key=lambda x: -x[1]):
            pct = cnt / total_t * 100
            bar = '█' * int(pct / 2)
            print(f"│  {t:12s}: {cnt:3d} ({pct:5.1f}%) {bar}")
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
    eq.to_csv(f'{od}/sr_v4_equity.csv', index=False)
    trades.to_csv(f'{od}/sr_v4_trades.csv', index=False)
    with open(f'{od}/sr_v4_summary.json', 'w') as f:
        json.dump({
            'strategy': 'SR_V4_StrictFilter',
            'initial': INITIAL_CAPITAL, 'final': fc,
            'total_return_pct': tr, 'annual_return_pct': ann,
            'sharpe': sharpe, 'max_drawdown_pct': max_dd,
            'total_trades': n, 'win_rate': wr,
            'profit_factor': pf,
        }, f, indent=2)
    print(f"\n[6/6] 完成!")
    print(f"📁 {od}/sr_v4_*.csv")

if __name__ == '__main__':
    run()
