# 🔧 FMZ平台语法错误解决方案

## 🚨 问题分析

FMZ平台报告了 `SyntaxError: Unexpected token` 错误。这通常是由于以下原因：

### 常见原因：
1. **ES6+语法不支持** - FMZ使用较旧的JavaScript引擎
2. **特殊字符问题** - 表情符号、Unicode字符
3. **模板字符串** - 使用反引号 `` ` `` 而不是单引号 `'`
4. **箭头函数** - `=>` 语法可能不被支持
5. **let/const声明** - 应该使用 `var`

## 🛠️ 已创建的解决方案

### 1. **最小测试版本** (`fmz_minimal_test.js`)
- 最简单的策略代码
- 仅包含基本功能
- 用于验证FMZ平台基础语法

### 2. **严格兼容版本** (`fmz_strict_compatible.js`)
- 使用ES5语法
- 移除所有ES6+特性
- 确保最大兼容性

### 3. **兼容版本** (`fmz_compatible_strategy.js`)
- 完整功能
- ES5语法
- 详细的错误处理

## 📋 部署步骤

### 步骤1: 使用严格兼容版本
```bash
# 查看代码
cat /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/fmz_strict_compatible.js
```

### 步骤2: 复制到FMZ平台
1. 登录 https://www.fmz.com
2. 进入"策略库" → "新建策略"
3. 选择"JavaScript"语言
4. 粘贴代码

### 步骤3: 修改关键配置
```javascript
// 修改这一行，将localhost改为你的服务器IP
aiApiUrl: "http://YOUR_SERVER_IP:5000/api/analyze",
```

### 步骤4: 保存并测试
1. 点击"保存"按钮
2. 点击"回测"进行测试
3. 如果没有语法错误，继续下一步

## 🔍 如果仍有语法错误

### 方法1: 使用最小测试版本
先部署最小测试版本，确保基础语法正确：
```bash
cat /home/billyqqq/.openclaw/workspaceopenclaw\ gateway\ restart/crypto_analyzer/fmz_minimal_test.js
```

### 方法2: 分步调试
1. **先注释掉所有代码**，只保留 `function main() { Log("test"); }`
2. **逐步添加功能**，每次添加一点代码
3. **找到具体引起错误的行**

### 方法3: 检查常见问题
```javascript
// ❌ 错误 - 模板字符串（FMZ可能不支持）
Log(`价格: ${price}`);

// ✅ 正确 - 字符串拼接
Log("价格: " + price);

// ❌ 错误 - 箭头函数
var func = () => {};

// ✅ 正确 - 普通函数
var func = function() {};

// ❌ 错误 - let/const
let x = 1;
const y = 2;

// ✅ 正确 - var
var x = 1;
var y = 2;

// ❌ 错误 - 表情符号
Log("🚀 启动");

// ✅ 正确 - 纯文本
Log("启动");
```

## 📝 FMZ平台JavaScript限制

根据FMZ官方文档，平台JavaScript环境有以下限制：

### 支持的语法：
- ES5标准语法
- 基本控制结构 (if/else, for, while)
- 函数声明和表达式
- 对象和数组字面量
- 基本的字符串操作

### 不支持的语法：
- ES6+特性 (箭头函数、类、模块)
- 模板字符串
- let/const (使用var)
- 解构赋值
- 扩展运算符
- Promise/async/await

### FMZ特有API：
```javascript
// 交易所操作
exchange.GetTicker()      // 获取行情
exchange.GetAccount()     // 获取账户
exchange.Buy(price, amount)  // 买入
exchange.Sell(price, amount) // 卖出

// 日志和工具
Log(message)              // 输出日志
Sleep(ms)                 // 等待
HttpQuery(url, method, data, headers) // HTTP请求
```

## 🎯 推荐的部署流程

### 阶段1: 验证基础语法
1. 部署 `fmz_minimal_test.js`
2. 确保能正常保存和回测
3. 验证基础API调用

### 阶段2: 添加AI集成
1. 部署 `fmz_strict_compatible.js`
2. 修改AI_API_URL为你的服务器地址
3. 测试AI信号获取

### 阶段3: 完整功能
1. 部署 `fmz_compatible_strategy.js`
2. 配置所有交易参数
3. 进行完整回测

## ⚠️ 重要注意事项

### 1. 网络连接
- 确保FMZ托管者能访问你的AI分析服务器
- 如果是本地服务器，需要配置端口转发
- 建议使用公网IP或域名

### 2. API响应格式
AI分析API必须返回以下格式：
```json
{
  "signal": {
    "direction": "buy|sell|hold",
    "confidence": 75
  },
  "current_price": 75234.50
}
```

### 3. 错误处理
- FMZ策略必须有完善的错误处理
- 使用try-catch包装所有操作
- 记录详细的错误日志

### 4. 资金安全
- 先使用模拟账户测试
- 小额资金开始
- 监控交易日志

## 🔄 故障排除

### 问题1: 仍然有语法错误
```bash
# 创建最简单的测试
echo 'function main() { Log("test"); }' > test.js
# 在FMZ平台测试这个最简单的代码
```

### 问题2: AI API连接失败
```bash
# 测试AI API是否可访问
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC"}'
```

### 问题3: 交易所API错误
- 检查API Key和Secret是否正确
- 检查API权限设置
- 检查IP白名单

### 问题4: 策略不执行交易
- 检查AI信号置信度阈值
- 检查账户余额
- 检查持仓限制

## 📞 获取帮助

如果问题仍然存在：

1. **查看FMZ官方文档**: https://www.fmz.com/bbs
2. **检查FMZ错误日志**: 在策略运行页面查看详细错误
3. **简化代码**: 回到最小测试版本，逐步添加功能
4. **联系支持**: 提供具体的错误信息和代码片段

## 🎉 成功标志

1. ✅ 策略代码能成功保存
2. ✅ 回测能正常运行
3. ✅ AI信号能正确获取
4. ✅ 交易能正常执行
5. ✅ 日志输出正常

---

**现在尝试使用 `fmz_strict_compatible.js` 版本，这应该能解决语法错误问题！**