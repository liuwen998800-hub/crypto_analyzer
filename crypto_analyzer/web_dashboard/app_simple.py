#!/usr/bin/env python3
"""
简化版虚拟币分析系统 - Web API
不需要flask-cors依赖
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

# ==================== API路由 ====================

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze_symbol():
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
        
        # 生成模拟数据
        result = generate_mock_analysis(symbol, timeframe, ai_model)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"分析失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze/batch', methods=['POST', 'OPTIONS'])
def analyze_batch():
    """批量分析币种"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json or {}
        symbols = data.get('symbols', ['BTC', 'ETH', 'SOL'])
        timeframe = data.get('timeframe', '1h')
        ai_model = data.get('ai_model', 'both')
        
        # 验证币种
        valid_symbols = []
        for symbol in symbols:
            if symbol.upper() in ['BTC', 'ETH', 'SOL']:
                valid_symbols.append(symbol.upper())
        
        if not valid_symbols:
            return jsonify({'error': '没有有效的币种'}), 400
        
        # 生成结果
        results = []
        for symbol in valid_symbols:
            results.append(generate_mock_analysis(symbol, timeframe, ai_model))
        
        # 市场总结
        market_summary = {
            'timestamp': datetime.now().isoformat(),
            'total_coins': len(results),
            'signal_distribution': calculate_signal_distribution(results),
            'market_sentiment': calculate_market_sentiment(results)
        }
        
        return jsonify({
            'results': results,
            'market_summary': market_summary
        })
        
    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/symbols', methods=['GET'])
def get_symbols():
    """获取支持的币种列表"""
    return jsonify({
        'symbols': ['BTC', 'ETH', 'SOL'],
        'timeframes': ['1h', '4h', '24h'],
        'ai_models': ['deepseek', 'minimax', 'both']
    })

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'services': {
            'data_fetcher': 'simulated',
            'ai_analysis': 'simulated',
            'technical_analysis': 'simulated'
        }
    })

@app.route('/api/history/<symbol>', methods=['GET'])
def get_history(symbol):
    """获取币种分析历史"""
    if symbol.upper() not in ['BTC', 'ETH', 'SOL']:
        return jsonify({'error': '不支持的币种'}), 400
    
    # 生成模拟历史数据
    history = []
    for i in range(10):
        timestamp = datetime.now().isoformat()
        score = random.randint(30, 80)
        direction = random.choice(['bullish', 'bearish', 'neutral'])
        
        history.append({
            'timestamp': timestamp,
            'score': score,
            'direction': direction,
            'signal': 'BUY' if score >= 60 else 'SELL' if score <= 40 else 'NEUTRAL'
        })
    
    return jsonify({
        'symbol': symbol,
        'history': history
    })

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取系统配置"""
    config = {
        'version': '1.0.0',
        'symbols': ['BTC', 'ETH', 'SOL'],
        'timeframes': ['1h', '4h', '24h'],
        'ai_models': ['simulated'],
        'scoring_weights': {
            'technical': 0.4,
            'ai': 0.4,
            'price': 0.2
        }
    }
    return jsonify(config)

@app.route('/enhanced', methods=['GET'])
def enhanced_dashboard():
    """增强版仪表板"""
    return render_template('enhanced_dashboard.html')

@app.route('/', methods=['GET'])
def index():
    """首页"""
    return render_template('enhanced_dashboard.html')

# ==================== 辅助函数 ====================

def generate_mock_analysis(symbol, timeframe, ai_model):
    """生成模拟分析结果"""
    
    # 基础价格
    base_prices = {
        'BTC': 74856.56,
        'ETH': 2347.29,
        'SOL': 85.33
    }
    
    base_price = base_prices.get(symbol, 10000)
    
    # 模拟价格波动
    price_change_pct = random.uniform(-3, 3)
    current_price = base_price * (1 + price_change_pct / 100)
    
    # 技术指标评分
    technical_score = random.randint(40, 80)
    ai_score = random.randint(50, 90)
    price_score = 80 if price_change_pct > 0 else 40 if price_change_pct < 0 else 60
    
    # 综合评分
    composite = int(technical_score * 0.4 + ai_score * 0.4 + price_score * 0.2)
    
    # 信号
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
    
    # AI分析结果
    directions = ['bullish', 'bearish', 'neutral']
    weights = [0.4, 0.3, 0.3]
    direction = random.choices(directions, weights=weights)[0]
    confidence = random.randint(60, 90)
    
    # 支撑阻力位
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
            'breakdown': {
                'technical': technical_score,
                'ai': ai_score,
                'price': price_score
            }
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

# ==================== 启动函数 ====================

if __name__ == '__main__':
    print("="*60)
    print("简化版虚拟币分析系统 - Web API")
    print("="*60)
    print(f"项目目录: {PROJECT_ROOT}")
    print(f"访问地址: http://localhost:5002")
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
    
    # 启动Web服务器
    app.run(host='0.0.0.0', port=5003, debug=False, threaded=True)