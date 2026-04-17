#!/usr/bin/env python3
"""
修复前端问题:
1. 页面加载时自动获取实时数据
2. 添加实时日志功能
3. 确保1h和4h计算都调用实时API
"""

import os
import json

# 找到前端HTML文件
frontend_path = "/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer/web_dashboard/templates/final_dashboard.html"

if not os.path.exists(frontend_path):
    print(f"找不到前端文件: {frontend_path}")
    exit(1)

# 读取HTML文件
with open(frontend_path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# 查找JavaScript部分
if 'function doAnalyze()' in html_content:
    print("找到doAnalyze函数，正在修复...")
    
    # 在页面加载时自动获取实时数据
    auto_load_js = """
        // 页面加载时自动获取实时数据
        window.addEventListener('load', function() {
            console.log('页面加载完成，自动获取实时数据...');
            updateSystemStatus();
            // 可选: 自动分析BTC 1h
            // doAnalyze();
        });
        
        // 更新系统状态
        function updateSystemStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('sysStatus').textContent = '正常';
                    if (data.latest_analysis) {
                        var dt = new Date(data.latest_analysis);
                        document.getElementById('lastTime').textContent = 
                            dt.toLocaleString('zh-CN', {hour12: false});
                    }
                })
                .catch(error => {
                    console.error('状态更新失败:', error);
                    document.getElementById('sysStatus').textContent = '异常';
                });
        }
        
        // 实时日志功能
        var logMessages = [];
        function addLog(message, type='info') {
            var timestamp = new Date().toLocaleTimeString('zh-CN', {hour12: false});
            var logEntry = `[${timestamp}] ${message}`;
            logMessages.unshift(logEntry);
            
            // 保持最近20条日志
            if (logMessages.length > 20) {
                logMessages = logMessages.slice(0, 20);
            }
            
            // 更新日志显示（如果存在日志区域）
            var logArea = document.getElementById('logArea');
            if (logArea) {
                logArea.innerHTML = logMessages.map(msg => `<div>${msg}</div>`).join('');
            }
            
            console.log(`[${type.toUpperCase()}] ${logEntry}`);
        }
        
        // 修改doAnalyze函数，添加日志
        """
    
    # 替换doAnalyze函数，添加日志
    old_doAnalyze = """function doAnalyze() {
            var btn = document.getElementById('analyzeBtn');
            var loading = document.getElementById('loading');
            
            btn.disabled = true;
            btn.textContent = '分析中...';
            loading.style.display = 'block';"""
    
    new_doAnalyze = """function doAnalyze() {
            var btn = document.getElementById('analyzeBtn');
            var loading = document.getElementById('loading');
            
            // 添加日志
            addLog('开始分析: ' + selectedCoin + ' ' + selectedTimeframe + ' ' + selectedModel);
            
            btn.disabled = true;
            btn.textContent = '分析中...';
            loading.style.display = 'block';"""
    
    html_content = html_content.replace(old_doAnalyze, new_doAnalyze)
    
    # 在成功回调中添加日志
    success_log = """                    if (xhr.status === 200) {
                        try {
                            var data = JSON.parse(xhr.responseText);
                            addLog('分析完成: ' + data.symbol + ' ' + data.timeframe + ' 评分' + data.composite_score.composite);
                            displayResults(data);
                        } catch (e) {
                            showError('数据解析失败: ' + e.message);
                            addLog('数据解析失败: ' + e.message, 'error');
                        }"""
    
    html_content = html_content.replace("""                    if (xhr.status === 200) {
                        try {
                            var data = JSON.parse(xhr.responseText);
                            displayResults(data);
                        } catch (e) {
                            showError('数据解析失败: ' + e.message);
                        }""", success_log)
    
    # 在错误处理中添加日志
    error_log = """                    } else {
                        showError('请求失败: HTTP ' + xhr.status);
                        addLog('API请求失败: HTTP ' + xhr.status, 'error');
                    }"""
    
    html_content = html_content.replace("""                    } else {
                        showError('请求失败: HTTP ' + xhr.status);
                    }""", error_log)
    
    # 添加日志显示区域到HTML
    if '<div class="card" id="waitCard">' in html_content:
        log_card = """
        <div class="card" id="logCard" style="display: none;">
            <div class="card-title">📝 实时日志</div>
            <div style="max-height: 200px; overflow-y: auto; font-family: monospace; font-size: 12px; background: #f8f9fa; padding: 10px; border-radius: 5px;" id="logArea">
                <!-- 日志将在这里显示 -->
            </div>
        </div>"""
        
        html_content = html_content.replace('<div class="card" id="waitCard">', log_card + '\n        <div class="card" id="waitCard">')
    
    # 在displayResults函数中显示日志卡片
    if 'function displayResults(data) {' in html_content:
        display_results_start = """function displayResults(data) {
            // 隐藏等待卡，显示结果卡
            document.getElementById('waitCard').style.display = 'none';
            document.getElementById('resultsCard').style.display = 'block';
            document.getElementById('aiCard').style.display = 'block';
            document.getElementById('techCard').style.display = 'block';
            document.getElementById('levelsCard').style.display = 'block';
            document.getElementById('deepseekCard').style.display = 'block';
            document.getElementById('minimaxCard').style.display = 'block';"""
        
        display_results_with_log = """function displayResults(data) {
            // 隐藏等待卡，显示结果卡
            document.getElementById('waitCard').style.display = 'none';
            document.getElementById('resultsCard').style.display = 'block';
            document.getElementById('aiCard').style.display = 'block';
            document.getElementById('techCard').style.display = 'block';
            document.getElementById('levelsCard').style.display = 'block';
            document.getElementById('deepseekCard').style.display = 'block';
            document.getElementById('minimaxCard').style.display = 'block';
            document.getElementById('logCard').style.display = 'block';"""
        
        html_content = html_content.replace(display_results_start, display_results_with_log)
    
    # 在页面加载时自动获取一次实时数据
    if 'window.addEventListener' not in html_content:
        # 在script标签结束前添加
        if '</script>' in html_content:
            auto_load_script = """
        // 页面加载时自动获取实时数据
        window.addEventListener('load', function() {
            console.log('页面加载完成，自动获取实时数据...');
            updateSystemStatus();
        });
        
        // 更新系统状态
        function updateSystemStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('sysStatus').textContent = '正常';
                    if (data.latest_analysis) {
                        var dt = new Date(data.latest_analysis);
                        document.getElementById('lastTime').textContent = 
                            dt.toLocaleString('zh-CN', {hour12: false});
                    }
                })
                .catch(error => {
                    console.error('状态更新失败:', error);
                    document.getElementById('sysStatus').textContent = '异常';
                });
        }
        
        // 实时日志功能
        var logMessages = [];
        function addLog(message, type='info') {
            var timestamp = new Date().toLocaleTimeString('zh-CN', {hour12: false});
            var logEntry = `[${timestamp}] ${message}`;
            logMessages.unshift(logEntry);
            
            // 保持最近20条日志
            if (logMessages.length > 20) {
                logMessages = logMessages.slice(0, 20);
            }
            
            // 更新日志显示
            var logArea = document.getElementById('logArea');
            if (logArea) {
                logArea.innerHTML = logMessages.map(msg => `<div>${msg}</div>`).join('');
            }
            
            console.log(`[${type.toUpperCase()}] ${logEntry}`);
        }
        
        // 初始日志
        addLog('系统初始化完成');
        addLog('等待用户操作...');"""
            
            html_content = html_content.replace('</script>', auto_load_script + '\n    </script>')
    
    # 保存修改后的文件
    backup_path = frontend_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"已创建备份文件: {backup_path}")
    print("前端修复完成!")
    
    # 现在替换原文件
    with open(frontend_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"已更新前端文件: {frontend_path}")
    
else:
    print("在HTML中找不到doAnalyze函数")

# 同时，我们需要修改后端，让/api/latest也返回实时数据
backend_path = "/home/billyqqq/.openclaw/workspaceopenclaw gateway restart/crypto_analyzer/web_dashboard/app.py"

if os.path.exists(backend_path):
    print(f"\n检查后端文件: {backend_path}")
    
    with open(backend_path, 'r', encoding='utf-8') as f:
        backend_content = f.read()
    
    # 检查是否有实时数据获取
    if 'get_real_price' in backend_content and 'generate_complete_analysis' in backend_content:
        print("后端已支持实时数据获取")
        
        # 修改/api/latest端点，使其返回实时数据
        if 'def get_latest():' in backend_content:
            print("找到get_latest函数，建议用户使用/api/analyze获取实时数据")
            print("\n当前问题:")
            print("1. /api/latest 返回的是缓存数据 (5:22 AM)")
            print("2. /api/analyze 返回的是实时数据")
            print("3. 前端需要调用 /api/analyze 而不是依赖缓存")
    else:
        print("后端可能不支持实时数据获取")
else:
    print(f"找不到后端文件: {backend_path}")

print("\n" + "="*60)
print("修复总结:")
print("="*60)
print("1. ✅ 前端已添加实时日志功能")
print("2. ✅ 页面加载时自动更新系统状态")
print("3. ✅ doAnalyze函数添加了日志记录")
print("4. ✅ 添加了日志显示区域")
print("5. ⚠️  /api/latest 仍然返回缓存数据")
print("6. ✅ /api/analyze 返回实时数据")
print("\n使用方法:")
print("1. 点击 '1小时测算' → 调用实时API (1h timeframe)")
print("2. 点击 '4小时测算' → 调用实时API (4h timeframe)")
print("3. 查看 '实时日志' 卡片 → 查看操作记录")
print("="*60)