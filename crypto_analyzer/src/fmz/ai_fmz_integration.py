#!/usr/bin/env python3
"""
AI分析系统与FMZ平台集成模块
将AI分析结果转换为FMZ可执行的交易信号
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests
import threading
from dataclasses import dataclass, asdict
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SignalDirection(Enum):
    """信号方向"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class SignalStrength(Enum):
    """信号强度"""
    WEAK = "weak"      # 置信度 < 60%
    MODERATE = "moderate"  # 置信度 60-75%
    STRONG = "strong"    # 置信度 75-90%
    VERY_STRONG = "very_strong"  # 置信度 > 90%


@dataclass
class AISignal:
    """AI分析信号"""
    symbol: str  # 交易对，如BTC_USDT
    direction: SignalDirection  # 方向
    confidence: float  # 置信度 0-100%
    price: Optional[float] = None  # 建议价格
    amount: Optional[float] = None  # 建议数量
    reasoning: Optional[str] = None  # 推理过程
    timestamp: Optional[str] = None  # 时间戳
    source: Optional[str] = None  # 信号来源
    support_levels: Optional[List[Dict]] = None  # 支撑位
    resistance_levels: Optional[List[Dict]] = None  # 阻力位
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['direction'] = self.direction.value
        data['timestamp'] = self.timestamp or datetime.now().isoformat()
        return data
    
    def get_strength(self) -> SignalStrength:
        """获取信号强度"""
        if self.confidence >= 90:
            return SignalStrength.VERY_STRONG
        elif self.confidence >= 75:
            return SignalStrength.STRONG
        elif self.confidence >= 60:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def is_actionable(self, min_confidence: float = 60) -> bool:
        """是否可执行（置信度是否足够）"""
        return self.confidence >= min_confidence


class AIFMZIntegrator:
    """AI-FMZ集成器"""
    
    def __init__(self, ai_api_url: str = "http://localhost:5000",
                 fmz_api_url: str = "http://localhost:5001",
                 min_confidence: float = 60):
        """
        初始化集成器
        
        Args:
            ai_api_url: AI分析API地址
            fmz_api_url: FMZ API地址
            min_confidence: 最小执行置信度
        """
        self.ai_api_url = ai_api_url.rstrip('/')
        self.fmz_api_url = fmz_api_url.rstrip('/')
        self.min_confidence = min_confidence
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'AIFMZIntegrator/1.0'
        })
        
        # 信号历史
        self.signal_history: List[Dict] = []
        self.max_history_size = 1000
        
        # 交易统计
        self.trade_stats = {
            'total_signals': 0,
            'executed_signals': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_profit': 0.0,
            'win_rate': 0.0
        }
        
        logger.info(f"AI-FMZ集成器初始化完成")
        logger.info(f"AI API: {self.ai_api_url}")
        logger.info(f"FMZ API: {self.fmz_api_url}")
        logger.info(f"最小置信度: {min_confidence}%")
    
    def check_ai_api_status(self) -> bool:
        """检查AI API状态"""
        try:
            response = self.session.get(f"{self.ai_api_url}/api/status", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"AI API状态检查失败: {e}")
            return False
    
    def check_fmz_api_status(self) -> bool:
        """检查FMZ API状态"""
        try:
            response = self.session.get(f"{self.fmz_api_url}/api/fmz/status", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"FMZ API状态检查失败: {e}")
            return False
    
    def get_ai_analysis(self, symbol: str = "BTC", timeframe: str = "1h") -> Optional[Dict]:
        """
        获取AI分析结果
        
        Args:
            symbol: 币种
            timeframe: 时间框架
        """
        try:
            payload = {
                "symbol": symbol,
                "timeframe": timeframe,
                "ai_model": "both"
            }
            
            response = self.session.post(
                f"{self.ai_api_url}/api/analyze",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"获取AI分析失败: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"获取AI分析异常: {e}")
            return None
    
    def convert_ai_to_signal(self, ai_analysis: Dict) -> Optional[AISignal]:
        """
        将AI分析转换为交易信号
        
        Args:
            ai_analysis: AI分析结果
        """
        try:
            symbol = ai_analysis.get('symbol', 'BTC')
            signal_data = ai_analysis.get('signal', {})
            ai_analysis_data = ai_analysis.get('ai_analysis', {})
            
            # 获取综合信号
            signal_score = signal_data.get('score', 50)
            signal_direction = signal_data.get('signal', '').lower()
            
            # 确定方向
            if signal_direction == 'buy':
                direction = SignalDirection.BUY
            elif signal_direction == 'sell':
                direction = SignalDirection.SELL
            else:
                direction = SignalDirection.HOLD
            
            # 计算综合置信度
            confidence = signal_score
            
            # 获取价格数据
            price_data = ai_analysis.get('price_data', {})
            current_price = price_data.get('current_price')
            
            # 获取AI详细分析
            reasoning = ""
            if ai_analysis_data.get('deepseek'):
                ds = ai_analysis_data['deepseek']
                reasoning += f"DeepSeek: {ds.get('direction', 'neutral')} ({ds.get('confidence', 0)}%)\n"
                reasoning += ds.get('reasoning', '')[:200] + "\n\n"
            
            if ai_analysis_data.get('minimax'):
                mm = ai_analysis_data['minimax']
                reasoning += f"MiniMax: {mm.get('direction', 'neutral')} ({mm.get('confidence', 0)}%)\n"
                reasoning += mm.get('reasoning', '')[:200]
            
            # 获取支撑阻力位
            support_resistance = ai_analysis.get('support_resistance', {})
            support_levels = support_resistance.get('key_supports', [])
            resistance_levels = support_resistance.get('key_resistances', [])
            
            # 创建信号
            signal = AISignal(
                symbol=f"{symbol}_USDT",
                direction=direction,
                confidence=confidence,
                price=current_price,
                reasoning=reasoning.strip(),
                source="ai_analysis",
                support_levels=support_levels,
                resistance_levels=resistance_levels
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"转换AI分析为信号失败: {e}")
            return None
    
    def execute_signal(self, signal: AISignal) -> Dict:
        """
        执行交易信号
        
        Args:
            signal: AI信号
        """
        self.trade_stats['total_signals'] += 1
        
        # 检查信号是否可执行
        if not signal.is_actionable(self.min_confidence):
            logger.info(f"信号置信度过低({signal.confidence}%)，跳过执行")
            return {
                'status': 'skipped',
                'reason': 'confidence_too_low',
                'confidence': signal.confidence,
                'min_confidence': self.min_confidence
            }
        
        if signal.direction == SignalDirection.HOLD:
            logger.info("信号方向为HOLD，跳过执行")
            return {
                'status': 'skipped',
                'reason': 'direction_hold'
            }
        
        try:
            # 准备执行数据
            execute_data = {
                'symbol': signal.symbol,
                'direction': signal.direction.value,
                'confidence': signal.confidence,
                'price': signal.price,
                'amount': signal.amount,
                'reasoning': signal.reasoning
            }
            
            # 发送到FMZ API执行
            response = self.session.post(
                f"{self.fmz_api_url}/api/fmz/execute-signal",
                json=execute_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 更新统计
                self.trade_stats['executed_signals'] += 1
                if result.get('status') == 'success':
                    self.trade_stats['successful_trades'] += 1
                else:
                    self.trade_stats['failed_trades'] += 1
                
                # 计算胜率
                if self.trade_stats['executed_signals'] > 0:
                    self.trade_stats['win_rate'] = (
                        self.trade_stats['successful_trades'] / 
                        self.trade_stats['executed_signals'] * 100
                    )
                
                logger.info(f"信号执行结果: {result.get('status')}")
                return result
            else:
                error_msg = f"FMZ API错误: {response.status_code}"
                logger.error(error_msg)
                return {
                    'status': 'failed',
                    'error': error_msg
                }
                
        except Exception as e:
            error_msg = f"执行信号失败: {e}"
            logger.error(error_msg)
            return {
                'status': 'failed',
                'error': error_msg
            }
    
    def analyze_and_execute(self, symbol: str = "BTC", timeframe: str = "1h") -> Dict:
        """
        分析并执行（完整流程）
        
        Args:
            symbol: 币种
            timeframe: 时间框架
        """
        logger.info(f"开始分析并执行: {symbol} {timeframe}")
        
        # 1. 获取AI分析
        ai_analysis = self.get_ai_analysis(symbol, timeframe)
        if not ai_analysis:
            return {'status': 'failed', 'reason': 'ai_analysis_failed'}
        
        # 2. 转换为信号
        signal = self.convert_ai_to_signal(ai_analysis)
        if not signal:
            return {'status': 'failed', 'reason': 'signal_conversion_failed'}
        
        # 3. 记录信号
        signal_dict = signal.to_dict()
        signal_dict['ai_analysis_timestamp'] = ai_analysis.get('timestamp')
        
        self.signal_history.append(signal_dict)
        if len(self.signal_history) > self.max_history_size:
            self.signal_history.pop(0)
        
        # 4. 执行信号
        execution_result = self.execute_signal(signal)
        
        # 5. 合并结果
        result = {
            'status': execution_result.get('status'),
            'symbol': symbol,
            'timeframe': timeframe,
            'signal': signal_dict,
            'execution': execution_result,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"分析执行完成: {result['status']}")
        return result
    
    def get_signal_history(self, limit: int = 50) -> List[Dict]:
        """获取信号历史"""
        return self.signal_history[-limit:] if self.signal_history else []
    
    def get_trade_stats(self) -> Dict:
        """获取交易统计"""
        return self.trade_stats.copy()
    
    def reset_stats(self):
        """重置统计"""
        self.trade_stats = {
            'total_signals': 0,
            'executed_signals': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'total_profit': 0.0,
            'win_rate': 0.0
        }
        logger.info("交易统计已重置")


class AutoTradingBot(threading.Thread):
    """自动交易机器人"""
    
    def __init__(self, integrator: AIFMZIntegrator, interval: int = 300):
        """
        初始化自动交易机器人
        
        Args:
            integrator: AI-FMZ集成器
            interval: 检查间隔（秒）
        """
        super().__init__()
        self.integrator = integrator
        self.interval = interval
        self.running = False
        self.daemon = True
        self.symbols = ["BTC", "ETH"]  # 监控的币种
        self.timeframe = "1h"  # 时间框架
        
        logger.info(f"自动交易机器人初始化完成")
        logger.info(f"监控币种: {self.symbols}")
        logger.info(f"时间框架: {self.timeframe}")
        logger.info(f"检查间隔: {interval}秒")
    
    def run(self):
        """机器人主循环"""
        self.running = True
        logger.info("自动交易机器人启动")
        
        while self.running:
            try:
                # 检查API状态
                ai_ok = self.integrator.check_ai_api_status()
                fmz_ok = self.integrator.check_fmz_api_status()
                
                if not ai_ok:
                    logger.warning("AI API不可用，跳过本次检查")
                    time.sleep(self.interval)
                    continue
                
                if not fmz_ok:
                    logger.warning("FMZ API不可用，跳过本次检查")
                    time.sleep(self.interval)
                    continue
                
                # 对每个币种进行分析
                for symbol in self.symbols:
                    try:
                        logger.info(f"分析 {symbol}...")
                        result = self.integrator.analyze_and_execute(symbol, self.timeframe)
                        
                        # 记录结果
                        status = result.get('status', 'unknown')
                        signal = result.get('signal', {})
                        direction = signal.get('direction', 'hold')
                        confidence = signal.get('confidence', 0)
                        
                        logger.info(f"{symbol} 分析结果: {direction} ({confidence}%) - {status}")
                        
                        # 短暂延迟，避免API限制
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"分析 {symbol} 失败: {e}")
                
                # 显示统计信息
                stats = self.integrator.get_trade_stats()
                logger.info(f"交易统计: {stats}")
                
            except Exception as e:
                logger.error(f"自动交易循环异常: {e}")
            
            # 等待下次检查
            logger.info(f"等待 {self.interval} 秒后再次检查...")
            time.sleep(self.interval)
    
    def stop(self):
        """停止机器人"""
        self.running = False
        logger.info("自动交易机器人停止")


# ========== 使用示例 ==========

def main():
    """使用示例"""
    print("AI-FMZ集成系统测试")
    
    # 创建集成器
    integrator = AIFMZIntegrator(
        ai_api_url="http://localhost:5000",
        fmz_api_url="http://localhost:5001",
        min_confidence=60
    )
    
    # 检查API状态
    print("检查API状态...")
    ai_status = integrator.check_ai_api_status()
    fmz_status = integrator.check_fmz_api_status()
    
    print(f"AI API状态: {'正常' if ai_status else '异常'}")
    print(f"FMZ API状态: {'正常' if fmz_status else '异常'}")
    
    if not ai_status or not fmz_status:
        print("API状态异常，请检查服务是否运行")
        return
    
    # 测试单次分析执行
    print("\n测试单次分析执行...")
    result = integrator.analyze_and_execute("BTC", "1h")
    
    print(f"执行结果: {result.get('status')}")
    if 'signal' in result:
        signal = result['signal']
        print(f"信号: {signal.get('direction')} ({signal.get('confidence')}%)")
    
    # 显示信号历史
    print(f"\n信号历史 ({len(integrator.signal_history)}条):")
    for i, signal in enumerate(integrator.get_signal_history(5)):
        print(f"  {i+1}. {signal.get('symbol')} - {signal.get('direction')} "
              f"({signal.get('confidence')}%)")
    
    # 显示交易统计
    stats = integrator.get_trade_stats()
    print(f"\n交易统计:")
    print(f"  总信号数: {stats['total_signals']}")
    print(f"  执行信号数: {stats['executed_signals']}")
    print(f"  成功交易: {stats['successful_trades']}")
    print(f"  失败交易: {stats['failed_trades']}")
    print(f"  胜率: {stats['win_rate']:.1f}%")
    
    print("\n测试完成！")


if __name__ == "__main__":
    main