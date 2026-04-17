#!/usr/bin/env python3
"""
增强版虚拟币分析系统测试脚本
测试所有API接口和功能
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any

BASE_URL = "http://localhost:5001"

def test_api_status() -> bool:
    """测试API状态"""
    print("🔍 测试API状态...")
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API状态: {data.get('status', 'unknown')}")
            print(f"   时间戳: {data.get('timestamp', 'N/A')}")
            return True
        else:
            print(f"❌ API状态测试失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API状态测试异常: {e}")
        return False

def test_symbols_api() -> bool:
    """测试币种列表API"""
    print("🔍 测试币种列表API...")
    try:
        response = requests.get(f"{BASE_URL}/api/symbols", timeout=10)
        if response.status_code == 200:
            data = response.json()
            symbols = data.get('symbols', [])
            timeframes = data.get('timeframes', [])
            ai_models = data.get('ai_models', [])
            
            print(f"✅ 支持的币种: {', '.join(symbols)}")
            print(f"✅ 时间框架: {', '.join(timeframes)}")
            print(f"✅ AI模型: {', '.join(ai_models)}")
            return True
        else:
            print(f"❌ 币种列表测试失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 币种列表测试异常: {e}")
        return False

def test_single_analysis(symbol: str = "BTC", timeframe: str = "1h", ai_model: str = "both") -> bool:
    """测试单个币种分析"""
    print(f"🔍 测试{symbol}分析 (时间框架: {timeframe}, AI模型: {ai_model})...")
    
    payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "ai_model": ai_model
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/analyze",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # 检查必要字段
            required_fields = ['symbol', 'timeframe', 'timestamp', 'price_data', 
                             'technical_indicators', 'ai_analysis', 'composite_score', 'signal']
            
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                print(f"❌ 缺少必要字段: {missing_fields}")
                return False
            
            # 显示关键信息
            price_data = data.get('price_data', {})
            signal = data.get('signal', {})
            composite_score = data.get('composite_score', {})
            ai_analysis = data.get('ai_analysis', {})
            
            print(f"✅ 分析成功:")
            print(f"   币种: {data.get('symbol')}")
            print(f"   时间框架: {data.get('timeframe')}")
            print(f"   当前价格: ${price_data.get('current_price', 0):,.2f}")
            print(f"   24小时涨跌幅: {price_data.get('price_change_pct_24h', 0):+.2f}%")
            print(f"   综合评分: {composite_score.get('composite', 0)}/100")
            print(f"   交易信号: {signal.get('signal', 'N/A')}")
            
            # AI分析结果
            consensus = ai_analysis.get('consensus', {})
            print(f"   AI共识: {consensus.get('direction', 'N/A')} (置信度: {consensus.get('confidence', 0)}%)")
            
            return True
        else:
            print(f"❌ 分析测试失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 分析测试异常: {e}")
        return False

def test_batch_analysis() -> bool:
    """测试批量分析"""
    print("🔍 测试批量分析...")
    
    payload = {
        "symbols": ["BTC", "ETH", "SOL"],
        "timeframe": "1h",
        "ai_model": "both"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/analyze/batch",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            market_summary = data.get('market_summary', {})
            
            print(f"✅ 批量分析成功:")
            print(f"   分析币种数: {len(results)}")
            print(f"   市场情绪: {market_summary.get('market_sentiment', {}).get('sentiment', 'N/A')}")
            
            # 显示每个币种的结果
            for result in results:
                symbol = result.get('symbol', 'N/A')
                score = result.get('composite_score', {}).get('composite', 0)
                signal = result.get('signal', {}).get('signal', 'N/A')
                print(f"   {symbol}: 评分={score}, 信号={signal}")
            
            return True
        else:
            print(f"❌ 批量分析测试失败: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 批量分析测试异常: {e}")
        return False

def test_history_api() -> bool:
    """测试历史数据API"""
    print("🔍 测试历史数据API...")
    
    symbols = ["BTC", "ETH", "SOL"]
    
    for symbol in symbols:
        try:
            response = requests.get(f"{BASE_URL}/api/history/{symbol}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                history = data.get('history', [])
                print(f"✅ {symbol}历史数据: {len(history)}条记录")
            else:
                print(f"❌ {symbol}历史数据测试失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ {symbol}历史数据测试异常: {e}")
            return False
    
    return True

def test_config_api() -> bool:
    """测试配置API"""
    print("🔍 测试配置API...")
    try:
        response = requests.get(f"{BASE_URL}/api/config", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 配置API测试成功")
            print(f"   配置项数: {len(data)}")
            # 不显示敏感信息
            return True
        else:
            print(f"❌ 配置API测试失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 配置API测试异常: {e}")
        return False

def test_web_interface() -> bool:
    """测试Web界面"""
    print("🔍 测试Web界面...")
    try:
        # 测试首页
        response = requests.get(f"{BASE_URL}/", timeout=10)
        if response.status_code == 200:
            print(f"✅ 首页访问成功")
            
            # 测试增强版仪表板
            response = requests.get(f"{BASE_URL}/enhanced", timeout=10)
            if response.status_code == 200:
                print(f"✅ 增强版仪表板访问成功")
                return True
            else:
                print(f"❌ 增强版仪表板访问失败: HTTP {response.status_code}")
                return False
        else:
            print(f"❌ 首页访问失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Web界面测试异常: {e}")
        return False

def run_comprehensive_test() -> Dict[str, bool]:
    """运行全面测试"""
    print("🧪 开始全面测试增强版虚拟币分析系统")
    print("="*60)
    
    test_results = {}
    
    # 1. 测试API状态
    test_results['api_status'] = test_api_status()
    time.sleep(1)
    
    # 2. 测试币种列表
    test_results['symbols_api'] = test_symbols_api()
    time.sleep(1)
    
    # 3. 测试单个分析
    test_results['single_analysis_btc'] = test_single_analysis("BTC", "1h", "both")
    time.sleep(2)
    
    test_results['single_analysis_eth'] = test_single_analysis("ETH", "4h", "deepseek")
    time.sleep(2)
    
    test_results['single_analysis_sol'] = test_single_analysis("SOL", "24h", "minimax")
    time.sleep(2)
    
    # 4. 测试批量分析
    test_results['batch_analysis'] = test_batch_analysis()
    time.sleep(3)
    
    # 5. 测试历史数据
    test_results['history_api'] = test_history_api()
    time.sleep(1)
    
    # 6. 测试配置API
    test_results['config_api'] = test_config_api()
    time.sleep(1)
    
    # 7. 测试Web界面
    test_results['web_interface'] = test_web_interface()
    
    print("="*60)
    print("📊 测试结果汇总:")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("="*60)
    print(f"总计: {passed}个通过, {failed}个失败")
    
    if failed == 0:
        print("🎉 所有测试通过！系统运行正常。")
        return {"overall": True, "details": test_results}
    else:
        print("⚠️  部分测试失败，请检查系统配置和日志。")
        return {"overall": False, "details": test_results}

def main():
    """主函数"""
    # 检查服务是否运行
    print("🔍 检查服务是否运行...")
    try:
        response = requests.get(f"{BASE_URL}/api/status", timeout=5)
        if response.status_code != 200:
            print("❌ 服务未运行，请先启动服务:")
            print("   cd /home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer/web_dashboard")
            print("   ./start_enhanced.sh")
            sys.exit(1)
    except:
        print("❌ 无法连接到服务，请先启动服务")
        print("   cd /home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer/web_dashboard")
        print("   ./start_enhanced.sh")
        sys.exit(1)
    
    # 运行测试
    results = run_comprehensive_test()
    
    # 生成测试报告
    print("\n📋 测试报告:")
    print("="*60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试URL: {BASE_URL}")
    print(f"总体结果: {'通过' if results['overall'] else '失败'}")
    print("="*60)
    
    if results['overall']:
        print("🎯 建议操作:")
        print("1. 访问 http://localhost:5001/enhanced 使用增强版仪表板")
        print("2. 配置API密钥以启用完整的AI分析功能")
        print("3. 设置定时任务进行自动分析")
    else:
        print("🔧 故障排除:")
        print("1. 检查日志文件: logs/app_enhanced.log")
        print("2. 确认API密钥配置正确")
        print("3. 检查网络连接和端口占用")
        print("4. 重启服务: ./start_enhanced.sh")
    
    return 0 if results['overall'] else 1

if __name__ == "__main__":
    sys.exit(main())