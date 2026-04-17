#!/usr/bin/env python3
"""
Polymarket式24H策略 V3 - 校准版
修复V2信号过少、止损过频的问题
"""

import pandas as pd
import numpy as np
import requests
import json
import time
import os
from datetime import datetime

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
    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': int(pd.Timestamp(start_str).timestamp() * 1000),
        'limit': limit
    }
    if end_str:
        params['endTime'] = int(pd.Timestamp(end_str).timestamp() * 1000)
    
    all_klines = []
    while True:
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            if isinstance(data, dict) and 'code' in data:
                break
            all_klines.extend(data)
            if len(data) < limit:
                break
            params['startTime'] = int(data[-1][0]) + 1
            time.sleep(0.2)
        except:
            break
    return all_klines

def parse_klines(klines):
    df = pd.DataFrame(klines, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
        df[col] = df[col].astype(float)
    return df.set_index('open_time')

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line

def calculate_bollinger_bands(prices, period=20):
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    position = (prices - lower) / (upper - lower + 1e-10)
    return upper, lower, position

def calculate_ema(prices, period):
    return prices.ewm(span=period, adjust=False).mean()

# ========== V3 信号生成 ==========
def generate_signal_v3(row):
    """
    V3: 更宽松的阈值 + 合理止损
    核心改动:
    - composite 55+ 是BUY, 45- 是SELL
    - 取消过度严格的共振要求
    - 趋势过滤作为软过滤而非硬过滤
    """
    close = row['close']
    rsi = row['rsi']
    macd = row['macd']
    macd_signal = row['macd_signal']
    macd_hist = row['macd_hist']
    bb_pos = row['bb_position']
    ema20 = row['ema20']
    ema60 = row['ema60']
    ema200 = row['ema200']
    price_change_24h = row['price_change_24h_pct']
    volatility = row['volatility']
    fear_greed = row['fear_greed']
    
    # 趋势判断
    if close > ema200 and ema20 > ema60:
        trend = 'bullish'
    elif close < ema200 and ema20 < ema60:
        trend = 'bearish'
    else:
        trend = 'neutral'
    
    # RSI打分 (0-100)
    if rsi < 25:
        rsi_score = 100
    elif rsi < 30:
        rsi_score = 85
    elif rsi < 35:
        rsi_score = 72
    elif rsi < 40:
        rsi_score = 62
    elif rsi < 45:
        rsi_score = 55
    elif rsi < 50:
        rsi_score = 52
    elif rsi < 55:
        rsi_score = 48
    elif rsi < 60:
        rsi_score = 42
    elif rsi < 65:
        rsi_score = 35
    elif rsi < 70:
        rsi_score = 25
    elif rsi < 75:
        rsi_score = 15
    else:
        rsi_score = 5
    
    # MACD打分
    if macd > macd_signal and macd_hist > 0:
        macd_score = 85
    elif macd > macd_signal:
        macd_score = 68
    elif macd > 0:
        macd_score = 55
    elif macd < macd_signal and macd_hist < 0:
        macd_score = 15
    elif macd < 0:
        macd_score = 32
    else:
        macd_score = 45
    
    # 布林带打分
    if bb_pos < 10:
        bb_score = 100
    elif bb_pos < 20:
        bb_score = 82
    elif bb_pos < 30:
        bb_score = 68
    elif bb_pos < 40:
        bb_score = 58
    elif bb_pos < 50:
        bb_score = 50
    elif bb_pos < 60:
        bb_score = 42
    elif bb_pos < 70:
        bb_score = 32
    elif bb_pos < 80:
        bb_score = 18
    elif bb_pos < 90:
        bb_score = 8
    else:
        bb_score = 2
    
    # 动量打分
    if price_change_24h > 5:
        mom_score = 88
    elif price_change_24h > 3:
        mom_score = 75
    elif price_change_24h > 1.5:
        mom_score = 63
    elif price_change_24h > 0.5:
        mom_score = 55
    elif price_change_24h > 0:
        mom_score = 50
    elif price_change_24h > -0.5:
        mom_score = 45
    elif price_change_24h > -1.5:
        mom_score = 37
    elif price_change_24h > -3:
        mom_score = 25
    elif price_change_24h > -5:
        mom_score = 12
    else:
        mom_score = 5
    
    # 技术综合分
    tech_score = int(rsi_score * 0.25 + macd_score * 0.25 + bb_score * 0.25 + mom_score * 0.25)
    
    # 情绪分
    if fear_greed < 20:
        emotion_score = 95
    elif fear_greed < 30:
        emotion_score = 78
    elif fear_greed < 40:
        emotion_score = 65
    elif fear_greed < 50:
        emotion_score = 55
    elif fear_greed < 60:
        emotion_score = 45
    elif fear_greed < 70:
        emotion_score = 32
    elif fear_greed < 80:
        emotion_score = 18
    else:
        emotion_score = 8
    
    # 综合评分
    composite = int(tech_score * 0.65 + emotion_score * 0.35)
    
    # 信号阈值
    if composite >= 70:
        raw_signal = 'STRONG_BUY'
    elif composite >= 55:
        raw_signal = 'BUY'
    elif composite <= 30:
        raw_signal = 'STRONG_SELL'
    elif composite <= 45:
        raw_signal = 'SELL'
    else:
        raw_signal = 'NEUTRAL'
    
    # 趋势软过滤: 震荡市场时降低信号强度但不完全阻止
    if trend == 'neutral':
        # 震荡市场时, 只在极端信号时交易
        if raw_signal == 'STRONG_BUY':
            raw_signal = 'BUY'
        elif raw_signal == 'STRONG_SELL':
            raw_signal = 'SELL'
    
    return {
        'signal': raw_signal,
        'trend': trend,
        'composite': composite,
        'tech_score': tech_score,
        'emotion_score': emotion_score,
        'rsi': rsi,
        'macd': macd,
        'bb_position': bb_pos,
        'fear_greed': fear_greed,
        'price_change_24h_pct': price_change_24h,
        'close': close
    }

# ========== 交易模拟器 ==========
class TradingSimV3:
    def __init__(self):
        self.capital = INITIAL_CAPITAL
        self.max_position = MAX_POSITION
        self.position = 0
        self.position_type = None
        self.entry_price = 0
        self.highest_price = 0
        self.lowest_price = float('inf')
        self.trades = []
        self.equity_curve = []
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0
        self.daily_start_capital = INITIAL_CAPITAL
        self.daily_loss_used = False
        
    def open_position(self, signal, price, timestamp):
        if self.position != 0:
            return
        
        position_value = min(self.max_position, self.capital * 0.5)
        shares = position_value / price
        
        if signal in ['STRONG_BUY', 'BUY']:
            self.position_type = 'long'
            cost = shares * price * (1 + TRADE_FEE)
            if cost <= self.capital:
                self.position = shares
                self.entry_price = price
                self.entry_timestamp = timestamp
                self.highest_price = price
                self.capital -= cost
                self.trades.append({
                    'timestamp': timestamp, 'type': 'OPEN_LONG',
                    'price': price, 'shares': shares, 'value': position_value,
                    'signal': signal
                })
        elif signal in ['STRONG_SELL', 'SELL']:
            self.position_type = 'short'
            proceeds = shares * price * (1 - TRADE_FEE)
            self.position = shares
            self.entry_price = price
            self.entry_timestamp = timestamp
            self.lowest_price = price
            self.capital += proceeds
            self.trades.append({
                'timestamp': timestamp, 'type': 'OPEN_SHORT',
                'price': price, 'shares': shares, 'value': position_value,
                'signal': signal
            })
    
    def close_position(self, reason, price, timestamp):
        if self.position == 0:
            return
        
        shares = self.position
        if self.position_type == 'long':
            proceeds = shares * price * (1 - TRADE_FEE)
            pnl = proceeds - (shares * self.entry_price * (1 + TRADE_FEE))
            self.capital += proceeds
        else:
            cost = shares * price * (1 + TRADE_FEE)
            pnl = (shares * self.entry_price * (1 - TRADE_FEE)) - cost
            self.capital -= cost
        
        self.total_pnl += pnl
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        holding_hours = (timestamp - self.entry_timestamp).total_seconds() / 3600 if self.entry_timestamp else 0
        
        self.trades.append({
            'timestamp': timestamp, 'type': f'CLOSE_{self.position_type.upper()}',
            'price': price, 'shares': shares, 'pnl': pnl,
            'reason': reason, 'capital_after': self.capital,
            'holding_hours': holding_hours
        })
        
        self.position = 0
        self.position_type = None
        self.entry_price = 0
        self.highest_price = 0
        self.lowest_price = float('inf')
    
    def update_position(self, price):
        if self.position == 0:
            return
        if self.position_type == 'long':
            self.highest_price = max(self.highest_price, price)
        else:
            self.lowest_price = min(self.lowest_price, price)
    
    def check_stops(self, price):
        if self.position == 0:
            return None
        
        if self.position_type == 'long':
            loss_pct = (self.entry_price - price) / self.entry_price
            # 止损6%
            if loss_pct >= 0.06:
                return 'STOP_LOSS_6'
            # 移动止损: 从最高回撤12%
            if self.highest_price > 0:
                drawback = (self.highest_price - price) / self.highest_price
                if drawback >= 0.12 and (self.highest_price - self.entry_price) / self.entry_price > 0.03:
                    return 'TRAILING_12'
        else:
            loss_pct = (price - self.entry_price) / self.entry_price
            if loss_pct >= 0.06:
                return 'STOP_LOSS_6'
            if self.lowest_price < float('inf'):
                drawback = (price - self.lowest_price) / self.lowest_price
                if drawback >= 0.12 and (self.entry_price - self.lowest_price) / self.entry_price > 0.03:
                    return 'TRAILING_12'
        return None
    
    def should_close(self, signal):
        if self.position == 0:
            return False
        if self.position_type == 'long' and signal == 'STRONG_SELL':
            return True
        if self.position_type == 'short' and signal == 'STRONG_BUY':
            return True
        return False
    
    def update_daily(self, date, close_price):
        self.update_position(close_price)
        pos_val = self.position * close_price if self.position > 0 else 0
        self.equity_curve.append({
            'date': date.strftime('%Y-%m-%d'),
            'capital': self.capital,
            'position_value': pos_val,
            'total_equity': self.capital + pos_val,
            'close': close_price
        })
    
    def new_day(self, date):
        total = self.capital + (self.position * self.equity_curve[-1]['close'] if self.position > 0 and self.equity_curve else 0)
        self.daily_start_capital = total
        self.daily_loss_used = False
    
    def check_daily_loss(self):
        if len(self.equity_curve) == 0:
            return False
        total = self.capital + (self.position * self.equity_curve[-1]['close'] if self.position > 0 else 0)
        return total < self.daily_start_capital * (1 - DAILY_LOSS_LIMIT)

# ========== 主程序 ==========
def run():
    print("=" * 70)
    print("24H策略 V3 - 校准版 (修复止损过频)")
    print("=" * 70)
    print(f"初始资金: ${INITIAL_CAPITAL:,.2f} | 最大仓位: ${MAX_POSITION:,.2f}")
    print(f"止损: 6%固定 + 12%移动止损(盈利>3%后启用)")
    print("=" * 70)
    
    # 数据
    print(f"\n[1/5] 获取 {SYMBOL} 历史K线...")
    cache = "/tmp/binance_BTCUSDT_1y.json"
    if os.path.exists(cache):
        with open(cache) as f:
            raw = json.load(f)
    else:
        raw = get_binance_klines(SYMBOL, INTERVAL, START_DATE, END_DATE)
        if raw:
            with open(cache, 'w') as f:
                json.dump(raw, f)
    if not raw:
        print("数据获取失败"); return
    
    df = parse_klines(raw)
    print(f"  {len(df)} 根K线")
    
    # 指标计算
    print("\n[2/5] 计算指标...")
    df['price_change_24h_pct'] = df['close'].pct_change(24) * 100
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df['close'])
    df['bb_upper'], df['bb_lower'], df['bb_position'] = calculate_bollinger_bands(df['close'])
    df['ema20'] = calculate_ema(df['close'], 20)
    df['ema60'] = calculate_ema(df['close'], 60)
    df['ema200'] = calculate_ema(df['close'], 200)
    
    df['volatility'] = df['close'].pct_change().rolling(14).std() * 100
    df['vol_change'] = df['volume'].pct_change().rolling(14).mean() * 100
    def calc_fg(vol, vc):
        vol = vol if pd.notna(vol) else 3
        vc = vc if pd.notna(vc) else 0
        if vol > 8: fg = max(10, 50 - (vol-5)*4)
        elif vol < 2: fg = min(90, 50 + (3-vol)*10)
        else: fg = 50
        if vc > 30: fg = min(100, fg+10)
        elif vc < -30: fg = max(0, fg-10)
        return int(np.clip(fg, 0, 100))
    df['fear_greed'] = df.apply(lambda r: calc_fg(r['volatility'], r['vol_change']), axis=1)
    df = df.dropna(subset=['rsi','macd','bb_position','ema20','ema60','ema200'])
    print(f"  有效数据: {len(df)}")
    
    # 信号
    print("\n[3/5] 生成信号...")
    signals = []
    for i in range(200, len(df)):
        row = df.iloc[i]
        sig = generate_signal_v3(row)
        sig['timestamp'] = row.name
        sig['close'] = row['close']
        signals.append(sig)
    
    df_s = pd.DataFrame(signals)
    
    print("  信号分布:")
    for s in ['STRONG_BUY','BUY','NEUTRAL','SELL','STRONG_SELL']:
        c = (df_s['signal']==s).sum()
        pct = c/len(df_s)*100
        print(f"    {s:12s}: {c:5d} ({pct:5.1f}%)")
    
    # 模拟
    print("\n[4/5] 运行模拟...")
    sim = TradingSimV3()
    current_date = None
    
    for _, row in df_s.iterrows():
        ts = row['timestamp']
        price = row['close']
        sig = row['signal']
        
        if current_date != ts.date():
            if current_date is not None:
                sim.new_day(ts)
            current_date = ts.date()
        
        if sim.check_daily_loss():
            if sim.position != 0:
                sim.close_position('DAILY_LOSS', price, ts)
            sim.daily_loss_used = True
        
        sim.update_daily(ts, price)
        
        # 止损
        if sim.position > 0:
            stop = sim.check_stops(price)
            if stop:
                sim.close_position(stop, price, ts)
                continue
        
        # 开平仓
        if sim.position == 0:
            if sig in ['STRONG_BUY','BUY']:
                sim.open_position(sig, price, ts)
            elif sig in ['STRONG_SELL','SELL']:
                sim.open_position(sig, price, ts)
        elif sim.should_close(sig):
            sim.close_position('SIGNAL_REVERSE', price, ts)
    
    if sim.position > 0:
        sim.close_position('END', df_s.iloc[-1]['close'], df_s.iloc[-1]['timestamp'])
    
    print("\n[5/5] 生成报告...")
    
    # 报告
    eq = pd.DataFrame(sim.equity_curve)
    trades = pd.DataFrame(sim.trades)
    
    closes = trades[trades['type'].str.startswith('CLOSE_')] if len(trades) else pd.DataFrame()
    
    final = sim.capital + (eq.iloc[-1]['position_value'] if len(eq) else 0)
    total_ret = (final - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    total_pnl = final - INITIAL_CAPITAL
    
    if len(closes) > 0:
        wr = sim.winning_trades / (sim.winning_trades + sim.losing_trades) * 100 if sim.winning_trades + sim.losing_trades > 0 else 0
        avg_win = closes[closes['pnl']>0]['pnl'].mean()
        avg_loss = closes[closes['pnl']<0]['pnl'].mean()
        pf = abs(closes[closes['pnl']>0]['pnl'].sum() / closes[closes['pnl']<0]['pnl'].sum()) if closes[closes['pnl']<0]['pnl'].sum() != 0 else 0
        total_trades = len(closes)
        long_t = len(closes[closes['type']=='CLOSE_LONG'])
        short_t = len(closes[closes['type']=='CLOSE_SHORT'])
        avg_hold = closes['holding_hours'].mean() if 'holding_hours' in closes.columns else 0
        
        stops = closes[closes['reason'].str.contains('STOP', na=False)]
        stop_count = len(stops)
    else:
        wr=avg_win=avg_loss=pf=total_trades=long_t=short_t=avg_hold=stop_count=0
    
    # 回撤
    if len(eq) > 0:
        eq['peak'] = eq['total_equity'].cummax()
        eq['dd'] = (eq['total_equity'] - eq['peak']) / eq['peak'] * 100
        max_dd = abs(eq['dd'].min())
        days = len(eq)
        ann_ret = ((final/INITIAL_CAPITAL)**(365/days)-1)*100 if days > 0 else 0
        rets = eq['total_equity'].pct_change().dropna()
        sharpe = rets.mean()/rets.std()*np.sqrt(365) if rets.std() > 0 else 0
    else:
        max_dd=ann_ret=sharpe=0
    
    # 日统计
    ds = eq.groupby('date').agg({'total_equity':'last','close':'last'}).reset_index()
    ds['dr'] = ds['total_equity'].pct_change()*100
    td = len(ds)
    pd_days = (ds['dr']>0).sum()
    ld_days = (ds['dr']<0).sum()
    wr_d = pd_days/td*100 if td>0 else 0
    bd = ds['dr'].max() if len(ds)>0 else 0
    wd = ds['dr'].min() if len(ds)>0 else 0
    
    print(f"""
{'='*70}
              📊 回测报告 V3 - 校准版 (币安1年)
{'='*70}

┌─ 【基本信息】 ─────────────────────────────────────────────────────────────
│  标的: {SYMBOL}  周期: {df_s.iloc[0]['timestamp'].strftime('%Y-%m-%d')} ~ {df_s.iloc[-1]['timestamp'].strftime('%Y-%m-%d')}
│  有效K线: {len(df_s):,}  交易日: {td}
└──────────────────────────────────────────────────────────────────────────────

┌─ 【账户概览】 ──────────────────────────────────────────────────────────────
│  初始资金:        ${INITIAL_CAPITAL:,.2f}
│  最终权益:        ${final:,.2f}
│  总收益:          ${total_pnl:,.2f}
│  总收益率:        {total_ret:.2f}%
│  年化收益率:      {ann_ret:.2f}%
│  夏普比率:        {sharpe:.2f}
│  最大回撤:        {max_dd:.2f}%
└──────────────────────────────────────────────────────────────────────────────

┌─ 【交易统计】 ──────────────────────────────────────────────────────────────
│  总交易次数:      {total_trades}
│  做多次数:        {long_t}    做空次数: {short_t}
│  胜率:            {wr:.2f}%
│  平均盈利:        ${avg_win:,.2f}
│  平均亏损:        ${avg_loss:,.2f}
│  盈亏比:          {pf:.2f}
│  盈利交易:        {sim.winning_trades}    亏损交易: {sim.losing_trades}
│  止损触发:        {stop_count} 次
│  平均持仓:        {avg_hold:.1f} 小时
└──────────────────────────────────────────────────────────────────────────────

┌─ 【日度统计】 ──────────────────────────────────────────────────────────────
│  盈利天数:        {pd_days} / {td}
│  亏损天数:        {ld_days}
│  日胜率:          {wr_d:.2f}%
│  最佳单日:        {bd:+.2f}%
│  最差单日:        {wd:+.2f}%
└──────────────────────────────────────────────────────────────────────────────
""")
    
    print("┌─ 【月度收益】 ──────────────────────────────────────────────────────────────")
    eq['month'] = eq['date'].str[:7]
    mo = eq.groupby('month').agg({'total_equity':['first','last']})
    mo.columns = ['s','e']
    mo['r'] = (mo['e']-mo['s'])/mo['s']*100
    for m,row in mo.iterrows():
        r=row['r']; c='🟢' if r>=0 else '🔴'; s='+'
        print(f"│  {m}: {s if r>=0 else ''}{r:6.2f}%  {c}")
    print(f"└{'─'*69}")
    
    if len(closes) > 0:
        print("┌─ 【平仓原因】 ──────────────────────────────────────────────────────────────")
        for r,cnt in closes['reason'].value_counts().items():
            pct = cnt/len(closes)*100
            print(f"│  {r:20s}: {cnt:3d} ({pct:5.1f}%)")
        print(f"└{'─'*69}")
    
    # 保存
    odir = '/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/backtest_results'
    os.makedirs(odir, exist_ok=True)
    eq.to_csv(f'{odir}/equity_v3.csv', index=False)
    trades.to_csv(f'{odir}/trades_v3.csv', index=False)
    df_s.to_csv(f'{odir}/signals_v3.csv', index=False)
    
    with open(f'{odir}/summary_v3.json','w') as f:
        json.dump({
            'initial': INITIAL_CAPITAL, 'final': final,
            'total_return_pct': total_ret, 'annual_return_pct': ann_ret,
            'sharpe': sharpe, 'max_drawdown_pct': max_dd,
            'total_trades': total_trades, 'win_rate': wr,
            'profit_factor': pf
        }, f, indent=2)
    
    print(f"\n📁 数据已保存: {odir}/")

if __name__ == '__main__':
    run()
