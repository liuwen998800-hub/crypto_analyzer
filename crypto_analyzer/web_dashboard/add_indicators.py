#!/usr/bin/env python3
"""添加真实技术指标计算到app.py"""

# 读取app.py
with open('/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer/web_dashboard/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 要插入的技术指标计算函数
indicators_code = '''
# ==================== 真实技术指标计算 ====================

def get_binance_klines(symbol, timeframe='1h', limit=200):
    """从币安获取K线数据"""
    symbol_map = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'SOL': 'SOLUSDT'}
    binance_symbol = symbol_map.get(symbol, 'BTCUSDT')
    interval_map = {'1h': '1h', '4h': '4h', '24h': '1d'}
    interval = interval_map.get(timeframe, '1h')
    
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval={interval}&limit={limit}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10)
        data = json.loads(response.read().decode())
        
        klines = []
        for k in data:
            klines.append({
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5]),
                'time': int(k[0])
            })
        return klines
    except Exception as e:
        logger.error(f"获取K线失败: {e}")
        return None

def calculate_ema(prices, period):
    """计算指数移动平均线"""
    ema = [prices[0]]
    multiplier = 2 / (period + 1)
    for i in range(1, len(prices)):
        ema.append((prices[i] - ema[-1]) * multiplier + ema[-1])
    return ema

def calculate_rsi(prices, period=14):
    """计算RSI"""
    deltas = []
    for i in range(1, len(prices)):
        deltas.append(prices[i] - prices[i-1])
    
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 50.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """计算MACD"""
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    dif = [ema_fast[i] - ema_slow[i] for i in range(len(ema_fast))]
    dea = calculate_ema(dif, signal)
    
    macd = [2 * (dif[i] - dea[i]) for i in range(len(dif))]
    
    return {
        'dif': dif[-1],
        'dea': dea[-1],
        'macd': macd[-1]
    }

def calculate_bollinger_bands(prices, period=20):
    """计算布林带"""
    import statistics
    ma = statistics.mean(prices[-period:])
    std = statistics.stdev(prices[-period:])
    upper = ma + 2 * std
    lower = ma - 2 * std
    position = (prices[-1] - lower) / (upper - lower) * 100 if upper != lower else 50
    return {
        'upper': upper,
        'middle': ma,
        'lower': lower,
        'position': position
    }

def calculate_kdj(highs, lows, closes, period=9):
    """计算KDJ"""
    lowest_lows = []
    highest_highs = []
    
    for i in range(period - 1, len(closes)):
        lowest_lows.append(min(lows[i-period+1:i+1]))
        highest_highs.append(max(highs[i-period+1:i+1]))
    
    rsv = []
    for i in range(len(closes) - period + 1):
        if highest_highs[i] == lowest_lows[i]:
            rsv.append(50)
        else:
            rsv.append((closes[i + period - 1] - lowest_lows[i]) / (highest_highs[i] - lowest_lows[i]) * 100)
    
    k = 50.0
    d = 50.0
    for r in rsv:
        k = (2/3) * k + (1/3) * r
        d = (2/3) * d + (1/3) * k
    
    return k

def calculate_williams(highs, lows, closes, period=14):
    """计算威廉指标"""
    highest_high = max(highs[-period:])
    lowest_low = min(lows[-period:])
    
    if highest_high == lowest_low:
        return -50
    
    williams = (highest_high - closes[-1]) / (highest_high - lowest_low) * -100
    return williams

def calculate_atr(highs, lows, closes, period=14):
    """计算ATR"""
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        trs.append(tr)
    
    if len(trs) < period:
        return 0
    
    return sum(trs[-period:]) / period

def calculate_real_indicators(symbol, timeframe='1h'):
    """计算真实技术指标"""
    klines = get_binance_klines(symbol, timeframe)
    if not klines or len(klines) < 50:
        return None
    
    closes = [k['close'] for k in klines]
    highs = [k['high'] for k in klines]
    lows = [k['low'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    current_price = closes[-1]
    
    # 计算各项指标
    rsi14 = calculate_rsi(closes, 14)
    rsi6 = calculate_rsi(closes, 6)
    rsi12 = calculate_rsi(closes, 12)
    rsi24 = calculate_rsi(closes, 24)
    
    macd = calculate_macd(closes)
    
    bb = calculate_bollinger_bands(closes)
    
    kdj = calculate_kdj(highs, lows, closes)
    
    williams = calculate_williams(highs, lows, closes)
    
    atr = calculate_atr(highs, lows, closes)
    
    # EMA
    ema5 = calculate_ema(closes, 5)[-1]
    ema10 = calculate_ema(closes, 10)[-1]
    ema20 = calculate_ema(closes, 20)[-1]
    ema50 = calculate_ema(closes, 50)[-1]
    ema200 = calculate_ema(closes, 200)[-1] if len(closes) >= 200 else ema50
    
    # 均线信号
    if ema5 > ema10 > ema20:
        ma_signal = 'bullish'
    elif ema5 < ema10 < ema20:
        ma_signal = 'bearish'
    else:
        ma_signal = 'neutral'
    
    # 成交量
    vol_ma20 = sum(volumes[-20:]) / 20
    vol_current = volumes[-1]
    vol_ratio = vol_current / vol_ma20 if vol_ma20 > 0 else 1
    
    return {
        'current_price': current_price,
        'rsi6': rsi6,
        'rsi14': rsi14,
        'rsi12': rsi12,
        'rsi24': rsi24,
        'macd_dif': macd['dif'],
        'macd_dea': macd['dea'],
        'macd': macd['macd'],
        'bb_upper': bb['upper'],
        'bb_middle': bb['middle'],
        'bb_lower': bb['lower'],
        'bb_position': bb['position'],
        'kdj_k': kdj,
        'williams': williams,
        'atr': atr,
        'ema5': ema5,
        'ema10': ema10,
        'ema20': ema20,
        'ema50': ema50,
        'ema200': ema200,
        'ma_signal': ma_signal,
        'volume_current': vol_current,
        'volume_ma20': vol_ma20,
        'volume_ratio': vol_ratio
    }

'''

# 找到import语句之后的位置插入代码
import_pos = content.find('# ==================== 原始功能兼容 ====================')
if import_pos != -1:
    content = content[:import_pos] + indicators_code + '\n' + content[import_pos:]
    print("成功插入技术指标计算函数")
else:
    print("未找到插入位置")

# 写回文件
with open('/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer/web_dashboard/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py已更新")
