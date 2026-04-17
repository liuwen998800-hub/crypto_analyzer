#!/usr/bin/env python3
"""
Polymarket式24H策略 V4 - 最终优化版
核心改动:
1. 日亏损软限制(超过后暂停交易,不强制平仓)
2. 加入止盈机制(移动止盈+固定目标)
3. 区分做多/做空的环境
"""

import pandas as pd
import numpy as np
import requests
import json
import time
import os

INITIAL_CAPITAL = 10000
MAX_POSITION = 1000
DAILY_LOSS_LIMIT = 0.05
SYMBOL = 'BTCUSDT'
INTERVAL = '1h'
START_DATE = '2024-04-16'
END_DATE = '2025-04-16'
TRADE_FEE = 0.001

# ========== 数据获取 ==========
def get_binance_klines(symbol, interval, start_str, end_str=None, limit=1000):
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
            time.sleep(0.2)
        except: break
    return all_klines

def parse_klines(klines):
    df = pd.DataFrame(klines, columns=[
        'open_time','open','high','low','close','volume','close_time',
        'quote_volume','trades','taker_buy_base','taker_buy_quote','ignore'])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    for c in ['open','high','low','close','volume','quote_volume']:
        df[c] = df[c].astype(float)
    return df.set_index('open_time')

def calc_rsi(p, n=14):
    d = p.diff()
    g = d.where(d>0,0).rolling(n).mean()
    l = (-d.where(d<0,0)).rolling(n).mean()
    return 100-(100/(1+g/(l+1e-10)))

def calc_macd(p, f=12,s=26,sig=9):
    ef = p.ewm(span=f,adjust=False).mean()
    es = p.ewm(span=s,adjust=False).mean()
    m = ef-es; s_=m.ewm(span=sig,adjust=False).mean()
    return m, s_, m-s_

def calc_bb(p, n=20):
    sma = p.rolling(n).mean(); std = p.rolling(n).std()
    u = sma+2*std; l = sma-2*std
    return u, l, (p-l)/(u-l+1e-10)

def calc_ema(p, n): return p.ewm(span=n, adjust=False).mean()

# ========== V4 信号 ==========
def calc_fg(vol, vc):
    vol = vol if pd.notna(vol) else 3
    vc = vc if pd.notna(vc) else 0
    if vol > 8: fg = max(10, 50-(vol-5)*4)
    elif vol < 2: fg = min(90, 50+(3-vol)*10)
    else: fg = 50
    if vc > 30: fg = min(100, fg+10)
    elif vc < -30: fg = max(0, fg-10)
    return int(np.clip(fg, 0, 100))

def gen_signal(row):
    rsi, macd = row['rsi'], row['macd']
    macd_sig, macd_h = row['macd_s'], row['macd_h']
    bb_pos = row['bb_pos']
    ema20, ema60, ema200 = row['ema20'], row['ema60'], row['ema200']
    pct24 = row['pct24']
    fg = row['fg']
    close = row['close']
    
    # 趋势
    if close > ema200 and ema20 > ema60: trend = 'bullish'
    elif close < ema200 and ema20 < ema60: trend = 'bearish'
    else: trend = 'neutral'
    
    # RSI (0-100)
    if rsi < 25: rs = 100
    elif rsi < 30: rs = 88
    elif rsi < 35: rs = 75
    elif rsi < 40: rs = 63
    elif rsi < 45: rs = 55
    elif rsi < 50: rs = 50
    elif rsi < 55: rs = 45
    elif rsi < 60: rs = 38
    elif rsi < 65: rs = 30
    elif rsi < 70: rs = 22
    elif rsi < 75: rs = 14
    else: rs = 5
    
    # MACD
    if macd > macd_sig and macd_h > 0: ms = 85
    elif macd > macd_sig: ms = 68
    elif macd > 0: ms = 55
    elif macd < macd_sig and macd_h < 0: ms = 15
    else: ms = 32
    
    # BB
    if bb_pos < 10: bs = 100
    elif bb_pos < 20: bs = 85
    elif bb_pos < 30: bs = 70
    elif bb_pos < 40: bs = 58
    elif bb_pos < 50: bs = 50
    elif bb_pos < 60: bs = 42
    elif bb_pos < 70: bs = 30
    elif bb_pos < 80: bs = 18
    else: bs = 8
    
    # 动量
    if pct24 > 5: mos = 88
    elif pct24 > 3: mos = 75
    elif pct24 > 2: mos = 65
    elif pct24 > 1: mos = 58
    elif pct24 > 0: mos = 52
    elif pct24 > -1: mos = 46
    elif pct24 > -2: mos = 38
    elif pct24 > -3: mos = 28
    elif pct24 > -5: mos = 15
    else: mos = 5
    
    tech = int(rs*0.25 + ms*0.25 + bs*0.25 + mos*0.25)
    
    # 情绪
    if fg < 20: es = 95
    elif fg < 30: es = 80
    elif fg < 40: es = 65
    elif fg < 50: es = 55
    elif fg < 60: es = 45
    elif fg < 70: es = 32
    elif fg < 80: es = 18
    else: es = 8
    
    comp = int(tech * 0.65 + es * 0.35)
    
    # 信号阈值
    if comp >= 68: sig = 'STRONG_BUY'
    elif comp >= 54: sig = 'BUY'
    elif comp <= 32: sig = 'STRONG_SELL'
    elif comp <= 46: sig = 'SELL'
    else: sig = 'NEUTRAL'
    
    # 趋势软过滤
    if trend == 'neutral':
        if sig == 'STRONG_BUY': sig = 'BUY'
        elif sig == 'STRONG_SELL': sig = 'SELL'
    
    return {
        'signal': sig, 'trend': trend, 'composite': comp,
        'tech': tech, 'emotion': es,
        'rsi': rsi, 'macd': macd, 'bb_pos': bb_pos,
        'fg': fg, 'pct24': pct24, 'close': close
    }

# ========== V4 模拟器 ==========
class SimV4:
    def __init__(self):
        self.cap = INITIAL_CAPITAL
        self.max_pos = MAX_POSITION
        self.pos = 0; self.pos_type = None
        self.entry_px = 0; self.entry_ts = None
        self.high_px = 0; self.low_px = float('inf')
        self.trades = []; self.eq = []
        self.win_t = 0; self.lose_t = 0
        self.day_start = INITIAL_CAPITAL
        self.day_loss_flag = False
        self.current_holding_pnl_pct = 0
        
    def open_pos(self, sig, px, ts):
        if self.pos != 0: return
        pv = min(self.max_pos, self.cap * 0.5)
        shares = pv / px
        fee = shares * px * TRADE_FEE
        
        if sig in ['STRONG_BUY','BUY']:
            self.pos_type = 'long'
            cost = shares * px + fee
            if cost <= self.cap:
                self.pos = shares; self.entry_px = px
                self.entry_ts = ts; self.high_px = px
                self.cap -= cost
                self.trades.append({'t':ts,'type':'OPEN_LONG','px':px,'shares':shares,'val':pv,'sig':sig})
        elif sig in ['STRONG_SELL','SELL']:
            self.pos_type = 'short'
            proceeds = shares * px - fee
            self.pos = shares; self.entry_px = px
            self.entry_ts = ts; self.low_px = px
            self.cap += proceeds
            self.trades.append({'t':ts,'type':'OPEN_SHORT','px':px,'shares':shares,'val':pv,'sig':sig})
    
    def close_pos(self, reason, px, ts):
        if self.pos == 0: return
        shares = self.pos
        if self.pos_type == 'long':
            proceeds = shares * px * (1 - TRADE_FEE)
            pnl = proceeds - shares * self.entry_px * (1 + TRADE_FEE)
            self.cap += proceeds
        else:
            cost = shares * px * (1 + TRADE_FEE)
            pnl = shares * self.entry_px * (1 - TRADE_FEE) - cost
            self.cap -= cost
        
        if pnl > 0: self.win_t += 1
        else: self.lose_t += 1
        
        hold_h = (ts - self.entry_ts).total_seconds()/3600 if self.entry_ts else 0
        
        self.trades.append({
            't':ts,'type':f'CLOSE_{self.pos_type.upper()}','px':px,
            'pnl':pnl,'reason':reason,'hold_h':hold_h,
            'cap_after':self.cap,'entry_px':self.entry_px
        })
        
        self.pos = 0; self.pos_type = None
        self.entry_px = 0; self.entry_ts = None
        self.high_px = 0; self.low_px = float('inf')
    
    def update(self, px):
        if self.pos == 0:
            self.current_holding_pnl_pct = 0
            return
        if self.pos_type == 'long':
            self.high_px = max(self.high_px, px)
            self.current_holding_pnl_pct = (px - self.entry_px) / self.entry_px
        else:
            self.low_px = min(self.low_px, px)
            self.current_holding_pnl_pct = (self.entry_px - px) / self.entry_px
    
    def check_stops(self, px):
        """返回止损类型或None"""
        if self.pos == 0: return None
        if self.pos_type == 'long':
            loss = (self.entry_px - px) / self.entry_px
            # 固定止损 8%
            if loss >= 0.08: return 'STOP_8'
            # 移动止盈: 15%后回撤50%止盈
            if self.high_px > 0:
                gain = (self.high_px - self.entry_px) / self.entry_px
                if gain >= 0.15:
                    retrace = (self.high_px - px) / self.high_px
                    if retrace >= 0.30: return 'TRAIL_PROFIT_30'
            # 移动止损: 盈利>5%后,回撤10%退出
            if self.high_px > 0:
                gain = (self.high_px - self.entry_px) / self.entry_px
                if gain >= 0.05:
                    retrace = (self.high_px - px) / self.high_px
                    if retrace >= 0.10: return 'TRAIL_10'
        else:
            loss = (px - self.entry_px) / self.entry_px
            if loss >= 0.08: return 'STOP_8'
            if self.low_px < float('inf'):
                gain = (self.entry_px - self.low_px) / self.entry_px
                if gain >= 0.15:
                    retrace = (px - self.low_px) / self.low_px
                    if retrace >= 0.30: return 'TRAIL_PROFIT_30'
            if self.low_px < float('inf'):
                gain = (self.entry_px - self.low_px) / self.entry_px
                if gain >= 0.05:
                    retrace = (px - self.low_px) / self.low_px
                    if retrace >= 0.10: return 'TRAIL_10'
        return None
    
    def should_close(self, sig):
        if self.pos == 0: return False
        if self.pos_type == 'long' and sig == 'STRONG_SELL': return True
        if self.pos_type == 'short' and sig == 'STRONG_BUY': return True
        return False
    
    def update_eq(self, date, px):
        self.update(px)
        pv = self.pos * px if self.pos > 0 else 0
        self.eq.append({
            'date': date.strftime('%Y-%m-%d'),
            'cap': self.cap, 'pv': pv,
            'total': self.cap + pv, 'close': px
        })
    
    def new_day(self, date):
        total = self.cap + (self.pos * self.eq[-1]['close'] if self.pos > 0 and self.eq else 0)
        self.day_start = total
        self.day_loss_flag = False
    
    def hit_daily_loss(self, px):
        total = self.cap + (self.pos * px if self.pos > 0 else 0)
        return total < self.day_start * (1 - DAILY_LOSS_LIMIT)

# ========== 主程序 ==========
def run():
    print("="*70)
    print("  24H策略 V4 - 最终优化版")
    print("  止盈止损: 8%固定止损 / 5%盈利后10%移动止损 / 15%盈利后30%移动止盈")
    print("  日亏损: 超过5%暂停开新仓(不平仓)")
    print("="*70)
    
    # 数据
    print(f"\n[1/5] 获取 {SYMBOL} 历史数据...")
    cache = "/tmp/binance_BTCUSDT_1y.json"
    if os.path.exists(cache):
        with open(cache) as f: raw = json.load(f)
    else:
        raw = get_binance_klines(SYMBOL, INTERVAL, START_DATE, END_DATE)
        if raw:
            with open(cache,'w') as f: json.dump(raw,f)
    if not raw: print("数据失败"); return
    
    df = parse_klines(raw)
    print(f"  {len(df)} 根K线")
    
    # 指标
    print("\n[2/5] 计算指标...")
    df['pct24'] = df['close'].pct_change(24)*100
    df['rsi'] = calc_rsi(df['close'],14)
    df['macd'],df['macd_s'],df['macd_h'] = calc_macd(df['close'])
    df['bb_u'],df['bb_l'],df['bb_pos'] = calc_bb(df['close'])
    df['ema20'] = calc_ema(df['close'],20)
    df['ema60'] = calc_ema(df['close'],60)
    df['ema200'] = calc_ema(df['close'],200)
    df['vol'] = df['close'].pct_change().rolling(14).std()*100
    df['vol_ch'] = df['volume'].pct_change().rolling(14).mean()*100
    df['fg'] = df.apply(lambda r: calc_fg(r['vol'],r['vol_ch']), axis=1)
    df = df.dropna(subset=['rsi','macd','bb_pos','ema20','ema60','ema200'])
    print(f"  有效数据: {len(df)}")
    
    # 信号
    print("\n[3/5] 生成信号...")
    sigs = []
    for i in range(200, len(df)):
        row = df.iloc[i]
        s = gen_signal(row)
        s['ts'] = row.name; s['close'] = row['close']
        sigs.append(s)
    
    df_s = pd.DataFrame(sigs)
    
    for s in ['STRONG_BUY','BUY','NEUTRAL','SELL','STRONG_SELL']:
        c = (df_s['signal']==s).sum()
        print(f"  {s:12s}: {c:5d} ({c/len(df_s)*100:5.1f}%)")
    
    # 模拟
    print("\n[4/5] 运行模拟...")
    sim = SimV4()
    cur_date = None
    
    for _, row in df_s.iterrows():
        ts = row['ts']; px = row['close']; sig = row['signal']
        
        if cur_date != ts.date():
            if cur_date is not None: sim.new_day(ts)
            cur_date = ts.date()
        
        # 日亏损检查
        if sim.hit_daily_loss(px):
            sim.day_loss_flag = True
        
        sim.update_eq(ts, px)
        
        # 止损
        if sim.pos > 0:
            stop = sim.check_stops(px)
            if stop:
                sim.close_pos(stop, px, ts)
                continue
        
        # 开平仓
        if sim.pos == 0:
            if not sim.day_loss_flag:
                if sig in ['STRONG_BUY','BUY']: sim.open_pos(sig, px, ts)
                elif sig in ['STRONG_SELL','SELL']: sim.open_pos(sig, px, ts)
        else:
            if sim.should_close(sig): sim.close_pos('SIGNAL_REVERSE', px, ts)
    
    if sim.pos > 0:
        sim.close_pos('END', df_s.iloc[-1]['close'], df_s.iloc[-1]['ts'])
    
    print("\n[5/5] 生成报告...")
    
    eq = pd.DataFrame(sim.eq)
    trades = pd.DataFrame(sim.trades)
    closes = trades[trades['type'].str.startswith('CLOSE_')] if len(trades) else pd.DataFrame()
    
    final = sim.cap + (eq.iloc[-1]['pv'] if len(eq) else 0)
    total_ret = (final-INITIAL_CAPITAL)/INITIAL_CAPITAL*100
    total_pnl = final - INITIAL_CAPITAL
    
    if len(closes) > 0:
        wr = sim.win_t/(sim.win_t+sim.lose_t)*100 if sim.win_t+sim.lose_t > 0 else 0
        avg_w = closes[closes['pnl']>0]['pnl'].mean()
        avg_l = closes[closes['pnl']<0]['pnl'].mean()
        pf = abs(closes[closes['pnl']>0]['pnl'].sum()/closes[closes['pnl']<0]['pnl'].sum()) if closes[closes['pnl']<0]['pnl'].sum() != 0 else 0
        n_t = len(closes)
        n_long = len(closes[closes['type']=='CLOSE_LONG'])
        n_short = len(closes[closes['type']=='CLOSE_SHORT'])
        avg_h = closes['hold_h'].mean() if 'hold_h' in closes.columns else 0
        stop_n = closes[closes['reason'].str.startswith('STOP')|closes['reason'].str.startswith('TRAIL')].groupby(
            closes[closes['reason'].str.startswith('STOP')|closes['reason'].str.startswith('TRAIL')]['reason'].str.split('_').str[0]
        ).size().to_dict() if len(closes) > 0 else {}
    else:
        wr=avg_w=avg_l=pf=n_t=n_long=n_short=avg_h=0
        stop_n = {}
    
    if len(eq) > 0:
        eq['peak'] = eq['total'].cummax()
        eq['dd'] = (eq['total']-eq['peak'])/eq['peak']*100
        max_dd = abs(eq['dd'].min())
        days = len(eq)
        ann = ((final/INITIAL_CAPITAL)**(365/days)-1)*100 if days>0 else 0
        rets = eq['total'].pct_change().dropna()
        sharpe = rets.mean()/rets.std()*np.sqrt(365) if rets.std()>0 else 0
    else:
        max_dd=ann=sharpe=0
    
    ds = eq.groupby('date').agg({'total':'last'}).reset_index()
    ds['dr'] = ds['total'].pct_change()*100
    td = len(ds)
    pd_d = (ds['dr']>0).sum()
    ld_d = (ds['dr']<0).sum()
    wr_d = pd_d/td*100 if td>0 else 0
    bd = ds['dr'].max() if len(ds)>0 else 0
    wd = ds['dr'].min() if len(ds)>0 else 0
    
    print(f"""
{'='*70}
              📊 回测报告 V4 - 最终优化版 (币安1年)
{'='*70}

┌─ 【账户概览】 ──────────────────────────────────────────────────────────────
│  初始资金:        ${INITIAL_CAPITAL:,.2f}
│  最终权益:        ${final:,.2f}
│  总收益:          ${total_pnl:,.2f}
│  总收益率:        {total_ret:.2f}%
│  年化收益率:      {ann:.2f}%
│  夏普比率:        {sharpe:.2f}
│  最大回撤:        {max_dd:.2f}%
└──────────────────────────────────────────────────────────────────────────────

┌─ 【交易统计】 ──────────────────────────────────────────────────────────────
│  总交易次数:      {n_t}
│  做多次数:        {n_long}    做空次数: {n_short}
│  胜率:            {wr:.2f}%
│  平均盈利:        ${avg_w:,.2f}
│  平均亏损:        ${avg_l:,.2f}
│  盈亏比:          {pf:.2f}
│  盈利交易:        {sim.win_t}    亏损交易: {sim.lose_t}
│  平均持仓:        {avg_h:.1f} 小时
└──────────────────────────────────────────────────────────────────────────────

┌─ 【日度统计】 ──────────────────────────────────────────────────────────────
│  盈利天数:        {pd_d} / {td}
│  亏损天数:        {ld_d}
│  日胜率:          {wr_d:.2f}%
│  最佳单日:        {bd:+.2f}%
│  最差单日:        {wd:+.2f}%
└──────────────────────────────────────────────────────────────────────────────

┌─ 【风控机制】 ──────────────────────────────────────────────────────────────
│  固定止损:        8%  (反手退出)
│  移动止损:        盈利>5%后回撤10%退出
│  移动止盈:        盈利>15%后回撤30%退出
│  日亏损:          超过5%暂停开仓(不平仓)
└──────────────────────────────────────────────────────────────────────────────
""")
    
    # 平仓原因
    if len(closes) > 0:
        print("┌─ 【平仓原因】 ──────────────────────────────────────────────────────────────")
        for r,cnt in closes['reason'].value_counts().items():
            print(f"│  {r:22s}: {cnt:3d} ({cnt/len(closes)*100:5.1f}%)")
        print(f"└{'─'*69}")
    
    # 月度
    print("┌─ 【月度收益】 ──────────────────────────────────────────────────────────────")
    eq['month'] = eq['date'].str[:7]
    mo = eq.groupby('month').agg({'total':['first','last']})
    mo.columns = ['s','e']; mo['r'] = (mo['e']-mo['s'])/mo['s']*100
    for m,row in mo.iterrows():
        r=row['r']; c='🟢' if r>=0 else '🔴'
        print(f"│  {m}: {'+' if r>=0 else ''}{r:6.2f}%  {c}")
    print(f"└{'─'*69}")
    
    # 保存
    od = '/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/backtest_results'
    os.makedirs(od, exist_ok=True)
    eq.to_csv(f'{od}/equity_v4.csv', index=False)
    trades.to_csv(f'{od}/trades_v4.csv', index=False)
    df_s.to_csv(f'{od}/signals_v4.csv', index=False)
    with open(f'{od}/summary_v4.json','w') as f:
        json.dump({
            'initial': INITIAL_CAPITAL, 'final': final,
            'total_return_pct': total_ret, 'annual_return_pct': ann,
            'sharpe': sharpe, 'max_drawdown_pct': max_dd,
            'total_trades': n_t, 'win_rate': wr, 'profit_factor': pf
        }, f, indent=2)
    
    print(f"\n📁 V4数据已保存: {od}/")

if __name__ == '__main__':
    run()
