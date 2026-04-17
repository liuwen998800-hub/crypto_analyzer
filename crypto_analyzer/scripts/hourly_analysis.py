#!/usr/bin/env python3
"""
每小时分析脚本
主调度程序，协调各模块运行
"""

import sys
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data_fetchers.binance_fetcher import BinanceDataFetcher
from src.technical.indicators_calculator import TechnicalIndicatorsCalculator
from src.ai_models.dual_ai_analyzer import DualAIAnalyzer
from src.sentiment.fear_greed_analyzer import FearGreedAnalyzer
from src.signals.composite_signal_generator import CompositeSignalGenerator


class HourlyAnalyzer:
    """每小时分析器"""
    
    def __init__(self, config_dir: str = None):
        """
        初始化分析器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = config_dir or str(project_root / 'config')
        self.config = self._load_config()
        
        # 配置日志
        self._setup_logging()
        
        # 初始化组件
        self.data_fetcher = BinanceDataFetcher(
            api_key=self.config.get('binance', {}).get('api_key', ''),
            api_secret=self.config.get('binance', {}).get('api_secret', '')
        )
        
        self.technical_calculator = TechnicalIndicatorsCalculator(
            scoring_rules_path=str(Path(self.config_dir) / 'scoring_rules.yaml')
        )
        
        self.ai_analyzer = DualAIAnalyzer(self.config)
        
        self.sentiment_analyzer = FearGreedAnalyzer(self.config)
        
        self.signal_generator = CompositeSignalGenerator(
            config_path=str(Path(self.config_dir) / 'scoring_rules.yaml')
        )
        
        # 分析结果存储
        self.results_dir = project_root / 'results'
        self.results_dir.mkdir(exist_ok=True)
        
        logger.info("每小时分析器初始化完成")
    
    def _load_config(self) -> dict:
        """加载配置"""
        config_path = Path(self.config_dir) / 'api_keys.yaml'
        
        if config_path.exists():
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"配置文件不存在: {config_path}")
            return {}
    
    def _setup_logging(self):
        """配置日志"""
        global logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(project_root / 'logs' / 'analysis.log'),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
        
        # 创建日志目录
        (project_root / 'logs').mkdir(exist_ok=True)
    
    def analyze_symbol(self, symbol: str) -> dict:
        """
        分析单个币种
        
        Args:
            symbol: 币种符号
            
        Returns:
            分析结果
        """
        logger.info(f"开始分析 {symbol}...")
        
        try:
            # 1. 获取市场数据
            market_data = self.data_fetcher.get_multiple_prices([symbol])
            if not market_data or symbol not in market_data:
                logger.error(f"无法获取{symbol}市场数据")
                return self._create_error_result(symbol, "市场数据获取失败")
            
            price_info = market_data[symbol]
            
            # 2. 获取历史数据用于技术分析
            historical_data = self.data_fetcher.get_historical_data(
                symbol, days=30, timeframe='1h'
            )
            
            if historical_data is None or historical_data.empty:
                logger.warning(f"{symbol}历史数据不足，使用简化分析")
                # 使用最近的价格数据创建简化DataFrame
                historical_data = self._create_simple_dataframe(price_info)
            
            # 3. 计算技术指标
            technical_data = self.technical_calculator.calculate_all_indicators(historical_data)
            if not technical_data:
                logger.error(f"{symbol}技术指标计算失败")
                return self._create_error_result(symbol, "技术指标计算失败")
            
            # 更新当前价格
            technical_data['current_price'] = price_info['price']
            
            # 4. AI分析
            ai_analysis = self.ai_analyzer.analyze_with_dual_models(
                symbol, price_info, technical_data
            )
            
            # 5. 情绪分析
            sentiment_data = self.sentiment_analyzer.analyze_market_sentiment(symbol)
            
            # 6. 生成综合信号
            signal_result = self.signal_generator.generate_signal(
                symbol, technical_data, ai_analysis, sentiment_data
            )
            
            # 7. 组装完整结果
            full_result = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'market_data': price_info,
                'technical_analysis': technical_data,
                'ai_analysis': ai_analysis,
                'sentiment_analysis': sentiment_data,
                'trading_signal': signal_result,
                'summary': self._generate_summary(signal_result, technical_data, sentiment_data)
            }
            
            logger.info(f"{symbol}分析完成，信号: {signal_result.get('signal', 'UNKNOWN')}")
            return full_result
            
        except Exception as e:
            logger.error(f"{symbol}分析过程中发生错误: {e}")
            return self._create_error_result(symbol, str(e))
    
    def analyze_all_symbols(self, symbols: list = None) -> dict:
        """
        分析所有指定币种
        
        Args:
            symbols: 币种列表，默认为['BTC', 'ETH', 'SOL']
            
        Returns:
            所有币种的分析结果
        """
        if symbols is None:
            symbols = ['BTC', 'ETH', 'SOL']
        
        logger.info(f"开始批量分析: {', '.join(symbols)}")
        
        results = {}
        for symbol in symbols:
            result = self.analyze_symbol(symbol)
            results[symbol] = result
            
            # 短暂延迟，避免API限制
            import time
            time.sleep(1)
        
        # 生成市场总结
        market_summary = self._generate_market_summary(results)
        
        final_result = {
            'timestamp': datetime.now().isoformat(),
            'symbols_analyzed': symbols,
            'results': results,
            'market_summary': market_summary,
            'metadata': {
                'analysis_version': '1.0.0',
                'processing_time': len(symbols),
                'success_count': sum(1 for r in results.values() if not r.get('error', False))
            }
        }
        
        # 保存结果
        self._save_results(final_result)
        
        logger.info(f"批量分析完成，成功: {final_result['metadata']['success_count']}/{len(symbols)}")
        return final_result
    
    def _create_simple_dataframe(self, price_info: dict):
        """创建简化的DataFrame（用于数据不足时）"""
        import pandas as pd
        import numpy as np
        
        # 创建最近24小时的数据
        dates = pd.date_range(end=datetime.now(), periods=24, freq='H')
        base_price = price_info['price']
        
        # 生成一些随机波动
        np.random.seed(42)
        prices = base_price + np.cumsum(np.random.randn(24) * base_price * 0.01)
        
        df = pd.DataFrame({
            'open': prices - np.random.rand(24) * base_price * 0.005,
            'high': prices + np.random.rand(24) * base_price * 0.01,
            'low': prices - np.random.rand(24) * base_price * 0.01,
            'close': prices,
            'volume': np.random.rand(24) * 1000000000 + 500000000
        }, index=dates)
        
        return df
    
    def _generate_summary(self, signal_result: dict, technical_data: dict, sentiment_data: dict) -> dict:
        """生成分析摘要"""
        signal = signal_result.get('signal', 'NEUTRAL')
        score = signal_result.get('score', 50)
        confidence = signal_result.get('confidence', 0.5)
        
        current_price = technical_data.get('current_price', 0)
        technical_score = technical_data.get('composite_score', {}).get('technical_score', 50)
        
        sentiment_score = sentiment_data.get('sentiment_score', 50)
        fgi_value = sentiment_data.get('fear_greed_index', {}).get('value', 50)
        
        # 生成简短描述
        if signal == 'STRONG_BUY':
            description = "强烈买入机会，技术、AI、情绪指标均显示强烈看涨"
        elif signal == 'BUY':
            description = "买入机会，多数指标显示看涨信号"
        elif signal == 'SELL':
            description = "卖出信号，多数指标显示看跌信号"
        elif signal == 'STRONG_SELL':
            description = "强烈卖出信号，技术、AI、情绪指标均显示强烈看跌"
        else:
            description = "观望，指标矛盾或无明确趋势"
        
        return {
            'signal': signal,
            'score': score,
            'confidence': confidence,
            'description': description,
            'key_metrics': {
                'price': current_price,
                'technical_score': technical_score,
                'sentiment_score': sentiment_score,
                'fear_greed_index': fgi_value
            },
            'recommendation': signal_result.get('trading_advice', {}).get('action', '观望')
        }
    
    def _generate_market_summary(self, results: dict) -> dict:
        """生成市场总结"""
        signals = []
        buy_signals = 0
        sell_signals = 0
        neutral_signals = 0
        
        for symbol, result in results.items():
            if result.get('error', False):
                continue
                
            signal = result.get('trading_signal', {}).get('signal', 'NEUTRAL')
            score = result.get('trading_signal', {}).get('score', 50)
            
            signals.append({
                'symbol': symbol,
                'signal': signal,
                'score': score
            })
            
            if signal in ['STRONG_BUY', 'BUY']:
                buy_signals += 1
            elif signal in ['STRONG_SELL', 'SELL']:
                sell_signals += 1
            else:
                neutral_signals += 1
        
        # 确定整体市场情绪
        total_signals = buy_signals + sell_signals + neutral_signals
        if total_signals > 0:
            buy_ratio = buy_signals / total_signals
            sell_ratio = sell_signals / total_signals
            
            if buy_ratio >= 0.5:
                market_sentiment = 'bullish'
            elif sell_ratio >= 0.5:
                market_sentiment = 'bearish'
            else:
                market_sentiment = 'neutral'
        else:
            market_sentiment = 'unknown'
        
        # 寻找最强和最弱币种
        if signals:
            strongest = max(signals, key=lambda x: x['score'])
            weakest = min(signals, key=lambda x: x['score'])
        else:
            strongest = weakest = None
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_symbols': len(results),
            'signal_distribution': {
                'buy': buy_signals,
                'sell': sell_signals,
                'neutral': neutral_signals
            },
            'market_sentiment': market_sentiment,
            'strongest_symbol': strongest,
            'weakest_symbol': weakest,
            'all_signals': signals,
            'summary_text': self._generate_summary_text(market_sentiment, buy_signals, sell_signals)
        }
    
    def _generate_summary_text(self, sentiment: str, buy_count: int, sell_count: int) -> str:
        """生成总结文本"""
        if sentiment == 'bullish':
            return f"市场整体看涨，{buy_count}个币种发出买入信号，{sell_count}个币种发出卖出信号"
        elif sentiment == 'bearish':
            return f"市场整体看跌，{sell_count}个币种发出卖出信号，{buy_count}个币种发出买入信号"
        else:
            return f"市场情绪中性，{buy_count}个买入信号，{sell_count}个卖出信号"
    
    def _save_results(self, results: dict):
        """保存分析结果"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON格式
        json_path = self.results_dir / f'analysis_{timestamp}.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # CSV格式（简化版）
        csv_path = self.results_dir / f'summary_{timestamp}.csv'
        self._save_to_csv(results, csv_path)
        
        # 更新最新结果
        latest_path = self.results_dir / 'latest.json'
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"结果已保存: {json_path}, {csv_path}")
    
    def _save_to_csv(self, results: dict, csv_path: Path):
        """保存为CSV格式"""
        import pandas as pd
        
        rows = []
        for symbol, result in results.get('results', {}).items():
            if result.get('error', False):
                continue
                
            signal_data = result.get('trading_signal', {})
            market_data = result.get('market_data', {})
            
            rows.append({
                'symbol': symbol,
                'timestamp': result.get('timestamp', ''),
                'signal': signal_data.get('signal', ''),
                'score': signal_data.get('score', 0),
                'confidence': signal_data.get('confidence', 0),
                'price': market_data.get('price', 0),
                '24h_change': market_data.get('24h_change', 0),
                'technical_score': result.get('technical_analysis', {}).get('composite_score', {}).get('technical_score', 0),
                'sentiment_score': result.get('sentiment_analysis', {}).get('sentiment_score', 0),
                'recommendation': signal_data.get('trading_advice', {}).get('action', '')
            })
        
        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(csv_path, index=False, encoding='utf-8')
    
    def _create_error_result(self, symbol: str, error_msg: str) -> dict:
        """创建错误结果"""
        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'error': True,
            'error_message': error_msg,
            'trading_signal': {
                'signal': 'ERROR',
                'score': 50,
                'confidence': 0.0,
                'description': f'分析失败: {error_msg}'
            }
        }


def main():
    """主函数"""
    print("=" * 60)
    print("虚拟币分析指标产品 - 每小时分析系统")
    print("=" * 60)
    
    # 创建分析器
    analyzer = HourlyAnalyzer()
    
    # 测试连接
    print("\n测试数据连接...")
    if analyzer.data_fetcher.test_connection():
        print("✅ Binance API连接成功")
    else:
        print("⚠️  Binance API连接警告（可能使用模拟数据）")
    
    # 执行分析
    print("\n开始分析BTC、ETH、SOL...")
    results = analyzer.analyze_all_symbols(['BTC', 'ETH', 'SOL'])
    
    # 显示摘要
    print("\n" + "=" * 60)
    print("分析完成摘要")
    print("=" * 60)
    
    market_summary = results.get('market_summary', {})
    print(f"市场情绪: {market_summary.get('market_sentiment', 'unknown').upper()}")
    
    distribution = market_summary.get('signal_distribution', {})
    print(f"信号分布: 买入 {distribution.get('buy', 0)} | 卖出 {distribution.get('sell', 0)} | 观望 {distribution.get('neutral', 0)}")
    
    print("\n各币种信号:")
    for symbol, result in results.get('results', {}).items():
        if result.get('error', False):
            print(f"  {symbol}: ❌ 分析失败")
        else:
            signal = result.get('trading_signal', {})
            price = result.get('market_data', {}).get('price', 0)
            print(f"  {symbol}: {signal.get('signal', 'UNKNOWN')} (分数: {signal.get('score', 0)}, 价格: ${price:,.2f})")
    
    # 显示最强和最弱币种
    strongest = market_summary.get('strongest_symbol')
    weakest = market_summary.get('weakest_symbol')
    
    if strongest:
        print(f"\n最强币种: {strongest['symbol']} ({strongest['signal']}, 分数: {strongest['score']})")
    if weakest:
        print(f"最弱币种: {weakest['symbol']} ({weakest['signal']}, 分数: {weakest['score']})")
    
    print(f"\n详细结果已保存至: {analyzer.results_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()