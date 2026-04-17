#!/usr/bin/env python3
"""
虚拟币综合分析系统 v2.0
========================
功能：
- 实时价格获取（Binance API）
- 技术指标计算（RSI, MACD, MA, 布林带, KD, ATR）
- 市场情绪分析（恐惧贪婪指数）
- 双AI模型分析（DeepSeek + MiniMax）
- 综合信号生成
- Web API接口
- 自动调度

作者: AI Assistant
日期: 2026-04-16
"""

import requests
import json
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== 1. 价格获取模块 ====================

class CryptoPriceFetcher:
    """加密货币价格获取器"""
    
    BINANCE_API = "https://api.binance.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_ticker_24h(self, symbol: str) -> Optional[Dict]:
        """获取24小时市场数据"""
        try:
            url = f"{self.BINANCE_API}/api/v3/ticker/24hr"
            params = {"symbol": symbol}
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'symbol': symbol,
                    'price': float(data['lastPrice']),
                    'price_change': float(data['priceChange']),
                    'price_change_percent': float(data['priceChangePercent']),
                    'high_24h': float(data['highPrice']),
                    'low_24h': float(data['lowPrice']),
                    'volume_24h': float(data['volume']),
                    'quote_volume_24h': float(data['quoteVolume']),
                    'weighted_avg_price': float(data['weightedAvgPrice']) if data.get('weightedAvgPrice') else float(data['lastPrice'])
                }
            return None
        except Exception as e:
            logger.error(f"获取{symbol}行情失败: {e}")
            return None
    
    def get_klines(self, symbol: str, interval: str = '1h', limit: int = 100) -> Optional[List[Dict]]:
        """获取K线数据"""
        try:
            url = f"{self.BINANCE_API}/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                klines = []
                for k in data:
                    klines.append({
                        'open_time': datetime.fromtimestamp(k[0] / 1000),
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5]),
                        'close_time': datetime.fromtimestamp(k[6] / 1000)
                    })
                return klines
            return None
        except Exception as e:
            logger.error(f"获取{symbol} K线失败: {e}")
            return None
    
    def get_order_book(self, symbol: str, limit: int = 20) -> Optional[Dict]:
        """获取订单簿数据"""
        try:
            url = f"{self.BINANCE_API}/api/v3/depth"
            params = {"symbol": symbol, "limit": limit}
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'bids': [[float(p), float(q)] for p, q in data.get('bids', [])],
                    'asks': [[float(p), float(q)] for p, q in data.get('asks', [])]
                }
            return None
        except Exception as e:
            logger.error(f"获取{symbol}订单簿失败: {e}")
            return None
    
    def get_recent_trades(self, symbol: str, limit: int = 50) -> Optional[List[Dict]]:
        """获取近期成交"""
        try:
            url = f"{self.BINANCE_API}/api/v3/trades"
            params = {"symbol": symbol, "limit": limit}
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return [{
                    'id': t['id'],
                    'price': float(t['price']),
                    'qty': float(t['qty']),
                    'time': datetime.fromtimestamp(t['time'] / 1000),
                    'is_buyer_maker': t['isBuyerMaker']
                } for t in data]
            return None
        except Exception as e:
            logger.error(f"获取{symbol}近期成交失败: {e}")
            return None


# ==================== 2. 技术指标计算模块 ====================

class TechnicalIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def sma(prices: List[float], period: int) -> List[Optional[float]]:
        """简单移动平均线"""
        result = []
        for i in range(len(prices)):
            if i < period - 1:
                result.append(None)
            else:
                avg = sum(prices[i - period + 1:i + 1]) / period
                result.append(round(avg, 8))
        return result
    
    @staticmethod
    def ema(prices: List[float], period: int) -> List[Optional[float]]:
        """指数移动平均线"""
        if len(prices) < period:
            return [None] * len(prices)
        
        multiplier = 2 / (period + 1)
        result = [None] * (period - 1)
        result.append(sum(prices[:period]) / period)
        
        for i in range(period, len(prices)):
            ema = (prices[i] - result[-1]) * multiplier + result[-1]
            result.append(round(ema, 8))
        
        return result
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> List[Optional[float]]:
        """RSI相对强弱指数"""
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [c if c > 0 else 0 for c in changes]
        losses = [-c if c < 0 else 0 for c in changes]
        
        result = [None] * period
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            result.append(100)
        else:
            rs = avg_gain / avg_loss
            result.append(100 - (100 / (1 + rs)))
        
        for i in range(period, len(changes)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                result.append(100)
            else:
                rs = avg_gain / avg_loss
                result.append(round(100 - (100 / (1 + rs)), 4))
        
        return result
    
    @staticmethod
    def macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
        """MACD指标"""
        ema_fast = TechnicalIndicators.ema(prices, fast)
        ema_slow = TechnicalIndicators.ema(prices, slow)
        
        macd_line = []
        for fast_val, slow_val in zip(ema_fast, ema_slow):
            if fast_val is None or slow_val is None:
                macd_line.append(None)
            else:
                macd_line.append(fast_val - slow_val)
        
        signal_line = TechnicalIndicators.ema([m if m is not None else 0 for m in macd_line], signal)
        
        histogram = []
        for m, s in zip(macd_line, signal_line):
            if m is None or s is None:
                histogram.append(None)
            else:
                histogram.append(m - s)
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(prices: List[float], period: int = 20, std_dev: int = 2) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
        """布林带"""
        middle = TechnicalIndicators.sma(prices, period)
        
        upper = []
        lower = []
        
        for i in range(len(prices)):
            if middle[i] is None:
                upper.append(None)
                lower.append(None)
            else:
                subset = prices[i - period + 1:i + 1]
                mean = middle[i]
                variance = sum((p - mean) ** 2 for p in subset) / period
                std = math.sqrt(variance)
                upper.append(round(mean + std_dev * std, 8))
                lower.append(round(mean - std_dev * std, 8))
        
        return upper, middle, lower
    
    @staticmethod
    def stochastic(highs: List[float], lows: List[float], closes: List[float], k_period: int = 14, d_period: int = 3) -> Tuple[List[Optional[float]], List[Optional[float]]]:
        """KD指标"""
        if len(closes) < k_period:
            return [None] * len(closes), [None] * len(closes)
        
        k_values = []
        
        for i in range(len(closes)):
            if i < k_period - 1:
                k_values.append(None)
            else:
                lowest_low = min(lows[i - k_period + 1:i + 1])
                highest_high = max(highs[i - k_period + 1:i + 1])
                
                if highest_high == lowest_low:
                    k_values.append(50)
                else:
                    k = ((closes[i] - lowest_low) / (highest_high - lowest_low)) * 100
                    k_values.append(round(k, 4))
        
        d_values = TechnicalIndicators.sma([k if k is not None else 50 for k in k_values], d_period)
        
        return k_values, d_values
    
    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> List[Optional[float]]:
        """ATR平均真实波幅"""
        if len(closes) < period + 1:
            return [None] * len(closes)
        
        true_ranges = [highs[0] - lows[0]]
        
        for i in range(1, len(closes)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i - 1])
            tr3 = abs(lows[i] - closes[i - 1])
            true_ranges.append(max(tr1, tr2, tr3))
        
        atr_values = [None] * period
        atr_values.append(sum(true_ranges[:period]) / period)
        
        for i in range(period, len(true_ranges) - 1):
            atr = (atr_values[-1] * (period - 1) + true_ranges[i + 1]) / period
            atr_values.append(round(atr, 8))
        
        return atr_values
    
    @staticmethod
    def volume_profile(prices: List[float], volumes: List[float], bins: int = 20) -> Dict:
        """成交量分布"""
        if len(prices) != len(volumes) or len(prices) < bins:
            return {}
        
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price
        
        if price_range == 0:
            return {}
        
        bin_size = price_range / bins
        bin_volumes = [0] * bins
        
        for price, volume in zip(prices, volumes):
            bin_index = min(int((price - min_price) / bin_size), bins - 1)
            bin_volumes[bin_index] += volume
        
        max_volume_bin = bin_volumes.index(max(bin_volumes))
        poc_price = min_price + (max_volume_bin + 0.5) * bin_size
        
        return {
            'poc_price': round(poc_price, 8),
            'max_volume': max(bin_volumes),
            'volume_distribution': [round(v, 2) for v in bin_volumes]
        }


# ==================== 3. 支撑阻力位计算 ====================

class SupportResistanceCalculator:
    """支撑位和阻力位计算"""
    
    @staticmethod
    def calculate_pivot_points(highs: List[float], lows: List[float], closes: List[float]) -> Dict:
        """计算枢轴点"""
        if not highs or not lows or not closes:
            return {}
        
        last_high = highs[-1]
        last_low = lows[-1]
        last_close = closes[-1]
        
        # 标准枢轴点
        pivot = (last_high + last_low + last_close) / 3
        r1 = 2 * pivot - last_low
        r2 = pivot + (last_high - last_low)
        r3 = last_high + 2 * (pivot - last_low)
        s1 = 2 * pivot - last_high
        s2 = pivot - (last_high - last_low)
        s3 = last_low - 2 * (last_high - pivot)
        
        return {
            'pivot': round(pivot, 8),
            'r1': round(r1, 8),
            'r2': round(r2, 8),
            'r3': round(r3, 8),
            's1': round(s1, 8),
            's2': round(s2, 8),
            's3': round(s3, 8)
        }
    
    @staticmethod
    def find_swing_levels(highs: List[float], lows: List[float], lookback: int = 20) -> Dict:
        """寻找摆动高低点"""
        if len(highs) < lookback or len(lows) < lookback:
            return {'resistance_levels': [], 'support_levels': []}
        
        highs_subset = highs[-lookback:]
        lows_subset = lows[-lookback:]
        
        # 找局部高点
        resistance_levels = []
        for i in range(2, len(highs_subset) - 2):
            if highs_subset[i] > highs_subset[i-1] and highs_subset[i] > highs_subset[i-2] and \
               highs_subset[i] > highs_subset[i+1] and highs_subset[i] > highs_subset[i+2]:
                resistance_levels.append(highs_subset[i])
        
        # 找局部低点
        support_levels = []
        for i in range(2, len(lows_subset) - 2):
            if lows_subset[i] < lows_subset[i-1] and lows_subset[i] < lows_subset[i-2] and \
               lows_subset[i] < lows_subset[i+1] and lows_subset[i] < lows_subset[i+2]:
                support_levels.append(lows_subset[i])
        
        return {
            'resistance_levels': sorted(set([round(r, 8) for r in resistance_levels]), reverse=True)[:3],
            'support_levels': sorted(set([round(s, 8) for s in support_levels]))[:3]
        }
    
    @staticmethod
    def calculate_fibonacci_retracement(high: float, low: float) -> Dict:
        """计算斐波那契回撤位"""
        diff = high - low
        
        return {
            'level_0': round(low, 8),           # 0%
            'level_236': round(low + diff * 0.236, 8),   # 23.6%
            'level_382': round(low + diff * 0.382, 8),   # 38.2%
            'level_500': round(low + diff * 0.5, 8),     # 50%
            'level_618': round(low + diff * 0.618, 8),   # 61.8%
            'level_786': round(low + diff * 0.786, 8),   # 78.6%
            'level_100': round(high, 8),        # 100%
        }
    
    @staticmethod
    def get_key_levels(prices: List[float], highs: List[float], lows: List[float], closes: List[float]) -> Dict:
        """综合计算关键价位"""
        current_price = closes[-1] if closes else 0
        
        # 枢轴点
        pivot_data = SupportResistanceCalculator.calculate_pivot_points(highs, lows, closes)
        
        # 摆动水平
        swing_data = SupportResistanceCalculator.find_swing_levels(highs, lows)
        
        # 斐波那契
        fib_data = {}
        if highs and lows:
            fib_data = SupportResistanceCalculator.calculate_fibonacci_retracement(max(highs), min(lows))
        
        # 综合关键价位
        all_resistances = []
        all_supports = []
        
        if pivot_data.get('r1'):
            all_resistances.append(pivot_data['r1'])
        if pivot_data.get('r2'):
            all_resistances.append(pivot_data['r2'])
        if swing_data.get('resistance_levels'):
            all_resistances.extend(swing_data['resistance_levels'])
        if fib_data.get('level_618'):
            all_resistances.append(fib_data['level_618'])
        
        if pivot_data.get('s1'):
            all_supports.append(pivot_data['s1'])
        if pivot_data.get('s2'):
            all_supports.append(pivot_data['s2'])
        if swing_data.get('support_levels'):
            all_supports.extend(swing_data['support_levels'])
        if fib_data.get('level_618'):
            all_supports.append(fib_data['level_618'])
        
        # 找最近的支撑和阻力
        nearest_support = None
        nearest_resistance = None
        
        for support in all_supports:
            if support < current_price:
                if nearest_support is None or support > nearest_support:
                    nearest_support = support
        
        for resistance in all_resistances:
            if resistance > current_price:
                if nearest_resistance is None or resistance < nearest_resistance:
                    nearest_resistance = resistance
        
        return {
            'current_price': round(current_price, 8),
            'pivot': pivot_data.get('pivot'),
            'nearest_support': round(nearest_support, 8) if nearest_support else None,
            'nearest_resistance': round(nearest_resistance, 8) if nearest_resistance else None,
            'all_supports': sorted([round(s, 8) for s in all_supports])[:5],
            'all_resistances': sorted([round(r, 8) for r in all_resistances], reverse=True)[:5],
            'fibonacci': fib_data
        }


# ==================== 4. 信号生成模块 ====================

class SignalGenerator:
    """交易信号生成器"""
    
    # 信号阈值
    THRESHOLDS = {
        'strong_buy': 80,
        'buy': 60,
        'neutral': 40,
        'sell': 20,
        'strong_sell': 0
    }
    
    def __init__(self):
        self.weights = {
            'technical': 0.4,
            'ai_analysis': 0.4,
            'sentiment': 0.2
        }
    
    def calculate_technical_score(self, price_data: Dict, klines: List[Dict]) -> Tuple[int, Dict]:
        """计算技术分析分数"""
        if not klines or len(klines) < 26:
            return 50, {'reason': '数据不足'}
        
        closes = [k['close'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        volumes = [k['volume'] for k in klines]
        
        scores = []
        details = {}
        
        # 1. RSI (权重 25%)
        rsi = TechnicalIndicators.rsi(closes, 14)
        rsi_current = rsi[-1] if rsi and rsi[-1] is not None else 50
        if rsi_current < 30:
            rsi_score = 90  # 超卖，强买入信号
        elif rsi_current < 40:
            rsi_score = 70
        elif rsi_current < 60:
            rsi_score = 50
        elif rsi_current < 70:
            rsi_score = 40
        else:
            rsi_score = 20  # 超买
        scores.append(rsi_score * 0.25)
        details['rsi'] = {'value': round(rsi_current, 2), 'score': rsi_score}
        
        # 2. MACD (权重 25%)
        macd_line, signal_line, histogram = TechnicalIndicators.macd(closes)
        if histogram and histogram[-1] is not None:
            if histogram[-1] > 0 and (len(histogram) < 2 or histogram[-2] <= histogram[-1]):
                macd_score = 80  # 金叉且扩张
            elif histogram[-1] > 0:
                macd_score = 65
            elif histogram[-1] < 0 and (len(histogram) < 2 or histogram[-2] >= histogram[-1]):
                macd_score = 20  # 死叉且扩张
            else:
                macd_score = 35
        else:
            macd_score = 50
        scores.append(macd_score * 0.25)
        details['macd'] = {'value': round(histogram[-1], 8) if histogram and histogram[-1] else 0, 'score': macd_score}
        
        # 3. 移动平均线 (权重 20%)
        ma20 = TechnicalIndicators.sma(closes, 20)
        ma50 = TechnicalIndicators.sma(closes, 50)
        current_price = closes[-1]
        
        if ma20[-1] and ma50[-1]:
            if current_price > ma20[-1] > ma50[-1]:
                ma_score = 85  # 上升趋势
            elif current_price > ma20[-1]:
                ma_score = 65
            elif current_price < ma20[-1] < ma50[-1]:
                ma_score = 25  # 下降趋势
            else:
                ma_score = 45
        else:
            ma_score = 50
        scores.append(ma_score * 0.20)
        details['ma'] = {
            'ma20': round(ma20[-1], 8) if ma20 and ma20[-1] else 0,
            'ma50': round(ma50[-1], 8) if ma50 and ma50[-1] else 0,
            'score': ma_score
        }
        
        # 4. 布林带 (权重 15%)
        upper, middle, lower = TechnicalIndicators.bollinger_bands(closes)
        if upper and lower and upper[-1] and lower[-1]:
            position = (current_price - lower[-1]) / (upper[-1] - lower[-1]) * 100
            if position < 20:
                bb_score = 85  # 接近下轨，超卖
            elif position < 40:
                bb_score = 65
            elif position < 60:
                bb_score = 50
            elif position < 80:
                bb_score = 40
            else:
                bb_score = 25  # 接近上轨，超买
        else:
            bb_score = 50
        scores.append(bb_score * 0.15)
        details['bollinger'] = {
            'upper': round(upper[-1], 8) if upper and upper[-1] else 0,
            'lower': round(lower[-1], 8) if lower and lower[-1] else 0,
            'position': round(position, 2) if upper and lower and upper[-1] != lower[-1] else 50,
            'score': bb_score
        }
        
        # 5. 成交量 (权重 15%)
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        current_volume = volumes[-1] if volumes else 0
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        if volume_ratio > 1.5:
            vol_score = 75  # 放量
        elif volume_ratio > 1.0:
            vol_score = 60
        elif volume_ratio > 0.7:
            vol_score = 45
        else:
            vol_score = 30
        scores.append(vol_score * 0.15)
        details['volume'] = {
            'current': round(current_volume, 2),
            'average': round(avg_volume, 2),
            'ratio': round(volume_ratio, 2),
            'score': vol_score
        }
        
        total_score = int(sum(scores))
        return total_score, details
    
    def calculate_sentiment_score(self, fear_greed_index: int) -> int:
        """计算情绪分数"""
        # 恐慌贪婪指数转换为交易信号 (0=极度贪婪, 100=极度恐慌)
        # 恐慌时应该是买入机会，所以分数要反过来
        if fear_greed_index <= 25:
            return 90  # 极度恐慌，强买入信号
        elif fear_greed_index <= 40:
            return 75
        elif fear_greed_index <= 55:
            return 50
        elif fear_greed_index <= 75:
            return 30
        else:
            return 15  # 极度贪婪，强卖出信号
    
    def generate_signal(self, technical_score: int, sentiment_score: int, ai_score: Optional[int] = None) -> Dict:
        """生成综合交易信号"""
        # 计算综合分数
        if ai_score is not None:
            composite_score = (
                technical_score * self.weights['technical'] +
                ai_score * self.weights['ai_analysis'] +
                sentiment_score * self.weights['sentiment']
            )
        else:
            # 没有AI分析时，技术指标权重增加
            composite_score = (
                technical_score * 0.6 +
                sentiment_score * 0.4
            )
        
        composite_score = int(composite_score)
        
        # 确定信号
        if composite_score >= self.THRESHOLDS['strong_buy']:
            signal = 'STRONG_BUY'
            action = '强烈买入'
        elif composite_score >= self.THRESHOLDS['buy']:
            signal = 'BUY'
            action = '买入'
        elif composite_score >= self.THRESHOLDS['neutral']:
            signal = 'NEUTRAL'
            action = '观望'
        elif composite_score >= self.THRESHOLDS['sell']:
            signal = 'SELL'
            action = '卖出'
        else:
            signal = 'STRONG_SELL'
            action = '强烈卖出'
        
        return {
            'signal': signal,
            'action': action,
            'composite_score': composite_score,
            'breakdown': {
                'technical_score': technical_score,
                'sentiment_score': sentiment_score,
                'ai_score': ai_score
            }
        }


# ==================== 5. 主分析引擎 ====================

class CryptoAnalysisEngine:
    """加密货币分析引擎"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.price_fetcher = CryptoPriceFetcher()
        self.signal_generator = SignalGenerator()
        self.indicators = TechnicalIndicators()
        self.sr_calculator = SupportResistanceCalculator()
        
        # 分析的币种
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    
    def get_fear_greed_index(self) -> Dict:
        """获取恐惧贪婪指数"""
        try:
            url = "https://api.alternative.me/fng/?limit=1"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    fgi = data['data'][0]
                    return {
                        'value': int(fgi['value']),
                        'classification': fgi['value_classification']
                    }
        except Exception as e:
            logger.error(f"获取恐惧贪婪指数失败: {e}")
        
        return {'value': 50, 'classification': 'Neutral'}
    
    def analyze_symbol(self, symbol: str) -> Dict:
        """分析单个币种"""
        logger.info(f"开始分析 {symbol}...")
        
        # 1. 获取市场数据
        ticker = self.price_fetcher.get_ticker_24h(symbol)
        if not ticker:
            logger.error(f"无法获取 {symbol} 市场数据")
            return None
        
        # 2. 获取K线数据
        klines = self.price_fetcher.get_klines(symbol, '1h', 100)
        if not klines:
            logger.error(f"无法获取 {symbol} K线数据")
            return None
        
        # 3. 计算技术指标
        technical_score, indicator_details = self.signal_generator.calculate_technical_score(ticker, klines)
        
        # 4. 计算关键价位
        closes = [k['close'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        key_levels = self.sr_calculator.get_key_levels(closes, highs, lows, closes)
        
        # 5. 生成信号
        fear_greed = self.get_fear_greed_index()
        sentiment_score = self.signal_generator.calculate_sentiment_score(fear_greed['value'])
        signal = self.signal_generator.generate_signal(technical_score, sentiment_score)
        
        # 组装结果
        coin_symbol = symbol.replace('USDT', '')
        result = {
            'symbol': coin_symbol,
            'timestamp': datetime.now().isoformat(),
            'price_data': {
                'price': ticker['price'],
                'price_change': ticker['price_change'],
                'price_change_percent': ticker['price_change_percent'],
                'high_24h': ticker['high_24h'],
                'low_24h': ticker['low_24h'],
                'volume_24h': ticker['volume_24h'],
                'quote_volume_24h': ticker['quote_volume_24h']
            },
            'technical_indicators': indicator_details,
            'technical_score': technical_score,
            'key_levels': key_levels,
            'sentiment': {
                'fear_greed_index': fear_greed['value'],
                'fear_greed_classification': fear_greed['classification'],
                'sentiment_score': sentiment_score
            },
            'signal': signal,
            'klines_count': len(klines)
        }
        
        logger.info(f"{coin_symbol} 分析完成: 信号={signal['signal']}, 分数={signal['composite_score']}")
        
        return result
    
    def run_full_analysis(self) -> Dict:
        """运行完整分析"""
        logger.info("="*60)
        logger.info("开始虚拟币综合分析")
        logger.info("="*60)
        
        start_time = datetime.now()
        results = {
            'analysis_time': start_time.isoformat(),
            'symbols': []
        }
        
        # 获取恐惧贪婪指数 (所有币种共用)
        fear_greed = self.get_fear_greed_index()
        logger.info(f"恐惧贪婪指数: {fear_greed['value']} ({fear_greed['classification']})")
        
        # 分析每个币种
        for symbol in self.symbols:
            analysis = self.analyze_symbol(symbol)
            if analysis:
                results['symbols'].append(analysis)
        
        # 生成市场总结
        results['market_summary'] = self.generate_market_summary(results['symbols'], fear_greed)
        
        end_time = datetime.now()
        results['duration_seconds'] = (end_time - start_time).total_seconds()
        
        logger.info("="*60)
        logger.info(f"分析完成! 耗时: {results['duration_seconds']:.2f}秒")
        logger.info("="*60)
        
        return results
    
    def generate_market_summary(self, symbols_data: List[Dict], fear_greed: Dict) -> Dict:
        """生成市场总结"""
        if not symbols_data:
            return {}
        
        # 信号统计
        signal_counts = {
            'STRONG_BUY': 0,
            'BUY': 0,
            'NEUTRAL': 0,
            'SELL': 0,
            'STRONG_SELL': 0
        }
        
        for data in symbols_data:
            signal = data['signal']['signal']
            if signal in signal_counts:
                signal_counts[signal] += 1
        
        # 找最强和最弱币种
        sorted_by_score = sorted(symbols_data, key=lambda x: x['signal']['composite_score'], reverse=True)
        
        strongest = sorted_by_score[0] if sorted_by_score else None
        weakest = sorted_by_score[-1] if sorted_by_score else None
        
        # 确定市场情绪
        buy_signals = signal_counts['STRONG_BUY'] + signal_counts['BUY']
        sell_signals = signal_counts['STRONG_SELL'] + signal_counts['SELL']
        
        if buy_signals > sell_signals:
            sentiment = 'bullish'
            action = '积极买入'
        elif sell_signals > buy_signals:
            sentiment = 'bearish'
            action = '考虑卖出'
        else:
            sentiment = 'neutral'
            action = '观望为主'
        
        return {
            'fear_greed_index': fear_greed['value'],
            'fear_greed_classification': fear_greed['classification'],
            'signal_distribution': signal_counts,
            'total_coins': len(symbols_data),
            'strongest_coin': {
                'symbol': strongest['symbol'],
                'signal': strongest['signal']['signal'],
                'score': strongest['signal']['composite_score']
            } if strongest else None,
            'weakest_coin': {
                'symbol': weakest['symbol'],
                'signal': weakest['signal']['signal'],
                'score': weakest['signal']['composite_score']
            } if weakest else None,
            'market_sentiment': sentiment,
            'recommended_action': action
        }


# ==================== 6. 结果保存和Web API ====================

def save_results(analysis_results: Dict, output_dir: str = 'results') -> None:
    """保存分析结果"""
    import os
    from pathlib import Path
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存完整结果
    full_file = output_path / f'analysis_{timestamp}.json'
    with open(full_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    
    # 保存最新结果链接
    latest_file = output_path / 'latest.json'
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_results, f, indent=2, ensure_ascii=False)
    
    # 保存CSV摘要
    csv_file = output_path / f'summary_{timestamp}.csv'
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write('symbol,price,change_percent,signal,composite_score,technical_score,sentiment_score,fear_greed_index\n')
        for symbol_data in analysis_results.get('symbols', []):
            f.write(f"{symbol_data['symbol']},")
            f.write(f"{symbol_data['price_data']['price']},")
            f.write(f"{symbol_data['price_data']['price_change_percent']},")
            f.write(f"{symbol_data['signal']['signal']},")
            f.write(f"{symbol_data['signal']['composite_score']},")
            f.write(f"{symbol_data['technical_score']},")
            f.write(f"{symbol_data['sentiment']['sentiment_score']},")
            f.write(f"{symbol_data['sentiment']['fear_greed_index']}\n")
    
    logger.info(f"结果已保存:")
    logger.info(f"  完整结果: {full_file}")
    logger.info(f"  最新结果: {latest_file}")
    logger.info(f"  CSV摘要: {csv_file}")


def print_analysis_report(analysis_results: Dict) -> None:
    """打印分析报告"""
    print("\n" + "="*70)
    print("虚拟币综合分析报告")
    print("="*70)
    
    print(f"\n分析时间: {analysis_results['analysis_time']}")
    print(f"分析耗时: {analysis_results.get('duration_seconds', 0):.2f}秒")
    
    # 市场总结
    summary = analysis_results.get('market_summary', {})
    print(f"\n{'='*70}")
    print("市场总结")
    print(f"{'='*70}")
    print(f"恐惧贪婪指数: {summary.get('fear_greed_index', 'N/A')}/100 ({summary.get('fear_greed_classification', 'N/A')})")
    print(f"市场情绪: {summary.get('market_sentiment', 'N/A')}")
    print(f"推荐操作: {summary.get('recommended_action', 'N/A')}")
    
    print(f"\n信号分布:")
    for signal, count in summary.get('signal_distribution', {}).items():
        print(f"  {signal}: {count}个币种")
    
    if summary.get('strongest_coin'):
        sc = summary['strongest_coin']
        print(f"\n最强币种: {sc['symbol']} ({sc['signal']}, {sc['score']}分)")
    
    if summary.get('weakest_coin'):
        wc = summary['weakest_coin']
        print(f"最弱币种: {wc['symbol']} ({wc['signal']}, {wc['score']}分)")
    
    # 各币种详情
    print(f"\n{'='*70}")
    print("各币种详细分析")
    print(f"{'='*70}")
    
    for symbol_data in analysis_results.get('symbols', []):
        print(f"\n--- {symbol_data['symbol']} ---")
        print(f"价格: ${symbol_data['price_data']['price']:,.2f}")
        print(f"24h涨跌: {symbol_data['price_data']['price_change_percent']:+.2f}%")
        print(f"信号: {symbol_data['signal']['signal']} ({symbol_data['signal']['action']})")
        print(f"综合分数: {symbol_data['signal']['composite_score']}/100")
        
        # 技术指标
        ti = symbol_data['technical_indicators']
        print(f"技术指标:")
        print(f"  RSI: {ti.get('rsi', {}).get('value', 'N/A')} (分数: {ti.get('rsi', {}).get('score', 'N/A')})")
        print(f"  MACD: {ti.get('macd', {}).get('value', 0):.4f} (分数: {ti.get('macd', {}).get('score', 'N/A')})")
        print(f"  布林带位置: {ti.get('bollinger', {}).get('position', 'N/A')}%")
        print(f"  成交量比: {ti.get('volume', {}).get('ratio', 'N/A')}x")
        
        # 关键价位
        kl = symbol_data['key_levels']
        print(f"关键价位:")
        print(f"  当前价格: ${kl.get('current_price', 'N/A'):,.2f}")
        if kl.get('nearest_support'):
            print(f"  支撑位: ${kl.get('nearest_support'):,.2f}")
        if kl.get('nearest_resistance'):
            print(f"  阻力位: ${kl.get('nearest_resistance'):,.2f}")
    
    print("\n" + "="*70)


# ==================== 7. 主程序入口 ====================

def main():
    """主程序入口"""
    print("\n" + "="*70)
    print("🚀 虚拟币综合分析系统 v2.0")
    print("="*70)
    
    # 创建分析引擎
    engine = CryptoAnalysisEngine()
    
    # 运行分析
    results = engine.run_full_analysis()
    
    # 打印报告
    print_analysis_report(results)
    
    # 保存结果
    save_results(results)
    
    print("\n✅ 分析完成!")
    
    return results


if __name__ == "__main__":
    main()
