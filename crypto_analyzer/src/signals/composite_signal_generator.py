"""
综合信号生成模块
结合技术指标、AI分析和恐慌情绪生成交易信号
"""

import json
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class CompositeSignalGenerator:
    """综合信号生成器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化信号生成器
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        if config_path and Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            # 默认配置
            self.config = {
                'scoring_weights': {
                    'technical': 0.4,
                    'ai_analysis': 0.4,
                    'sentiment': 0.2
                },
                'signal_thresholds': {
                    'strong_buy': 80,
                    'buy': 60,
                    'neutral': 40,
                    'sell': 20,
                    'strong_sell': 0
                }
            }
        
        logger.info("综合信号生成器初始化完成")
    
    def generate_signal(self, symbol: str, 
                       technical_data: Dict,
                       ai_analysis: Dict,
                       sentiment_data: Dict) -> Dict:
        """
        生成综合交易信号
        
        Args:
            symbol: 币种符号
            technical_data: 技术分析数据
            ai_analysis: AI分析数据
            sentiment_data: 情绪分析数据
            
        Returns:
            综合交易信号
        """
        try:
            # 提取各维度分数
            technical_score = technical_data.get('composite_score', {}).get('technical_score', 50)
            technical_confidence = technical_data.get('composite_score', {}).get('confidence', 0.5)
            
            ai_score = ai_analysis.get('composite_signal', {}).get('score', 50)
            ai_confidence = ai_analysis.get('ai_confidence', 0.5)
            
            sentiment_score = sentiment_data.get('sentiment_score', 50)
            sentiment_reliability = sentiment_data.get('reliability_factor', 0.5)
            
            # 应用可靠性调整
            adjusted_technical_score = technical_score * technical_confidence
            adjusted_ai_score = ai_score * ai_confidence
            adjusted_sentiment_score = sentiment_score * sentiment_reliability
            
            # 加权计算综合分数
            weights = self.config['scoring_weights']
            composite_score = (
                adjusted_technical_score * weights['technical'] +
                adjusted_ai_score * weights['ai_analysis'] +
                adjusted_sentiment_score * weights['sentiment']
            )
            
            # 归一化到0-100
            composite_score = max(0, min(100, composite_score))
            
            # 确定信号类型
            signal_info = self._determine_signal(composite_score)
            
            # 计算置信度（基于各维度一致性）
            confidence = self._calculate_confidence(
                technical_score, ai_score, sentiment_score,
                technical_confidence, ai_confidence, sentiment_reliability
            )
            
            # 生成交易建议
            trading_advice = self._generate_trading_advice(
                signal_info, technical_data, ai_analysis, sentiment_data
            )
            
            # 组装结果
            result = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'signal': signal_info['type'],
                'score': int(round(composite_score)),
                'confidence': confidence,
                'description': signal_info['description'],
                'trading_advice': trading_advice,
                'breakdown': {
                    'technical': {
                        'score': technical_score,
                        'confidence': technical_confidence,
                        'adjusted_score': round(adjusted_technical_score, 1)
                    },
                    'ai_analysis': {
                        'score': ai_score,
                        'confidence': ai_confidence,
                        'adjusted_score': round(adjusted_ai_score, 1),
                        'consensus': ai_analysis.get('consensus', {}).get('score', 0.5)
                    },
                    'sentiment': {
                        'score': sentiment_score,
                        'reliability': sentiment_reliability,
                        'adjusted_score': round(adjusted_sentiment_score, 1),
                        'fgi_value': sentiment_data.get('fear_greed_index', {}).get('value', 50)
                    },
                    'weights': weights,
                    'composite_score': round(composite_score, 1)
                },
                'key_levels': self._extract_key_levels(technical_data, sentiment_data),
                'risk_assessment': self._assess_risk(technical_data, sentiment_data, confidence)
            }
            
            logger.info(f"综合信号生成完成: {symbol}, 信号: {signal_info['type']}, 分数: {composite_score:.1f}")
            return result
            
        except Exception as e:
            logger.error(f"生成综合信号失败: {e}")
            return self._generate_error_signal(symbol, str(e))
    
    def _determine_signal(self, score: float) -> Dict:
        """根据分数确定信号类型"""
        thresholds = self.config['signal_thresholds']
        
        if score >= thresholds['strong_buy']:
            return {
                'type': 'STRONG_BUY',
                'description': '强烈买入 - 技术、AI、情绪指标均显示强烈看涨',
                'color': 'green',
                'strength': 'very_strong'
            }
        elif score >= thresholds['buy']:
            return {
                'type': 'BUY',
                'description': '买入 - 多数指标显示看涨信号',
                'color': 'light_green',
                'strength': 'strong'
            }
        elif score >= thresholds['neutral']:
            return {
                'type': 'NEUTRAL',
                'description': '观望 - 指标矛盾或无明显趋势',
                'color': 'yellow',
                'strength': 'weak'
            }
        elif score >= thresholds['sell']:
            return {
                'type': 'SELL',
                'description': '卖出 - 多数指标显示看跌信号',
                'color': 'light_red',
                'strength': 'strong'
            }
        else:
            return {
                'type': 'STRONG_SELL',
                'description': '强烈卖出 - 技术、AI、情绪指标均显示强烈看跌',
                'color': 'red',
                'strength': 'very_strong'
            }
    
    def _calculate_confidence(self, 
                            tech_score: float, 
                            ai_score: float, 
                            sent_score: float,
                            tech_conf: float,
                            ai_conf: float,
                            sent_rel: float) -> float:
        """计算信号置信度"""
        # 计算各维度分数差异
        scores = [tech_score, ai_score, sent_score]
        score_variance = self._calculate_variance(scores) / 10000  # 归一化
        
        # 计算一致性（差异越小，一致性越高）
        consistency = 1.0 - min(score_variance, 1.0)
        
        # 计算平均置信度
        avg_confidence = (tech_conf + ai_conf + sent_rel) / 3
        
        # 综合置信度 = 一致性 * 平均置信度
        confidence = consistency * avg_confidence
        
        return round(confidence, 2)
    
    def _generate_trading_advice(self, 
                               signal_info: Dict,
                               technical_data: Dict,
                               ai_analysis: Dict,
                               sentiment_data: Dict) -> Dict:
        """生成交易建议"""
        signal_type = signal_info['type']
        signal_strength = signal_info['strength']
        
        # 基础建议
        base_advice = {
            'STRONG_BUY': {
                'action': '积极买入',
                'position': '可重仓',
                'timing': '立即或分批买入',
                'risk': '低风险'
            },
            'BUY': {
                'action': '买入',
                'position': '中等仓位',
                'timing': '逢低买入',
                'risk': '中低风险'
            },
            'NEUTRAL': {
                'action': '观望',
                'position': '轻仓或空仓',
                'timing': '等待明确信号',
                'risk': '不确定'
            },
            'SELL': {
                'action': '卖出',
                'position': '减仓',
                'timing': '逢高卖出',
                'risk': '中高风险'
            },
            'STRONG_SELL': {
                'action': '积极卖出',
                'position': '清仓或做空',
                'timing': '立即卖出',
                'risk': '高风险'
            }
        }
        
        advice = base_advice.get(signal_type, base_advice['NEUTRAL'])
        
        # 添加具体建议
        current_price = technical_data.get('current_price', 0)
        support_levels = technical_data.get('support_resistance', {}).get('supports', [])
        resistance_levels = technical_data.get('support_resistance', {}).get('resistances', [])
        
        # 目标价位
        targets = []
        stop_loss = None
        
        if signal_type in ['STRONG_BUY', 'BUY']:
            # 买入目标：最近的阻力位
            if resistance_levels:
                nearest_resistance = min(resistance_levels, key=lambda x: abs(x - current_price))
                targets.append(nearest_resistance)
                if len(resistance_levels) > 1:
                    targets.append(resistance_levels[1])
            
            # 止损：最近的支撑位下方
            if support_levels:
                nearest_support = min(support_levels, key=lambda x: abs(x - current_price))
                stop_loss = nearest_support * 0.98  # 支撑位下方2%
        
        elif signal_type in ['STRONG_SELL', 'SELL']:
            # 卖出目标：最近的支撑位
            if support_levels:
                nearest_support = min(support_levels, key=lambda x: abs(x - current_price))
                targets.append(nearest_support)
                if len(support_levels) > 1:
                    targets.append(support_levels[1])
            
            # 止损：最近的阻力位上方
            if resistance_levels:
                nearest_resistance = min(resistance_levels, key=lambda x: abs(x - current_price))
                stop_loss = nearest_resistance * 1.02  # 阻力位上方2%
        
        # AI分析的具体建议
        ai_recommendation = ai_analysis.get('composite_signal', {}).get('description', '')
        
        # 情绪影响
        sentiment_impact = sentiment_data.get('trading_advice', '')
        
        return {
            'action': advice['action'],
            'position_sizing': advice['position'],
            'timing': advice['timing'],
            'risk_level': advice['risk'],
            'target_prices': targets[:3],  # 最多3个目标
            'stop_loss': stop_loss,
            'ai_insight': ai_recommendation,
            'sentiment_context': sentiment_impact,
            'notes': self._generate_trading_notes(signal_type, technical_data, sentiment_data)
        }
    
    def _extract_key_levels(self, technical_data: Dict, sentiment_data: Dict) -> Dict:
        """提取关键价位"""
        supports = technical_data.get('support_resistance', {}).get('supports', [])
        resistances = technical_data.get('support_resistance', {}).get('resistances', [])
        current_price = technical_data.get('current_price', 0)
        
        # 情绪影响的关键位强度
        sentiment_impact = sentiment_data.get('impact_on_technical', {})
        support_weight = sentiment_impact.get('support_weight', 1.0)
        resistance_weight = sentiment_impact.get('resistance_weight', 1.0)
        
        key_levels = {
            'current_price': current_price,
            'supports': [],
            'resistances': [],
            'strongest_support': None,
            'strongest_resistance': None
        }
        
        # 标记支撑位强度
        for i, support in enumerate(supports[:3]):  # 最多3个
            strength = 'strong' if i == 0 else 'medium' if i == 1 else 'weak'
            # 应用情绪权重
            adjusted_strength = 'very_strong' if support_weight > 1.2 else strength
            key_levels['supports'].append({
                'price': support,
                'strength': adjusted_strength,
                'distance_pct': round(((current_price - support) / current_price * 100), 1)
            })
        
        # 标记阻力位强度
        for i, resistance in enumerate(resistances[:3]):  # 最多3个
            strength = 'strong' if i == 0 else 'medium' if i == 1 else 'weak'
            # 应用情绪权重
            adjusted_strength = 'very_strong' if resistance_weight > 1.2 else strength
            key_levels['resistances'].append({
                'price': resistance,
                'strength': adjusted_strength,
                'distance_pct': round(((resistance - current_price) / current_price * 100), 1)
            })
        
        # 确定最强支撑阻力
        if key_levels['supports']:
            key_levels['strongest_support'] = key_levels['supports'][0]
        if key_levels['resistances']:
            key_levels['strongest_resistance'] = key_levels['resistances'][0]
        
        return key_levels
    
    def _assess_risk(self, technical_data: Dict, sentiment_data: Dict, confidence: float) -> Dict:
        """评估风险"""
        current_price = technical_data.get('current_price', 0)
        supports = technical_data.get('support_resistance', {}).get('supports', [])
        
        # 计算到最近支撑的距离（下跌风险）
        downside_risk = 0
        if supports:
            nearest_support = min(supports, key=lambda x: abs(x - current_price))
            downside_risk = ((current_price - nearest_support) / current_price * 100)
        
        # 情绪风险
        sentiment_risk = 0
        fgi_value = sentiment_data.get('fear_greed_index', {}).get('value', 50)
        if fgi_value >= 80:  # 极度贪婪
            sentiment_risk = 80
        elif fgi_value >= 60:  # 贪婪
            sentiment_risk = 60
        elif fgi_value <= 20:  # 极度恐惧
            sentiment_risk = 20  # 风险低，机会高
        elif fgi_value <= 40:  # 恐惧
            sentiment_risk = 40
        
        # 技术指标风险（基于RSI）
        rsi_value = technical_data.get('indicators', {}).get('rsi', {}).get('value', 50)
        technical_risk = 0
        if rsi_value >= 70:  # 超买
            technical_risk = 70
        elif rsi_value <= 30:  # 超卖
            technical_risk = 30  # 风险低
        
        # 综合风险（0-100，越高风险越大）
        composite_risk = (downside_risk * 0.3 + sentiment_risk * 0.3 + technical_risk * 0.4)
        
        # 根据置信度调整
        adjusted_risk = composite_risk * (1.0 - confidence * 0.5)
        
        return {
            'downside_risk_pct': round(downside_risk, 1),
            'sentiment_risk': sentiment_risk,
            'technical_risk': technical_risk,
            'composite_risk': round(composite_risk, 1),
            'adjusted_risk': round(adjusted_risk, 1),
            'risk_level': self._get_risk_level(adjusted_risk),
            'recommended_position_pct': self._get_recommended_position(adjusted_risk)
        }
    
    def _generate_trading_notes(self, signal_type: str, technical_data: Dict, sentiment_data: Dict) -> List[str]:
        """生成交易备注"""
        notes = []
        
        # 技术面备注
        rsi_signal = technical_data.get('indicators', {}).get('rsi', {}).get('signal', '')
        macd_signal = technical_data.get('indicators', {}).get('macd', {}).get('signal', '')
        
        if rsi_signal:
            notes.append(f"RSI信号: {rsi_signal}")
        if macd_signal:
            notes.append(f"MACD信号: {macd_signal}")
        
        # 情绪面备注
        fgi_classification = sentiment_data.get('fear_greed_index', {}).get('classification', '')
        if fgi_classification:
            notes.append(f"市场情绪: {fgi_classification}")
        
        # 风险提示
        if signal_type in ['STRONG_BUY', 'STRONG_SELL']:
            notes.append("注意：强烈信号通常伴随较高波动性")
        
        return notes
    
    def _get_risk_level(self, risk_score: float) -> str:
        """获取风险等级"""
        if risk_score >= 70:
            return "极高风险"
        elif risk_score >= 50:
            return "高风险"
        elif risk_score >= 30:
            return "中等风险"
        elif risk_score >= 15:
            return "低风险"
        else:
            return "极低风险"
    
    def _get_recommended_position(self, risk_score: float) -> int:
        """获取推荐仓位百分比"""
        if risk_score >= 70:
            return 10  # 10%仓位
        elif risk_score >= 50:
            return 25  # 25%仓位
        elif risk_score >= 30:
            return 50  # 50%仓位
        elif risk_score >= 15:
            return 75  # 75%仓位
        else:
            return 100  # 满仓
    
    def _calculate_variance(self, values: List[float]) -> float:
        """计算方差"""
        if not values:
            return 0
        mean = sum(values) / len(values)
        return sum((x - mean) ** 2 for x in values) / len(values)
    
    def _generate_error_signal(self, symbol: str, error_msg: str) -> Dict:
        """生成错误信号"""
        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'signal': 'ERROR',
            'score': 50,
            'confidence': 0.0,
            'description': f'信号生成失败: {error_msg}',
            'trading_advice': {
                'action': '暂停交易',
                'position_sizing': '空仓',
                'timing': '等待系统修复',
                'risk_level': '未知',
                'target_prices': [],
                'stop_loss': None,
                'ai_insight': '',
                'sentiment_context': '',
                'notes': ['系统错误，请检查日志']
            },
            'breakdown': {},
            'key_levels': {},
            'risk_assessment': {},
            'error': True,
            'error_message': error_msg
        }


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 创建信号生成器
    generator = CompositeSignalGenerator()
    
    # 测试数据
    test_technical_data = {
        'current_price': 65432.10,
        'composite_score': {
            'technical_score': 65,
            'confidence': 0.7
        },
        'indicators': {
            'rsi': {'value': 62.5, 'signal': '接近超买'},
            'macd': {'histogram': 150.60, 'signal': '柱状图为正'}
        },
        'support_resistance': {
            'supports': [61400, 60000, 58500],
            'resistances': [67000, 68500, 70000]
        }
    }
    
    test_ai_analysis = {
        'composite_signal': {
            'score': 70,
            'description': '双模型一致看涨'
        },
        'ai_confidence': 0.8,
        'consensus': {'score': 0.85}
    }
    
    test_sentiment_data = {
        'sentiment_score': 75,  # 恐慌分数高（100-恐慌指数）
        'reliability_factor': 0.9,
        'fear_greed_index': {
            'value': 25,  # 恐慌指数25，情绪分数75
            'classification': 'Fear'
        },
        'trading_advice': '市场恐惧，可考虑逢低买入',
        'impact_on_technical': {
            'support_weight': 1.1,
            'resistance_weight': 0.9
        }
    }
    
    # 生成信号
    print("测试综合信号生成...")
    signal_result = generator.generate_signal(
        'BTC',
        test_technical_data,
        test_ai_analysis,
        test_sentiment_data
    )
    
    if signal_result and not signal_result.get('error', False):
        print("✅ 信号生成完成")
        print(f"符号: {signal_result['symbol']}")
        print(f"信号: {signal_result['signal']} ({signal_result['description']})")
        print(f"分数: {signal_result['score']}/100")
        print(f"置信度: {signal_result['confidence']}")
        
        print("\n交易建议:")
        advice = signal_result['trading_advice']
        print(f"  操作: {advice['action']}")
        print(f"  仓位: {advice['position_sizing']}")
        print(f"  时机: {advice['timing']}")
        print(f"  风险: {advice['risk_level']}")
        
        if advice['target_prices']:
            print(f"  目标价位: {', '.join([f'${p:,.0f}' for p in advice['target_prices']])}")
        if advice['stop_loss']:
            print(f"  止损位: ${advice['stop_loss']:,.0f}")
        
        print("\n关键价位:")
        levels = signal_result['key_levels']
        print(f"  当前价格: ${levels.get('current_price', 0):,.2f}")
        
        if levels.get('supports'):
            print("  支撑位:")
            for support in levels['supports'][:2]:
                print(f"    - ${support['price']:,.0f} ({support['strength']}, 距离: {support['distance_pct']}%)")
        
        if levels.get('resistances'):
            print("  阻力位:")
            for resistance in levels['resistances'][:2]:
                print(f"    - ${resistance['price']:,.0f} ({resistance['strength']}, 距离: {resistance['distance_pct']}%)")
        
        print("\n风险评估:")
        risk = signal_result['risk_assessment']
        print(f"  综合风险: {risk.get('composite_risk', 0):.1f} ({risk.get('risk_level', '未知')})")
        print(f"  推荐仓位: {risk.get('recommended_position_pct', 0)}%")
        
        print("\n细分分数:")
        breakdown = signal_result['breakdown']
        for dimension, data in breakdown.items():
            if dimension != 'weights' and dimension != 'composite_score':
                if isinstance(data, dict):
                    score = data.get('adjusted_score', data.get('score', 0))
                    print(f"  {dimension}: {score:.1f}")
        
        print(f"  综合分数: {breakdown.get('composite_score', 0):.1f}")
        
        print("\n备注:")
        for note in advice.get('notes', []):
            print(f"  • {note}")
    else:
        print("❌ 信号生成失败")
        if signal_result:
            print(f"错误: {signal_result.get('error_message', '未知错误')}")