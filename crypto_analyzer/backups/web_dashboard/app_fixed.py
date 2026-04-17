#!/usr/bin/env python3
"""
增强版虚拟币分析系统 - 5000端口修复版
"""

from flask import Flask, render_template, jsonify, request
from pathlib import Path
import json
import os
import yaml
from datetime import datetime
import random
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CORS装饰器
@app.after_request
def add_cors_headers(response):
    """添加CORS头"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# 配置路径
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
RESULTS_DIR = PROJECT_ROOT / 'results'
CONFIG_DIR = PROJECT_ROOT / 'config'

# 确保目录存在
RESULTS_DIR.mkdir(exist_ok=True)

# ==================== 原始功能兼容 ====================

def load_latest_results():
    """加载最新分析结果"""
    latest_file = RESULTS_DIR / 'latest.json'
    if not latest_file.exists():
        return None
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载最新结果失败: {e}")
        return None

@app.route('/api/latest')
def get_latest():
    """获取最新分析结果"""
    data = load_latest_results()
    if not data:
        return jsonify({'error': 'No analysis results found'}), 404
    return jsonify(data)

@app.route('/api/market_summary')
def get_market_summary():
    """获取市场总结"""
    data = load_latest_results()
    if not data:
        return jsonify({'error': 'No analysis results found'}), 404
    
    symbols = data.get('symbols', [])
    signal_counts = {'STRONG_BUY': 0, 'BUY': 0, 'NEUTRAL': 0, 'SELL': 0, 'STRONG_SELL': 0}
    
    for symbol_data in symbols:
        signal = symbol_data.get('signal', {}).get('signal', 'NEUTRAL')
        if signal in signal_counts:
            signal_counts[signal] += 1
    
    buy_signals = signal_counts['STRONG_BUY'] + signal_counts['BUY']
    sell_signals = signal_counts['STRONG_SELL'] + signal_counts['SELL']
    
    if buy_signals > sell_signals:
        sentiment = 'bullish'
        action = '积极买入'
    elif sell_signals > buy_signals:
        sentiment = 'bearish'
        action = '考虑卖出'
    else:
        sentiment = 'neutral'
        action = '观望为主'
    
    return jsonify({
        'timestamp': data.get('analysis_time'),
        'market_sentiment': sentiment,
        'trading_advice': action,
        'signal_distribution': signal_counts,
        'total_coins': len(symbols)
    })

@app.route('/api/coin/<symbol>')
def get_coin_detail(symbol):
    """获取币种详情"""
    data = load_latest_results()
    if not data:
        return jsonify({'error': 'No analysis results found'}), 404
    
    symbol_data = None
    for s in data.get('symbols', []):
        if s.get('symbol', '').upper() == symbol.upper():
            symbol_data = s
            break
    
    if not symbol_data:
        return jsonify({'error': f'Symbol {symbol} not found'}), 404
    
    return jsonify({
        'symbol': symbol_data.get('symbol'),
        'price_data': symbol_data.get('price_data', {}),
        'signal': symbol_data.get('signal', {}),
        'technical_indicators': symbol_data.get('technical_indicators', {})
    })

@app.route('/api/run_analysis')
def run_analysis():
    """运行新的分析"""
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        
        try:
            from crypto_analyzer_v2 import main as run_analysis_v2
            run_analysis_v2()
        except ImportError:
            from simple_analysis import main as run_simple_analysis
            run_simple_analysis()
        
        return jsonify({
            'status': 'success',
            'message': 'Analysis completed successfully',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/status')
def get_status():
    """获取系统状态"""
    latest_file = RESULTS_DIR / 'latest.json'
    status = {
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'results_count': len(list(RESULTS_DIR.glob('analysis_*.json'))) if RESULTS_DIR.exists() else 0,
        'latest_analysis': None
    }
    
    if latest_file.exists():
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(latest_file))
            status['latest_analysis'] = mtime.isoformat()
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
    
    return jsonify(status)

@app.route('/api/history')
def get_history():
    """获取分析历史"""
    if not RESULTS_DIR.exists():
        return jsonify({'error': 'No history found'}), 404
    
    files = sorted(RESULTS_DIR.glob('analysis_*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
    history = []
    
    for f in files[:20]:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                history.append({
                    'filename': f.name,
                    'analysis_time': data.get('analysis_time'),
                    'symbols': [s.get('symbol') for s in data.get('symbols', [])]
                })
        except Exception as e:
            continue
    
    return jsonify({'history': history})

# ==================== 增强版功能 ====================

def generate_mock_analysis(symbol, timeframe, ai_model):
    """生成模拟分析结果"""
    base_prices = {'BTC': 74856.56, 'ETH': 2347.29, 'SOL': 85.33}
    base_price = base_prices.get(symbol, 10000)
    
    price_change_pct = random.uniform(-3, 3)
    current_price = base_price * (1 + price_change_pct / 100)
    
    technical_score = random.randint(40, 80)
    ai_score = random.randint(50, 90)
    price_score = 80 if price_change_pct > 0 else 40 if price_change_pct < 0 else 60
    
    composite = int(technical_score * 0.4 + ai_score * 0.4 + price_score * 0.2)
    
    if composite >= 80:
        signal = 'STRONG_BUY'
    elif composite >= 60:
        signal = 'BUY'
    elif composite >= 40:
        signal = 'NEUTRAL'
    elif composite >= 20:
        signal = 'SELL'
    else:
        signal = 'STRONG_SELL'
    
    directions = ['bullish', 'bearish', 'neutral']
    direction = random.choices(directions, weights=[0.4, 0.3, 0.3])[0]
    confidence = random.randint(60, 90)
    
    supports = []
    resistances = []
    for i in range(3):
        supports.append({
            'level': round(current_price * (1 - random.uniform(0.01, 0.05)), 2),
            'strength': random.randint(70, 95),
            'type': 'major' if random.random() > 0.7 else 'minor'
        })
        resistances.append({
            'level': round(current_price * (1 + random.uniform(0.01, 0.05)), 2),
            'strength': random.randint(70, 95),
            'type': 'major' if random.random() > 0.7 else 'minor'
        })
    
    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'timestamp': datetime.now().isoformat(),
        'price_data': {
            'current_price': round(current_price, 2),
            'price_change_24h': round(current_price - base_price, 2),
            'price_change_pct_24h': round(price_change_pct, 2),
            'high_24h': round(base_price * 1.03, 2),
            'low_24h': round(base_price * 0.97, 2),
            'volume_24h': random.uniform(1000, 5000)
        },
        'technical_indicators': {
            'core_indicators': {
                'rsi': {'value': random.uniform(30, 70), 'confidence': random.randint(60, 90)},
                'macd': {'value': random.uniform(-10, 10), 'confidence': random.randint(60, 90)},
                'moving_averages': {'signal': random.choice(['bullish', 'bearish', 'neutral']), 'confidence': random.randint(60, 90)},
                'bollinger_bands': {'position': random.uniform(20, 80), 'confidence': random.randint(60, 90)}
            },
            'market_sentiment': {
                'overall': direction,
                'confidence': confidence,
                'fear_greed_index': random.randint(20, 80)
            }
        },
        'support_resistance': {
            'key_supports': sorted(supports, key=lambda x: x['level'], reverse=True),
            'key_resistances': sorted(resistances, key=lambda x: x['level']),
            'current_price': round(current_price, 2)
        },
        'ai_analysis': {
            'consensus': {
                'direction': direction,
                'confidence': confidence,
                'reasoning': f"基于技术分析，{symbol}呈现{direction}趋势。技术指标支持{direction}观点。",
                'agreement_score': random.randint(70, 100)
            }
        },
        'composite_score': {
            'composite': composite,
            'breakdown': {'technical': technical_score, 'ai': ai_score, 'price': price_score}
        },
        'signal': {
            'signal': signal,
            'score': composite,
            'description': get_signal_description(signal)
        }
    }

def get_signal_description(signal):
    """获取信号描述"""
    descriptions = {
        'STRONG_BUY': '强烈买入信号，技术面非常积极',
        'BUY': '买入信号，技术面积极',
        'NEUTRAL': '中性信号，建议观望',
        'SELL': '卖出信号，技术面消极',
        'STRONG_SELL': '强烈卖出信号，技术面非常消极'
    }
    return descriptions.get(signal, '信号不明')

# ==================== 增强版API ====================

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze_symbol_enhanced():
    """分析币种"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json or {}
        symbol = data.get('symbol', 'BTC').upper()
        timeframe = data.get('timeframe', '1h')
        ai_model = data.get('ai_model', 'both')
        
        if symbol not in ['BTC', 'ETH', 'SOL']:
            return jsonify({'error': '不支持的币种'}), 400
        
        if timeframe not in ['1h', '4h', '24h']:
            return jsonify({'error': '不支持的时间框架'}), 400
        
        result = generate_mock_analysis(symbol, timeframe, ai_model)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"分析失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze/batch', methods=['POST', 'OPTIONS'])
def analyze_batch_enhanced():
    """批量分析"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json or {}
        symbols = data.get('symbols', ['BTC', 'ETH', 'SOL'])
        timeframe = data.get('timeframe', '1h')
        ai_model = data.get('ai_model', 'both')
        
        valid_symbols = []
        for symbol in symbols:
            if symbol.upper() in ['BTC', 'ETH', 'SOL']:
                valid_symbols.append(symbol.upper())
        
        if not valid_symbols:
            return jsonify({'error': '没有有效的币种'}), 400
        
        results = []
        for symbol in valid_symbols:
            results.append(generate_mock_analysis(symbol, timeframe, ai_model))
        
        # 计算市场总结
        total_score = 0
        bullish_count = 0
        bearish_count = 0
        
        for result in results:
            score = result.get('composite_score', {}).get('composite', 50)
            total_score += score
            
            direction = result.get('ai_analysis', {}).get('consensus', {}).get('direction', 'neutral')
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
        
        market_summary = {
            'timestamp': datetime.now().isoformat(),
            'total_coins': len(results),
            'market_sentiment': {
                'sentiment': sentiment,
                'average_score': round(avg_score, 1),
                'bullish_coins': bullish_count,
                'bearish_coins': bearish_count
            }
        }
        
        return jsonify({
            'results': results,
            'market_summary': market_summary
        })
        
    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/symbols_enhanced', methods=['GET'])
def get_symbols_enhanced():
    """获取币种列表"""
    return jsonify({
        'symbols': ['BTC', 'ETH', 'SOL'],
        'timeframes': ['1h', '4h', '24h'],
        'ai_models': ['deepseek', 'minimax', 'both']
    })

# ==================== 前端页面 ====================

@app.route('/enhanced')
def enhanced_dashboard():
    """增强版仪表板"""
    return render_template('enhanced_dashboard.html')

@app.route('/')
def index():
    """首页"""
    return render_template('enhanced_dashboard.html')

@app.route('/original')
def original_dashboard():
    """原始仪表板"""
    return render_template('index.html')

# ==================== 启动函数 ====================

if __name__ == '__main__':
    print("="*60)
    print("增强版虚拟币分析系统 - 5000端口")
    print("="*60)
    print(f"项目目录: {PROJECT_ROOT}")
    print(f"访问地址: http://localhost:5000")
    print("="*60)
    print("原始API (保持兼容):")
    print("  GET  /api/latest        - 最新分析")
    print("  GET  /api/market_summary - 市场总结")
    print("  GET  /api/coin/<symbol> - 币种详情")
    print("  GET  /api/run_analysis  - 运行分析")
    print("  GET  /api/status        - 系统状态")
    print("  GET  /api/history       - 分析历史")
    print("="*60)
    print("增强版API:")
    print("  POST /api/analyze       - 分析单个币种")
    print("  POST /api/analyze/batch  - 批量分析")
    print("  GET  /api/symbols_enhanced - 币种列表")
    print("="*60)
    print("前端页面:")
    print("  GET  /                  - 增强版仪表板")
    print("  GET  /enhanced          - 增强版仪表板")
    print("  GET  /original          - 原始仪表板")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)