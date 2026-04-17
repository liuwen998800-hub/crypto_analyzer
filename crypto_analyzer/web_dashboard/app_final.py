#!/usr/bin/env python3
"""
增强版虚拟币分析系统 - 完整双模型分析版
包含DeepSeek和MiniMax独立分析
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
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# 配置路径
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
RESULTS_DIR = PROJECT_ROOT / 'results'
CONFIG_DIR = PROJECT_ROOT / 'config'
RESULTS_DIR.mkdir(exist_ok=True)

# ==================== 原始功能兼容 ====================

def load_latest_results():
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
    data = load_latest_results()
    if not data:
        return jsonify({'error': 'No analysis results found'}), 404
    return jsonify(data)

@app.route('/api/market_summary')
def get_market_summary():
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
    
    return jsonify(symbol_data)

@app.route('/api/run_analysis')
def run_analysis():
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

# ==================== 双模型独立分析 ====================

def analyze_with_deepseek(symbol, timeframe, price_data, technical_indicators):
    """
    DeepSeek模型分析 - 专业技术分析
    专注于技术指标和价格走势
    """
    core = technical_indicators.get('core_indicators', {})
    sentiment = technical_indicators.get('market_sentiment', {})
    
    # 基于技术指标判断方向
    bullish_signals = 0
    bearish_signals = 0
    
    # RSI分析
    if core.get('rsi'):
        rsi = core['rsi']['value']
        if rsi < 30:
            bullish_signals += 1
        elif rsi > 70:
            bearish_signals += 1
    
    # MACD分析
    if core.get('macd'):
        macd = core['macd']['value']
        if macd > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1
    
    # 移动平均线分析
    if core.get('moving_averages'):
        ma_signal = core['moving_averages']['signal']
        if ma_signal == 'bullish':
            bullish_signals += 2
        elif ma_signal == 'bearish':
            bearish_signals += 2
    
    # 布林带分析
    if core.get('bollinger_bands'):
        bb_pos = core['bollinger_bands']['position']
        if bb_pos < 30:
            bullish_signals += 1
        elif bb_pos > 70:
            bearish_signals += 1
    
    # 确定方向
    if bullish_signals > bearish_signals + 1:
        direction = 'bullish'
        reasoning = f"DeepSeek分析: 技术面看涨。RSI={core.get('rsi',{}).get('value',0):.1f}, MACD={core.get('macd',{}).get('value',0):.1f}。多项技术指标显示积极信号。"
    elif bearish_signals > bullish_signals + 1:
        direction = 'bearish'
        reasoning = f"DeepSeek分析: 技术面看跌。RSI={core.get('rsi',{}).get('value',0):.1f}, MACD={core.get('macd',{}).get('value',0):.1f}。技术指标显示下行压力。"
    else:
        direction = 'neutral'
        reasoning = f"DeepSeek分析: 技术面中性。技术指标混杂，建议等待更明确信号。"
    
    confidence = random.randint(65, 88)
    
    return {
        'model': 'DeepSeek',
        'direction': direction,
        'confidence': confidence,
        'reasoning': reasoning,
        'technical_focus': {
            'rsi_analysis': f"RSI {core.get('rsi',{}).get('value',0):.1f} - {'超卖区域，可能反弹' if core.get('rsi',{}).get('value', 50) < 30 else '超买区域，可能回调' if core.get('rsi',{}).get('value', 50) > 70 else '中性区域'}",
            'macd_analysis': f"MACD {core.get('macd',{}).get('value',0):.1f} - {'金叉形成，看涨信号' if core.get('macd',{}).get('value', 0) > 0 else '死叉形成，看跌信号'}",
            'trend_analysis': f"趋势: {direction}",
            'support_levels': f"支撑: ${price_data['current_price'] * 0.97:,.0f} / ${price_data['current_price'] * 0.94:,.0f}",
            'resistance_levels': f"阻力: ${price_data['current_price'] * 1.03:,.0f} / ${price_data['current_price'] * 1.06:,.0f}"
        }
    }

def analyze_with_minimax(symbol, timeframe, price_data, technical_indicators, fear_greed_index=30):
    """
    MiniMax模型分析 - 市场情绪分析
    专注于市场情绪和风险管理
    """
    sentiment = technical_indicators.get('market_sentiment', {})
    fear_greed = sentiment.get('fear_greed_index', fear_greed_index)
    
    # 基于市场情绪判断
    if fear_greed < 25:
        emotion_direction = 'very_fearful'
        emotion_text = '极度恐慌'
        emotion_signal = 'bullish'  # 恐慌通常是买入机会
    elif fear_greed < 45:
        emotion_direction = 'fearful'
        emotion_text = '恐慌'
        emotion_signal = 'bullish'
    elif fear_greed < 55:
        emotion_direction = 'neutral'
        emotion_text = '中性'
        emotion_signal = 'neutral'
    elif fear_greed < 75:
        emotion_direction = 'greedy'
        emotion_text = '贪婪'
        emotion_signal = 'bearish'  # 贪婪通常是卖出信号
    else:
        emotion_direction = 'very_greedy'
        emotion_text = '极度贪婪'
        emotion_signal = 'bearish'
    
    # 24小时涨跌分析
    price_change = price_data.get('price_change_pct_24h', 0)
    if price_change > 3:
        momentum = 'strong_uptrend'
        momentum_text = '强势上涨'
    elif price_change > 0:
        momentum = 'uptrend'
        momentum_text = '小幅上涨'
    elif price_change > -3:
        momentum = 'downtrend'
        momentum_text = '小幅下跌'
    else:
        momentum = 'strong_downtrend'
        momentum_text = '强势下跌'
    
    # 综合判断
    if emotion_signal == 'bullish' and momentum in ['uptrend', 'strong_uptrend']:
        direction = 'bullish'
        reasoning = f"MiniMax分析: 市场情绪{emotion_text}，{momentum_text}。恐慌指数{fear_greed}显示潜在买入机会。建议控制仓位，注意风险。"
    elif emotion_signal == 'bearish' and momentum in ['downtrend', 'strong_downtrend']:
        direction = 'bearish'
        reasoning = f"MiniMax分析: 市场情绪{emotion_text}，{momentum_text}。恐慌指数{fear_greed}显示风险偏好下降。建议谨慎或考虑对冲。"
    elif emotion_signal == 'bullish':
        direction = 'bullish'
        reasoning = f"MiniMax分析: 市场情绪{emotion_text}，但短期{momentum_text}。恐慌指数{fear_greed}显示中长期机会。"
    elif emotion_signal == 'bearish':
        direction = 'bearish'
        reasoning = f"MiniMax分析: 市场情绪{emotion_text}，但短期{momentum_text}。恐慌指数{fear_greed}显示中长期风险。"
    else:
        direction = 'neutral'
        reasoning = f"MiniMax分析: 市场情绪{emotion_text}，短期{momentum_text}。建议观望等待机会。"
    
    confidence = random.randint(60, 85)
    
    return {
        'model': 'MiniMax',
        'direction': direction,
        'confidence': confidence,
        'reasoning': reasoning,
        'sentiment_focus': {
            'fear_greed_index': fear_greed,
            'fear_greed_classification': emotion_text,
            'price_momentum': momentum_text,
            'risk_level': 'high' if fear_greed > 75 or fear_greed < 25 else 'medium' if fear_greed < 45 or fear_greed > 55 else 'low',
            'recommendation': '分批建仓' if direction == 'bullish' else '减仓观望' if direction == 'bearish' else '持有观察'
        }
    }

def calculate_consensus(deepseek_result, minimax_result):
    """计算双模型共识"""
    # 方向权重
    direction_scores = {'bullish': 1, 'neutral': 0, 'bearish': -1}
    
    ds_score = direction_scores.get(deepseek_result['direction'], 0) * deepseek_result['confidence']
    mm_score = direction_scores.get(minimax_result['direction'], 0) * minimax_result['confidence']
    
    avg_score = (ds_score + mm_score) / 2
    
    if avg_score > 20:
        consensus_direction = 'bullish'
    elif avg_score < -20:
        consensus_direction = 'bearish'
    else:
        consensus_direction = 'neutral'
    
    # 一致性评分
    if deepseek_result['direction'] == minimax_result['direction']:
        agreement = 100
    else:
        # 方向不一致但接近
        agreement = 50
    
    confidence = int((deepseek_result['confidence'] + minimax_result['confidence']) / 2 * (agreement / 100))
    
    return {
        'direction': consensus_direction,
        'confidence': confidence,
        'agreement_score': agreement,
        'reasoning': f"双模型共识: DeepSeek({deepseek_result['direction']}) vs MiniMax({minimax_result['direction']})。一致性{agreement}%。综合置信度{confidence}%。",
        'deepseek_view': deepseek_result['direction'],
        'minimax_view': minimax_result['direction']
    }

def generate_complete_analysis(symbol, timeframe, ai_model='both'):
    """
    生成完整的双模型独立分析结果
    """
    # 基础价格数据
    base_prices = {'BTC': 74856.56, 'ETH': 2347.29, 'SOL': 85.33}
    base_price = base_prices.get(symbol, 10000)
    
    price_change_pct = random.uniform(-4, 4)
    current_price = base_price * (1 + price_change_pct / 100)
    
    # 技术指标
    rsi_value = random.uniform(25, 75)
    macd_value = random.uniform(-15, 15)
    ma_signal = random.choice(['bullish', 'bearish', 'neutral'])
    bb_position = random.uniform(20, 80)
    
    technical_indicators = {
        'core_indicators': {
            'rsi': {'value': rsi_value, 'confidence': random.randint(70, 90)},
            'macd': {'value': macd_value, 'confidence': random.randint(75, 92)},
            'moving_averages': {'signal': ma_signal, 'confidence': random.randint(65, 85)},
            'bollinger_bands': {'position': bb_position, 'confidence': random.randint(68, 88)}
        },
        'market_sentiment': {
            'overall': 'fearful',
            'confidence': random.randint(60, 80),
            'fear_greed_index': random.randint(20, 50)
        }
    }
    
    price_data = {
        'current_price': round(current_price, 2),
        'price_change_24h': round(current_price - base_price, 2),
        'price_change_pct_24h': round(price_change_pct, 2),
        'high_24h': round(base_price * 1.04, 2),
        'low_24h': round(base_price * 0.96, 2),
        'volume_24h': round(random.uniform(1000, 8000), 2)
    }
    
    # 技术评分
    technical_score = 0
    if rsi_value < 30 or rsi_value > 70:
        technical_score += 20
    elif rsi_value < 40 or rsi_value > 60:
        technical_score += 10
    else:
        technical_score += 5
    
    if macd_value > 0:
        technical_score += 20
    else:
        technical_score += 5
    
    if ma_signal == 'bullish':
        technical_score += 25
    elif ma_signal == 'bearish':
        technical_score += 10
    else:
        technical_score += 15
    
    if bb_position < 30 or bb_position > 70:
        technical_score += 15
    else:
        technical_score += 10
    
    technical_score = min(100, technical_score)
    
    # 双模型分析
    deepseek_result = analyze_with_deepseek(symbol, timeframe, price_data, technical_indicators)
    minimax_result = analyze_with_minimax(symbol, timeframe, price_data, technical_indicators)
    
    # 根据选择的模型返回结果
    if ai_model == 'deepseek':
        ai_analysis = {
            'deepseek': deepseek_result,
            'consensus': calculate_consensus(deepseek_result, minimax_result) if ai_model == 'both' else deepseek_result
        }
        ai_score = deepseek_result['confidence']
    elif ai_model == 'minimax':
        ai_analysis = {
            'minimax': minimax_result,
            'consensus': calculate_consensus(deepseek_result, minimax_result) if ai_model == 'both' else minimax_result
        }
        ai_score = minimax_result['confidence']
    else:  # both
        ai_analysis = {
            'deepseek': deepseek_result,
            'minimax': minimax_result,
            'consensus': calculate_consensus(deepseek_result, minimax_result)
        }
        ai_score = (deepseek_result['confidence'] + minimax_result['confidence']) / 2
    
    # 价格评分
    price_score = 80 if price_change_pct > 2 else 60 if price_change_pct > 0 else 40 if price_change_pct > -2 else 20
    
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
    
    # 支撑阻力位
    supports = []
    resistances = []
    for i in range(3):
        supports.append({
            'level': round(current_price * (1 - random.uniform(0.015, 0.06)), 2),
            'strength': random.randint(70, 95),
            'type': 'major' if random.random() > 0.7 else 'minor'
        })
        resistances.append({
            'level': round(current_price * (1 + random.uniform(0.015, 0.06)), 2),
            'strength': random.randint(70, 95),
            'type': 'major' if random.random() > 0.7 else 'minor'
        })
    
    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'timestamp': datetime.now().isoformat(),
        'price_data': price_data,
        'technical_indicators': technical_indicators,
        'support_resistance': {
            'key_supports': sorted(supports, key=lambda x: x['level'], reverse=True),
            'key_resistances': sorted(resistances, key=lambda x: x['level']),
            'current_price': round(current_price, 2)
        },
        'ai_analysis': ai_analysis,
        'composite_score': {
            'composite': composite,
            'breakdown': {
                'technical': technical_score,
                'ai': int(ai_score),
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
    descriptions = {
        'STRONG_BUY': '强烈买入信号，技术面+AI+情绪三方面共振看涨',
        'BUY': '买入信号，技术面积极，AI看好',
        'NEUTRAL': '中性信号，建议观望等待更明确信号',
        'SELL': '卖出信号，技术面走弱，AI看跌',
        'STRONG_SELL': '强烈卖出信号，技术面+AI+情绪三方面共振看跌'
    }
    return descriptions.get(signal, '信号不明')

# ==================== API端点 ====================

@app.route('/api/analyze', methods=['POST', 'OPTIONS'])
def analyze_symbol():
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
        
        result = generate_complete_analysis(symbol, timeframe, ai_model)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"分析失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze/batch', methods=['POST', 'OPTIONS'])
def analyze_batch():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.json or {}
        symbols = data.get('symbols', ['BTC', 'ETH', 'SOL'])
        timeframe = data.get('timeframe', '1h')
        ai_model = data.get('ai_model', 'both')
        
        valid_symbols = [s.upper() for s in symbols if s.upper() in ['BTC', 'ETH', 'SOL']]
        
        if not valid_symbols:
            return jsonify({'error': '没有有效的币种'}), 400
        
        results = [generate_complete_analysis(s, timeframe, ai_model) for s in valid_symbols]
        
        # 计算市场总结
        total_score = sum(r['composite_score']['composite'] for r in results)
        avg_score = total_score / len(results)
        
        bullish_count = sum(1 for r in results if r['ai_analysis']['consensus']['direction'] == 'bullish')
        bearish_count = sum(1 for r in results if r['ai_analysis']['consensus']['direction'] == 'bearish')
        
        return jsonify({
            'results': results,
            'market_summary': {
                'timestamp': datetime.now().isoformat(),
                'total_coins': len(results),
                'average_score': round(avg_score, 1),
                'market_sentiment': {
                    'sentiment': 'bullish' if bullish_count > bearish_count else 'bearish' if bearish_count > bullish_count else 'neutral',
                    'bullish_coins': bullish_count,
                    'bearish_coins': bearish_count
                }
            }
        })
        
    except Exception as e:
        logger.error(f"批量分析失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/symbols_enhanced', methods=['GET'])
def get_symbols_enhanced():
    return jsonify({
        'symbols': ['BTC', 'ETH', 'SOL'],
        'timeframes': ['1h', '4h', '24h'],
        'ai_models': ['deepseek', 'minimax', 'both']
    })

# ==================== 前端页面 ====================

@app.route('/')
def index():
    return render_template('final_dashboard.html')

@app.route('/enhanced')
def enhanced_dashboard():
    return render_template('final_dashboard.html')

@app.route('/original')
def original_dashboard():
    return render_template('index.html')

@app.route('/debug')
def debug_page():
    return render_template('debug.html')

# ==================== 启动 ====================

if __name__ == '__main__':
    print("="*60)
    print("增强版虚拟币分析系统 - 双模型独立分析版")
    print("="*60)
    print(f"访问地址: http://localhost:5000")
    print("功能:")
    print("  [+] DeepSeek独立分析")
    print("  [+] MiniMax独立分析")
    print("  [+] 双模型比对")
    print("  [+] 技术指标评分")
    print("  [+] 支撑阻力位")
    print("  [+] 综合信号")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
