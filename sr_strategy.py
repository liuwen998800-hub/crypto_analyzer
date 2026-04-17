#!/usr/bin/env python3
"""
支撑压力做单策略 - 完整版
- 本金: $10,000 USDT
- 永续合约
- 双向挂单: 支撑位做多 + 压力位做空
- 动态止损止盈 (ATR-based)
- 金字塔+凯莉仓位管理
"""

import pandas as pd
import numpy as np
import requests
import json
import time
import os
from datetime import datetime

# ========== 基础配置 ==========
INITIAL_CAPITAL = 10000
ORDER_SIZE = 1000       # 每单USDT
SYMBOL = 'BTCUSDT'
INTERVAL = '1h'
START_DATE = '2024-04-16'
END_DATE = '2025-04-16'
TRADE_FEE = 0.0004      # 合约手续费 0.04%
FUNDING_RATE = 0.0001  # 资金费率 0.01%

# ========== ATR配置 ==========
ATR_PERIOD = 14
SL_ATR_MULT = 1.5       # 止损: 1.5倍ATR
TP_ATR_MULT = 2.5       # 止盈: 2.5倍ATR
SR_ATR_RANGE = 0.5      # 支撑/压力区间: 0.5倍ATR

# ========== 仓位管理 ==========
USE_KELLY = True        # True=Kelly公式, False=金字塔
KELLY_FRACTION = 0.3   # Kelly结果的启用比例(保守起见)
MAX_PYRAMID = 3         # 金字塔最大加仓次数
PYRAMID_SCALE = 1.5     # 金字塔加仓递减系数

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
                print(f"API Error: {data}")
                break
            all_klines.extend(data)
            if len(data) < limit:
                break
            params['startTime'] = int(data[-1][0]) + 1
            time.sleep(0.25)
        except Exception as e:
            print(f"Error: {e}")
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
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

def calc_ema(p, n):
    return p.ewm(span=n, adjust=False).mean()

def calc_rsi(p, n=14):
    d = p.diff()
    g = d.where(d>0, 0).rolling(n).mean()
    l = (-d.where(d<0, 0)).rolling(n).mean()
    return 100 - (100 / (1 + g / (l + 1e-10)))

def calc_fib_levels(low, high):
    """斐波那契回撤位"""
    diff = high - low
    return {
        's1': high - diff * 0.236,
        's2': high - diff * 0.382,
        's3': high - diff * 0.618,
        'r1': low + diff * 0.236,
        'r2': low + diff * 0.382,
        'r3': low + diff * 0.618,
    }

# ========== 支撑压力计算 (DeepSeek式分析) ==========
def find_support_resistance(df, lookback=20, atr=None):
    """
    找支撑和压力位
    方法:
    1. 前20根K线的最高/最低点
    2. 结合ATR调整
    3. 近期成交密集区
    4. 整数关口
    """
    if atr is None:
        atr = df['close'].std() * 0.02  # 备用ATR
    
    current_price = df['close'].iloc[-1]
    
    # 方法1: 近期高低点
    recent = df.tail(lookback)
    swing_high = recent['high'].max()
    swing_low = recent['low'].min()
    
    # 方法2: 布林带
    bb_sma = df['close'].tail(20).mean()
    bb_std = df['close'].tail(20).std()
    bb_upper = bb_sma + 2 * bb_std
    bb_lower = bb_sma - 2 * bb_std
    
    # 方法3: 均线支撑压力
    ema20 = df['close'].tail(20).mean()
    ema60 = df['close'].tail(60).mean() if len(df) >= 60 else ema20
    
    # 压力位 (多个因素取交集)
    resistance_levels = []
    for level in [swing_high, bb_upper, ema60]:
        if level > current_price:
            resistance_levels.append(level)
    
    # 支撑位
    support_levels = []
    for level in [swing_low, bb_lower, ema60]:
        if level < current_price:
            support_levels.append(level)
    
    # 整数关口
    int_level = round(current_price / 1000) * 1000
    if int_level > current_price:
        resistance_levels.append(int_level)
    else:
        support_levels.append(int_level)
    
    # 取最近的
    resistance = min(resistance_levels) if resistance_levels else current_price * 1.02
    support = max(support_levels) if support_levels else current_price * 0.98
    
    # ATR调整
    if atr > 0:
        # 支撑在支撑位上方一点
        support_entry = support + atr * SR_ATR_RANGE
        # 压力在压力位下方一点
        resistance_entry = resistance - atr * SR_ATR_RANGE
    else:
        support_entry = support
        resistance_entry = resistance
    
    return {
        'support': support,
        'resistance': resistance,
        'support_entry': support_entry,
        'resistance_entry': resistance_entry,
        'atr': atr,
        'current_price': current_price,
        'swing_high': swing_high,
        'swing_low': swing_low
    }

# ========== 动态止损止盈 ==========
def calc_sl_tp(entry_price, position_type, atr, tech_score=None):
    """
    计算动态止损止盈
    - 止损: 根据波动率和方向自适应
    - 止盈: 2:1以上的盈亏比
    """
    if position_type == 'long':
        # 多单: 止损在下, 止盈在上
        sl = entry_price - atr * SL_ATR_MULT
        tp = entry_price + atr * TP_ATR_MULT
    else:
        # 空单: 止损在上, 止盈在下
        sl = entry_price + atr * SL_ATR_MULT
        tp = entry_price - atr * TP_ATR_MULT
    
    # 最小盈亏比 2:1
    risk = abs(entry_price - sl)
    reward = abs(tp - entry_price)
    if reward / risk < 2.0:
        if position_type == 'long':
            tp = entry_price + risk * 2.0
        else:
            tp = entry_price - risk * 2.0
    
    return sl, tp

# ========== Kelly仓位计算 ==========
def kelly_fraction(win_rate, avg_win, avg_loss):
    """
    Kelly公式: f* = (bp - q) / b
    b = avg_win / avg_loss (赔率)
    p = win_rate
    q = 1 - p
    """
    if avg_loss == 0:
        return 0.1  # 默认10%
    b = abs(avg_win / avg_loss)
    q = 1 - win_rate
    kelly = (b * win_rate - q) / b
    
    # Kelly在币圈太激进, 乘以系数
    return max(0.05, min(kelly * KELLY_FRACTION, 0.3))

def pyramid_size(base_size, pyramid_level, max_level=MAX_PYRAMID):
    """
    金字塔加仓: 每加一层减少规模
    """
    scale = PYRAMID_SCALE ** pyramid_level
    return base_size / scale

# ========== 模拟交易 ==========
class SRLimitStrategy:
    def __init__(self):
        self.capital = INITIAL_CAPITAL
        self.available_capital = INITIAL_CAPITAL
        
        # 持仓 (可能同时持有多空)
        self.positions = []  # [{type, size, entry, sl, tp, level, pnl}]
        
        # 挂单 (模拟已报入交易所的限价单)
        self.pending_orders = []  # [{type, size, price, sl, tp, level}]
        
        # 交易记录
        self.trades = []
        self.equity_curve = []
        
        # 统计
        self.win_count = 0
        self.lose_count = 0
        self.total_pnl = 0
        
        # 历史数据 (用于计算Kelly)
        self.win_history = []
        self.loss_history = []
        self.trade_results = []
        
        # 当前Kelly值
        self.current_kelly = 0.15  # 默认15%
        
        # 追踪
        self.last_rebalance_hour = None
        
    def get_total_exposure(self):
        """当前总持仓USDT价值"""
        return sum(p['size'] for p in self.positions)
    
    def get_position_value(self):
        """账户权益 = 现金 + 持仓盈亏"""
        pos_pnl = sum(p.get('unrealized_pnl', 0) for p in self.positions)
        return self.capital + pos_pnl
    
    def update_unrealized_pnl(self, current_price):
        """更新持仓浮动盈亏"""
        for pos in self.positions:
            if pos['type'] == 'long':
                pos['unrealized_pnl'] = pos['size'] * (current_price - pos['entry']) / pos['entry']
            else:
                pos['unrealized_pnl'] = pos['size'] * (pos['entry'] - current_price) / pos['entry']
    
    def update_pending_orders(self, current_price, sr_levels):
        """检查挂单是否被触发"""
        triggered = []
        still_pending = []
        
        for order in self.pending_orders:
            if order['type'] == 'long':
                # 多单: 价格跌到支撑区间就触发
                if current_price <= order['price']:
                    triggered.append(order)
                else:
                    still_pending.append(order)
            else:  # short
                # 空单: 价格涨到压力区间就触发
                if current_price >= order['price']:
                    triggered.append(order)
                else:
                    still_pending.append(order)
        
        self.pending_orders = still_pending
        return triggered
    
    def execute_order(self, order, current_price, timestamp):
        """执行一个被触发的挂单"""
        pos_type = order['type']
        size = order['size']
        entry = current_price
        sl = order['sl']
        tp = order['tp']
        level = order['level']
        atr = order['atr']
        
        # 计算手续费
        fee = size * TRADE_FEE
        
        # 开仓
        if pos_type == 'long':
            cost = size * (1 + TRADE_FEE)
            if cost > self.capital:
                return None  # 资金不足
        else:  # short
            # 做空需要保证金 (假设10倍杠杆, 保证金=仓位/杠杆)
            margin_required = size / 10
            if margin_required > self.capital:
                return None
        
        pos = {
            'type': pos_type,
            'size': size,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'atr': atr,
            'level': level,
            'open_time': timestamp,
            'pyramid_level': 0,
            'unrealized_pnl': 0,
            'fee': fee
        }
        
        self.positions.append(pos)
        
        self.trades.append({
            'timestamp': timestamp,
            'type': f'OPEN_{pos_type.upper()}',
            'price': entry,
            'size': size,
            'sl': sl,
            'tp': tp,
            'atr': atr,
            'level': level,
            'capital_after': self.capital
        })
        
        return pos
    
    def check_positions(self, current_price, timestamp, sr_levels):
        """检查持仓是否触发止损止盈"""
        closed = []
        
        for pos in self.positions[:]:  # 复制列表以安全删除
            should_close = False
            reason = ''
            pnl = 0
            
            if pos['type'] == 'long':
                # 止盈检查
                if current_price >= pos['tp']:
                    should_close = True
                    reason = 'TAKE_PROFIT'
                # 止损检查
                elif current_price <= pos['sl']:
                    should_close = True
                    reason = 'STOP_LOSS'
            else:  # short
                if current_price <= pos['tp']:
                    should_close = True
                    reason = 'TAKE_PROFIT'
                elif current_price >= pos['sl']:
                    should_close = True
                    reason = 'STOP_LOSS'
            
            if should_close:
                if pos['type'] == 'long':
                    proceeds = pos['size'] * current_price * (1 - TRADE_FEE)
                    gross_pnl = proceeds - pos['size'] * pos['entry'] * (1 + TRADE_FEE)
                else:
                    cost = pos['size'] * current_price * (1 + TRADE_FEE)
                    gross_pnl = pos['size'] * pos['entry'] * (1 - TRADE_FEE) - cost
                
                pnl = gross_pnl - pos['fee']
                
                # 收尾手续费
                self.capital += pnl
                
                if pnl > 0:
                    self.win_count += 1
                    self.win_history.append(pnl)
                else:
                    self.lose_count += 1
                    self.loss_history.append(pnl)
                
                self.total_pnl += pnl
                self.trade_results.append(pnl)
                
                self.trades.append({
                    'timestamp': timestamp,
                    'type': f'CLOSE_{pos["type"].upper()}',
                    'price': current_price,
                    'size': pos['size'],
                    'pnl': pnl,
                    'reason': reason,
                    'holding_hours': (timestamp - pos['open_time']).total_seconds() / 3600 if 'open_time' in pos else 0,
                    'pyramid_level': pos.get('pyramid_level', 0),
                    'capital_after': self.capital
                })
                
                closed.append((pos, pnl, reason))
                self.positions.remove(pos)
        
        return closed
    
    def add_pyramid(self, existing_pos, current_price, timestamp, atr, sr_levels):
        """金字塔加仓"""
        if existing_pos.get('pyramid_level', 0) >= MAX_PYRAMID - 1:
            return None
        
        pos_type = existing_pos['type']
        next_level = existing_pos.get('pyramid_level', 0) + 1
        
        # 计算加仓量 (递减)
        base_size = ORDER_SIZE
        add_size = pyramid_size(base_size, next_level, MAX_PYRAMID)
        
        # 检查资金
        if add_size > self.capital * 0.3:  # 最多用30%资金金字塔
            add_size = self.capital * 0.3
        
        if add_size < 50:  # 最小加仓量
            return None
        
        # 新增仓位的止损/止盈
        sl, tp = calc_sl_tp(current_price, pos_type, atr)
        
        pos = {
            'type': pos_type,
            'size': add_size,
            'entry': current_price,
            'sl': sl,
            'tp': tp,
            'atr': atr,
            'level': f'Pyramid_L{next_level}',
            'open_time': timestamp,
            'pyramid_level': next_level,
            'unrealized_pnl': 0,
            'fee': add_size * TRADE_FEE,
            'is_pyramid': True,
            'parent_entry': existing_pos['entry']
        }
        
        self.positions.append(pos)
        
        self.trades.append({
            'timestamp': timestamp,
            'type': f'PYRAMID_{pos_type.upper()}_L{next_level}',
            'price': current_price,
            'size': add_size,
            'sl': sl,
            'tp': tp,
            'atr': atr,
            'capital_after': self.capital
        })
        
        return pos
    
    def should_add_pyramid(self, pos, current_price):
        """判断是否应该金字塔加仓"""
        if pos.get('pyramid_level', 0) >= MAX_PYRAMID - 1:
            return False
        
        # 只在盈利时加仓
        if pos['type'] == 'long':
            profit_pct = (current_price - pos['entry']) / pos['entry']
            if profit_pct < 0.01:  # 至少1%利润
                return False
            # 价格回调时加仓 (金字塔抄底)
            if current_price < pos['entry'] * 1.01:  # 回调不超过1%
                return True
        else:
            profit_pct = (pos['entry'] - current_price) / pos['entry']
            if profit_pct < 0.01:
                return False
            if current_price > pos['entry'] * 0.99:
                return True
        
        return False
    
    def place_orders(self, sr_levels, current_price, atr):
        """在支撑压力位挂单"""
        # 清空旧挂单
        self.pending_orders = []
        
        # 支撑位挂多单
        support_price = sr_levels['support_entry']
        if support_price < current_price and support_price > current_price * 0.9:
            sl, tp = calc_sl_tp(support_price, 'long', atr)
            order = {
                'type': 'long',
                'size': ORDER_SIZE,
                'price': support_price,
                'sl': sl,
                'tp': tp,
                'atr': atr,
                'level': f'Support_{round(support_price, 0)}'
            }
            self.pending_orders.append(order)
        
        # 压力位挂空单
        resistance_price = sr_levels['resistance_entry']
        if resistance_price > current_price and resistance_price < current_price * 1.1:
            sl, tp = calc_sl_tp(resistance_price, 'short', atr)
            order = {
                'type': 'short',
                'size': ORDER_SIZE,
                'price': resistance_price,
                'sl': sl,
                'tp': tp,
                'atr': atr,
                'level': f'Resistance_{round(resistance_price, 0)}'
            }
            self.pending_orders.append(order)
    
    def update_kelly(self):
        """更新Kelly值"""
        if len(self.win_history) < 5 or len(self.loss_history) < 5:
            return  # 数据不够不更新
        
        wins = np.array(self.win_history)
        losses = np.array(self.loss_history)
        
        win_rate = len(wins) / (len(wins) + len(losses))
        avg_win = wins.mean()
        avg_loss = abs(losses).mean()
        
        if avg_loss > 0:
            self.current_kelly = kelly_fraction(win_rate, avg_win, avg_loss)
    
    def get_total_equity(self, current_price):
        return self.capital + sum(
            p['size'] * (current_price - p['entry']) / p['entry'] if p['type'] == 'long'
            else p['size'] * (p['entry'] - current_price) / p['entry']
            for p in self.positions
        )

# ========== 主回测 ==========
def run_backtest():
    print("=" * 70)
    print("  支撑压力双向挂单策略 - 完整回测")
    print("=" * 70)
    print(f"本金: ${INITIAL_CAPITAL:,.2f}")
    print(f"每单金额: ${ORDER_SIZE:,.2f} × 2 = ${ORDER_SIZE*2:,.2f} (双向同时挂)")
    print(f"止损: {SL_ATR_MULT}倍ATR | 止盈: {TP_ATR_MULT}倍ATR (动态)")
    print(f"仓位管理: {'Kelly公式(%.0f%%)'%(KELLY_FRACTION*100) if USE_KELLY else '金字塔(最多%d层)'%MAX_PYRAMID}")
    print(f"手续费: {TRADE_FEE*100:.2f}% | 资金费率: {FUNDING_RATE*100:.2f}%")
    print("=" * 70)
    
    # Step 1: 获取数据
    print(f"\n[1/6] 获取 {SYMBOL} 历史K线...")
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
    print(f"  {len(df)} 根K线, {df.index[0]} ~ {df.index[-1]}")
    
    # Step 2: 计算指标
    print("\n[2/6] 计算技术指标...")
    df['atr'] = calc_atr(df, ATR_PERIOD)
    df['ema20'] = calc_ema(df['close'], 20)
    df['ema60'] = calc_ema(df['close'], 60)
    df['rsi'] = calc_rsi(df['close'], 14)
    df['volume_ma'] = df['volume'].rolling(20).mean()
    df['volatility'] = df['close'].pct_change().rolling(14).std() * 100
    
    # Step 3: 逐小时回测
    print("\n[3/6] 逐小时回测模拟...")
    strategy = SRLimitStrategy()
    current_hour = None
    
    for i in range(60, len(df)):
        row = df.iloc[i]
        ts = row.name
        price = row['close']
        atr = row['atr'] if pd.notna(row['atr']) else price * 0.01
        current_hour = ts
        
        # 更新浮动盈亏
        strategy.update_unrealized_pnl(price)
        
        # 检查挂单触发
        triggered = strategy.update_pending_orders(price, None)
        for order in triggered:
            strategy.execute_order(order, price, ts)
        
        # 检查持仓止损止盈
        closed = strategy.check_positions(price, ts, None)
        
        # 金字塔加仓检查 (每K线检查一次)
        for pos in strategy.positions:
            if strategy.should_add_pyramid(pos, price):
                strategy.add_pyramid(pos, price, ts, atr, None)
        
        # 每小时重新计算支撑压力并挂单
        if current_hour != ts or len(strategy.pending_orders) == 0:
            lookback_df = df.iloc[:i+1]
            sr = find_support_resistance(lookback_df, lookback=24, atr=atr)
            
            # 每小时挂单一次
            strategy.place_orders(sr, price, atr)
        
        # 更新Kelly
        if i % 24 == 0:
            strategy.update_kelly()
        
        # 记录权益曲线 (每小时一次)
        total_eq = strategy.get_total_equity(price)
        strategy.equity_curve.append({
            'timestamp': ts,
            'hour': ts.strftime('%Y-%m-%d %H:00'),
            'date': ts.strftime('%Y-%m-%d'),
            'close': price,
            'capital': strategy.capital,
            'total_equity': total_eq,
            'positions': len(strategy.positions),
            'pending_orders': len(strategy.pending_orders),
            'kelly': strategy.current_kelly,
            'atr': atr,
            'support': sr.get('support', 0) if 'sr' in dir() else 0,
            'resistance': sr.get('resistance', 0) if 'sr' in dir() else 0
        })
    
    # 最终平仓
    final_price = df.iloc[-1]['close']
    for pos in strategy.positions[:]:
        if pos['type'] == 'long':
            proceeds = pos['size'] * final_price * (1 - TRADE_FEE)
            pnl = proceeds - pos['size'] * pos['entry'] * (1 + TRADE_FEE)
        else:
            cost = pos['size'] * final_price * (1 + TRADE_FEE)
            pnl = pos['size'] * pos['entry'] * (1 - TRADE_FEE) - cost
        strategy.capital += pnl
        strategy.trades.append({
            'timestamp': df.iloc[-1].name,
            'type': f'CLOSE_{pos["type"].upper()}',
            'price': final_price,
            'pnl': pnl,
            'reason': 'END_OF_BACKTEST',
            'capital_after': strategy.capital
        })
        strategy.positions.remove(pos)
    
    # Step 4: 生成报告
    print("\n[4/6] 生成报告...")
    print("\n" + "=" * 70)
    print("  📊 回测报告 - 支撑压力双向挂单策略")
    print("=" * 70)
    
    eq_df = pd.DataFrame(strategy.equity_curve)
    trades_df = pd.DataFrame(strategy.trades)
    closes_df = trades_df[trades_df['type'].str.startswith('CLOSE')] if len(trades_df) > 0 else pd.DataFrame()
    
    final_eq = strategy.capital  # 归零后是最终资金
    total_ret = (final_eq - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    total_pnl = final_eq - INITIAL_CAPITAL
    
    # 统计
    n_trades = len(closes_df)
    win_rate = strategy.win_count / (strategy.win_count + strategy.lose_count) * 100 if (strategy.win_count + strategy.lose_count) > 0 else 0
    avg_win = closes_df[closes_df['pnl'] > 0]['pnl'].mean() if len(closes_df[closes_df['pnl'] > 0]) > 0 else 0
    avg_loss = closes_df[closes_df['pnl'] < 0]['pnl'].mean() if len(closes_df[closes_df['pnl'] < 0]) > 0 else 0
    pf = abs(closes_df[closes_df['pnl'] > 0]['pnl'].sum() / closes_df[closes_df['pnl'] < 0]['pnl'].sum()) if len(closes_df[closes_df['pnl'] < 0]) > 0 and closes_df[closes_df['pnl'] < 0]['pnl'].sum() != 0 else 0
    
    # 最大回撤
    if len(eq_df) > 0:
        eq_df['peak'] = eq_df['total_equity'].cummax()
        eq_df['dd'] = (eq_df['total_equity'] - eq_df['peak']) / eq_df['peak'] * 100
        max_dd = abs(eq_df['dd'].min())
        max_dd_idx = eq_df['dd'].idxmin()
        days = len(eq_df)
        ann_ret = ((final_eq / INITIAL_CAPITAL) ** (365 * 24 / days) - 1) * 100 if days > 0 else 0
        rets = eq_df['total_equity'].pct_change().dropna()
        sharpe = rets.mean() / rets.std() * np.sqrt(365 * 24) if rets.std() > 0 else 0
    else:
        max_dd = ann_ret = sharpe = 0
    
    # 月度
    eq_df['month'] = eq_df['date'].str[:7]
    
    # 平仓原因
    tp_count = len(closes_df[closes_df['reason'] == 'TAKE_PROFIT']) if len(closes_df) > 0 else 0
    sl_count = len(closes_df[closes_df['reason'] == 'STOP_LOSS']) if len(closes_df) > 0 else 0
    pyramid_count = len(closes_df[closes_df.get('pyramid_level', 0) > 0]) if len(closes_df) > 0 else 0
    
    print(f"""
┌─ 【策略概览】 ─────────────────────────────────────────────────────────────
│  策略名称:        支撑压力双向挂单 + ATR动态止损止盈
│  交易标的:        {SYMBOL} 永续合约
│  回测周期:        {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}
│  数据周期:        1小时K线
│  交易天数:        {len(eq_df)//24} 天
└──────────────────────────────────────────────────────────────────────────────

┌─ 【账户概览】 ──────────────────────────────────────────────────────────────
│  初始本金:        ${INITIAL_CAPITAL:,.2f}
│  最终权益:        ${final_eq:,.2f}
│  总收益:          ${total_pnl:,.2f}
│  总收益率:        {total_ret:.2f}%
│  年化收益率:      {ann_ret:.2f}%
│  夏普比率:        {sharpe:.2f}
│  最大回撤:        {max_dd:.2f}%
└──────────────────────────────────────────────────────────────────────────────

┌─ 【交易统计】 ──────────────────────────────────────────────────────────────
│  总开仓次数:      {n_trades}
│  盈利交易:        {strategy.win_count}    亏损交易: {strategy.lose_count}
│  胜率:            {win_rate:.2f}%
│  平均盈利:        ${avg_win:,.2f}
│  平均亏损:        ${avg_loss:,.2f}
│  盈亏比:          {pf:.2f}
│  止盈次数:        {tp_count} ({tp_count/n_trades*100:.1f}%)
│  止损次数:        {sl_count} ({sl_count/n_trades*100:.1f}%)
│  金字塔加仓:      {pyramid_count} 次
│  最终Kelly值:     {strategy.current_kelly:.1%}
└──────────────────────────────────────────────────────────────────────────────

┌─ 【仓位管理】 ──────────────────────────────────────────────────────────────
│  模式:            {'Kelly公式' if USE_KELLY else '金字塔加仓'}
│  每单金额:        ${ORDER_SIZE:,.2f}
│  最大持仓:        ${ORDER_SIZE * MAX_PYRAMID:,.2f} (金字塔{MAX_PYRAMID}层)
│  动态止损:        {SL_ATR_MULT}倍ATR
│  动态止盈:        {TP_ATR_MULT}倍ATR (最低2:1盈亏比)
└──────────────────────────────────────────────────────────────────────────────
""")
    
    # 挂单统计
    open_orders = trades_df[trades_df['type'].str.startswith('OPEN')]
    if len(open_orders) > 0:
        long_orders = len(open_orders[open_orders['type'] == 'OPEN_long'])
        short_orders = len(open_orders[open_orders['type'] == 'OPEN_short'])
        pyramid_orders = len(open_orders[open_orders['type'].str.startswith('PYRAMID')])
        print(f"┌─ 【挂单统计】 ──────────────────────────────────────────────────────────────")
        print(f"│  多单触发:        {long_orders} 次")
        print(f"│  空单触发:        {short_orders} 次")
        print(f"│  金字塔加仓:      {pyramid_orders} 次")
        print(f"│  总挂单利用率:    {(long_orders+short_orders)/len(eq_df)*100:.1f}%")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 月度收益
    print(f"\n┌─ 【月度收益】 ──────────────────────────────────────────────────────────────")
    monthly = eq_df.groupby('month').agg({'total_equity': ['first', 'last']})
    monthly.columns = ['start', 'end']
    monthly['return'] = (monthly['end'] - monthly['start']) / monthly['start'] * 100
    
    for m, row in monthly.iterrows():
        r = row['return']
        c = '🟢' if r >= 0 else '🔴'
        print(f"│  {m}: {'+' if r >= 0 else ''}{r:6.2f}%  {c}")
    print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 平仓原因
    if len(closes_df) > 0:
        print(f"\n┌─ 【平仓原因】 ──────────────────────────────────────────────────────────────")
        for r, cnt in closes_df['reason'].value_counts().items():
            pct = cnt / len(closes_df) * 100
            print(f"│  {r:20s}: {cnt:3d} ({pct:5.1f}%)")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 日度统计
    daily = eq_df.groupby('date').agg({'total_equity': 'last'})
    daily['prev'] = daily['total_equity'].shift(1)
    daily['return'] = (daily['total_equity'] - daily['prev']) / daily['prev'] * 100
    n_days = len(daily)
    n_win_days = (daily['return'] > 0).sum()
    best_day = daily['return'].max()
    worst_day = daily['return'].min()
    
    print(f"\n┌─ 【日度统计】 ──────────────────────────────────────────────────────────────")
    print(f"│  交易天数:        {n_days}")
    print(f"│  盈利天数:        {n_win_days} ({n_win_days/n_days*100:.1f}%)")
    print(f"│  最佳单日:        {best_day:+.2f}%")
    print(f"│  最差单日:        {worst_day:+.2f}%")
    print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 保存
    print("\n[5/6] 保存数据...")
    od = '/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/backtest_results'
    os.makedirs(od, exist_ok=True)
    
    eq_df.to_csv(f'{od}/sr_equity.csv', index=False)
    trades_df.to_csv(f'{od}/sr_trades.csv', index=False)
    eq_df.to_csv(f'{od}/sr_hourly.csv', index=False)
    
    summary = {
        'strategy': 'SR_Limit_Orders',
        'symbol': SYMBOL,
        'period': f"{df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}",
        'initial_capital': INITIAL_CAPITAL,
        'final_equity': final_eq,
        'total_return_pct': total_ret,
        'annual_return_pct': ann_ret,
        'sharpe': sharpe,
        'max_drawdown_pct': max_dd,
        'total_trades': n_trades,
        'win_rate': win_rate,
        'profit_factor': pf,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'tp_count': tp_count,
        'sl_count': sl_count,
    }
    
    with open(f'{od}/sr_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n[6/6] 完成!")
    print(f"\n📁 数据已保存: {od}/sr_*.csv")
    
    return strategy, eq_df, trades_df

if __name__ == '__main__':
    run_backtest()
