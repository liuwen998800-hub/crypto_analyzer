"""
恐慌情绪分析模块
计算市场恐慌贪婪指数
"""

import requests
import json
import time
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


class FearGreedAnalyzer:
    """恐慌贪婪指数分析器"""
    
    def __init__(self, config: Dict = None):
        """
        初始化情绪分析器
        
        Args:
            config: 配置字典，包含API密钥等
        """
        self.config = config or {}
        self.cache = {}
        self.cache_ttl = 300  # 缓存5分钟
        
        # 数据源配置
        self.data_sources = {
            'alternative_me': 'https://api.alternative.me/fng/',  # 免费API
            'twitter': None,  # 需要Twitter API
            'reddit': None,   # 需要Reddit API
            'news': None      # 需要新闻API
        }
        
        logger.info("恐慌情绪分析器初始化完成")
    
    def calculate_fear_greed_index(self, symbol: str = 'BTC') -> Dict:
        """
        计算恐慌贪婪指数
        
        Args:
            symbol: 币种符号（目前主要支持BTC）
            
        Returns:
            恐慌贪婪指数数据
        """
        # 检查缓存
        cache_key = f"fgi_{symbol}_{datetime.now().strftime('%Y%m%d%H')}"
        if cache_key in self.cache:
            cache_time, cached_data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_ttl:
                logger.info(f"使用缓存的恐慌贪婪指数: {symbol}")
                return cached_data
        
        try:
            # 尝试从多个数据源获取
            fgi_data = self._fetch_from_alternative_me()
            
            if not fgi_data:
                # 如果主要数据源失败，使用模拟数据
                fgi_data = self._generate_mock_fgi()
            
            # 计算综合指数
            composite_fgi = self._calculate_composite_fgi(fgi_data, symbol)
            
            # 缓存结果
            self.cache[cache_key] = (time.time(), composite_fgi)
            
            logger.info(f"恐慌贪婪指数计算完成: {symbol}, 指数: {composite_fgi.get('value', 0)}")
            return composite_fgi
            
        except Exception as e:
            logger.error(f"计算恐慌贪婪指数失败: {e}")
            return self._generate_mock_fgi()
    
    def _fetch_from_alternative_me(self) -> Optional[Dict]:
        """从Alternative.me获取恐慌贪婪指数"""
        try:
            response = requests.get(
                self.data_sources['alternative_me'],
                params={'limit': 1, 'format': 'json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    fgi_data = data['data'][0]
                    return {
                        'value': int(fgi_data.get('value', 50)),
                        'classification': fgi_data.get('value_classification', 'Neutral'),
                        'timestamp': int(fgi_data.get('timestamp', time.time())),
                        'source': 'alternative.me'
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f"从Alternative.me获取数据失败: {e}")
            return None
    
    def _calculate_composite_fgi(self, base_fgi: Dict, symbol: str) -> Dict:
        """计算综合恐慌贪婪指数"""
        if not base_fgi:
            base_fgi = {'value': 50, 'classification': 'Neutral'}
        
        # 基础指数
        base_value = base_fgi.get('value', 50)
        
        # 计算其他因素（模拟）
        volatility_factor = self._calculate_volatility_factor(symbol)
        social_factor = self._calculate_social_sentiment(symbol)
        volume_factor = self._calculate_volume_factor(symbol)
        
        # 加权计算
        weights = {
            'base': 0.5,
            'volatility': 0.2,
            'social': 0.2,
            'volume': 0.1
        }
        
        composite_value = (
            base_value * weights['base'] +
            volatility_factor * weights['volatility'] +
            social_factor * weights['social'] +
            volume_factor * weights['volume']
        )
        
        # 确保在0-100范围内
        composite_value = max(0, min(100, composite_value))
        
        # 分类
        classification = self._classify_fgi(composite_value)
        
        # 计算分数（反向：恐慌=高分，贪婪=低分）
        # 在交易系统中，恐慌时买入机会（高分），贪婪时卖出机会（低分）
        score = 100 - composite_value  # 恐慌时分数高
        
        return {
            'value': int(round(composite_value)),
            'classification': classification,
            'score': int(round(score)),
            'breakdown': {
                'base': base_value,
                'volatility': volatility_factor,
                'social': social_factor,
                'volume': volume_factor,
                'weights': weights
            },
            'description': self._get_fgi_description(composite_value),
            'trading_implication': self._get_trading_implication(composite_value),
            'timestamp': datetime.now().isoformat(),
            'source': 'composite'
        }
    
    def _calculate_volatility_factor(self, symbol: str) -> float:
        """计算波动率因子（模拟）"""
        # 在实际系统中，这里应该计算实际波动率
        # 模拟：随机生成50-70的值
        import random
        return random.uniform(50, 70)
    
    def _calculate_social_sentiment(self, symbol: str) -> float:
        """计算社交媒体情绪因子（模拟）"""
        # 在实际系统中，这里应该分析Twitter/Reddit情绪
        # 模拟：随机生成40-80的值
        import random
        return random.uniform(40, 80)
    
    def _calculate_volume_factor(self, symbol: str) -> float:
        """计算成交量因子（模拟）"""
        # 在实际系统中，这里应该分析成交量变化
        # 模拟：随机生成30-90的值
        import random
        return random.uniform(30, 90)
    
    def _classify_fgi(self, value: float) -> str:
        """分类恐慌贪婪指数"""
        if value >= 80:
            return "Extreme Greed"
        elif value >= 60:
            return "Greed"
        elif value >= 40:
            return "Neutral"
        elif value >= 20:
            return "Fear"
        else:
            return "Extreme Fear"
    
    def _get_fgi_description(self, value: float) -> str:
        """获取指数描述"""
        if value >= 80:
            return "市场极度贪婪，投资者过于乐观，可能是卖出信号"
        elif value >= 60:
            return "市场贪婪，投资者情绪积极"
        elif value >= 40:
            return "市场情绪中性，投资者观望"
        elif value >= 20:
            return "市场恐惧，投资者情绪悲观"
        else:
            return "市场极度恐惧，投资者恐慌，可能是买入机会"
    
    def _get_trading_implication(self, value: float) -> str:
        """获取交易含义"""
        if value >= 80:
            return "强烈卖出信号 - 市场过热，回调风险高"
        elif value >= 60:
            return "谨慎卖出 - 市场情绪过于乐观"
        elif value >= 40:
            return "中性 - 等待更明确信号"
        elif value >= 20:
            return "考虑买入 - 市场恐惧提供机会"
        else:
            return "强烈买入信号 - 极度恐惧通常是底部信号"
    
    def _generate_mock_fgi(self) -> Dict:
        """生成模拟恐慌贪婪指数"""
        import random
        
        value = random.randint(25, 75)
        classification = self._classify_fgi(value)
        score = 100 - value
        
        return {
            'value': value,
            'classification': classification,
            'score': score,
            'breakdown': {
                'base': value,
                'volatility': random.randint(40, 80),
                'social': random.randint(30, 70),
                'volume': random.randint(50, 90)
            },
            'description': self._get_fgi_description(value),
            'trading_implication': self._get_trading_implication(value),
            'timestamp': datetime.now().isoformat(),
            'source': 'mock',
            'is_mock': True
        }
    
    def analyze_market_sentiment(self, symbol: str) -> Dict:
        """
        综合分析市场情绪
        
        Args:
            symbol: 币种符号
            
        Returns:
            综合情绪分析
        """
        # 获取恐慌贪婪指数
        fgi_data = self.calculate_fear_greed_index(symbol)
        
        # 计算情绪分数（用于交易系统）
        sentiment_score = fgi_data.get('score', 50)
        
        # 确定情绪信号
        if sentiment_score >= 80:
            signal = 'extreme_fear_buy'
            signal_strength = 'strong'
        elif sentiment_score >= 60:
            signal = 'fear_buy'
            signal_strength = 'moderate'
        elif sentiment_score >= 40:
            signal = 'neutral'
            signal_strength = 'weak'
        elif sentiment_score >= 20:
            signal = 'greed_sell'
            signal_strength = 'moderate'
        else:
            signal = 'extreme_greed_sell'
            signal_strength = 'strong'
        
        # 情绪对技术分析的影响权重
        # 恐慌时技术信号更可靠，贪婪时需谨慎
        reliability_factor = sentiment_score / 100  # 0-1，越高越可靠
        
        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'fear_greed_index': fgi_data,
            'sentiment_score': sentiment_score,
            'signal': signal,
            'signal_strength': signal_strength,
            'reliability_factor': round(reliability_factor, 2),
            'trading_advice': self._get_sentiment_trading_advice(sentiment_score),
            'impact_on_technical': self._get_technical_impact(sentiment_score)
        }
    
    def _get_sentiment_trading_advice(self, score: int) -> str:
        """获取基于情绪的交易建议"""
        if score >= 80:
            return "市场极度恐慌，是良好的买入机会，可分批建仓"
        elif score >= 60:
            return "市场恐惧，可考虑逢低买入，设置严格止损"
        elif score >= 40:
            return "市场情绪中性，以技术分析为主，控制仓位"
        elif score >= 20:
            return "市场贪婪，考虑减仓或设置止盈"
        else:
            return "市场极度贪婪，风险较高，建议减仓或观望"
    
    def _get_technical_impact(self, score: int) -> Dict:
        """获取情绪对技术分析的影响"""
        if score >= 80:  # 极度恐慌
            return {
                'rsi_weight': 1.2,  # RSI超卖信号更可靠
                'support_weight': 1.3,  # 支撑位更有效
                'resistance_weight': 0.8,  # 阻力位可能被突破
                'overall_impact': 'positive'  # 对技术分析有正面影响
            }
        elif score >= 60:  # 恐慌
            return {
                'rsi_weight': 1.1,
                'support_weight': 1.1,
                'resistance_weight': 0.9,
                'overall_impact': 'slightly_positive'
            }
        elif score >= 40:  # 中性
            return {
                'rsi_weight': 1.0,
                'support_weight': 1.0,
                'resistance_weight': 1.0,
                'overall_impact': 'neutral'
            }
        elif score >= 20:  # 贪婪
            return {
                'rsi_weight': 0.9,
                'support_weight': 0.9,
                'resistance_weight': 1.1,
                'overall_impact': 'slightly_negative'
            }
        else:  # 极度贪婪
            return {
                'rsi_weight': 0.8,  # RSI超买信号需谨慎
                'support_weight': 0.7,  # 支撑位可能失效
                'resistance_weight': 1.2,  # 阻力位更有效
                'overall_impact': 'negative'  # 对技术分析有负面影响
            }


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 创建分析器
    analyzer = FearGreedAnalyzer()
    
    # 测试恐慌贪婪指数
    print("测试恐慌贪婪指数分析...")
    fgi_result = analyzer.calculate_fear_greed_index('BTC')
    
    if fgi_result:
        print("✅ 恐慌贪婪指数计算完成")
        print(f"指数值: {fgi_result['value']} ({fgi_result['classification']})")
        print(f"情绪分数: {fgi_result['score']}/100")
        print(f"描述: {fgi_result['description']}")
        print(f"交易含义: {fgi_result['trading_implication']}")
        
        print("\n细分因素:")
        for factor, value in fgi_result['breakdown'].items():
            if factor != 'weights':
                print(f"  {factor}: {value}")
    
    # 测试综合情绪分析
    print("\n测试综合情绪分析...")
    sentiment_result = analyzer.analyze_market_sentiment('BTC')
    
    if sentiment_result:
        print("✅ 情绪分析完成")
        print(f"情绪信号: {sentiment_result['signal']} ({sentiment_result['signal_strength']})")
        print(f"可靠性因子: {sentiment_result['reliability_factor']}")
        print(f"交易建议: {sentiment_result['trading_advice']}")
        
        print("\n对技术分析的影响:")
        impact = sentiment_result['impact_on_technical']
        for key, value in impact.items():
            print(f"  {key}: {value}")