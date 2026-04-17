"""
技术指标计算模块
基于现有评分体系计算技术指标并评分
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging
import yaml
from pathlib import Path

# 尝试导入TA-Lib，如果失败则使用备用实现
try:
    import talib
    TA_LIB_AVAILABLE = True
except ImportError:
    TA_LIB_AVAILABLE = False
    import warnings
    warnings.warn("TA-Lib未安装，使用备用技术指标计算")

logger = logging.getLogger(__name__)


class TechnicalIndicatorsCalculator:
    """技术指标计算器"""
    
    def __init__(self, scoring_rules_path: Optional[str] = None):
        """
        初始化技术指标计算器
        
        Args:
            scoring_rules_path: 评分规则配置文件路径
        """
        # 加载评分规则
        if scoring_rules_path and Path(scoring_rules_path).exists():
            with open(scoring_rules_path, 'r', encoding='utf-8') as f:
                self.scoring_rules = yaml.safe_load(f)
        else:
            # 默认评分规则
            self.scoring_rules = {
                'technical_scoring': {
                    'rsi': {
                        'oversold_threshold': 30,
                        'overbought_threshold': 70,
                        'scoring': {
                            'below_30': 90, '30_40': 70, '40_60': 50,
                            '60_70': 30, 'above_70': 10
                        }
                    }
                }
            }
        
        logger.info("技术指标计算器初始化完成")
    
    def calculate_all_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算所有技术指标
        
        Args:
            df: 包含OHLCV数据的DataFrame
            
        Returns:
            包含所有技术指标的字典
        """
        if df.empty or len(df) < 50:
            logger.warning("数据不足，无法计算技术指标")
            return {}
        
        try:
            results = {}
            
            # 基础价格数据
            close_prices = df['close'].values
            high_prices = df['high'].values
            low_prices = df['low'].values
            volume = df['volume'].values
            
            # 1. RSI (相对强弱指数)
            rsi_values = self.calculate_rsi(close_prices)
            rsi_score = self.score_rsi(rsi_values[-1] if len(rsi_values) > 0 else 50)
            
            # 2. MACD (移动平均收敛发散)
            macd_values = self.calculate_macd(close_prices)
            macd_score = self.score_macd(macd_values)
            
            # 3. 移动平均线
            ma_values = self.calculate_moving_averages(close_prices)
            ma_score = self.score_moving_averages(close_prices, ma_values)
            
            # 4. 布林带
            bb_values = self.calculate_bollinger_bands(close_prices)
            bb_score = self.score_bollinger_bands(close_prices[-1], bb_values)
            
            # 5. 成交量分析
            volume_score = self.score_volume(volume, close_prices)
            
            # 6. 支撑阻力位
            support_resistance = self.calculate_support_resistance(df)
            
            # 7. 综合技术评分
            technical_score = self.calculate_composite_score({
                'rsi': rsi_score,
                'macd': macd_score,
                'moving_averages': ma_score,
                'bollinger_bands': bb_score,
                'volume': volume_score
            })
            
            # 组装结果
            results = {
                'indicators': {
                    'rsi': {
                        'value': float(rsi_values[-1]) if len(rsi_values) > 0 else 50.0,
                        'score': rsi_score,
                        'signal': self.get_rsi_signal(rsi_values[-1] if len(rsi_values) > 0 else 50)
                    },
                    'macd': {
                        'macd_line': float(macd_values['macd'][-1]) if len(macd_values['macd']) > 0 else 0.0,
                        'signal_line': float(macd_values['signal'][-1]) if len(macd_values['signal']) > 0 else 0.0,
                        'histogram': float(macd_values['histogram'][-1]) if len(macd_values['histogram']) > 0 else 0.0,
                        'score': macd_score,
                        'signal': self.get_macd_signal(macd_values)
                    },
                    'moving_averages': {
                        'sma_7': float(ma_values['sma_7'][-1]) if len(ma_values['sma_7']) > 0 else close_prices[-1],
                        'sma_20': float(ma_values['sma_20'][-1]) if len(ma_values['sma_20']) > 0 else close_prices[-1],
                        'sma_50': float(ma_values['sma_50'][-1]) if len(ma_values['sma_50']) > 0 else close_prices[-1],
                        'score': ma_score,
                        'signal': self.get_ma_signal(close_prices[-1], ma_values)
                    },
                    'bollinger_bands': {
                        'upper': float(bb_values['upper'][-1]) if len(bb_values['upper']) > 0 else close_prices[-1],
                        'middle': float(bb_values['middle'][-1]) if len(bb_values['middle']) > 0 else close_prices[-1],
                        'lower': float(bb_values['lower'][-1]) if len(bb_values['lower']) > 0 else close_prices[-1],
                        'bandwidth': float(bb_values['bandwidth'][-1]) if len(bb_values['bandwidth']) > 0 else 0.0,
                        'score': bb_score,
                        'signal': self.get_bb_signal(close_prices[-1], bb_values)
                    },
                    'volume': {
                        'current': float(volume[-1]) if len(volume) > 0 else 0.0,
                        'avg_20': float(np.mean(volume[-20:])) if len(volume) >= 20 else float(np.mean(volume)),
                        'score': volume_score,
                        'signal': self.get_volume_signal(volume, close_prices)
                    }
                },
                'support_resistance': support_resistance,
                'composite_score': {
                    'technical_score': technical_score,
                    'breakdown': {
                        'rsi': rsi_score,
                        'macd': macd_score,
                        'moving_averages': ma_score,
                        'bollinger_bands': bb_score,
                        'volume': volume_score
                    },
                    'confidence': self.calculate_confidence({
                        'rsi': rsi_score,
                        'macd': macd_score,
                        'moving_averages': ma_score
                    })
                },
                'current_price': float(close_prices[-1]),
                'timestamp': df.index[-1].isoformat() if hasattr(df.index[-1], 'isoformat') else str(df.index[-1])
            }
            
            logger.info(f"技术指标计算完成，综合评分: {technical_score}")
            return results
            
        except Exception as e:
            logger.error(f"计算技术指标失败: {e}")
            return {}
    
    def calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """计算RSI指标"""
        if TA_LIB_AVAILABLE:
            return talib.RSI(prices, timeperiod=period)
        else:
            # 备用RSI实现
            deltas = np.diff(prices)
            seed = deltas[:period+1]
            up = seed[seed >= 0].sum() / period
            down = -seed[seed < 0].sum() / period
            rs = up / down if down != 0 else 0
            rsi = np.zeros_like(prices)
            rsi[:period] = 100.0 - 100.0 / (1.0 + rs)
            
            for i in range(period, len(prices)):
                delta = deltas[i-1]
                if delta > 0:
                    upval = delta
                    downval = 0.0
                else:
                    upval = 0.0
                    downval = -delta
                
                up = (up * (period - 1) + upval) / period
                down = (down * (period - 1) + downval) / period
                rs = up / down if down != 0 else 0
                rsi[i] = 100.0 - 100.0 / (1.0 + rs)
            
            return rsi
    
    def calculate_macd(self, prices: np.ndarray, fastperiod: int = 12, slowperiod: int = 26, signalperiod: int = 9) -> Dict:
        """计算MACD指标"""
        if TA_LIB_AVAILABLE:
            macd, signal, hist = talib.MACD(prices, fastperiod=fastperiod, 
                                           slowperiod=slowperiod, signalperiod=signalperiod)
        else:
            # 备用MACD实现
            ema_fast = self.calculate_ema(prices, fastperiod)
            ema_slow = self.calculate_ema(prices, slowperiod)
            macd = ema_fast - ema_slow
            signal = self.calculate_ema(macd, signalperiod)
            hist = macd - signal
        
        return {
            'macd': macd,
            'signal': signal,
            'histogram': hist
        }
    
    def calculate_moving_averages(self, prices: np.ndarray) -> Dict:
        """计算移动平均线"""
        periods = [7, 20, 50]
        results = {}
        
        for period in periods:
            if TA_LIB_AVAILABLE:
                sma = talib.SMA(prices, timeperiod=period)
            else:
                sma = self.calculate_sma(prices, period)
            results[f'sma_{period}'] = sma
        
        return results
    
    def calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, nbdev: float = 2.0) -> Dict:
        """计算布林带"""
        if TA_LIB_AVAILABLE:
            upper, middle, lower = talib.BBANDS(prices, timeperiod=period, 
                                               nbdevup=nbdev, nbdevdn=nbdev)
        else:
            # 备用布林带实现
            middle = self.calculate_sma(prices, period)
            std = pd.Series(prices).rolling(window=period).std()
            upper = middle + (std * nbdev)
            lower = middle - (std * nbdev)
        
        # 计算带宽
        bandwidth = ((upper - lower) / middle) * 100
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'bandwidth': bandwidth
        }
    
    def calculate_support_resistance(self, df: pd.DataFrame, lookback: int = 20) -> Dict:
        """计算支撑阻力位"""
        if len(df) < lookback:
            return {'supports': [], 'resistances': []}
        
        # 使用最近的数据
        recent_df = df.tail(lookback)
        
        # 寻找局部高点和低点
        highs = recent_df['high'].values
        lows = recent_df['low'].values
        
        supports = []
        resistances = []
        
        # 简单实现：使用近期高低点
        current_price = df['close'].iloc[-1]
        
        # 支撑位：近期低点
        recent_lows = sorted(lows)[:3]  # 取3个最低点
        for low in recent_lows:
            if low < current_price * 0.95:  # 低于当前价格5%以上
                supports.append(float(low))
        
        # 阻力位：近期高点
        recent_highs = sorted(highs, reverse=True)[:3]  # 取3个最高点
        for high in recent_highs:
            if high > current_price * 1.05:  # 高于当前价格5%以上
                resistances.append(float(high))
        
        # 添加移动平均线作为动态支撑阻力
        ma_values = self.calculate_moving_averages(df['close'].values)
        for period in [20, 50]:
            ma_key = f'sma_{period}'
            if ma_key in ma_values and len(ma_values[ma_key]) > 0:
                ma_value = ma_values[ma_key][-1]
                if ma_value < current_price:
                    supports.append(float(ma_value))
                else:
                    resistances.append(float(ma_value))
        
        # 去重并排序
        supports = sorted(list(set(supports)), reverse=True)
        resistances = sorted(list(set(resistances)))
        
        return {
            'supports': supports[:5],  # 最多返回5个支撑位
            'resistances': resistances[:5],  # 最多返回5个阻力位
            'current_price': float(current_price)
        }
    
    # 评分函数
    def score_rsi(self, rsi_value: float) -> int:
        """RSI评分"""
        rules = self.scoring_rules.get('technical_scoring', {}).get('rsi', {})
        scoring = rules.get('scoring', {})
        
        if rsi_value < 30:
            return scoring.get('below_30', 90)
        elif 30 <= rsi_value < 40:
            return scoring.get('30_40', 70)
        elif 40 <= rsi_value < 60:
            return scoring.get('40_60', 50)
        elif 60 <= rsi_value < 70:
            return scoring.get('60_70', 30)
        else:  # rsi_value >= 70
            return scoring.get('above_70', 10)
    
    def score_macd(self, macd_values: Dict) -> int:
        """MACD评分"""
        if len(macd_values['histogram']) == 0:
            return 50
        
        hist = macd_values['histogram'][-1]
        macd_line = macd_values['macd'][-1]
        signal_line = macd_values['signal'][-1]
        
        score = 50  # 中性基础分
        
        # 柱状图方向
        if hist > 0:
            score += 20  # 看涨
        elif hist < 0:
            score -= 20  # 看跌
        
        # MACD线与信号线关系
        if macd_line > signal_line:
            score += 10  # 金叉或在上方
        elif macd_line < signal_line:
            score -= 10  # 死叉或在下方
        
        return max(0, min(100, score))
    
    def score_moving_averages(self, current_price: float, ma_values: Dict) -> int:
        """移动平均线评分"""
        score = 50
        
        # 检查价格与均线关系
        above_count = 0
        below_count = 0
        
        for period in [7, 20, 50]:
            ma_key = f'sma_{period}'
            if ma_key in ma_values and len(ma_values[ma_key]) > 0:
                ma_value = ma_values[ma_key][-1]
                if current_price > ma_value:
                    above_count += 1
                else:
                    below_count += 1
        
        # 价格在多数均线上方 -> 看涨
        if above_count > below_count:
            score += 20
        # 价格在多数均线下方 -> 看跌
        elif below_count > above_count:
            score -= 20
        
        # 检查均线排列（多头/空头）
        if 'sma_7' in ma_values and 'sma_20' in ma_values and 'sma_50' in ma_values:
            sma_7 = ma_values['sma_7'][-1] if len(ma_values['sma_7']) > 0 else current_price
            sma_20 = ma_values['sma_20'][-1] if len(ma_values['sma_20']) > 0 else current_price
            sma_50 = ma_values['sma_50'][-1] if len(ma_values['sma_50']) > 0 else current_price
            
            # 多头排列：短期 > 中期 > 长期
            if sma_7 > sma_20 > sma_50:
                score += 15
            # 空头排列：短期 < 中期 < 长期
            elif sma_7 < sma_20 < sma_50:
                score -= 15
        
        return max(0, min(100, score))
    
    def score_bollinger_bands(self, current_price: float, bb_values: Dict) -> int:
        """布林带评分"""
        if len(bb_values['upper']) == 0 or len(bb_values['lower']) == 0:
            return 50
        
        upper = bb_values['upper'][-1]
        lower = bb_values['lower'][-1]
        middle = bb_values['middle'][-1]
        
        score = 50
        
        # 价格在布林带中的位置
        band_width = upper - lower
        if band_width > 0:
            position = (current_price - lower) / band_width
            
            if position < 0.2:  # 接近下轨
                score += 20  # 超卖，买入机会
            elif position > 0.8:  # 接近上轨
                score -= 20  # 超买，卖出机会
        
        # 布林带收缩（低波动率）
        bandwidth_value = bb_values['bandwidth'][-1] if len(bb_values['bandwidth']) > 0 else 0
        if bandwidth_value < 10:  # 带宽小于10%
            score += 10  # 低波动率，可能即将突破
        
        return max(0, min(100, score))
    
    def score_volume(self, volume: np.ndarray, prices: np.ndarray) -> int:
        """成交量评分"""
        if len(volume) < 20:
            return 50
        
        score = 50
        current_volume = volume[-1]
        avg_volume_20 = np.mean(volume[-20:])
        
        # 成交量放大
        if current_volume > avg_volume_20 * 1.5:
            # 结合价格方向
            if prices[-1] > prices[-2]:  # 放量上涨
                score += 20
            else:  # 放量下跌
                score -= 10
        elif current_volume < avg_volume_20 * 0.5:  # 成交量萎缩
            score -= 5
        
        return max(0, min(100, score))
    
    def calculate_composite_score(self, component_scores: Dict) -> int:
        """计算综合技术评分"""
        weights = {
            'rsi': 0.25,
            'macd': 0.25,
            'moving_averages': 0.20,
            'bollinger_bands': 0.15,
            'volume': 0.15
        }
        
        total_score = 0
        total_weight = 0
        
        for component, weight in weights.items():
            if component in component_scores:
                total_score += component_scores[component] * weight
                total_weight += weight
        
        if total_weight > 0:
            return int(round(total_score / total_weight))
        else:
            return 50
    
    def calculate_confidence(self, key_scores: Dict) -> float:
        """计算置信度（基于关键指标的一致性）"""
        if not key_scores:
            return 0.5
        
        scores = list(key_scores.values())
        
        # 计算指标间的一致性
        variance = np.var(scores) / 10000  # 归一化到0-1
        consistency = 1.0 - min(variance, 1.0)
        
        # 基于平均分数的置信度调整
        avg_score = np.mean(scores)
        if 30 <= avg_score <= 70:  # 中性区域，置信度较低
            confidence = consistency * 0.7
        else:  # 极端区域，置信度较高
            confidence = consistency * 0.9
        
        return round(confidence, 2)
    
    # 信号生成函数
    def get_rsi_signal(self, rsi_value: float) -> str:
        """生成RSI信号"""
        if rsi_value < 30:
            return "强烈买入（超卖）"
        elif rsi_value < 40:
            return "买入（接近超卖）"
        elif rsi_value < 60:
            return "中性"
        elif rsi_value < 70:
            return "卖出（接近超买）"
        else:
            return "强烈卖出（超买）"
    
    def get_macd_signal(self, macd_values: Dict) -> str:
        """生成MACD信号"""
        if len(macd_values['histogram']) == 0:
            return "无信号"
        
        hist = macd_values['histogram'][-1]
        macd_line = macd_values['macd'][-1]
        signal_line = macd_values['signal'][-1]
        
        if hist > 0 and macd_line > signal_line:
            return "强烈买入（金叉）"
        elif hist > 0:
            return "买入（柱状图为正）"
        elif hist < 0 and macd_line < signal_line:
            return "强烈卖出（死叉）"
        elif hist < 0:
            return "卖出（柱状图为负）"
        else:
            return "中性"
    
    def get_ma_signal(self, current_price: float, ma_values: Dict) -> str:
        """生成移动平均线信号"""
        above_count = 0
        for period in [7, 20, 50]:
            ma_key = f'sma_{period}'
            if ma_key in ma_values and len(ma_values[ma_key]) > 0:
                if current_price > ma_values[ma_key][-1]:
                    above_count += 1
        
        if above_count >= 2:
            return "买入（价格在多数均线上方）"
        elif above_count <= 1:
            return "卖出（价格在多数均线下方）"
        else:
            return "中性"
    
    def get_bb_signal(self, current_price: float, bb_values: Dict) -> str:
        """生成布林带信号"""
        if len(bb_values['upper']) == 0:
            return "无信号"
        
        upper = bb_values['upper'][-1]
        lower = bb_values['lower'][-1]
        
        if current_price < lower:
            return "强烈买入（突破下轨）"
        elif current_price > upper:
            return "强烈卖出（突破上轨）"
        elif current_price < (lower + (upper - lower) * 0.3):
            return "买入（接近下轨）"
        elif current_price > (lower + (upper - lower) * 0.7):
            return "卖出（接近上轨）"
        else:
            return "中性（中轨附近）"
    
    def get_volume_signal(self, volume: np.ndarray, prices: np.ndarray) -> str:
        """生成成交量信号"""
        if len(volume) < 2:
            return "无信号"
        
        current_volume = volume[-1]
        prev_volume = volume[-2]
        price_change = prices[-1] - prices[-2]
        
        if current_volume > prev_volume * 1.5:
            if price_change > 0:
                return "买入（放量上涨）"
            else:
                return "卖出（放量下跌）"
        elif current_volume < prev_volume * 0.7:
            return "观望（缩量）"
        else:
            return "中性（正常成交量）"
    
    # 辅助计算函数
    def calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """计算指数移动平均线"""
        if len(prices) < period:
            return np.full_like(prices, np.nan)
        
        ema = np.zeros_like(prices)
        ema[:period] = np.mean(prices[:period])
        
        multiplier = 2 / (period + 1)
        for i in range(period, len(prices)):
            ema[i] = (prices[i] - ema[i-1]) * multiplier + ema[i-1]
        
        return ema
    
    def calculate_sma(self, prices: np.ndarray, period: int) -> np.ndarray:
        """计算简单移动平均线"""
        if len(prices) < period:
            return np.full_like(prices, np.nan)
        
        sma = np.zeros_like(prices)
        for i in range(period-1, len(prices)):
            sma[i] = np.mean(prices[i-period+1:i+1])
        
        return sma


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 创建测试数据
    np.random.seed(42)
    dates = pd.date_range('2026-01-01', periods=100, freq='H')
    base_price = 50000
    prices = base_price + np.cumsum(np.random.randn(100) * 1000)
    
    df = pd.DataFrame({
        'open': prices - np.random.rand(100) * 100,
        'high': prices + np.random.rand(100) * 200,
        'low': prices - np.random.rand(100) * 200,
        'close': prices,
        'volume': np.random.rand(100) * 1000 + 500
    }, index=dates)
    
    # 创建计算器
    calculator = TechnicalIndicatorsCalculator()
    
    # 计算技术指标
    results = calculator.calculate_all_indicators(df)
    
    if results:
        print("✅ 技术指标计算完成")
        print(f"当前价格: ${results['current_price']:,.2f}")
        print(f"综合技术评分: {results['composite_score']['technical_score']}")
        print(f"置信度: {results['composite_score']['confidence']}")
        
        print("\n支撑位:")
        for support in results['support_resistance']['supports'][:3]:
            print(f"  - ${support:,.2f}")
        
        print("\n阻力位:")
        for resistance in results['support_resistance']['resistances'][:3]:
            print(f"  - ${resistance:,.2f}")
        
        print("\n各指标信号:")
        for indicator, data in results['indicators'].items():
            if 'signal' in data:
                print(f"  {indicator.upper()}: {data['signal']} (评分: {data.get('score', 'N/A')})")
    else:
        print("❌ 技术指标计算失败")