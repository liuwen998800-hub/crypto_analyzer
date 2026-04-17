            distribution[signal] += 1
    
    return distribution

def _calculate_market_sentiment(results):
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

def _find_top_performer(results):
    """找到表现最好的币种"""
    if not results:
        return None
    
    top_result = max(results, key=lambda x: x.get('composite_score', {}).get('composite', 0))
    
    return {
        'symbol': top_result.get('symbol'),
        'score': top_result.get('composite_score', {}).get('composite', 0),
        'signal': top_result.get('signal', {}).get('signal', 'NEUTRAL')
    }

def _find_weakest_performer(results):
    """找到表现最差的币种"""
    if not results:
        return None
    
    weakest_result = min(results, key=lambda x: x.get('composite_score', {}).get('composite', 100))
    
    return {
        'symbol': weakest_result.get('symbol'),
        'score': weakest_result.get('composite_score', {}).get('composite', 0),
        'signal': weakest_result.get('signal', {}).get('signal', 'NEUTRAL')
    }

# ==================== 前端页面 ====================

@app.route('/enhanced')
def enhanced_dashboard():
    """增强版仪表板"""
    return render_template('enhanced_dashboard.html')

@app.route('/')
def index():
    """首页"""
    return render_template('enhanced_dashboard.html')

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ==================== 启动函数 ====================

def run_scheduler():
    """运行定时分析任务"""
    import schedule
    import time
    
    async def scheduled_analysis():
        """定时分析任务"""
        logger.info("执行定时分析任务")
        try:
            symbols = ['BTC', 'ETH', 'SOL']
            for symbol in symbols:
                result = await analyzer.analyze_symbol(symbol, '1h', 'both')
                # 保存结果到数据库或文件
                logger.info(f"定时分析完成: {symbol}")
        except Exception as e:
            logger.error(f"定时分析失败: {e}")
    
    # 每小时执行一次
    schedule.every(1).hours.do(lambda: asyncio.run(scheduled_analysis()))
    
    logger.info("定时任务调度器已启动")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    print("="*60)
    print("增强版虚拟币分析系统 - Web API")
    print("="*60)
    print(f"项目目录: {PROJECT_ROOT}")
    print(f"访问地址: http://localhost:5001")
    print("="*60)
    print("API端点:")
    print("  POST /api/analyze      - 分析单个币种")
    print("  POST /api/analyze/batch - 批量分析")
    print("  GET  /api/symbols      - 获取币种列表")
    print("  GET  /api/status       - 系统状态")
    print("  GET  /api/history/<symbol> - 分析历史")
    print("  GET  /api/config       - 系统配置")
    print("  GET  /enhanced         - 增强版仪表板")
    print("="*60)
    
    # 启动定时任务线程
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # 启动Web服务器
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)