#!/usr/bin/env python3
"""修复detailed_indicators添加rsi12, rsi24"""

with open('/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer/web_dashboard/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到detailed_indicators中的rsi部分
old_rsi = """'rsi6': rsi6_value,
            'rsi14': rsi_value,"""

new_rsi = """'rsi6': rsi6_value,
            'rsi14': rsi_value,
            'rsi12': rsi12_value,
            'rsi24': rsi24_value,"""

if old_rsi in content:
    content = content.replace(old_rsi, new_rsi)
    print("成功添加rsi12, rsi24")
else:
    print("未找到目标代码")

# 同时需要添加rsi12_value和rsi24_value变量
# 找到rsi_value赋值的位置
old_rsi_assign = """    if real_indicators:
        rsi_value = real_indicators['rsi14']
        rsi6_value = real_indicators['rsi6']"""

new_rsi_assign = """    if real_indicators:
        rsi_value = real_indicators['rsi14']
        rsi6_value = real_indicators['rsi6']
        rsi12_value = real_indicators['rsi12']
        rsi24_value = real_indicators['rsi24']"""

if old_rsi_assign in content:
    content = content.replace(old_rsi_assign, new_rsi_assign)
    print("成功添加rsi12_value, rsi24_value变量")
else:
    print("未找到变量赋值位置")

with open('/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer/web_dashboard/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("修复完成")
