#!/usr/bin/env python3
"""修复MACD和RSI计算"""

with open('/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer/web_dashboard/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复RSI计算 - 使用Wilder's RSI
old_rsi = '''def calculate_rsi(prices, period=14):
    """计算RSI"""
    deltas = []
    for i in range(1, len(prices)):
        deltas.append(prices[i] - prices[i-1])
    
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 50.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi'''

new_rsi = '''def calculate_rsi(prices, period=14):
    """计算RSI - 使用Wilder's平滑方法"""
    deltas = []
    for i in range(1, len(prices)):
        deltas.append(prices[i] - prices[i-1])
    
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    # 使用Wilder's平滑
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 50.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi'''

if old_rsi in content:
    content = content.replace(old_rsi, new_rsi)
    print("成功修复RSI计算")
else:
    print("未找到RSI代码")

# 修复MACD返回值 - 使用(DIF-DEA)而非2*(DIF-DEA)
old_macd_return = '''        'macd': macd['macd']'''

new_macd_return = '''        'macd': macd['dif'] - macd['dea']  # MACD柱状图'''

if old_macd_return in content:
    content = content.replace(old_macd_return, new_macd_return)
    print("成功修复MACD返回值")
else:
    print("未找到MACD代码")

with open('/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer/web_dashboard/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("修复完成")
