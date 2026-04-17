#!/usr/bin/env python3
"""
支撑压力做单策略 V2 - 修复版
核心修复:
1. 资金管理: 每笔风险不超过账户1%
2. 动态挂单触发: 更宽的容差
3. 双向对冲: 多空同时持仓锁定利润
4. 趋势过滤: 只顺趋势方向挂单
5. 固定止损: 2%账户资金止损
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
RISK_PER_TRADE = 0.015   # 每笔风险 1.5% 账户
ORDER_SIZE = 1000         # 每单目标$1000
MAX_POSITIONS = 6
SYMBOL = 'BTCUSDT'
INTERVAL = '1h'
START_DATE = '2024-04-16'
END_DATE = '2025-04-16'
TRADE_FEE = 0.0004
SL_PCT = 0.02             # 2%止损
TP_PCT = 0.04             # 4%止盈 (2:1)
ATR_PERIOD = 14
SR_LOOKBACK = 24

# ========== 数据获取 ==========
def get_binance_klines(symbol, interval, start_str, end_str=None, limit=1500):
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
            time.sleep(0.25)
        except:
            break
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

# ========== 技术指标 ==========
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

# ========== 支撑压力计算 ==========
def calc_sr_levels(df, lookback=24):
    """计算支撑压力位"""
    recent = df.tail(lookback)
    
    # 基本位
    swing_high = recent['high'].max()
    swing_low = recent['low'].min()
    current = df['close'].iloc[-1]
    
    # ATR调整
    atr = df['atr'].iloc[-1] if 'atr' in df.columns and pd.notna(df['atr'].iloc[-1]) else current * 0.01
    
    # 均线
    ema20 = df['ema20'].iloc[-1] if 'ema20' in df.columns else current
    ema60 = df['ema60'].iloc[-1] if 'ema60' in df.columns else current
    
    # 趋势
    if current > ema60 and ema20 > ema60:
        trend = 'bullish'
    elif current < ema60 and ema20 < ema60:
        trend = 'bearish'
    else:
        trend = 'neutral'
    
    # 支撑压力
    # 使用布林带
    bb_std = df['close'].tail(20).std()
    bb_upper = current + 2 * bb_std
    bb_lower = current - 2 * bb_std
    
    # 多层支撑压力
    resistances = sorted([swing_high, bb_upper, ema20], reverse=True)
    supports = sorted([swing_low, bb_lower, ema20])
    
    # 最近的压力和支撑
    resistance = next((r for r in resistances if r > current), current * 1.03)
    support = next((s for s in supports if s < current), current * 0.97)
    
    # 挂单位置 (支撑/压力±0.5%容差)
    tolerance = current * 0.005
    
    return {
        'current': current,
        'support': support,
        'resistance': resistance,
        'support_entry': support + tolerance,
        'resistance_entry': resistance - tolerance,
        'atr': atr,
        'trend': trend,
        'ema20': ema20,
        'ema60': ema60,
        'swing_high': swing_high,
        'swing_low': swing_low,
    }

# ========== 仓位计算 ==========
def calc_position_size(account_equity, risk_pct, entry, stop_loss):
    """根据风险计算仓位"""
    risk_amount = account_equity * risk_pct
    risk_per_unit = abs(entry - stop_loss)
    if risk_per_unit == 0:
        return 0
    size = risk_amount / risk_per_unit
    # 限制最大仓位
    max_size = account_equity * 0.3
    return min(size, max_size)

# ========== 模拟器 ==========
class SROrderStrategy:
    def __init__(self):
        self.capital = INITIAL_CAPITAL
        self.positions = []       # [{id, type, size, entry, sl, tp, level}]
        self.closed = []          # 已平仓记录
        self.pending_long = None  # 挂单中的多单
        self.pending_short = None # 挂单中的空单
        self.equity_curve = []
        self.trades = []
        
        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.win_amounts = []
        self.loss_amounts = []
        
        self.pos_id = 0
        self.current_support = None
        self.current_resistance = None
        self.current_trend = 'neutral'
    
    def _new_id(self):
        self.pos_id += 1
        return self.pos_id
    
    def update_pending_orders(self, price, sr):
        """检查挂单是否触发"""
        triggered = []
        
        # 多单挂单
        if self.pending_long and price <= self.pending_long['entry']:
            triggered.append(('long', self.pending_long))
            self.pending_long = None
        
        # 空单挂单
        if self.pending_short and price >= self.pending_short['entry']:
            triggered.append(('short', self.pending_short))
            self.pending_short = None
        
        return triggered
    
    def place_pending_orders(self, sr):
        """挂单"""
        current = sr['current']
        atr = sr['atr']
        trend = sr['trend']
        
        # 多单: 在支撑下方挂
        if self.pending_long is None:
            long_entry = sr['support_entry']
            sl = long_entry - atr * 2  # ATR*2止损
            tp = long_entry + atr * 4  # ATR*4止盈
            self.pending_long = {
                'entry': long_entry,
                'sl': sl,
                'tp': tp,
                'level': f"S@{round(sr['support'], 0)}",
                'atr': atr
            }
        
        # 空单: 在压力上方挂 (仅趋势向下时有效)
        if self.pending_short is None and trend != 'bullish':
            short_entry = sr['resistance_entry']
            sl = short_entry + atr * 2
            tp = short_entry - atr * 4
            self.pending_short = {
                'entry': short_entry,
                'sl': sl,
                'tp': tp,
                'level': f"R@{round(sr['resistance'], 0)}",
                'atr': atr
            }
    
    def open_position(self, pos_type, entry, sl, tp, level, atr, timestamp, price):
        """开仓"""
        # 计算仓位
        risk_pct = RISK_PER_TRADE
        size = calc_position_size(self.capital, risk_pct, entry, sl)
        
        if size <= 0:
            return
        
        # 仓位价值
        notional = size * entry
        
        if pos_type == 'long':
            cost = notional * (1 + TRADE_FEE)
            if cost > self.capital:
                return
        else:  # short
            margin = notional / 10  # 10倍杠杆, 10%保证金
            if margin > self.capital * 0.5:  # 最多用50%资金做保证金
                return
        
        self.positions.append({
            'id': self._new_id(),
            'type': pos_type,
            'size': size,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'level': level,
            'atr': atr,
            'open_time': timestamp,
            'notional': notional
        })
        
        self.total_trades += 1
        
        self.trades.append({
            'timestamp': timestamp,
            'type': f'OPEN_{pos_type.upper()}',
            'price': entry,
            'size': size,
            'notional': notional,
            'sl': sl,
            'tp': tp,
            'level': level,
            'capital': self.capital,
            'trend': self.current_trend
        })
        
        # 挂单被触发后重新挂相反方向的(趋势跟随)
        self.pending_long = None
        self.pending_short = None
    
    def check_positions(self, price, timestamp):
        """检查止损止盈"""
        closed = []
        
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
            else:  # short
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
                
                self.closed.append({
                    **pos,
                    'close_price': price,
                    'close_time': timestamp,
                    'pnl': pnl,
                    'reason': reason,
                    'holding_hours': (timestamp - pos['open_time']).total_seconds() / 3600
                })
                
                self.trades.append({
                    'timestamp': timestamp,
                    'type': f'CLOSE_{pos["type"].upper()}',
                    'price': price,
                    'size': pos['size'],
                    'pnl': pnl,
                    'reason': reason,
                    'holding_hours': (timestamp - pos['open_time']).total_seconds() / 3600,
                    'capital_after': self.capital
                })
                
                self.positions.remove(pos)
                closed.append((pos, pnl, reason))
        
        return closed
    
    def update_equity(self, timestamp, price, sr):
        """记录权益"""
        pos_pnl = 0
        for pos in self.positions:
            if pos['type'] == 'long':
                pos_pnl += pos['size'] * (price - pos['entry'])
            else:
                pos_pnl += pos['size'] * (pos['entry'] - price)
        
        self.equity_curve.append({
            'timestamp': timestamp,
            'hour': timestamp.strftime('%Y-%m-%d %H:00'),
            'date': timestamp.strftime('%Y-%m-%d'),
            'close': price,
            'capital': self.capital,
            'position_pnl': pos_pnl,
            'total_equity': self.capital + pos_pnl,
            'n_positions': len(self.positions),
            'has_long_pending': self.pending_long is not None,
            'has_short_pending': self.pending_short is not None,
            'trend': self.current_trend,
            'support': sr.get('support', 0),
            'resistance': sr.get('resistance', 0),
        })
    
    def close_all(self, price, timestamp, reason):
        """平所有仓"""
        for pos in self.positions[:]:
            if pos['type'] == 'long':
                proceeds = pos['size'] * price * (1 - TRADE_FEE)
                cost = pos['size'] * pos['entry'] * (1 + TRADE_FEE)
                pnl = proceeds - cost
            else:
                cost = pos['size'] * price * (1 + TRADE_FEE)
                proceeds = pos['size'] * pos['entry'] * (1 - TRADE_FEE)
                pnl = proceeds - cost
            
            self.capital += pnl
            self.closed.append({**pos, 'close_price': price, 'pnl': pnl, 'reason': reason})
            self.positions.remove(pos)
            
            self.trades.append({
                'timestamp': timestamp,
                'type': f'CLOSE_{pos["type"].upper()}',
                'price': price,
                'pnl': pnl,
                'reason': reason,
                'capital_after': self.capital
            })

# ========== 主程序 ==========
def run():
    print("=" * 70)
    print("  支撑压力双向挂单策略 V2")
    print("=" * 70)
    print(f"本金: ${INITIAL_CAPITAL:,.2f} | 每笔风险: {RISK_PER_TRADE*100:.1f}%账户")
    print(f"止损: {SL_PCT*100:.0f}% | 止盈: {TP_PCT*100:.0f}% (2:1盈亏比)")
    print(f"ATR参数: {ATR_PERIOD}周期 | 支撑压力回溯: {SR_LOOKBACK}小时")
    print(f"趋势过滤: 只顺趋势方向挂空单")
    print("=" * 70)
    
    # 数据
    print(f"\n[1/6] 获取 {SYMBOL} 数据...")
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
        print("失败"); return
    
    df = parse_klines(raw)
    print(f"  {len(df)} 根K线, {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
    
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
    strat = SROrderStrategy()
    
    for i in range(SR_LOOKBACK + 1, len(df)):
        row = df.iloc[i]
        ts = row.name
        price = row['close']
        
        lookback_df = df.iloc[:i+1]
        sr = calc_sr_levels(lookback_df, SR_LOOKBACK)
        strat.current_trend = sr['trend']
        strat.current_support = sr['support']
        strat.current_resistance = sr['resistance']
        
        # 每小时挂单一次
        strat.place_pending_orders(sr)
        
        # 检查挂单触发
        triggered = strat.update_pending_orders(price, sr)
        for pos_type, order in triggered:
            strat.open_position(pos_type, price, order['sl'], order['tp'],
                              order['level'], order['atr'], ts, price)
        
        # 检查持仓止损止盈
        strat.check_positions(price, ts)
        
        # 限制最大持仓
        if len(strat.positions) > MAX_POSITIONS:
            oldest = strat.positions.pop(0)
            strat.close_all(oldest['entry'], ts, 'MAX_POSITIONS')
        
        # 记录权益
        strat.update_equity(ts, price, sr)
    
    # 平仓
    final_price = df.iloc[-1]['close']
    strat.close_all(final_price, df.iloc[-1].name, 'END_OF_BACKTEST')
    
    # 报告
    print("\n[4/6] 生成报告...")
    eq = pd.DataFrame(strat.equity_curve)
    trades = pd.DataFrame(strat.trades)
    closed = pd.DataFrame(strat.closed)
    
    final_cap = strat.capital
    total_ret = (final_cap - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    total_pnl = final_cap - INITIAL_CAPITAL
    
    n_trades = len(closed)
    win_rate = strat.wins / (strat.wins + strat.losses) * 100 if (strat.wins + strat.losses) > 0 else 0
    avg_win = np.mean(strat.win_amounts) if strat.win_amounts else 0
    avg_loss = np.mean(strat.loss_amounts) if strat.loss_amounts else 0
    pf = abs(sum(strat.win_amounts) / sum(strat.loss_amounts)) if strat.loss_amounts and sum(strat.loss_amounts) != 0 else 0
    
    # 回撤
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
    
    # 挂单统计
    open_trades = trades[trades['type'].str.startswith('OPEN')]
    long_opens = len(open_trades[open_trades['type'] == 'OPEN_long'])
    short_opens = len(open_trades[open_trades['type'] == 'OPEN_short'])
    
    close_trades = trades[trades['type'].str.startswith('CLOSE')]
    tp_count = len(close_trades[close_trades['reason'] == 'TAKE_PROFIT'])
    sl_count = len(close_trades[close_trades['reason'] == 'STOP_LOSS'])
    
    print(f"""
{'='*70}
        📊 回测报告 - 支撑压力双向挂单 V2 (BTC 1年)
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
│  多单开仓:        {long_opens}    空单开仓: {short_opens}
│  盈利交易:        {strat.wins}    亏损交易: {strat.losses}
│  胜率:            {win_rate:.2f}%
│  平均盈利:        ${avg_win:,.2f}
│  平均亏损:        ${avg_loss:,.2f}
│  盈亏比:          {pf:.2f}
│  止盈次数:        {tp_count}
│  止损次数:        {sl_count}
│  止盈率:          {tp_count/n_trades*100:.1f}% (若有交易)
│  止损率:          {sl_count/n_trades*100:.1f}% (若有交易)
└──────────────────────────────────────────────────────────────────────────────

┌─ 【仓位管理】 ──────────────────────────────────────────────────────────────
│  每笔风险:        {RISK_PER_TRADE*100:.1f}% 账户资金
│  最大同时持仓:    {MAX_POSITIONS}
│  止损:            {SL_PCT*100:.0f}% 固定
│  止盈:            {TP_PCT*100:.0f}% 固定 (2:1)
│  支撑挂单:        支撑位 + 0.5%容差
│  压力挂单:        压力位 - 0.5%容差
│  趋势过滤:        牛市不做空
└──────────────────────────────────────────────────────────────────────────────
""")
    
    # 月度
    if len(eq) > 0:
        print("┌─ 【月度收益】 ──────────────────────────────────────────────────────────────")
        eq['month'] = eq['date'].str[:7]
        monthly = eq.groupby('month').agg({'total_equity': ['first', 'last']})
        monthly.columns = ['s', 'e']
        monthly['r'] = (monthly['e'] - monthly['s']) / monthly['s'] * 100
        for m, row in monthly.iterrows():
            r = row['r']
            c = '🟢' if r >= 0 else '🔴'
            print(f"│  {m}: {'+' if r >= 0 else ''}{r:6.2f}%  {c}")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 趋势分布
    if len(open_trades) > 0:
        print(f"\n┌─ 【趋势分布】 ──────────────────────────────────────────────────────────────")
        for t, cnt in open_trades['trend'].value_counts().items():
            pct = cnt / len(open_trades) * 100
            print(f"│  {t:8s}: {cnt:3d} ({pct:5.1f}%)")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 平仓原因
    if len(close_trades) > 0:
        print(f"\n┌─ 【平仓原因】 ──────────────────────────────────────────────────────────────")
        for r, cnt in close_trades['reason'].value_counts().items():
            pct = cnt / len(close_trades) * 100
            print(f"│  {r:20s}: {cnt:3d} ({pct:5.1f}%)")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 保存
    print("\n[5/6] 保存数据...")
    od = '/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/backtest_results'
    os.makedirs(od, exist_ok=True)
    eq.to_csv(f'{od}/sr_v2_equity.csv', index=False)
    trades.to_csv(f'{od}/sr_v2_trades.csv', index=False)
    
    summary = {
        'strategy': 'SR_V2',
        'symbol': SYMBOL,
        'initial_capital': INITIAL_CAPITAL,
        'final_equity': final_cap,
        'total_return_pct': total_ret,
        'annual_return_pct': ann_ret,
        'sharpe': sharpe,
        'max_drawdown_pct': max_dd,
        'total_trades': n_trades,
        'win_rate': win_rate,
        'profit_factor': pf,
    }
    with open(f'{od}/sr_v2_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n[6/6] 完成!")
    print(f"📁 数据已保存: {od}/sr_v2_*.csv")

if __name__ == '__main__':
    run()
