#!/usr/bin/env python3
"""
FMZ集成测试脚本
测试AI分析系统与FMZ平台的集成
"""

import sys
import os
import time
import json
import requests
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_ai_api():
    """测试AI分析API"""
    print("1. 测试AI分析API...")
    try:
        response = requests.post(
            "http://localhost:5000/api/analyze",
            json={"symbol": "BTC", "timeframe": "1h", "ai_model": "both"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ AI分析API正常")
            print(f"     信号: {data.get('signal', {}).get('signal')}")
            print(f"     置信度: {data.get('signal', {}).get('score')}%")
            print(f"     时间戳: {data.get('timestamp')}")
            return True
        else:
            print(f"   ✗ AI分析API错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ AI分析API异常: {e}")
        return False

def test_fmz_api():
    """测试FMZ API"""
    print("2. 测试FMZ API...")
    try:
        response = requests.get(
            "http://localhost:5001/api/fmz/status",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ FMZ API正常")
            print(f"     状态: {data.get('status')}")
            print(f"     交易启用: {data.get('trading_enabled')}")
            return True
        else:
            print(f"   ✗ FMZ API错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ FMZ API异常: {e}")
        return False

def test_fmz_balance():
    """测试FMZ余额查询"""
    print("3. 测试FMZ余额查询...")
    try:
        response = requests.get(
            "http://localhost:5001/api/fmz/balance?exchange=binance",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 余额查询正常")
            print(f"     交易所: {data.get('exchange')}")
            print(f"     时间戳: {data.get('timestamp')}")
            return True
        else:
            print(f"   ✗ 余额查询错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ 余额查询异常: {e}")
        return False

def test_signal_execution():
    """测试信号执行（模拟）"""
    print("4. 测试信号执行...")
    try:
        # 创建测试信号
        test_signal = {
            "symbol": "BTC_USDT",
            "direction": "buy",
            "confidence": 75,
            "price": 75000,
            "amount": 0.001,
            "reasoning": "测试信号 - AI分析显示看涨"
        }
        
        response = requests.post(
            "http://localhost:5001/api/fmz/execute-signal",
            json=test_signal,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ 信号执行API正常")
            print(f"     状态: {data.get('status')}")
            print(f"     原因: {data.get('reason', 'N/A')}")
            return True
        elif response.status_code == 403:
            # 交易被禁用是正常情况
            data = response.json()
            print(f"   ⚠ 交易功能已禁用（正常）")
            print(f"     状态: {data.get('status')}")
            print(f"     消息: {data.get('message')}")
            return True
        else:
            print(f"   ✗ 信号执行错误: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ✗ 信号执行异常: {e}")
        return False

def test_integration_module():
    """测试集成模块"""
    print("5. 测试集成模块...")
    try:
        from src.fmz.ai_fmz_integration import AIFMZIntegrator
        
        integrator = AIFMZIntegrator(
            ai_api_url="http://localhost:5000",
            fmz_api_url="http://localhost:5001",
            min_confidence=60
        )
        
        # 测试API状态检查
        ai_ok = integrator.check_ai_api_status()
        fmz_ok = integrator.check_fmz_api_status()
        
        print(f"   ✓ 集成模块初始化成功")
        print(f"     AI API状态: {'正常' if ai_ok else '异常'}")
        print(f"     FMZ API状态: {'正常' if fmz_ok else '异常'}")
        
        if ai_ok and fmz_ok:
            # 测试获取AI分析
            ai_analysis = integrator.get_ai_analysis("BTC", "1h")
            if ai_analysis:
                print(f"   ✓ 获取AI分析成功")
                
                # 测试信号转换
                signal = integrator.convert_ai_to_signal(ai_analysis)
                if signal:
                    print(f"   ✓ 信号转换成功")
                    print(f"     方向: {signal.direction.value}")
                    print(f"     置信度: {signal.confidence}%")
                    print(f"     强度: {signal.get_strength().value}")
                    
                    # 测试是否可执行
                    actionable = signal.is_actionable(60)
                    print(f"     可执行: {'是' if actionable else '否'}")
                    
                    return True
                else:
                    print(f"   ✗ 信号转换失败")
                    return False
            else:
                print(f"   ✗ 获取AI分析失败")
                return False
        else:
            print(f"   ✗ API状态异常")
            return False
            
    except Exception as e:
        print(f"   ✗ 集成模块异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_auto_trading_bot():
    """测试自动交易机器人（不实际启动）"""
    print("6. 测试自动交易机器人...")
    try:
        from src.fmz.ai_fmz_integration import AIFMZIntegrator, AutoTradingBot
        
        integrator = AIFMZIntegrator(
            ai_api_url="http://localhost:5000",
            fmz_api_url="http://localhost:5001",
            min_confidence=60
        )
        
        # 创建但不启动机器人
        bot = AutoTradingBot(
            integrator=integrator,
            interval=300,
            symbols=["BTC", "ETH"],
            timeframe="1h"
        )
        
        print(f"   ✓ 自动交易机器人创建成功")
        print(f"     监控币种: {bot.symbols}")
        print(f"     时间框架: {bot.timeframe}")
        print(f"     检查间隔: {bot.interval}秒")
        
        # 测试机器人属性
        assert bot.integrator == integrator
        assert bot.interval == 300
        assert bot.symbols == ["BTC", "ETH"]
        assert bot.timeframe == "1h"
        
        print(f"   ✓ 机器人属性验证通过")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 自动交易机器人测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("=" * 60)
    print("FMZ集成系统测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().isoformat()}")
    print()
    
    tests = [
        ("AI分析API", test_ai_api),
        ("FMZ API", test_fmz_api),
        ("余额查询", test_fmz_balance),
        ("信号执行", test_signal_execution),
        ("集成模块", test_integration_module),
        ("自动交易机器人", test_auto_trading_bot),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            success = test_func()
            results.append((test_name, success))
            time.sleep(1)  # 避免请求过快
        except KeyboardInterrupt:
            print("测试被用户中断")
            break
        except Exception as e:
            print(f"测试异常: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{test_name:20} {status}")
        
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {len(results)} 项测试")
    print(f"通过: {passed} 项")
    print(f"失败: {failed} 项")
    
    if failed == 0:
        print("\n🎉 所有测试通过！")
        print("FMZ集成系统可以正常使用。")
    else:
        print(f"\n⚠  {failed} 项测试失败")
        print("请检查相关服务是否正常运行。")
    
    # 提供下一步建议
    print("\n" + "=" * 60)
    print("下一步建议:")
    print("=" * 60)
    
    if passed >= 4:  # 大部分测试通过
        print("1. 编辑 config/fmz_config.yaml，填写你的FMZ API Key")
        print("2. 运行 ./start_fmz_integration.sh 启动完整系统")
        print("3. 访问 http://localhost:5000 使用AI分析系统")
        print("4. 访问 http://localhost:5001/api/fmz/status 检查FMZ连接")
        print("5. 使用小额资金进行实盘测试")
    else:
        print("1. 确保AI分析系统正在运行: python3 web_dashboard/app.py")
        print("2. 确保FMZ API服务正在运行: python3 src/fmz/fmz_api.py")
        print("3. 检查网络连接和防火墙设置")
        print("4. 查看日志文件获取详细错误信息")
        print("5. 重新运行测试脚本")
    
    return failed == 0

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)