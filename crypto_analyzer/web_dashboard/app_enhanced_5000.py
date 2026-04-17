        logger.error(f"批量分析失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/symbols_enhanced', methods=['GET'])
def get_symbols_enhanced():
    """获取支持的币种列表 - 增强版API"""
    return jsonify({
        'symbols': ['BTC', 'ETH', 'SOL'],
        'timeframes': ['1h', '4h', '24h'],
        'ai_models': ['deepseek', 'minimax', 'both']
    })

def calculate_signal_distribution(results):
    """计算信号分布"""
    distribution = {
        'STRONG_BUY': 0,
        'BUY': 0,
        'NEUTRAL': 0,
        'SELL': 0,
        'STRONG_SELL': 0
    }
    
    for result in results:
        signal = result.get('signal', {}).get('signal', 'NEUTRAL')
        if signal in distribution:
            distribution[signal] += 1
    
    return distribution

def calculate_market_sentiment(results):
    """计算市场情绪"""
    total_score = 0
    bullish_count = 0
    bearish_count = 0
    
    for result in results:
        score = result.get('composite_score', {}).get('composite', 50)
        total_score += score
        
        consensus = result.get('ai_analysis', {}).get('consensus', {})
        direction = consensus.get('direction', 'neutral')
        
        if direction == 'bullish':
            bullish_count += 1
        elif direction == 'bearish':
            bearish_count += 1
    
    avg_score = total_score / len(results) if results else 50
    
    if bullish_count > bearish_count:
        sentiment = 'bullish'
    elif bearish_count > bullish_count:
        sentiment = 'bearish'
    else:
        sentiment = 'neutral'
    
    return {
        'average_score': round(avg_score, 1),
        'bullish_coins': bullish_count,
        'bearish_coins': bearish_count,
        'neutral_coins': len(results) - bullish_count - bearish_count,
        'sentiment': sentiment
    }

# ==================== 前端页面 ====================

@app.route('/enhanced')
def enhanced_dashboard():
    """增强版仪表板"""
    return render_template('enhanced_dashboard.html')

@app.route('/')
def index():
    """首页 - 显示增强版仪表板"""
    return render_template('enhanced_dashboard.html')

@app.route('/original')
def original_dashboard():
    """原始仪表板"""
    return render_template('index.html')

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ==================== 启动函数 ====================

if __name__ == '__main__':
    print("="*60)
    print("增强版虚拟币分析系统 - 5000端口版本")
    print("="*60)
    print(f"项目目录: {PROJECT_ROOT}")
    print(f"访问地址: http://localhost:5000")
    print("="*60)
    print("原始API端点 (保持兼容):")
    print("  GET  /api/latest        - 最新分析结果")
    print("  GET  /api/market_summary - 市场总结")
    print("  GET  /api/coin/<symbol> - 币种详情")
    print("  GET  /api/run_analysis  - 运行分析")
    print("  GET  /api/status        - 系统状态")
    print("  GET  /api/history       - 分析历史")
    print("="*60)
    print("增强版API端点:")
    print("  POST /api/analyze       - 分析单个币种")
    print("  POST /api/analyze/batch  - 批量分析")
    print("  GET  /api/symbols_enhanced - 币种列表")
    print("="*60)
    print("前端页面:")
    print("  GET  /                  - 增强版仪表板")
    print("  GET  /enhanced          - 增强版仪表板")
    print("  GET  /original          - 原始仪表板")
    print("="*60)
    
    # 启动Web服务器
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)