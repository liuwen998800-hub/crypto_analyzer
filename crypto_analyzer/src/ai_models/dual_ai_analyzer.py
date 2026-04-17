"""
双AI模型分析模块
使用DeepSeek和MiniMax进行互补分析
"""

import json
import time
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime

# 尝试导入AI库
try:
    from openai import OpenAI as DeepSeekClient
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False
    logging.warning("DeepSeek客户端未安装")

try:
    import anthropic
    MINIMAX_AVAILABLE = True
except ImportError:
    MINIMAX_AVAILABLE = False
    logging.warning("MiniMax客户端未安装")

logger = logging.getLogger(__name__)


class DualAIAnalyzer:
    """双AI模型分析器"""
    
    def __init__(self, config: Dict):
        """
        初始化AI分析器
        
        Args:
            config: 配置字典，包含API密钥等信息
        """
        self.config = config
        self.deepseek_client = None
        self.minimax_client = None
        
        # 初始化DeepSeek客户端
        if DEEPSEEK_AVAILABLE and config.get('deepseek', {}).get('api_key'):
            self.deepseek_client = DeepSeekClient(
                api_key=config['deepseek']['api_key'],
                base_url=config['deepseek'].get('base_url', 'https://api.deepseek.com/v1')
            )
            logger.info("DeepSeek客户端初始化完成")
        
        # 初始化MiniMax客户端
        if MINIMAX_AVAILABLE and config.get('minimax', {}).get('api_key'):
            self.minimax_client = anthropic.Anthropic(
                api_key=config['minimax']['api_key'],
                base_url=config['minimax'].get('base_url', 'https://api.minimax.chat/v1')
            )
            logger.info("MiniMax客户端初始化完成")
        
        if not self.deepseek_client and not self.minimax_client:
            logger.warning("未配置任何AI模型，将使用模拟分析")
    
    def analyze_with_deepseek(self, symbol: str, market_data: Dict, technical_data: Dict) -> Dict:
        """
        使用DeepSeek分析
        
        Args:
            symbol: 币种符号
            market_data: 市场数据
            technical_data: 技术分析数据
            
        Returns:
            DeepSeek分析结果
        """
        if not self.deepseek_client:
            return self._get_mock_analysis('deepseek', symbol)
        
        try:
            # 构建分析提示
            prompt = self._build_analysis_prompt(symbol, market_data, technical_data, 'deepseek')
            
            # 调用DeepSeek API
            response = self.deepseek_client.chat.completions.create(
                model=self.config['deepseek'].get('model', 'deepseek-chat'),
                messages=[
                    {"role": "system", "content": "你是一个专业的加密货币交易分析师。请分析以下市场数据并提供专业的交易建议。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # 解析响应
            analysis_text = response.choices[0].message.content
            
            # 提取结构化信息
            result = self._parse_ai_response(analysis_text, 'deepseek')
            result['raw_response'] = analysis_text
            result['model'] = 'deepseek-chat'
            
            logger.info(f"DeepSeek分析完成: {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"DeepSeek分析失败: {e}")
            return self._get_mock_analysis('deepseek', symbol)
    
    def analyze_with_minimax(self, symbol: str, market_data: Dict, technical_data: Dict) -> Dict:
        """
        使用MiniMax分析
        
        Args:
            symbol: 币种符号
            market_data: 市场数据
            technical_data: 技术分析数据
            
        Returns:
            MiniMax分析结果
        """
        if not self.minimax_client:
            return self._get_mock_analysis('minimax', symbol)
        
        try:
            # 构建分析提示
            prompt = self._build_analysis_prompt(symbol, market_data, technical_data, 'minimax')
            
            # 调用MiniMax API
            response = self.minimax_client.messages.create(
                model=self.config['minimax'].get('model', 'MiniMax-M2.7'),
                max_tokens=500,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # 解析响应
            analysis_text = response.content[0].text
            
            # 提取结构化信息
            result = self._parse_ai_response(analysis_text, 'minimax')
            result['raw_response'] = analysis_text
            result['model'] = 'MiniMax-M2.7'
            
            logger.info(f"MiniMax分析完成: {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"MiniMax分析失败: {e}")
            return self._get_mock_analysis('minimax', symbol)
    
    def analyze_with_dual_models(self, symbol: str, market_data: Dict, technical_data: Dict) -> Dict:
        """
        使用双模型分析
        
        Args:
            symbol: 币种符号
            market_data: 市场数据
            technical_data: 技术分析数据
            
        Returns:
            双模型综合分析结果
        """
        # 并行调用两个模型
        deepseek_result = self.analyze_with_deepseek(symbol, market_data, technical_data)
        minimax_result = self.analyze_with_minimax(symbol, market_data, technical_data)
        
        # 计算一致性评分
        consensus_score = self._calculate_consensus(deepseek_result, minimax_result)
        
        # 生成综合信号
        composite_signal = self._generate_composite_signal(deepseek_result, minimax_result)
        
        # 计算AI置信度
        ai_confidence = self._calculate_ai_confidence(deepseek_result, minimax_result, consensus_score)
        
        # 组装结果
        result = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'deepseek_analysis': deepseek_result,
            'minimax_analysis': minimax_result,
            'consensus': {
                'score': consensus_score,
                'level': self._get_consensus_level(consensus_score),
                'description': self._get_consensus_description(deepseek_result, minimax_result)
            },
            'composite_signal': composite_signal,
            'ai_confidence': ai_confidence,
            'breakdown': {
                'deepseek_score': deepseek_result.get('score', 50),
                'minimax_score': minimax_result.get('score', 50),
                'consensus_score': consensus_score
            }
        }
        
        logger.info(f"双模型分析完成: {symbol}, 一致性: {consensus_score}, 置信度: {ai_confidence}")
        return result
    
    def _build_analysis_prompt(self, symbol: str, market_data: Dict, technical_data: Dict, model_type: str) -> str:
        """构建分析提示"""
        current_price = market_data.get('price', 0)
        price_change_24h = market_data.get('24h_change', 0)
        
        # 技术指标摘要
        tech_summary = ""
        if technical_data and 'indicators' in technical_data:
            indicators = technical_data['indicators']
            tech_summary = f"""
技术指标:
- RSI: {indicators.get('rsi', {}).get('value', 0):.1f} ({indicators.get('rsi', {}).get('signal', 'N/A')})
- MACD: 柱状图={indicators.get('macd', {}).get('histogram', 0):.4f} ({indicators.get('macd', {}).get('signal', 'N/A')})
- 移动平均线: 价格在{self._count_ma_position(current_price, indicators.get('moving_averages', {}))}/3条均线上方
- 布林带: 价格位置{self._get_bb_position(current_price, indicators.get('bollinger_bands', {}))}
- 综合技术评分: {technical_data.get('composite_score', {}).get('technical_score', 50)}/100
"""
        
        # 支撑阻力位
        sr_levels = ""
        if technical_data and 'support_resistance' in technical_data:
            sr = technical_data['support_resistance']
            sr_levels = f"""
支撑阻力位:
- 主要支撑: {', '.join([f'${s:,.0f}' for s in sr.get('supports', [])[:2]]) if sr.get('supports') else '无'}
- 主要阻力: {', '.join([f'${r:,.0f}' for r in sr.get('resistances', [])[:2]]) if sr.get('resistances') else '无'}
"""
        
        prompt = f"""
请分析{symbol}的当前市场状况并提供交易建议。

市场数据:
- 当前价格: ${current_price:,.2f}
- 24小时变化: {price_change_24h:+.2f}%
- 24小时高点: ${market_data.get('24h_high', 0):,.2f}
- 24小时低点: ${market_data.get('24h_low', 0):,.2f}
- 24小时成交量: ${market_data.get('24h_volume', 0):,.0f}

{tech_summary}
{sr_levels}

请提供:
1. 趋势判断 (看涨/看跌/中性)
2. 置信度 (0-100%)
3. 关键理由 (2-3个主要因素)
4. 交易建议 (买入/卖出/持有)
5. 目标价位和止损位建议

请用JSON格式回复，包含以下字段:
- trend: 趋势判断
- confidence: 置信度 (0-100)
- reasoning: 理由列表
- recommendation: 交易建议
- targets: 目标价位列表
- stop_loss: 止损位
"""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str, model_type: str) -> Dict:
        """解析AI响应"""
        # 尝试提取JSON
        try:
            # 查找JSON部分
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
                
                # 确保必要字段
                if 'trend' not in result:
                    result['trend'] = 'neutral'
                if 'confidence' not in result:
                    result['confidence'] = 50
                if 'recommendation' not in result:
                    result['recommendation'] = 'hold'
                
                # 计算分数
                result['score'] = self._convert_to_score(result.get('recommendation', 'hold'), 
                                                         result.get('confidence', 50))
                return result
        except:
            pass
        
        # 如果JSON解析失败，使用文本分析
        return self._analyze_text_response(response_text, model_type)
    
    def _analyze_text_response(self, text: str, model_type: str) -> Dict:
        """分析文本响应"""
        text_lower = text.lower()
        
        # 判断趋势
        if '看涨' in text or 'bullish' in text_lower or '上涨' in text:
            trend = 'bullish'
        elif '看跌' in text or 'bearish' in text_lower or '下跌' in text:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        # 判断建议
        if '买入' in text or 'buy' in text_lower:
            recommendation = 'buy'
        elif '卖出' in text or 'sell' in text_lower:
            recommendation = 'sell'
        else:
            recommendation = 'hold'
        
        # 提取置信度
        confidence = 50
        if '%' in text:
            import re
            percentages = re.findall(r'(\d+)%', text)
            if percentages:
                confidence = min(100, max(0, int(percentages[0])))
        
        # 提取理由
        reasoning = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and ('因为' in line or '原因' in line or 'due to' in text_lower or 'because' in text_lower):
                reasoning.append(line)
        
        if not reasoning:
            reasoning = ["基于技术分析和市场数据"]
        
        return {
            'trend': trend,
            'confidence': confidence,
            'reasoning': reasoning[:3],  # 最多3个理由
            'recommendation': recommendation,
            'score': self._convert_to_score(recommendation, confidence),
            'parsed_from_text': True
        }
    
    def _convert_to_score(self, recommendation: str, confidence: int) -> int:
        """将建议和置信度转换为分数"""
        base_score = 50
        
        if recommendation == 'buy':
            base_score = 60 + (confidence / 100 * 40)  # 60-100
        elif recommendation == 'sell':
            base_score = 40 - (confidence / 100 * 40)  # 0-40
        elif recommendation == 'hold':
            base_score = 50
        
        return int(max(0, min(100, base_score)))
    
    def _calculate_consensus(self, deepseek_result: Dict, minimax_result: Dict) -> float:
        """计算两个模型的一致性评分"""
        deepseek_score = deepseek_result.get('score', 50)
        minimax_score = minimax_result.get('score', 50)
        
        # 计算分数差异
        score_diff = abs(deepseek_score - minimax_score)
        
        # 计算趋势一致性
        deepseek_trend = deepseek_result.get('trend', 'neutral')
        minimax_trend = minimax_result.get('trend', 'neutral')
        
        trend_match = 1.0 if deepseek_trend == minimax_trend else 0.5
        
        # 计算建议一致性
        deepseek_rec = deepseek_result.get('recommendation', 'hold')
        minimax_rec = minimax_result.get('recommendation', 'hold')
        
        rec_match = 1.0 if deepseek_rec == minimax_rec else 0.5
        
        # 综合一致性
        score_consistency = 1.0 - (score_diff / 100)
        consensus = (score_consistency + trend_match + rec_match) / 3
        
        return round(consensus, 2)
    
    def _generate_composite_signal(self, deepseek_result: Dict, minimax_result: Dict) -> Dict:
        """生成综合信号"""
        deepseek_score = deepseek_result.get('score', 50)
        minimax_score = minimax_result.get('score', 50)
        
        # 加权平均
        avg_score = (deepseek_score + minimax_score) / 2
        
        # 确定信号
        if avg_score >= 80:
            signal = 'strong_buy'
        elif avg_score >= 60:
            signal = 'buy'
        elif avg_score >= 40:
            signal = 'neutral'
        elif avg_score >= 20:
            signal = 'sell'
        else:
            signal = 'strong_sell'
        
        # 信号描述
        descriptions = {
            'strong_buy': '强烈买入 - 双模型一致看涨',
            'buy': '买入 - 多数模型看涨',
            'neutral': '观望 - 模型意见分歧或无明确趋势',
            'sell': '卖出 - 多数模型看跌',
            'strong_sell': '强烈卖出 - 双模型一致看跌'
        }
        
        return {
            'signal': signal,
            'score': int(avg_score),
            'description': descriptions.get(signal, '未知信号'),
            'deepseek_contribution': deepseek_score,
            'minimax_contribution': minimax_score
        }
    
    def _calculate_ai_confidence(self, deepseek_result: Dict, minimax_result: Dict, consensus: float) -> float:
        """计算AI置信度"""
        deepseek_conf = deepseek_result.get('confidence', 50) / 100
        minimax_conf = minimax_result.get('confidence', 50) / 100
        
        # 平均置信度
        avg_confidence = (deepseek_conf + minimax_conf) / 2
        
        # 结合一致性
        ai_confidence = avg_confidence * consensus
        
        return round(ai_confidence, 2)
    
    def _get_consensus_level(self, consensus_score: float) -> str:
        """获取一致性等级"""
        if consensus_score >= 0.8:
            return 'high'
        elif consensus_score >= 0.6:
            return 'medium'
        elif consensus_score >= 0.4:
            return 'low'
        else:
            return 'very_low'
    
    def _get_consensus_description(self, deepseek_result: Dict, minimax_result: Dict) -> str:
        """获取一致性描述"""
        deepseek_trend = deepseek_result.get('trend', 'neutral')
        minimax_trend = minimax_result.get('trend', 'neutral')
        
        if deepseek_trend == minimax_trend:
            if deepseek_trend == 'bullish':
                return '双模型一致看涨'
            elif deepseek_trend == 'bearish':
                return '双模型一致看跌'
            else:
                return '双模型一致中性'
        else:
            return '模型意见分歧'
    
    def _count_ma_position(self, price: float, ma_data: Dict) -> int:
        """计算价格在多少条均线上方"""
        if not ma_data:
            return 0
        
        count = 0
        for key in ['sma_7', 'sma_20', 'sma_50']:
            if key in ma_data and ma_data[key] is not None:
                ma_value = ma_data[key].get('value') if isinstance(ma_data[key], dict) else ma_data[key]
                if isinstance(ma_value, (int, float)) and price > ma_value:
                    count += 1
        
        return count
    
    def _get_bb_position(self, price: float, bb_data: Dict) -> str:
        """获取布林带位置描述"""
        if not bb_data or 'upper' not in bb_data or 'lower' not in bb_data:
            return "未知"
        
        upper = bb_data['upper'].get('value') if isinstance(bb_data['upper'], dict) else bb_data['upper']
        lower = bb_data['lower'].get('value') if isinstance(bb_data['lower'], dict) else bb_data['lower']
        
        if not isinstance(upper, (int, float)) or not isinstance(lower, (int, float)):
            return "未知"
        
        if upper == lower:
            return "中轨"
        
        position = (price - lower) / (upper - lower)
        
        if position < 0.2:
            return "接近下轨"
        elif position < 0.4:
            return "下轨附近"
        elif position < 0.6:
            return "中轨附近"
        elif position < 0.8:
            return "上轨附近"
        else:
            return "接近上轨"
    
    def _get_mock_analysis(self, model_type: str, symbol: str) -> Dict:
        """获取模拟分析结果（用于测试）"""
        import random
        
        trends = ['bullish', 'bearish', 'neutral']
        recommendations = ['buy', 'sell', 'hold']
        
        trend = random.choice(trends)
        confidence = random.randint(60, 90)
        recommendation = random.choice(recommendations)
        
        reasoning_options = [
            ["技术指标显示突破信号", "成交量放大配合价格上涨", "市场情绪转向积极"],
            ["价格接近阻力位", "成交量萎缩显示动能不足", "市场存在获利了结压力"],
            ["技术指标矛盾", "市场观望情绪浓厚", "等待明确方向信号"]
        ]
        
        reasoning = random.choice(reasoning_options)
        
        return {
            'trend': trend,
            'confidence': confidence,
            'reasoning': reasoning,
            'recommendation': recommendation,
            'score': self._convert_to_score(recommendation, confidence),
            'is_mock': True,
            'model': f'{model_type}-mock'
        }


# 使用示例
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 测试配置
    test_config = {
        'deepseek': {
            'api_key': 'test_key',  # 替换为实际密钥
            'model': 'deepseek-chat'
        },
        'minimax': {
            'api_key': 'test_key',  # 替换为实际密钥
            'model': 'MiniMax-M2.7'
        }
    }
    
    # 创建分析器
    analyzer = DualAIAnalyzer(test_config)
    
    # 测试数据
    test_market_data = {
        'price': 65432.10,
        '24h_change': 2.35,
        '24h_high': 66000.00,
        '24h_low': 63800.50,
        '24h_volume': 28500000000
    }
    
    test_technical_data = {
        'indicators': {
            'rsi': {'value': 62.5, 'signal': '接近超买'},
            'macd': {'histogram': 150.60, 'signal': '柱状图为正'},
            'moving_averages': {
                'sma_7': 64800.50,
                'sma_20': 63200.30,
                'sma_50': 61500.00
            },
            'bollinger_bands': {
                'upper': 67000.00,
                'lower': 61400.00,
                'middle': 64200.00
            }
        },
        'support_resistance': {
            'supports': [61400, 60000],
            'resistances': [67000, 68500]
        },
        'composite_score': {
            'technical_score': 65
        }
    }
    
    # 测试分析
    print("测试双模型分析...")
    result = analyzer.analyze_with_dual_models('BTC', test_market_data, test_technical_data)
    
    if result:
        print("✅ 分析完成")
        print(f"符号: {result['symbol']}")
        print(f"时间: {result['timestamp']}")
        print(f"一致性评分: {result['consensus']['score']} ({result['consensus']['level']})")
        print(f"AI置信度: {result['ai_confidence']}")
        
        print("\n综合信号:")
        signal = result['composite_signal']
        print(f"  {signal['signal']}: {signal['description']}")
        print(f"  分数: {signal['score']}")
        
        print("\nDeepSeek分析:")
        ds = result['deepseek_analysis']
        print(f"  趋势: {ds.get('trend', 'N/A')}")
        print(f"  建议: {ds.get('recommendation', 'N/A')}")
        print(f"  置信度: {ds.get('confidence', 'N/A')}%")
        print(f"  分数: {ds.get('score', 'N/A')}")
        
        print("\nMiniMax分析:")
        mm = result['minimax_analysis']
        print(f"  趋势: {mm.get('trend', 'N/A')}")
        print(f"  建议: {mm.get('recommendation', 'N/A')}")
        print(f"  置信度: {mm.get('confidence', 'N/A')}%")
        print(f"  分数: {mm.get('score', 'N/A')}")
    else:
        print("❌ 分析失败")