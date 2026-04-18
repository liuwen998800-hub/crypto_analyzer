#!/usr/bin/env python3
"""
系统状态检查脚本
"""

import requests
import json
from datetime import datetime

def check_service(name, url, method='GET', timeout=5):
    """检查服务状态"""
    try:
        if method == 'GET':
            response = requests.get(url, timeout=timeout)
        else:
            response = requests.post(url, timeout=timeout)
        
        if response.status_code == 200:
            try:
                data = response.json()
                return True, data
            except:
                return True, {'raw': response.text[:100]}
        else:
            return False, {'status_code': response.status_code, 'error': response.text[:100]}
    except Exception as e:
        return False, {'error': str(e)}

def main():
    print("🔍 系统状态检查")
    print("=" * 60)
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    services = [
        ("AI分析系统", "http://localhost:5000/api/status", "GET"),
        ("AI分析API", "http://localhost:5000/api/analyze", "POST"),
        ("FMZ集成API状态", "http://localhost:5001/api/fmz/status", "GET"),
        ("FMZ余额查询", "http://localhost:5001/api/fmz/balance?exchange=binance", "GET"),
    ]
    
    results = []
    
    for name, url, method in services:
        print(f"检查 {name}...")
        success, data = check_service(name, url, method)
        
        if success:
            print(f"  ✅ {name} 正常")
            if name == "AI分析系统":
                print(f"     状态: {data.get('status', '未知')}")
            elif name == "AI分析API":
                signal = data.get('signal', {})
                print(f"     信号: {signal.get('direction', '未知')}")
                print(f"     置信度: {signal.get('confidence', '未知')}%")
            elif name == "FMZ集成API状态":
                print(f"     状态: {data.get('status', '未知')}")
                print(f"     交易启用: {data.get('trading_enabled', '未知')}")
            elif name == "FMZ余额查询":
                balance = data.get('balance', {})
                print(f"     总资产: ${balance.get('total_usd', 0):,.2f}")
        else:
            print(f"  ❌ {name} 异常")
            print(f"     错误: {data.get('error', '未知')}")
        
        results.append((name, success))
        print()
    
    # 显示总结
    print("📊 检查结果汇总")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    for name, success in results:
        status = "✅ 正常" if success else "❌ 异常"
        print(f"{name:20} {status}")
    
    print(f"\n总计: {passed}/{total} 项服务正常")
    
    if passed == total:
        print("\n🎉 所有系统服务运行正常！")
        print("\n🚀 下一步:")
        print("1. 配置FMZ平台交易所")
        print("2. 启动FMZ托管者")
        print("3. 创建并运行AI交易策略")
    elif passed >= total * 0.7:
        print("\n⚠️  多数服务正常，部分服务需要检查")
    else:
        print("\n❌ 多数服务异常，需要紧急修复")
    
    return passed == total

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)