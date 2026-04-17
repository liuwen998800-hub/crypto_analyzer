#!/usr/bin/env python3
"""
连接测试脚本
测试所有组件的连接和功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data_fetchers.binance_fetcher import BinanceDataFetcher
from src.technical.indicators_calculator import TechnicalIndicatorsCalculator
from src.ai_models.dual_ai_analyzer import DualAIAnalyzer
from src.sentiment.fear_greed_analyzer import FearGreedAnalyzer
from src.signals.composite_signal_generator import CompositeSignalGenerator


def test_binance_connection():
    """测试Binance连接"""
    print("测试Binance连接...")
    
    fetcher = BinanceDataFetcher()
    
    # 测试连接
    if fetcher.test_connection():
        print("✅ Binance API连接成功")
        
        # 测试获取价格
        btc_price = fetcher.get_current_price('BTC')
        if btc_price:
            print(f"  BTC价格: ${btc_price:,.2f}")
        else:
            print("  ❌ 获取BTC价格失败")
        
        # 测试获取多种价格
        prices = fetcher.get_multiple_prices(['BTC', 'ETH', 'SOL'])
        if prices:
            print(f"  成功获取{len(prices)}种币种价格")
            for symbol, data in prices.items():
                print(f"    {symbol}: ${data['price']:,.2f} (24h: {data['24h_change']:+.2f}%)")
        else:
            print("  ❌ 获取多种价格失败")
        
        return True
    else:
        print("❌ Binance API连接失败")
        return False


def test_technical_calculator():
    """测试技术指标计算"""
    print("\n测试技术指标计算...")
    
    calculator = TechnicalIndicatorsCalculator()
    
    # 创建测试数据
    import pandas as pd
    import numpy as np
    
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
    
    # 计算技术指标
    results = calculator.calculate_all_indicators(df)
    
    if results:
        print("✅ 技术指标计算成功")
        print(f"  综合评分: {results['composite_score']['technical_score']}")
        print(f"  置信度: {results['composite_score']['confidence']}")
        
        if results['support_resistance']['supports']:
            print(f"  支撑位: {', '.join([f'${s:,.0f}' for s in results['support_resistance']['supports'][:2]])}")
        if results['support_resistance']['resistances']:
            print(f"  阻力位: {', '.join([f'${r:,.0f}' for r in results['support_resistance']['resistances'][:2]])}")
        
        return True
    else:
        print("❌ 技术指标计算失败")
        return False


def test_ai_analyzer():
    """测试AI分析器"""
    print("\n测试AI分析器...")
    
    # 测试配置
    test_config = {
        'deepseek': {
            'api_key': '',  # 需要实际密钥
            'model': 'deepseek-chat'
        },
        'minimax': {
            'api_key': '',  # 需要实际密钥
            'model': 'MiniMax-M2.7'
        }
    }
    
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
            }
        },
        'composite_score': {
            'technical_score': 65
        }
    }
    
    # 测试分析
    result = analyzer.analyze_with_dual_models('BTC', test_market_data, test_technical_data)
    
    if result:
        print("✅ AI分析器测试成功")
        print(f"  综合信号: {result['composite_signal']['signal']}")
        print(f"  AI置信度: {result['ai_confidence']}")
        print(f"  一致性评分: {result['consensus']['score']}")
        
        # 检查是否使用模拟数据
        if result['deepseek_analysis'].get('is_mock', False):
            print("  ⚠️  使用模拟数据（未配置API密钥）")
        
        return True
    else:
        print("❌ AI分析器测试失败")
        return False


def test_sentiment_analyzer():
    """测试情绪分析器"""
    print("\n测试情绪分析器...")
    
    analyzer = FearGreedAnalyzer()
    
    # 测试恐慌贪婪指数
    fgi_result = analyzer.calculate_fear_greed_index('BTC')
    
    if fgi_result:
        print("✅ 情绪分析器测试成功")
        print(f"  恐慌贪婪指数: {fgi_result['value']} ({fgi_result['classification']})")
        print(f"  情绪分数: {fgi_result['score']}")
        print(f"  描述: {fgi_result['description']}")
        
        # 测试综合情绪分析
        sentiment_result = analyzer.analyze_market_sentiment('BTC')
        if sentiment_result:
            print(f"  情绪信号: {sentiment_result['signal']}")
            print(f"  可靠性因子: {sentiment_result['reliability_factor']}")
        
        # 检查是否使用模拟数据
        if fgi_result.get('is_mock', False):
            print("  ⚠️  使用模拟数据（API可能不可用）")
        
        return True
    else:
        print("❌ 情绪分析器测试失败")
        return False


def test_signal_generator():
    """测试信号生成器"""
    print("\n测试信号生成器...")
    
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
        'sentiment_score': 75,
        'reliability_factor': 0.9,
        'fear_greed_index': {
            'value': 25,
            'classification': 'Fear'
        }
    }
    
    # 生成信号
    signal_result = generator.generate_signal(
        'BTC',
        test_technical_data,
        test_ai_analysis,
        test_sentiment_data
    )
    
    if signal_result and not signal_result.get('error', False):
        print("✅ 信号生成器测试成功")
        print(f"  信号: {signal_result['signal']}")
        print(f"  分数: {signal_result['score']}")
        print(f"  置信度: {signal_result['confidence']}")
        print(f"  建议: {signal_result['trading_advice']['action']}")
        
        return True
    else:
        print("❌ 信号生成器测试失败")
        if signal_result:
            print(f"  错误: {signal_result.get('error_message', '未知错误')}")
        return False


def test_integration():
    """测试集成功能"""
    print("\n测试集成功能...")
    
    from scripts.hourly_analysis import HourlyAnalyzer
    
    analyzer = HourlyAnalyzer()
    
    # 测试单个币种分析
    print("测试BTC分析...")
    btc_result = analyzer.analyze_symbol('BTC')
    
    if btc_result and not btc_result.get('error', False):
        print("✅ 集成测试成功")
        signal = btc_result.get('trading_signal', {})
        print(f"  BTC信号: {signal.get('signal', 'UNKNOWN')}")
        print(f"  分数: {signal.get('score', 0)}")
        print(f"  价格: ${btc_result.get('market_data', {}).get('price', 0):,.2f}")
        
        # 检查各组件状态
        if btc_result.get('technical_analysis'):
            print("  ✅ 技术分析正常")
        if btc_result.get('ai_analysis'):
            print("  ✅ AI分析正常")
        if btc_result.get('sentiment_analysis'):
            print("  ✅ 情绪分析正常")
        
        return True
    else:
        print("❌ 集成测试失败")
        if btc_result:
            print(f"  错误: {btc_result.get('error_message', '未知错误')}")
        return False


def main():
    """主测试函数"""
    print("=" * 60)
    print("虚拟币分析指标产品 - 连接测试")
    print("=" * 60)
    
    test_results = {}
    
    # 运行所有测试
    test_results['binance'] = test_binance_connection()
    test_results['technical'] = test_technical_calculator()
    test_results['ai'] = test_ai_analyzer()
    test_results['sentiment'] = test_sentiment_analyzer()
    test_results['signal'] = test_signal_generator()
    test_results['integration'] = test_integration()
    
    # 显示总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("\n✅ 所有测试通过！系统准备就绪。")
        print("\n下一步:")
        print("1. 编辑 config/api_keys.yaml 配置API密钥")
        print("2. 运行 python scripts/hourly_analysis.py 进行完整分析")
        print("3. 运行 python scripts/scheduler_service.py 启动调度服务")
    else:
        print("\n⚠️  部分测试失败，请检查:")
        for test_name, result in test_results.items():
            status = "✅" if result else "❌"
            print(f"  {status} {test_name}")
        
        print("\n建议:")
        if not test_results['binance']:
            print("  • 检查网络连接，Binance API可能需要代理")
        if not test_results['ai']:
            print("  • 配置DeepSeek和MiniMax API密钥以获得完整AI分析")
        if not test_results['sentiment']:
            print("  • 情绪分析使用模拟数据，可配置真实API")
    
    print("=" * 60)


if __name__ == "__main__":
    main()