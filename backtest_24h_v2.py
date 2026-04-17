#!/usr/bin/env python3
"""
Polymarket式24H策略 V2 - 优化版
- 初始资金: $10,000
- 最大仓位: $1,000
- 日亏损控制: 5%
- 信号: STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL
- 优化: 趋势过滤 + 指标共振 + 收紧止损
"""

import pandas as pd
import numpy as np
import requests
import json
import time
import os
from datetime import datetime, timedelta
from collections import defaultdict

# ========== 配置 ==========
INITIAL_CAPITAL = 10000
MAX_POSITION = 1000
DAILY_LOSS_LIMIT = 0.05
SYMBOL = 'BTCUSDT'
INTERVAL = '1h'
START_DATE = '2024-04-16'
END_DATE = '2025-04-16'
TRADE_FEE = 0.001

# ========== 币安API ==========
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
            last_time = int(data[-1][0])
            params['startTime'] = last_time + 1
            time.sleep(0.2)
        except Exception as e:
            break
    return all_klines

def parse_klines(klines):
    df = pd.DataFrame(klines, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
        df[col] = df[col].astype(float)
    return df

# ========== 技术指标 ==========
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - signal_line
    return macd_line, signal_line, macd_hist

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    position = (prices - lower_band) / (upper_band - lower_band + 1e-10)
    return upper_band, lower_band, position

def calculate_ema(prices, period):
    return prices.ewm(span=period, adjust=False).mean()

# ========== 优化后的信号生成 ==========
def generate_signal_v2(row, lookback):
    """
    V2 信号生成: 趋势过滤 + 多指标共振
    - 首先判断趋势 (EMA200)
    - RSI极端区 + MACD方向 + 布林带位置 综合打分
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
    
    # ========== Step 1: 判断全局趋势 ==========
    if close > ema200 and ema20 > ema60:
        trend = 'bullish'      # 多头趋势
    elif close < ema200 and ema20 < ema60:
        trend = 'bearish'      # 空头趋势
    else:
        trend = 'neutral'       # 震荡
    
    # ========== Step 2: 技术面打分 (0-100, 50=中性) ==========
    tech_score = 50
    
    # RSI (20%权重, 范围0-100)
    if rsi < 20:
        rsi_score = 100  # 严重超卖
    elif rsi < 30:
        rsi_score = 85
    elif rsi < 40:
        rsi_score = 70
    elif rsi < 50:
        rsi_score = 58
    elif rsi < 60:
        rsi_score = 42
    elif rsi < 70:
        rsi_score = 30
    elif rsi < 80:
        rsi_score = 15
    else:
        rsi_score = 0  # 严重超买
    
    # MACD (30%权重)
    # 简化判断
    if macd > macd_signal and macd_hist > 0:
        macd_score = 80  # 金叉且零轴上方
    elif macd > macd_signal:
        macd_score = 65  # 金叉
    elif macd > 0:
        macd_score = 55  # 零轴上方但死叉
    elif macd < macd_signal:
        macd_score = 35  # 零轴下方死叉
    else:
        macd_score = 20  # 零轴下方且扩张
    
    # 布林带 (25%权重)
    if bb_pos < 10:
        bb_score = 100  # 严重超卖
    elif bb_pos < 20:
        bb_score = 85
    elif bb_pos < 30:
        bb_score = 70
    elif bb_pos < 45:
        bb_score = 55
    elif bb_pos < 55:
        bb_score = 50
    elif bb_pos < 70:
        bb_score = 45
    elif bb_pos < 80:
        bb_score = 30
    elif bb_pos < 90:
        bb_score = 15
    else:
        bb_score = 0  # 严重超买
    
    # 24h动量 (25%权重)
    if price_change_24h > 5:
        mom_score = 90
    elif price_change_24h > 3:
        mom_score = 75
    elif price_change_24h > 1:
        mom_score = 60
    elif price_change_24h > 0:
        mom_score = 55
    elif price_change_24h > -1:
        mom_score = 45
    elif price_change_24h > -3:
        mom_score = 30
    elif price_change_24h > -5:
        mom_score = 15
    else:
        mom_score = 5
    
    tech_score = int(rsi_score * 0.20 + macd_score * 0.30 + bb_score * 0.25 + mom_score * 0.25)
    
    # ========== Step 3: 情绪面 ==========
    # 恐慌贪婪
    if fear_greed < 20:
        emotion_score = 95
    elif fear_greed < 30:
        emotion_score = 80
    elif fear_greed < 40:
        emotion_score = 65
    elif fear_greed < 50:
        emotion_score = 55
    elif fear_greed < 60:
        emotion_score = 45
    elif fear_greed < 70:
        emotion_score = 35
    elif fear_greed < 80:
        emotion_score = 20
    else:
        emotion_score = 5
    
    # ========== Step 4: 综合评分 ==========
    composite = int(tech_score * 0.65 + emotion_score * 0.35)
    
    # ========== Step 5: 趋势过滤 ==========
    # 只有趋势方向匹配时才能开仓
    if composite >= 75:
        raw_signal = 'STRONG_BUY'
    elif composite >= 62:
        raw_signal = 'BUY'
    elif composite >= 38:
        raw_signal = 'NEUTRAL'
    elif composite >= 25:
        raw_signal = 'SELL'
    else:
        raw_signal = 'STRONG_SELL'
    
    # 趋势过滤: 多头市场中不做空, 空头市场中不做多
    if trend == 'bullish':
        final_signal = raw_signal if raw_signal not in ['SELL', 'STRONG_SELL'] else 'NEUTRAL'
    elif trend == 'bearish':
        final_signal = raw_signal if raw_signal not in ['BUY', 'STRONG_BUY'] else 'NEUTRAL'
    else:
        # 震荡市场中, 只做超卖超买反弹
        if raw_signal in ['STRONG_BUY', 'BUY'] and tech_score < 60:
            final_signal = 'NEUTRAL'
        elif raw_signal in ['STRONG_SELL', 'SELL'] and tech_score > 40:
            final_signal = 'NEUTRAL'
        else:
            final_signal = raw_signal
    
    # ========== Step 6: 额外过滤 - 指标共振 ==========
    # 至少2个指标同时看涨/看跌才发出STRONG信号
    bullish_count = 0
    bearish_count = 0
    if rsi < 35: bullish_count += 1
    if rsi > 65: bearish_count += 1
    if macd > macd_signal: bullish_count += 1
    if macd < macd_signal: bearish_count += 1
    if bb_pos < 25: bullish_count += 1
    if bb_pos > 75: bearish_count += 1
    if price_change_24h > 2: bullish_count += 1
    if price_change_24h < -2: bearish_count += 1
    
    if final_signal == 'STRONG_BUY' and bullish_count < 3:
        final_signal = 'BUY'
    if final_signal == 'STRONG_SELL' and bearish_count < 3:
        final_signal = 'SELL'
    
    return {
        'signal': final_signal,
        'trend': trend,
        'composite': composite,
        'tech_score': tech_score,
        'emotion_score': emotion_score,
        'rsi': rsi,
        'macd': macd,
        'macd_hist': macd_hist,
        'bb_position': bb_pos,
        'fear_greed': fear_greed,
        'price_change_24h_pct': price_change_24h,
        'close': close
    }

# ========== 交易模拟器 V2 ==========
class TradingSimulatorV2:
    def __init__(self, initial_capital=INITIAL_CAPITAL, max_position=MAX_POSITION, daily_loss_limit=DAILY_LOSS_LIMIT):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.max_position = max_position
        self.daily_loss_limit = daily_loss_limit
        
        self.position = 0
        self.position_type = None
        self.entry_price = 0
        self.highest_price = 0  # 跟踪最高价(多头)
        self.lowest_price = float('inf')  # 跟踪最低价(空头)
        
        self.trades = []
        self.equity_curve = []
        
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0
        
        self.daily_start_capital = initial_capital
        self.trading_paused = False
        self.pause_reason = None
        
    def open_position(self, signal, price, timestamp):
        if self.position != 0:
            return
        
        position_value = min(self.max_position, self.capital * 0.4)
        shares = position_value / price
        
        if signal in ['STRONG_BUY', 'BUY']:
            self.position_type = 'long'
            cost = shares * price * (1 + TRADE_FEE)
            if cost <= self.capital:
                self.position = shares
                self.entry_price = price
                self.highest_price = price
                self.capital -= cost
                self.trades.append({
                    'timestamp': timestamp,
                    'type': 'OPEN_LONG',
                    'price': price,
                    'shares': shares,
                    'value': position_value,
                    'signal': signal
                })
        elif signal in ['STRONG_SELL', 'SELL']:
            self.position_type = 'short'
            proceeds = shares * price * (1 - TRADE_FEE)
            self.position = shares
            self.entry_price = price
            self.lowest_price = price
            self.capital += proceeds
            self.trades.append({
                'timestamp': timestamp,
                'type': 'OPEN_SHORT',
                'price': price,
                'shares': shares,
                'value': position_value,
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
        
        self.trades.append({
            'timestamp': timestamp,
            'type': f'CLOSE_{self.position_type.upper()}',
            'price': price,
            'shares': shares,
            'pnl': pnl,
            'reason': reason,
            'capital_after': self.capital,
            'holding_hours': (timestamp - self.trades[-2]['timestamp']).total_seconds() / 3600 if len(self.trades) > 1 else 0
        })
        
        self.position = 0
        self.position_type = None
        self.entry_price = 0
        self.highest_price = 0
        self.lowest_price = float('inf')
    
    def update_position(self, price):
        """更新持仓跟踪"""
        if self.position == 0:
            return
        if self.position_type == 'long':
            self.highest_price = max(self.highest_price, price)
        else:
            self.lowest_price = min(self.lowest_price, price)
    
    def check_stops(self, price):
        """检查止损"""
        if self.position == 0:
            return None
        
        # 固定止损 5%
        if self.position_type == 'long':
            loss_pct = (self.entry_price - price) / self.entry_price
            if loss_pct >= 0.05:
                return 'FIXED_STOP_5'
            # 移动止损: 从最高点回撤8%止损
            if self.highest_price > 0:
                drawback = (self.highest_price - price) / self.highest_price
                if drawback >= 0.08:
                    return 'TRAILING_STOP_8'
        else:
            loss_pct = (price - self.entry_price) / self.entry_price
            if loss_pct >= 0.05:
                return 'FIXED_STOP_5'
            if self.lowest_price < float('inf'):
                drawback = (price - self.lowest_price) / self.lowest_price
                if drawback >= 0.08:
                    return 'TRAILING_STOP_8'
        
        return None
    
    def should_close(self, signal):
        if self.position == 0:
            return False
        # 反向信号
        if self.position_type == 'long' and signal in ['STRONG_SELL']:
            return True
        if self.position_type == 'short' and signal in ['STRONG_BUY']:
            return True
        return False
    
    def update_daily(self, current_date, close_price):
        self.update_position(close_price)
        total_equity = self.capital + (self.position * close_price if self.position > 0 else 0)
        self.equity_curve.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'capital': self.capital,
            'position_value': self.position * close_price if self.position > 0 else 0,
            'total_equity': total_equity,
            'close': close_price
        })
    
    def new_day(self, current_date):
        total_equity = self.capital + (self.position * self.equity_curve[-1]['close'] if self.position > 0 and len(self.equity_curve) > 0 else 0)
        self.daily_start_capital = total_equity
        self.trading_paused = False
        self.pause_reason = None
    
    def check_daily_loss(self):
        total_equity = self.capital + (self.position * self.equity_curve[-1]['close'] if self.position > 0 and len(self.equity_curve) > 0 else 0)
        if total_equity < self.daily_start_capital * (1 - self.daily_loss_limit):
            return True
        return False

# ========== 主回测 ==========
def run_backtest_v2():
    print("=" * 70)
    print("24H策略 V2 - 优化版 (趋势过滤 + 指标共振)")
    print("=" * 70)
    print(f"初始资金: ${INITIAL_CAPITAL:,.2f}")
    print(f"最大仓位: ${MAX_POSITION:,.2f}")
    print(f"日亏损限制: {DAILY_LOSS_LIMIT*100:.1f}%")
    print(f"止损: 5%固定 + 8%移动止损")
    print(f"趋势过滤: EMA200 + EMA20/60交叉")
    print(f"指标共振: 至少3指标确认才发STRONG信号")
    print("=" * 70)
    
    # ========== 获取数据 ==========
    print(f"\n[1/5] 正在获取 {SYMBOL} 历史K线数据...")
    cache_file = f"/tmp/binance_{SYMBOL}_1y.json"
    
    if os.path.exists(cache_file):
        print("  使用缓存数据...")
        with open(cache_file, 'r') as f:
            raw_klines = json.load(f)
    else:
        raw_klines = get_binance_klines(SYMBOL, INTERVAL, START_DATE, END_DATE)
        if raw_klines:
            with open(cache_file, 'w') as f:
                json.dump(raw_klines, f)
    
    if not raw_klines:
        print("获取数据失败!")
        return
    
    print(f"  获取到 {len(raw_klines)} 根K线")
    
    # ========== 计算指标 ==========
    print("\n[2/5] 解析数据并计算技术指标...")
    df = parse_klines(raw_klines)
    df = df.set_index('open_time')
    
    df['price_change_24h_pct'] = df['close'].pct_change(24) * 100
    
    print("  RSI...")
    df['rsi'] = calculate_rsi(df['close'], 14)
    
    print("  MACD...")
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df['close'])
    
    print("  布林带...")
    df['bb_upper'], df['bb_lower'], df['bb_position'] = calculate_bollinger_bands(df['close'])
    
    print("  EMA均线...")
    df['ema20'] = calculate_ema(df['close'], 20)
    df['ema60'] = calculate_ema(df['close'], 60)
    df['ema200'] = calculate_ema(df['close'], 200)
    
    print("  恐惧贪婪指数...")
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(14).std() * 100
    df['vol_change'] = df['volume'].pct_change().rolling(14).mean() * 100
    
    def calc_fg(vol, vc):
        vol = vol if not pd.isna(vol) else 3
        vc = vc if not pd.isna(vc) else 0
        if vol > 8:
            fg = max(10, 50 - (vol - 5) * 4)
        elif vol < 2:
            fg = min(90, 50 + (3 - vol) * 10)
        else:
            fg = 50
        if vc > 30:
            fg = min(100, fg + 10)
        elif vc < -30:
            fg = max(0, fg - 10)
        return int(np.clip(fg, 0, 100))
    
    df['fear_greed'] = df.apply(lambda row: calc_fg(row['volatility'], row['vol_change']), axis=1)
    
    # 去掉na
    df = df.dropna(subset=['rsi', 'macd', 'bb_position', 'ema20', 'ema60', 'ema200'])
    print(f"  有效数据点: {len(df)}")
    
    # ========== 生成信号 ==========
    print("\n[3/5] 生成交易信号...")
    signals = []
    for i in range(200, len(df)):
        lookback = df.iloc[:i+1]
        row = df.iloc[i]
        sig = generate_signal_v2(row, lookback)
        sig['timestamp'] = row.name
        sig['close'] = row['close']
        sig['trend'] = sig['trend']
        signals.append(sig)
    
    df_signals = pd.DataFrame(signals)
    print(f"  生成信号数: {len(df_signals)}")
    
    # 统计信号分布
    signal_counts = df_signals['signal'].value_counts()
    print(f"  信号分布:")
    for sig in ['STRONG_BUY', 'BUY', 'NEUTRAL', 'SELL', 'STRONG_SELL']:
        count = signal_counts.get(sig, 0)
        pct = count / len(df_signals) * 100
        print(f"    {sig:12s}: {count:5d} ({pct:5.1f}%)")
    
    trend_counts = df_signals['trend'].value_counts()
    print(f"  趋势分布:")
    for t in ['bullish', 'bearish', 'neutral']:
        count = trend_counts.get(t, 0)
        pct = count / len(df_signals) * 100
        print(f"    {t:8s}: {count:5d} ({pct:5.1f}%)")
    
    # ========== 交易模拟 ==========
    print("\n[4/5] 运行交易模拟...")
    sim = TradingSimulatorV2()
    current_date = None
    
    for idx, row in df_signals.iterrows():
        ts = row['timestamp']
        price = row['close']
        signal = row['signal']
        
        if current_date != ts.date():
            if current_date is not None:
                sim.new_day(ts)
            current_date = ts.date()
        
        # 日亏损检查
        if sim.check_daily_loss():
            if sim.position != 0:
                sim.close_position('DAILY_LOSS_LIMIT', price, ts)
            sim.trading_paused = True
            sim.pause_reason = 'DAILY_LOSS'
        
        sim.update_daily(ts, price)
        
        # 止损检查
        if sim.position != 0:
            stop_reason = sim.check_stops(price)
            if stop_reason:
                sim.close_position(stop_reason, price, ts)
                continue
        
        # 交易逻辑
        if sim.position == 0 and not sim.trading_paused:
            if signal in ['STRONG_BUY', 'BUY']:
                sim.open_position(signal, price, ts)
            elif signal in ['STRONG_SELL', 'SELL']:
                sim.open_position(signal, price, ts)
        elif sim.position != 0:
            if sim.should_close(signal):
                sim.close_position('SIGNAL_REVERSE', price, ts)
    
    # 最终平仓
    if sim.position != 0:
        sim.close_position('END_OF_BACKTEST', df_signals.iloc[-1]['close'], df_signals.iloc[-1]['timestamp'])
    
    # ========== 生成报告 ==========
    print("\n[5/5] 生成回测报告...")
    generate_report_v2(sim, df_signals)
    
    return sim, df_signals

def generate_report_v2(sim, df_signals):
    equity_curve = pd.DataFrame(sim.equity_curve)
    trades_df = pd.DataFrame(sim.trades)
    
    initial = INITIAL_CAPITAL
    final = sim.capital + (sim.equity_curve[-1]['position_value'] if len(sim.equity_curve) > 0 else 0)
    total_return = (final - initial) / initial * 100
    total_pnl = final - initial
    
    closes = trades_df[trades_df['type'].str.startswith('CLOSE_')] if len(trades_df) > 0 else pd.DataFrame()
    
    if len(closes) > 0:
        win_rate = sim.winning_trades / (sim.winning_trades + sim.losing_trades) * 100 if (sim.winning_trades + sim.losing_trades) > 0 else 0
        avg_win = closes[closes['pnl'] > 0]['pnl'].mean()
        avg_loss = closes[closes['pnl'] < 0]['pnl'].mean()
        profit_factor = abs(closes[closes['pnl'] > 0]['pnl'].sum() / closes[closes['pnl'] < 0]['pnl'].sum()) if closes[closes['pnl'] < 0]['pnl'].sum() != 0 else 0
        total_trades = len(closes)
        long_trades = len(closes[closes['type'] == 'CLOSE_LONG'])
        short_trades = len(closes[closes['type'] == 'CLOSE_SHORT'])
        
        # 持仓时间
        if 'holding_hours' in closes.columns:
            avg_holding = closes['holding_hours'].mean()
        else:
            avg_holding = 0
        
        # 止损统计
        stop_trades = closes[closes['reason'].str.contains('STOP', na=False)]
        stop_loss_count = len(stop_trades)
        stop_loss_rate = stop_loss_count / total_trades * 100 if total_trades > 0 else 0
    else:
        win_rate = avg_win = avg_loss = profit_factor = total_trades = long_trades = short_trades = avg_holding = stop_loss_rate = 0
        stop_loss_count = 0
    
    # 最大回撤
    if len(equity_curve) > 0:
        equity_curve['peak'] = equity_curve['total_equity'].cummax()
        equity_curve['drawdown'] = (equity_curve['total_equity'] - equity_curve['peak']) / equity_curve['peak'] * 100
        max_drawdown = equity_curve['drawdown'].min()
        max_drawdown_pct = abs(max_drawdown)
        
        days = len(equity_curve)
        annual_return = ((final / initial) ** (365 / days) - 1) * 100 if days > 0 else 0
        
        returns = equity_curve['total_equity'].pct_change().dropna()
        sharpe = returns.mean() / returns.std() * np.sqrt(365) if returns.std() > 0 else 0
    else:
        max_drawdown_pct = annual_return = sharpe = 0
    
    # 每日统计
    daily_stats = equity_curve.groupby('date').agg({
        'total_equity': 'last',
        'close': 'last'
    }).reset_index()
    daily_stats['daily_return'] = daily_stats['total_equity'].pct_change() * 100
    
    trading_days = len(daily_stats)
    profitable_days = len(daily_stats[daily_stats['daily_return'] > 0])
    losing_days = len(daily_stats[daily_stats['daily_return'] < 0])
    win_rate_days = profitable_days / trading_days * 100 if trading_days > 0 else 0
    best_day = daily_stats['daily_return'].max() if len(daily_stats) > 0 else 0
    worst_day = daily_stats['daily_return'].min() if len(daily_stats) > 0 else 0
    
    print("\n" + "=" * 70)
    print("              📊 回测报告 V2 - 优化策略 (币安1年)")
    print("=" * 70)
    
    print(f"""
┌─ 【基本信息】 ─────────────────────────────────────────────────────────────
│  交易标的:        {SYMBOL}
│  回测周期:        {df_signals.iloc[0]['timestamp'].strftime('%Y-%m-%d')} ~ {df_signals.iloc[-1]['timestamp'].strftime('%Y-%m-%d')}
│  数据频率:        1小时K线
│  交易天数:        {trading_days} 天
│  策略:            V2 (趋势过滤 + 指标共振)
└──────────────────────────────────────────────────────────────────────────────

┌─ 【账户概览】 ──────────────────────────────────────────────────────────────
│  初始资金:        ${initial:,.2f}
│  最终权益:        ${final:,.2f}
│  总收益:          ${total_pnl:,.2f}
│  总收益率:        {total_return:.2f}%
│  年化收益率:      {annual_return:.2f}%
│  夏普比率:        {sharpe:.2f}
│  最大回撤:        {max_drawdown_pct:.2f}%
└──────────────────────────────────────────────────────────────────────────────

┌─ 【交易统计】 ──────────────────────────────────────────────────────────────
│  总交易次数:      {total_trades}
│  做多次数:        {long_trades}
│  做空次数:        {short_trades}
│  胜率:            {win_rate:.2f}%
│  平均盈利:        ${avg_win:,.2f}
│  平均亏损:        ${avg_loss:,.2f}
│  盈亏比:          {profit_factor:.2f}
│  盈利交易:        {sim.winning_trades}
│  亏损交易:        {sim.losing_trades}
│  触发止损:        {stop_loss_count} 次 ({stop_loss_rate:.1f}%)
│  平均持仓:        {avg_holding:.1f} 小时
└──────────────────────────────────────────────────────────────────────────────

┌─ 【日度统计】 ──────────────────────────────────────────────────────────────
│  盈利天数:        {profitable_days} / {trading_days}
│  亏损天数:        {losing_days}
│  日胜率:          {win_rate_days:.2f}%
│  最佳单日:        {best_day:+.2f}%
│  最差单日:        {worst_day:+.2f}%
└──────────────────────────────────────────────────────────────────────────────

┌─ 【风控统计】 ──────────────────────────────────────────────────────────────
│  最大仓位:        ${MAX_POSITION:,.2f}
│  日亏损限制:      {DAILY_LOSS_LIMIT*100:.1f}%
│  止损策略:        5%固定止损 + 8%移动止损
│  趋势过滤:        EMA200多空过滤
│  共振要求:        ≥3指标确认才发STRONG信号
│  手续费:          {TRADE_FEE*100:.2f}%
└──────────────────────────────────────────────────────────────────────────────
""")
    
    # 信号分布
    print(f"┌─ 【信号分布】 ──────────────────────────────────────────────────────────────")
    signal_counts = df_signals['signal'].value_counts()
    for sig in ['STRONG_BUY', 'BUY', 'NEUTRAL', 'SELL', 'STRONG_SELL']:
        count = signal_counts.get(sig, 0)
        pct = count / len(df_signals) * 100
        bar = '█' * int(pct / 2)
        print(f"│  {sig:12s}: {count:5d} ({pct:5.1f}%) {bar}")
    print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 月度收益
    print(f"\n┌─ 【月度收益】 ──────────────────────────────────────────────────────────────")
    equity_curve['month'] = equity_curve['date'].str[:7]
    monthly = equity_curve.groupby('month').agg({
        'total_equity': ['first', 'last']
    })
    monthly.columns = ['start', 'end']
    monthly['return'] = (monthly['end'] - monthly['start']) / monthly['start'] * 100
    
    for month, row in monthly.iterrows():
        ret = row['return']
        sign = '+' if ret >= 0 else ''
        color = '🟢' if ret >= 0 else '🔴'
        print(f"│  {month}: {sign}{ret:6.2f}%  {color}")
    print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 平仓原因分析
    if len(closes) > 0:
        print(f"\n┌─ 【平仓原因分析】 ─────────────────────────────────────────────────────────")
        close_reasons = closes['reason'].value_counts()
        for reason, count in close_reasons.items():
            pct = count / len(closes) * 100
            print(f"│  {reason:20s}: {count:3d} ({pct:5.1f}%)")
        print(f"└──────────────────────────────────────────────────────────────────────────────")
    
    # 保存
    output_dir = '/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/backtest_results'
    os.makedirs(output_dir, exist_ok=True)
    
    equity_curve.to_csv(f'{output_dir}/equity_curve_v2.csv', index=False)
    trades_df.to_csv(f'{output_dir}/trades_v2.csv', index=False)
    df_signals.to_csv(f'{output_dir}/signals_v2.csv', index=False)
    
    summary = {
        'strategy': 'V2_TrendFilter_MultiSignal',
        'period': f"{df_signals.iloc[0]['timestamp'].strftime('%Y-%m-%d')} ~ {df_signals.iloc[-1]['timestamp'].strftime('%Y-%m-%d')}",
        'initial_capital': initial,
        'final_equity': final,
        'total_return_pct': total_return,
        'annual_return_pct': annual_return,
        'sharpe_ratio': sharpe,
        'max_drawdown_pct': max_drawdown_pct,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
    }
    
    with open(f'{output_dir}/summary_v2.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📁 V2详细数据已保存到: {output_dir}/")

if __name__ == '__main__':
    run_backtest_v2()
