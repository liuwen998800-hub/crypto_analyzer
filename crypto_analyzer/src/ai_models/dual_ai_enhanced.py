#!/usr/bin/env python3
"""
增强版双AI模型分析器
集成DeepSeek和MiniMax模型进行技术分析
"""

import os
import json
import yaml
import requests
import asyncio
import aiohttp
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedDualAIAnalyzer:
    """增强版双AI模型分析器"""
    
    def __init__(self, config_path: str = None):
        """初始化分析器"""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / 'config' / 'api_keys.yaml'
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.models = {
            'deepseek': self._init_deepseek(),
            'minimax': self._init_minimax()
        }
        
        # 分析模板
        self.analysis_template = {
            "core_indicators": {
                "rsi": {"value": 0, "signal": "", "confidence": 0},
                "macd": {"value": 0, "signal": "", "confidence": 0},
                "moving_averages": {"signal": "", "confidence": 0},
                "bollinger_bands": {"position": 0, "signal": "", "confidence": 0}
            },
            "momentum_indicators": {
                "stochastic": {"k": 0, "d": 0, "signal": "", "confidence": 0},
                "williams": {"value": 0, "signal": "", "confidence": 0},
                "cci": {"value": 0, "signal": "", "confidence": 0}
            },
            "trend_indicators": {
                "adx": {"value": 0, "strength": "", "confidence": 0},
                "parabolic_sar": {"signal": "", "confidence": 0},
                "ichimoku": {"signal": "", "confidence": 0}
            },
            "volatility_indicators": {
                "atr": {"value": 0, "signal": "", "confidence": 0},
                "volatility_channels": {"signal": "", "confidence": 0}
            },
            "volume_indicators": {
                "obv": {"trend": "", "confidence": 0},
                "volume_profile": {"signal": "", "confidence": 0}
            },
            "pattern_recognition": {
                "candle_patterns": [],
                "chart_patterns": [],
                "divergence": {"detected": False, "type": "", "confidence": 0}
            },
            "multi_indicator_resonance": {
                "bullish_resonance": 0,
                "bearish_resonance": 0,
                "neutral_resonance": 0
            },
            "market_sentiment": {
                "overall": "",
                "confidence": 0,
                "fear_greed_index": 0
            },
            "final_analysis": {
                "direction": "",  # "bullish", "bearish", "neutral"
                "confidence": 0,
                "reasoning": "",
                "timeframe_analysis": {
                    "1h": {"direction": "", "confidence": 0},
                    "4h": {"direction": "", "confidence": 0},
                    "24h": {"direction": "", "confidence": 0}
                },
                "support_resistance": {
                    "key_supports": [],
                    "key_resistances": [],
                    "dense_trading_zones": []
                }
            }
        }
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _init_deepseek(self) -> Dict:
        """初始化DeepSeek配置"""
        deepseek_config = self.config.get('deepseek', {})
        return {
            'api_key': deepseek_config.get('api_key', ''),
            'base_url': deepseek_config.get('base_url', 'https://api.deepseek.com/v1'),
            'model': deepseek_config.get('model', 'deepseek-chat'),
            'enabled': bool(deepseek_config.get('api_key'))
        }
    
    def _init_minimax(self) -> Dict:
        """初始化MiniMax配置"""
        minimax_config = self.config.get('minimax', {})
        return {
            'api_key': minimax_config.get('api_key', ''),
            'group_id': minimax_config.get('group_id', ''),
            'base_url': minimax_config.get('base_url', 'https://api.minimax.chat/v1'),
            'model': minimax_config.get('model', 'MiniMax-M2.7'),
            'enabled': bool(minimax_config.get('api_key') and minimax_config.get('group_id'))
        }
    
    async def analyze_with_deepseek(self, symbol: str, timeframe: str, 
                                   technical_data: Dict, price_data: Dict) -> Dict:
        """使用DeepSeek分析"""
        if not self.models['deepseek']['enabled']:
            logger.warning("DeepSeek API未配置，跳过分析")
            return {"error": "DeepSeek API not configured"}
        
        prompt = self._create_analysis_prompt(symbol, timeframe, technical_data, price_data, "deepseek")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.models["deepseek"]["api_key"]}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'model': self.models['deepseek']['model'],
                    'messages': [
                        {
                            'role': 'system',
                            'content': '你是一个专业的加密货币技术分析师。请基于提供的技术指标数据进行分析，给出专业的交易建议。'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': 0.3,
                    'max_tokens': 2000
                }
                
                async with session.post(
                    f"{self.models['deepseek']['base_url']}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        analysis_text = result['choices'][0]['message']['content']
                        return self._parse_ai_response(analysis_text, "deepseek")
                    else:
                        error_text = await response.text()
                        logger.error(f"DeepSeek API错误: {response.status} - {error_text}")
                        return {"error": f"API error: {response.status}"}
                        
        except Exception as e:
            logger.error(f"DeepSeek分析失败: {e}")
            return {"error": str(e)}
    
    async def analyze_with_minimax(self, symbol: str, timeframe: str,
                                  technical_data: Dict, price_data: Dict) -> Dict:
        """使用MiniMax分析"""
        if not self.models['minimax']['enabled']:
            logger.warning("MiniMax API未配置，跳过分析")
            return {"error": "MiniMax API not configured"}
        
        prompt = self._create_analysis_prompt(symbol, timeframe, technical_data, price_data, "minimax")
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.models["minimax"]["api_key"]}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'model': self.models['minimax']['model'],
                    'messages': [
                        {
                            'role': 'system',
                            'content': '你是一个专业的加密货币技术分析师。请基于提供的技术指标数据进行分析，给出专业的交易建议。'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': 0.3,
                    'max_tokens': 2000,
                    'group_id': self.models['minimax']['group_id']
                }
                
                async with session.post(
                    f"{self.models['minimax']['base_url']}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        analysis_text = result['choices'][0]['message']['content']
                        return self._parse_ai_response(analysis_text, "minimax")
                    else:
                        error_text = await response.text()
                        logger.error(f"MiniMax API错误: {response.status} - {error_text}")
                        return {"error": f"API error: {response.status}"}
                        
        except Exception as e:
            logger.error(f"MiniMax分析失败: {e}")
            return {"error": str(e)}
    
    def _create_analysis_prompt(self, symbol: str, timeframe: str,
                               technical_data: Dict, price_data: Dict,
                               model_name: str) -> str:
        """创建分析提示词"""
        current_price = price_data.get('current_price', 0)
        price_change_24h = price_data.get('price_change_24h', 0)
        price_change_pct_24h = price_data.get('price_change_pct_24h', 0)
        
        prompt = f"""
请分析以下加密货币的技术指标数据：

币种: {symbol}
时间框架: {timeframe}
当前价格: ${current_price:,.2f}
24小时涨跌幅: {price_change_pct_24h:.2f}% ({price_change_24h:+,.2f})

技术指标数据:
{json.dumps(technical_data, indent=2, ensure_ascii=False)}

请按照以下结构进行分析：

1. 核心指标分析 (RSI, MACD, 移动平均线, 布林带)
   - 每个指标的当前值
   - 信号方向 (看涨/看跌/中性)
   - 置信度 (0-100)

2. 动量指标分析 (KD, 威廉指标, CCI)
   - 超买超卖状态
   - 动量方向

3. 趋势指标分析 (ADX, 抛物线SAR, Ichimoku云)
   - 趋势强度
   - 趋势方向

4. 波动率指标分析 (ATR, 波动率通道)
   - 波动率水平
   - 风险提示

5. 成交量指标分析 (OBV, 成交量分布)
   - 成交量趋势
   - 资金流向

6. 形态识别
   - K线形态
   - 图表形态
   - 指标背离检测

7. 多指标共振分析
   - 看涨共振强度
   - 看跌共振强度

8. 市场情绪分析
   - 整体情绪
   - 恐惧贪婪指数影响

9. 最终分析结论
   - 方向预测 (看涨/看跌/中性)
   - 置信度 (0-100)
   - 详细理由
   - 各时间框架分析 (1小时, 4小时, 24小时)
   - 关键支撑阻力位
   - 密集成交区

请以JSON格式返回分析结果，确保包含所有上述部分。
"""
        return prompt
    
    def _parse_ai_response(self, response_text: str, model_name: str) -> Dict:
        """解析AI响应"""
        try:
            # 尝试提取JSON部分
            lines = response_text.strip().split('\n')
            json_start = -1
            json_end = -1
            
            for i, line in enumerate(lines):
                if line.strip().startswith('{'):
                    json_start = i
                    break
            
            if json_start >= 0:
                for i in range(json_start, len(lines)):
                    if lines[i].strip().endswith('}'):
                        json_end = i
                        break
                
                if json_end >= json_start:
                    json_str = '\n'.join(lines[json_start:json_end + 1])
                    analysis = json.loads(json_str)
                    analysis['model'] = model_name
                    analysis['timestamp'] = datetime.now().isoformat()
                    return analysis
            
            # 如果找不到JSON，返回原始文本
            return {
                'model': model_name,
                'timestamp': datetime.now().isoformat(),
                'raw_response': response_text,
                'error': '无法解析JSON响应'
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"解析{model_name}响应失败: {e}")
            return {
                'model': model_name,
                'timestamp': datetime.now().isoformat(),
                'raw_response': response_text,
                'error': f'JSON解析失败: {str(e)}'
            }
        except Exception as e:
            logger.error(f"处理{model_name}响应失败: {e}")
            return {
                'model': model_name,
                'timestamp': datetime.now().isoformat(),
                'raw_response': response_text,
                'error': str(e)
            }
    
    async def analyze_dual_ai(self, symbol: str, timeframe: str,
                             technical_data: Dict, price_data: Dict) -> Dict:
        """双AI模型分析"""
        logger.info(f"开始双AI模型分析: {symbol} - {timeframe}")
        
        # 并行调用两个AI模型
        deepseek_task = self.analyze_with_deepseek(symbol, timeframe, technical_data, price_data)
        minimax_task = self.analyze_with_minimax(symbol, timeframe, technical_data, price_data)
        
        deepseek_result, minimax_result = await asyncio.gather(
            deepseek_task,
            minimax_task,
            return_exceptions=True
        )
        
        # 处理异常
        if isinstance(deepseek_result, Exception):
            deepseek_result = {"error": str(deepseek_result), "model": "deepseek"}
        if isinstance(minimax_result, Exception):
            minimax_result = {"error": str(minimax_result), "model": "minimax"}
        
        # 合并结果
        combined_result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': datetime.now().isoformat(),
            'deepseek_analysis': deepseek_result,
            'minimax_analysis': minimax_result,
            'consensus': self._calculate_consensus(deepseek_result, minimax_result)
        }
        
        logger.info(f"双AI模型分析完成: {symbol}")
        return combined_result
    
    def _calculate_consensus(self, deepseek_result: Dict, minimax_result: Dict) -> Dict:
        """计算两个模型的共识"""
        consensus = {
            'direction_agreement': False,
            'confidence_agreement': False,
            'final_direction': 'neutral',
            'final_confidence': 50,
            'agreement_score': 0,
            'disagreement_reasons': []
        }
        
        try:
            # 提取方向预测
            ds_direction = deepseek_result.get('final_analysis', {}).get('direction', 'neutral')
            mm_direction = minimax_result.get('final_analysis', {}).get('direction', 'neutral')
            
            # 提取置信度
            ds_confidence = deepseek_result.get('final_analysis', {}).get('confidence', 50)
            mm_confidence = minimax_result.get('final_analysis', {}).get('confidence', 50)
            
            # 检查方向一致性
            if ds_direction == mm_direction:
                consensus['direction_agreement'] = True
                consensus['final_direction'] = ds_direction
            else:
                consensus['direction_agreement'] = False
                # 选择置信度更高的方向
                if ds_confidence > mm_confidence:
                    consensus['final_direction'] = ds_direction
                else:
                    consensus['final_direction'] = mm_direction
            
            # 检查置信度一致性
            confidence_diff = abs(ds_confidence - mm_confidence)
            if confidence_diff <= 20:  # 差异小于20认为一致
                consensus['confidence_agreement'] = True
                consensus['final_confidence'] = (ds_confidence + mm_confidence) / 2
            else:
                consensus['confidence_agreement'] = False
                consensus['final_confidence'] = max(ds_confidence, mm_confidence)
            
            # 计算一致性分数
            direction_score = 50 if consensus['direction_agreement'] else 0
            confidence_score = 50 * (1 - min(confidence_diff / 100, 1))
            consensus['agreement_score'] = direction_score + confidence_score
            
            # 记录分歧原因
            if not consensus['direction_agreement']:
                ds_reason = deepseek_result.get('final_analysis', {}).get('reasoning', '无理由')
                mm_reason = minimax_result.get('final_analysis', {}).get('reasoning', '无理由')
                consensus['disagreement_reasons'] = [
                    f"DeepSeek: {ds_reason[:100]}...",
                    f"MiniMax: {mm_reason[:100]}..."
                ]
                
        except Exception as e:
            logger.error(f"计算共识失败: {e}")
            consensus['error'] = str(e)
        
        return consensus
    
    def generate_technical_data(self, symbol: str, timeframe: str) -> Dict:
        """生成技术指标数据（模拟，实际应从数据源获取）"""
        # 这里应该从数据库或API获取实际数据
        # 为了演示，返回模拟数据
        
        import random
        
        return {
            'core_indicators': {
                'rsi': {'value': random.uniform(30, 70), 'signal': 'neutral'},
                'macd': {'value': random.uniform(-10, 10), 'signal': 'neutral'},
                'moving_averages': {
                    'ma20': random.uniform(70000, 80000),
                    'ma50': random.uniform(69000,