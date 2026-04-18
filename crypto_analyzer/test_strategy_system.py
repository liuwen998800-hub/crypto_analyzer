#!/usr/bin/env python3
"""
策略系统完整测试
"""

import requests
import json
import time
from datetime import datetime

print("🎯 策略系统完整测试")
print("=" * 60)
print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 测试配置
STRATEGY_API_URL = "http://localhost:5002"
FMZ_API_URL = "http://localhost:5001"
AI_API_URL = "http://localhost:5000"

def test_strategy_api():
    """测试策略API服务"""
    print("1. 🔌 测试策略API服务...")
    print("-" * 40)
    
    try:
        # 测试健康检查
        response = requests.get(f"{STRATEGY_API_URL}/api/strategy/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ 策略API服务健康检查通过")
        else:
            print(f"   ❌ 健康检查失败: {response.status_code}")
            return False
        
        # 测试状态检查
        response = requests.get(f"{STRATEGY_API_URL}/api/strategy/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ 策略服务状态: {data.get('status', '未知')}")
            print(f"   ✅ 活跃策略: {', '.join(data.get('active_strategies', []))}")
        else:
            print(f"   ❌ 状态检查失败: {response.status_code}")
            return False
        
        # 测试获取策略列表
        response = requests.get(f"{STRATEGY_API_URL}/api/strategy/strategies", timeout=5)
        if response.status_code == 200:
            data = response.json()
            strategies = data.get('strategies', [])
            print(f"   ✅ 可用策略数量: {len(strategies)}")
            for strategy in strategies:
                print(f"      - {strategy.get('name')}: {strategy.get('description')}")
        else:
            print(f"   ❌ 获取策略列表失败: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ 策略API测试异常: {e}")
        return False

def test_ai_signal_processing():
    """测试AI信号处理"""
    print("\n2. 🤖 测试AI信号处理...")
    print("-" * 40)
    
    # 模拟AI信号
    ai_signal = {
        'symbol': 'BTC_USDT',
        'direction': 'buy',
        'confidence': 78.5,
        'price': 75234.50,
        'amount': 0.001,
        'reasoning': '技术分析显示看涨信号，RSI超卖反弹，MACD金叉形成'
    }
    
    print(f"   模拟AI信号:")
    print(f"     币种: {ai_signal['symbol']}")
    print(f"     方向: {ai_signal['direction'].upper()}")
    print(f"     置信度: {ai_signal['confidence']}%")
    print(f"     价格: ${ai_signal['price']:,.2f}")
    print(f"     数量: {ai_signal['amount']} BTC")
    
    try:
        # 测试信号处理
        payload = {
            'signal': ai_signal,
            'strategy': 'balanced'
        }
        
        response = requests.post(
            f"{STRATEGY_API_URL}/api/strategy/process-signal",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            decision = data.get('decision', {})
            
            print(f"   ✅ AI信号处理成功")
            print(f"     决策ID: {decision.get('decision_id', '未知')}")
            print(f"     决策方向: {decision.get('direction', '未知')}")
            print(f"     决策原因: {decision.get('reason', '未知')}")
            print(f"     使用策略: {data.get('strategy', '未知')}")
            
            # 检查决策合理性
            if decision.get('direction') == 'hold':
                print(f"     📝 决策: 持仓不动")
            elif decision.get('direction') in ['buy', 'sell']:
                print(f"     🎯 决策: {decision.get('direction').upper()} {decision.get('amount')} {decision.get('symbol')}")
                print(f"     订单类型: {decision.get('order_type', 'market')}")
                print(f"     止损: {decision.get('stop_loss')}%")
                print(f"     止盈: {decision.get('take_profit')}%")
            
            return True
        else:
            print(f"   ❌ 信号处理失败: {response.status_code}")
            print(f"     错误: {response.text[:100]}")
            return False
            
    except Exception as e:
        print(f"   ❌ 信号处理异常: {e}")
        return False

def test_simulation_mode():
    """测试模拟交易模式"""
    print("\n3. 🧪 测试模拟交易模式...")
    print("-" * 40)
    
    # 模拟AI信号
    ai_signal = {
        'symbol': 'ETH_USDT',
        'direction': 'sell',
        'confidence': 65,
        'price': 3500.25,
        'amount': 0.01,
        'reasoning': '阻力位突破失败，短期看跌'
    }
    
    try:
        # 测试模拟交易
        payload = {
            'signal': ai_signal,
            'strategy': 'conservative',
            'simulation_days': 30
        }
        
        response = requests.post(
            f"{STRATEGY_API_URL}/api/strategy/simulate",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            simulation = data.get('simulation', {})
            decision = simulation.get('decision', {})
            
            print(f"   ✅ 模拟交易测试成功")
            print(f"     模拟天数: {simulation.get('days', 0)}天")
            print(f"     策略: {simulation.get('strategy', '未知')}")
            print(f"     决策方向: {decision.get('direction', '未知')}")
            
            if decision.get('simulated_result'):
                result = decision['simulated_result']
                print(f"     模拟结果: {result.get('status', '未知')}")
                print(f"     模拟订单ID: {result.get('order_id', '未知')}")
                print(f"     模拟成交价: ${result.get('executed_price', 0):,.2f}")
                print(f"     模拟手续费: ${result.get('fee', 0):,.4f}")
            
            return True
        else:
            print(f"   ❌ 模拟交易失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ 模拟交易异常: {e}")
        return False

def test_strategy_performance():
    """测试策略性能统计"""
    print("\n4. 📊 测试策略性能统计...")
    print("-" * 40)
    
    try:
        # 测试平衡策略性能
        response = requests.get(
            f"{STRATEGY_API_URL}/api/strategy/performance?strategy=balanced",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            performance = data.get('performance', {})
            
            print(f"   ✅ 策略性能统计获取成功")
            print(f"     总交易次数: {performance.get('total_trades', 0)}")
            print(f"     胜率: {performance.get('win_rate', 0)}%")
            print(f"     总盈亏: ${performance.get('total_pnl', 0):,.2f}")
            print(f"     夏普比率: {performance.get('sharpe_ratio', 0):.2f}")
            print(f"     最大回撤: {performance.get('max_drawdown', 0)}%")
            
            return True
        else:
            print(f"   ❌ 性能统计失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ 性能统计异常: {e}")
        return False

def test_fmz_integration():
    """测试FMZ集成"""
    print("\n5. 🔗 测试FMZ集成...")
    print("-" * 40)
    
    try:
        # 测试FMZ API状态
        response = requests.get(f"{FMZ_API_URL}/api/fmz/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ FMZ集成API状态: {data.get('status', '未知')}")
            print(f"   ✅ 交易启用: {data.get('trading_enabled', '未知')}")
        else:
            print(f"   ❌ FMZ API状态检查失败: {response.status_code}")
            return False
        
        # 测试FMZ余额查询
        response = requests.get(f"{FMZ_API_URL}/api/fmz/balance?exchange=binance", timeout=5)
        if response.status_code == 200:
            data = response.json()
            balance = data.get('balance', {})
            print(f"   ✅ FMZ余额查询成功")
            print(f"     总资产: ${balance.get('total_usd', 0):,.2f}")
        else:
            print(f"   ❌ FMZ余额查询失败: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ FMZ集成测试异常: {e}")
        return False

def test_ai_analysis_system():
    """测试AI分析系统"""
    print("\n6. 🧠 测试AI分析系统...")
    print("-" * 40)
    
    try:
        # 测试AI分析系统状态
        response = requests.get(f"{AI_API_URL}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ AI分析系统状态: {data.get('status', '未知')}")
        else:
            print(f"   ❌ AI分析系统状态检查失败: {response.status_code}")
            return False
        
        # 测试AI分析API
        payload = {'symbol': 'BTC'}
        response = requests.post(
            f"{AI_API_URL}/api/analyze",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            signal = data.get('signal', {})
            ai_analysis = data.get('ai_analysis', {})
            consensus = ai_analysis.get('consensus', {})
            
            print(f"   ✅ AI分析API测试成功")
            print(f"     信号方向: {signal.get('direction', '未知')}")
            print(f"     信号置信度: {signal.get('confidence', '未知')}%")
            print(f"     共识方向: {consensus.get('direction', '未知')}")
            print(f"     共识置信度: {consensus.get('confidence', '未知')}%")
            
            return True
        else:
            print(f"   ❌ AI分析API失败: {response.status_code}")
            print(f"     错误: {response.text[:100]}")
            return False
            
    except Exception as e:
        print(f"   ❌ AI分析系统测试异常: {e}")
        return False

def show_system_architecture():
    """显示系统架构"""
    print("\n7. 🏗️  系统架构概览")
    print("-" * 40)
    
    print("   📊 数据流:")
    print("     1. AI分析系统 → 分析市场数据")
    print("     2. 策略引擎 → 处理AI信号，生成决策")
    print("     3. 策略执行器 → 执行交易决策")
    print("     4. FMZ集成API → 调用FMZ平台")
    print("     5. FMZ平台 → 执行实际交易")
    
    print("\n   🔧 核心组件:")
    print("     • StrategyEngine - 策略引擎（决策生成）")
    print("     • StrategyExecutor - 策略执行器（决策执行）")
    print("     • StrategyManager - 策略管理器（多策略管理）")
    print("     • StrategyAPI - 策略API服务（HTTP接口）")
    
    print("\n   🎯 可用策略:")
    print("     • balanced - 平衡策略（默认）")
    print("     • conservative - 保守策略")
    print("     • aggressive - 激进策略")
    
    print("\n   ⚙️  风险控制:")
    print("     • 仓位管理（最大仓位限制）")
    print("     • 止损止盈（自动平仓）")
    print("     • 交易频率限制（冷却时间）")
    print("     • 每日交易次数限制")

def show_next_steps():
    """显示下一步操作"""
    print("\n8. 🚀 下一步操作")
    print("-" * 40)
    
    print("   1. 🏃 启动策略API服务:")
    print("      cd /home/billyqqq/.openclaw/workspaceopenclaw\\ gateway\\ restart/crypto_analyzer")
    print("      python3 src/strategy/strategy_api.py")
    
    print("\n   2. 🔧 配置FMZ平台:")
    print("      • 登录 https://www.fmz.com")
    print("      • 添加Binance交易所")
    print("      • 使用币安API Key")
    
    print("\n   3. 🐳 启动FMZ托管者:")
    print("      docker run -d --name fmz-worker \\")
    print("        -e ACCESS_KEY=74c1c98076616ccb54015c18c5ae7950 \\")
    print("        -e SECRET_KEY=a4418a9b969650012682b54f5b578933 \\")
    print("        fmzquant/worker:latest")
    
    print("\n   4. 🧪 测试完整流程:")
    print("      • 使用模拟模式测试")
    print("      • 小额真实交易测试")
    print("      • 监控交易表现")
    
    print("\n   5. 📊 优化策略:")
    print("      • 调整策略参数")
    print("      • 优化风险控制")
    print("      • 分析交易数据")

def main():
    """主函数"""
    
    # 运行测试
    tests = [
        ("策略API服务", test_strategy_api),
        ("AI信号处理", test_ai_signal_processing),
        ("模拟交易模式", test_simulation_mode),
        ("策略性能统计", test_strategy_performance),
        ("FMZ集成", test_fmz_integration),
        ("AI分析系统", test_ai_analysis_system)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 运行测试: {test_name}")
        success = test_func()
        results.append((test_name, success))
    
    # 显示结果
    print("\n" + "=" * 60)
    print("📋 测试结果汇总")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name:20} {status}")
    
    print(f"\n📊 总计: {passed_tests}/{total_tests} 项测试通过")
    
    # 显示系统架构
    show_system_architecture()
    
    # 显示下一步操作
    show_next_steps()
    
    print("\n" + "=" * 60)
    if passed_tests == total_tests:
        print("🎉 所有测试通过！策略系统已就绪。")
    elif passed_tests >= total_tests * 0.7:
        print("⚠️  多数测试通过，系统基本可用。")
    else:
        print("❌ 多数测试失败，需要检查配置。")
    
    print("=" * 60)
    
    return passed_tests == total_tests

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)