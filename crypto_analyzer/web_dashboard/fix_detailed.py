#!/usr/bin/env python3
"""修复detailed_indicators缺少的字段"""

with open('/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer/web_dashboard/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 找到detailed_indicators的bollinger_bands部分
old_bb = """            'bollinger_bands': {
                'upper': bb_upper,
                'middle': bb_middle,
                'lower': bb_lower
            }
        }
    }"""

new_bb = """            'bollinger_bands': {
                'upper': bb_upper,
                'middle': bb_middle,
                'lower': bb_lower,
                'position': bb_position
            },
            'macd_dif': macd_dif,
            'macd_dea': macd_dea,
            'bb_position': bb_position
        }
    }"""

if old_bb in content:
    content = content.replace(old_bb, new_bb)
    print("成功添加缺失字段")
else:
    print("未找到目标代码")
    # 打印实际内容
    import re
    match = re.search(r"'bollinger_bands':\s*\{[^}]+\}", content)
    if match:
        print("找到bollinger_bands:", match.group())

with open('/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer/web_dashboard/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("修复完成")
