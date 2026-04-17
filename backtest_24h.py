#!/usr/bin/env python3
"""
Polymarket式24H策略 - 币安1年历史回测
- 初始资金: $10,000
- 最大仓位: $1,000
- 日亏损控制: 5%
- 信号: STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL
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
INITIAL_CAPITAL = 10000      # 初始资金
MAX_POSITION = 1000         # 最大仓位
DAILY_LOSS_LIMIT = 0.05     # 日亏损限制 5%
SYMBOL = 'BTCUSDT'
INTERVAL = '1h'              # 1小时K线
START_DATE = '2024-04-16'   # 1年前
END_DATE = '2025-04-16'     # 现在
TRADE_FEE = 0.001            # 手续费 0.1%

# ========== 币安API获取K线数据 ==========
def get_binance_klines(symbol, interval, start_str, end_str=None, limit=1000):
    """获取币安K线数据"""
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
                print(f"API错误: {data}")
                break
            all_klines.extend(data)
            if len(data) < limit:
                break
            # 移动到下一个时间窗口
            last_time = int(data[-1][0])
            params['startTime'] = last_time + 1
            time.sleep(0.2)  # 避免频率限制
        except Exception as e:
            print(f"获取数据异常: {e}")
            break
    
    return all_klines

def parse_klines(klines):
    """解析K线数据为DataFrame"""
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

# ========== 技术指标计算 ==========
def calculate_rsi(prices, period=14):
    """计算RSI"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """计算MACD"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - signal_line
    return macd_line, signal_line, macd_hist

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """计算布林带"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    position = (prices - lower_band) / (upper_band - lower_band + 1e-10)
    return upper_band, lower_band, position

def calculate_ma_signal(prices):
    """计算均线多空信号"""
    ma5 = prices.rolling(5).mean()
    ma20 = prices.rolling(20).mean()
    ma60 = prices.rolling(60).mean()
    
    if ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]:
        return 'bullish'
    elif ma5.iloc[-1] < ma20.iloc[-1] < ma60.iloc[-1]:
        return 'bearish'
    else:
        return 'neutral'

def calculate_fear_greed_index(prices, volumes):
    """模拟恐惧贪婪指数 (基于价格波动率和成交量)"""
    # 计算近期波动率
    returns = prices.pct_change()
    volatility = returns.rolling(14).std() * 100
    current_vol = volatility.iloc[-1] if not np.isnan(volatility.iloc[-1]) else 20
    
    # 计算成交量变化
    vol_change = volumes.pct_change().rolling(14).mean().iloc[-1] * 100 if not np.isnan(volatility.iloc[-1]) else 0
    
    # 基于波动率估算恐惧贪婪 (0-100)
    if current_vol > 8:
        fear_greed = max(10, 50 - (current_vol - 5) * 4)
    elif current_vol < 2:
        fear_greed = min(90, 50 + (3 - current_vol) * 10)
    else:
        fear_greed = 50
    
    # 成交量调整
    if vol_change > 30:
        fear_greed = min(100, fear_greed + 10)
    elif vol_change < -30:
        fear_greed = max(0, fear_greed - 10)
    
    return int(np.clip(fear_greed, 0, 100))

# ========== 生成分析信号 (模拟DeepSeek + MiniMax双模型) ==========
def generate_signal(row, lookback_df):
    """
    生成交易信号
    核心逻辑:
    - Technical Score (40%): RSI + MACD + MA + Bollinger
    - AI Score (40%): Fear/Greed + 24h动量
    - Price Score (20%): 24h涨跌
    """
    prices = lookback_df['close']
    current_price = row['close']
    
    # ========== DeepSeek 技术分析 ==========
    rsi = row['rsi'] if not np.isnan(row['rsi']) else 50
    macd_val = row['macd'] if not np.isnan(row['macd']) else 0
    bb_pos = row['bb_position'] if not np.isnan(row['bb_position']) else 50
    ma_signal = row['ma_signal']
    
    # RSI分析 (权重25%)
    if rsi < 25:
        rsi_bullish = 95
    elif rsi < 35:
        rsi_bullish = 80
    elif rsi < 45:
        rsi_bullish = 65
    elif rsi < 55:
        rsi_bullish = 50
    elif rsi < 65:
        rsi_bullish = 35
    elif rsi < 75:
        rsi_bullish = 20
    else:
        rsi_bullish = 5
    
    # MACD分析 (权重30%)
    if macd_val > 5:
        macd_bullish = 90
    elif macd_val > 0:
        macd_bullish = 70
    elif macd_val > -5:
        macd_bullish = 40
    else:
        macd_bullish = 15
    
    # 均线分析 (权重25%)
    if ma_signal == 'bullish':
        ma_bullish = 85
    elif ma_signal == 'bearish':
        ma_bullish = 15
    else:
        ma_bullish = 50
    
    # 布林带分析 (权重20%)
    if bb_pos < 15:
        bb_bullish = 95
    elif bb_pos < 25:
        bb_bullish = 80
    elif bb_pos < 35:
        bb_bullish = 65
    elif bb_pos < 50:
        bb_bullish = 50
    elif bb_pos < 65:
        bb_bullish = 35
    elif bb_pos < 85:
        bb_bullish = 20
    else:
        bb_bullish = 5
    
    # 技术评分
    technical_score = int(rsi_bullish * 0.25 + macd_bullish * 0.30 + ma_bullish * 0.25 + bb_bullish * 0.20)
    
    # ========== MiniMax 情绪分析 ==========
    fear_greed = row['fear_greed']
    price_change_24h = row['price_change_24h_pct']
    
    # 恐慌贪婪分析 (权重50%)
    if fear_greed < 20:
        emotion_bullish, emotion_bearish = 95, 5
    elif fear_greed < 30:
        emotion_bullish, emotion_bearish = 85, 15
    elif fear_greed < 45:
        emotion_bullish, emotion_bearish = 70, 30
    elif fear_greed < 55:
        emotion_bullish, emotion_bearish = 50, 50
    elif fear_greed < 70:
        emotion_bullish, emotion_bearish = 30, 70
    elif fear_greed < 85:
        emotion_bullish, emotion_bearish = 15, 85
    else:
        emotion_bullish, emotion_bearish = 5, 95
    
    # 24h动量分析 (权重50%)
    if price_change_24h > 5:
        momentum_bullish, momentum_bearish = 90, 10
    elif price_change_24h > 2:
        momentum_bullish, momentum_bearish = 75, 25
    elif price_change_24h > 0:
        momentum_bullish, momentum_bearish = 60, 40
    elif price_change_24h > -2:
        momentum_bullish, momentum_bearish = 40, 60
    elif price_change_24h > -5:
        momentum_bullish, momentum_bearish = 25, 75
    else:
        momentum_bullish, momentum_bearish = 10, 90
    
    # 情绪评分
    ai_score = int((emotion_bullish * 0.5 + momentum_bullish * 0.5))
    
    # ========== 价格评分 ==========
    if price_change_24h > 2:
        price_score = 80
    elif price_change_24h > 0:
        price_score = 60
    elif price_change_24h > -2:
        price_score = 40
    else:
        price_score = 20
    
    # ========== 综合评分 ==========
    composite = int(technical_score * 0.4 + ai_score * 0.4 + price_score * 0.2)
    
    # ========== 信号 ==========
    if composite >= 80:
        signal = 'STRONG_BUY'
    elif composite >= 60:
        signal = 'BUY'
    elif composite >= 40:
        signal = 'NEUTRAL'
    elif composite >= 20:
        signal = 'SELL'
    else:
        signal = 'STRONG_SELL'
    
    return {
        'signal': signal,
        'composite': composite,
        'technical_score': technical_score,
        'ai_score': ai_score,
        'price_score': price_score,
        'rsi': rsi,
        'macd': macd_val,
        'fear_greed': fear_greed,
        'price_change_24h_pct': price_change_24h,
        'close': current_price
    }

# ========== 交易模拟器 ==========
class TradingSimulator:
    def __init__(self, initial_capital=INITIAL_CAPITAL, max_position=MAX_POSITION, daily_loss_limit=DAILY_LOSS_LIMIT):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.max_position = max_position
        self.daily_loss_limit = daily_loss_limit
        
        self.position = 0  # 持仓数量
        self.position_value = 0  # 持仓价值
        self.position_type = None  # 'long' or 'short'
        self.entry_price = 0
        
        self.trades = []  # 交易记录
        self.daily_pnl = {}  # 每日盈亏
        self.equity_curve = []  # 权益曲线
        
        # 持仓统计
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0
        
        # 风险控制
        self.daily_start_capital = initial_capital
        self.daily_loss_taken = 0
        self.trading_paused = False
        
    def open_position(self, signal, price, timestamp):
        """开仓"""
        if self.position != 0:
            return  # 已有持仓不重复开
        
        # 仓位计算
        position_value = min(self.max_position, self.capital * 0.5)  # 最大用50%资金
        shares = position_value / price
        
        if signal in ['STRONG_BUY', 'BUY']:
            self.position_type = 'long'
            cost = shares * price * (1 + TRADE_FEE)
            if cost <= self.capital:
                self.position = shares
                self.entry_price = price
                self.capital -= cost
                self.position_value = shares * price
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
            self.capital += proceeds  # 做空收到现金
            self.position_value = shares * price
            self.trades.append({
                'timestamp': timestamp,
                'type': 'OPEN_SHORT',
                'price': price,
                'shares': shares,
                'value': position_value,
                'signal': signal
            })
    
    def close_position(self, reason, price, timestamp):
        """平仓"""
        if self.position == 0:
            return
        
        shares = self.position
        if self.position_type == 'long':
            proceeds = shares * price * (1 - TRADE_FEE)
            pnl = proceeds - (shares * self.entry_price * (1 + TRADE_FEE))
            self.capital += proceeds
        else:  # short
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
            'capital_after': self.capital
        })
        
        self.position = 0
        self.position_value = 0
        self.position_type = None
        self.entry_price = 0
    
    def check_daily_loss(self, current_date):
        """检查日亏损"""
        daily_pnl = self.capital - self.daily_start_capital
        if daily_pnl < -self.daily_start_capital * self.daily_loss_limit:
            self.daily_loss_taken += 1
            return True
        return False
    
    def update_daily(self, current_date, close_price):
        """更新日结算"""
        date_str = current_date.strftime('%Y-%m-%d')
        
        # 更新持仓市值
        if self.position > 0:
            if self.position_type == 'long':
                self.position_value = self.position * close_price
            else:
                self.position_value = self.position * close_price
        
        # 记录权益
        total_equity = self.capital + self.position_value
        self.equity_curve.append({
            'date': date_str,
            'capital': self.capital,
            'position_value': self.position_value,
            'total_equity': total_equity,
            'close': close_price
        })
        
        # 记录日盈亏
        daily_pnl = total_equity - self.daily_start_capital
        self.daily_pnl[date_str] = daily_pnl
    
    def new_day(self, current_date):
        """新的一天重置"""
        date_str = current_date.strftime('%Y-%m-%d')
        total_equity = self.capital + self.position_value
        self.daily_pnl[date_str] = 0
        self.daily_start_capital = total_equity
        self.daily_loss_taken = 0
        self.trading_paused = False
    
    def should_close(self, signal):
        """判断是否需要平仓"""
        if self.position == 0:
            return False
        
        # 止损: 反向信号
        if self.position_type == 'long' and signal in ['STRONG_SELL', 'SELL']:
            return True
        if self.position_type == 'short' and signal in ['STRONG_BUY', 'BUY']:
            return True
        
        # 止盈: 持仓超过3天且有盈利
        return False
    
    def get_status(self):
        """获取当前状态"""
        total_equity = self.capital + self.position_value
        return {
            'capital': self.capital,
            'position_value': self.position_value,
            'total_equity': total_equity,
            'position': self.position,
            'position_type': self.position_type,
            'entry_price': self.entry_price,
            'pnl': total_equity - self.initial_capital
        }

# ========== 主回测函数 ==========
def run_backtest():
    print("=" * 70)
    print("24H策略 - 币安1年历史回测")
    print("=" * 70)
    print(f"初始资金: ${INITIAL_CAPITAL:,.2f}")
    print(f"最大仓位: ${MAX_POSITION:,.2f}")
    print(f"日亏损限制: {DAILY_LOSS_LIMIT*100:.1f}%")
    print(f"手续费: {TRADE_FEE*100:.2f}%")
    print("=" * 70)
    
    # ========== Step 1: 获取数据 ==========
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
            print(f"  数据已缓存到 {cache_file}")
    
    if not raw_klines:
        print("获取数据失败!")
        return
    
    print(f"  获取到 {len(raw_klines)} 根K线")
    
    # ========== Step 2: 解析并计算指标 ==========
    print("\n[2/5] 解析数据并计算技术指标...")
    df = parse_klines(raw_klines)
    df = df.set_index('open_time')
    
    # 计算24h变化率 (使用前24根1h K线)
    df['price_change_24h_pct'] = df['close'].pct_change(24) * 100
    
    # 技术指标
    print("  计算RSI...")
    df['rsi'] = calculate_rsi(df['close'], 14)
    
    print("  计算MACD...")
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df['close'])
    
    print("  计算布林带...")
    df['bb_upper'], df['bb_lower'], df['bb_position'] = calculate_bollinger_bands(df['close'])
    
    print("  计算均线信号...")
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    
    def ma_signal_func(row):
        if pd.isna(row['ma5']) or pd.isna(row['ma20']) or pd.isna(row['ma60']):
            return 'neutral'
        if row['ma5'] > row['ma20'] > row['ma60']:
            return 'bullish'
        elif row['ma5'] < row['ma20'] < row['ma60']:
            return 'bearish'
        else:
            return 'neutral'
    
    df['ma_signal'] = df.apply(ma_signal_func, axis=1)
    
    print("  计算恐惧贪婪指数...")
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
    
    df = df.dropna(subset=['rsi', 'macd', 'bb_position'])
    print(f"  有效数据点: {len(df)}")
    
    # ========== Step 3: 生成信号 ==========
    print("\n[3/5] 生成交易信号...")
    signals = []
    for i in range(60, len(df)):
        lookback = df.iloc[:i+1]
        row = df.iloc[i]
        sig = generate_signal(row, lookback)
        sig['timestamp'] = row.name
        sig['close'] = row['close']
        signals.append(sig)
    
    df_signals = pd.DataFrame(signals)
    print(f"  生成信号数: {len(df_signals)}")
    
    signal_counts = df_signals['signal'].value_counts()
    print(f"  信号分布: {dict(signal_counts)}")
    
    # ========== Step 4: 运行交易模拟 ==========
    print("\n[4/5] 运行交易模拟...")
    simulator = TradingSimulator()
    
    current_date = None
    last_close_price = None
    
    for idx, row in df_signals.iterrows():
        ts = row['timestamp']
        price = row['close']
        signal = row['signal']
        
        # 新的一天
        if current_date != ts.date():
            if current_date is not None:
                simulator.new_day(ts)
            current_date = ts.date()
            last_close_price = price
        
        # 日亏损检查
        if simulator.check_daily_loss(ts):
            if simulator.position != 0:
                simulator.close_position('DAILY_LOSS_STOP', price, ts)
                simulator.trading_paused = True
            simulator.update_daily(ts, price)
            continue
        
        # 更新权益
        simulator.update_daily(ts, price)
        
        # 交易逻辑
        if simulator.position == 0 and not simulator.trading_paused:
            # 开仓
            if signal in ['STRONG_BUY', 'BUY']:
                simulator.open_position(signal, price, ts)
            elif signal in ['STRONG_SELL', 'SELL']:
                simulator.open_position(signal, price, ts)
        elif simulator.position != 0:
            # 平仓检查
            if simulator.should_close(signal):
                simulator.close_position('SIGNAL_REVERSE', price, ts)
            # 止损检查 (持仓亏损超过10%自动止损)
            if simulator.position_type == 'long':
                loss_pct = (simulator.entry_price - price) / simulator.entry_price
                if loss_pct > 0.10:
                    simulator.close_position('STOP_LOSS', price, ts)
            elif simulator.position_type == 'short':
                loss_pct = (price - simulator.entry_price) / simulator.entry_price
                if loss_pct > 0.10:
                    simulator.close_position('STOP_LOSS', price, ts)
    
    # 最终平仓
    if simulator.position != 0:
        final_price = df_signals.iloc[-1]['close']
        simulator.close_position('END_OF_BACKTEST', final_price, df_signals.iloc[-1]['timestamp'])
    
    # ========== Step 5: 生成报告 ==========
    print("\n[5/5] 生成回测报告...")
    generate_report(simulator, df_signals)
    
    return simulator, df_signals

def generate_report(simulator, df_signals):
    """生成完整回测报告"""
    
    equity_curve = pd.DataFrame(simulator.equity_curve)
    trades_df = pd.DataFrame(simulator.trades)
    
    initial = INITIAL_CAPITAL
    final = simulator.capital + simulator.position_value
    total_return = (final - initial) / initial * 100
    total_pnl = final - initial
    
    # 统计交易
    if len(trades_df) > 0:
        closes = trades_df[trades_df['type'].str.startswith('CLOSE_')]
        if len(closes) > 0:
            win_rate = simulator.winning_trades / (simulator.winning_trades + simulator.losing_trades) * 100 if (simulator.winning_trades + simulator.losing_trades) > 0 else 0
            avg_win = closes[closes['pnl'] > 0]['pnl'].mean() if len(closes[closes['pnl'] > 0]) > 0 else 0
            avg_loss = closes[closes['pnl'] < 0]['pnl'].mean() if len(closes[closes['pnl'] < 0]) > 0 else 0
            profit_factor = abs(closes[closes['pnl'] > 0]['pnl'].sum() / closes[closes['pnl'] < 0]['pnl'].sum()) if closes[closes['pnl'] < 0]['pnl'].sum() != 0 else 0
            
            total_trades = len(closes)
            long_trades = len(closes[closes['type'] == 'CLOSE_LONG'])
            short_trades = len(closes[closes['type'] == 'CLOSE_SHORT'])
        else:
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
            total_trades = 0
            long_trades = 0
            short_trades = 0
    else:
        win_rate = 0
        avg_win = 0
        avg_loss = 0
        profit_factor = 0
        total_trades = 0
        long_trades = 0
        short_trades = 0
    
    # 最大回撤
    if len(equity_curve) > 0:
        equity_curve['peak'] = equity_curve['total_equity'].cummax()
        equity_curve['drawdown'] = (equity_curve['total_equity'] - equity_curve['peak']) / equity_curve['peak'] * 100
        max_drawdown = equity_curve['drawdown'].min()
        max_drawdown_pct = abs(max_drawdown)
        
        # 年化收益
        days = len(equity_curve)
        annual_return = ((final / initial) ** (365 / days) - 1) * 100 if days > 0 else 0
        
        # 夏普比率 (简化)
        if len(equity_curve) > 30:
            returns = equity_curve['total_equity'].pct_change().dropna()
            sharpe = returns.mean() / returns.std() * np.sqrt(365) if returns.std() > 0 else 0
        else:
            sharpe = 0
    else:
        max_drawdown_pct = 0
        annual_return = 0
        sharpe = 0
    
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
    print("                    📊 回测报告 - 24H策略 (币安1年)")
    print("=" * 70)
    
    print(f"""
┌─ 【基本信息】 ─────────────────────────────────────────────────────────────
│  交易标的:        {SYMBOL}
│  回测周期:        {df_signals.iloc[0]['timestamp'].strftime('%Y-%m-%d')} ~ {df_signals.iloc[-1]['timestamp'].strftime('%Y-%m-%d')}
│  数据频率:        1小时K线
│  K线总数:         {len(df_signals):,} 根
│  交易天数:        {trading_days} 天
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
│  盈利交易:        {simulator.winning_trades}
│  亏损交易:        {simulator.losing_trades}
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
│  止损线:          10% 移动止损
│  手续费:          {TRADE_FEE*100:.2f}%
└──────────────────────────────────────────────────────────────────────────────
""")
    
    # 信号分析
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
    
    # 保存详细数据
    output_dir = '/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/backtest_results'
    os.makedirs(output_dir, exist_ok=True)
    
    equity_curve.to_csv(f'{output_dir}/equity_curve.csv', index=False)
    trades_df.to_csv(f'{output_dir}/trades.csv', index=False)
    df_signals.to_csv(f'{output_dir}/signals.csv', index=False)
    
    # 保存汇总
    summary = {
        'strategy': '24H_Binance',
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
        'best_day_pct': best_day,
        'worst_day_pct': worst_day,
    }
    
    with open(f'{output_dir}/summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📁 详细数据已保存到: {output_dir}/")
    print(f"   - equity_curve.csv  (权益曲线)")
    print(f"   - trades.csv        (交易记录)")
    print(f"   - signals.csv       (信号序列)")
    print(f"   - summary.json      (汇总数据)")
    
    # 生成简单ASCII权益曲线
    print(f"\n┌─ 【权益曲线】 ──────────────────────────────────────────────────────────────")
    if len(equity_curve) > 0:
        eq = equity_curve['total_equity'].values
        # 归一化显示
        eq_norm = (eq - eq.min()) / (eq.max() - eq.min() + 1e-10)
        # 按月采样显示
        monthly_eq = equity_curve.groupby('month')['total_equity'].last().values
        monthly_norm = (monthly_eq - monthly_eq.min()) / (monthly_eq.max() - monthly_eq.min() + 1e-10)
        
        chart = ""
        for v in monthly_norm:
            height = int(v * 20)
            chart += f"{'█' * height:25s} |\n"
        print(chart)
    print(f"└──────────────────────────────────────────────────────────────────────────────")

if __name__ == '__main__':
    run_backtest()
