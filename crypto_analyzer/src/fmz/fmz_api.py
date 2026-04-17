#!/usr/bin/env python3
"""
FMZ API服务
提供HTTP API接口，用于AI信号与FMZ平台的对接
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import threading
import time
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.fmz.fmz_client import FMZClient, FMZConfig

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局FMZ客户端
fmz_client = None
signal_cache = {}  # 信号缓存
trading_enabled = False  # 交易开关


def init_fmz_client():
    """初始化FMZ客户端"""
    global fmz_client
    try:
        fmz_client = FMZConfig.create_client_from_config()
        logger.info("FMZ客户端初始化成功")
        return True
    except Exception as e:
        logger.error(f"FMZ客户端初始化失败: {e}")
        return False


@app.route('/api/fmz/status', methods=['GET'])
def get_fmz_status():
    """获取FMZ状态"""
    if fmz_client is None:
        return jsonify({
            'status': 'error',
            'message': 'FMZ客户端未初始化',
            'timestamp': datetime.now().isoformat()
        }), 500
    
    try:
        # 测试API连接
        account_info = fmz_client.get_account_info()
        
        return jsonify({
            'status': 'connected',
            'account_info': account_info,
            'trading_enabled': trading_enabled,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'disconnected',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/fmz/balance', methods=['GET'])
def get_balance():
    """获取账户余额"""
    if fmz_client is None:
        return jsonify({'error': 'FMZ客户端未初始化'}), 500
    
    exchange = request.args.get('exchange', 'binance')
    
    try:
        balance = fmz_client.get_balance(exchange)
        return jsonify({
            'exchange': exchange,
            'balance': balance,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fmz/positions', methods=['GET'])
def get_positions():
    """获取持仓信息"""
    if fmz_client is None:
        return jsonify({'error': 'FMZ客户端未初始化'}), 500
    
    exchange = request.args.get('exchange', 'binance')
    
    try:
        positions = fmz_client.get_positions(exchange)
        return jsonify({
            'exchange': exchange,
            'positions': positions,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fmz/strategies', methods=['GET'])
def get_strategies():
    """获取策略列表"""
    if fmz_client is None:
        return jsonify({'error': 'FMZ客户端未初始化'}), 500
    
    try:
        strategies = fmz_client.get_strategies()
        return jsonify({
            'strategies': strategies,
            'count': len(strategies),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fmz/running-strategies', methods=['GET'])
def get_running_strategies():
    """获取运行中的策略"""
    if fmz_client is None:
        return jsonify({'error': 'FMZ客户端未初始化'}), 500
    
    try:
        strategies = fmz_client.get_running_strategies()
        return jsonify({
            'running_strategies': strategies,
            'count': len(strategies),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fmz/create-ai-strategy', methods=['POST'])
def create_ai_strategy():
    """创建AI量化策略"""
    if fmz_client is None:
        return jsonify({'error': 'FMZ客户端未初始化'}), 500
    
    try:
        data = request.json or {}
        strategy_name = data.get('name', 'AI量化策略')
        
        result = fmz_client.create_ai_strategy(strategy_name)
        
        return jsonify({
            'status': 'success',
            'strategy_id': result.get('id'),
            'strategy_name': strategy_name,
            'message': 'AI策略创建成功',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fmz/execute-signal', methods=['POST'])
def execute_signal():
    """执行AI分析信号"""
    if fmz_client is None:
        return jsonify({'error': 'FMZ客户端未初始化'}), 500
    
    if not trading_enabled:
        return jsonify({
            'status': 'disabled',
            'message': '交易功能已禁用',
            'timestamp': datetime.now().isoformat()
        }), 403
    
    try:
        signal = request.json
        if not signal:
            return jsonify({'error': '无效的信号数据'}), 400
        
        # 验证必要字段
        required_fields = ['symbol', 'direction', 'confidence']
        for field in required_fields:
            if field not in signal:
                return jsonify({'error': f'缺少必要字段: {field}'}), 400
        
        # 执行信号
        result = fmz_client.execute_ai_signal(signal)
        
        # 缓存信号结果
        signal_key = f"{signal['symbol']}_{signal['direction']}_{datetime.now().timestamp()}"
        signal_cache[signal_key] = {
            'signal': signal,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        
        # 清理旧缓存（保留最近100条）
        if len(signal_cache) > 100:
            oldest_key = min(signal_cache.keys())
            del signal_cache[oldest_key]
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"执行信号失败: {e}")
        return jsonify({
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/fmz/signal-history', methods=['GET'])
def get_signal_history():
    """获取信号执行历史"""
    limit = int(request.args.get('limit', 50))
    
    # 按时间排序
    sorted_signals = sorted(
        signal_cache.items(),
        key=lambda x: x[1]['timestamp'],
        reverse=True
    )[:limit]
    
    history = []
    for key, data in sorted_signals:
        history.append({
            'signal_key': key,
            'signal': data['signal'],
            'result': data['result'],
            'timestamp': data['timestamp']
        })
    
    return jsonify({
        'history': history,
        'count': len(history),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/fmz/trading-control', methods=['POST'])
def trading_control():
    """交易控制开关"""
    global trading_enabled
    
    try:
        data = request.json or {}
        action = data.get('action')
        
        if action == 'enable':
            trading_enabled = True
            message = '交易功能已启用'
        elif action == 'disable':
            trading_enabled = False
            message = '交易功能已禁用'
        elif action == 'toggle':
            trading_enabled = not trading_enabled
            message = f'交易功能已{"启用" if trading_enabled else "禁用"}'
        else:
            return jsonify({'error': '无效的操作'}), 400
        
        return jsonify({
            'status': 'success',
            'trading_enabled': trading_enabled,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fmz/market-data/<exchange>/<symbol>', methods=['GET'])
def get_market_data(exchange, symbol):
    """获取市场数据"""
    if fmz_client is None:
        return jsonify({'error': 'FMZ客户端未初始化'}), 500
    
    data_type = request.args.get('type', 'ticker')
    
    try:
        if data_type == 'ticker':
            data = fmz_client.get_ticker(exchange, symbol)
        elif data_type == 'klines':
            interval = request.args.get('interval', '1h')
            limit = int(request.args.get('limit', 100))
            data = fmz_client.get_klines(exchange, symbol, interval, limit)
        elif data_type == 'depth':
            limit = int(request.args.get('limit', 20))
            data = fmz_client.get_depth(exchange, symbol, limit)
        else:
            return jsonify({'error': '不支持的数据类型'}), 400
        
        return jsonify({
            'exchange': exchange,
            'symbol': symbol,
            'data_type': data_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fmz/place-order', methods=['POST'])
def place_order():
    """手动下单"""
    if fmz_client is None:
        return jsonify({'error': 'FMZ客户端未初始化'}), 500
    
    if not trading_enabled:
        return jsonify({
            'status': 'disabled',
            'message': '交易功能已禁用',
            'timestamp': datetime.now().isoformat()
        }), 403
    
    try:
        order_data = request.json
        if not order_data:
            return jsonify({'error': '无效的订单数据'}), 400
        
        # 必要字段验证
        required_fields = ['exchange', 'symbol', 'side', 'type', 'amount']
        for field in required_fields:
            if field not in order_data:
                return jsonify({'error': f'缺少必要字段: {field}'}), 400
        
        result = fmz_client.place_order(
            exchange=order_data['exchange'],
            symbol=order_data['symbol'],
            side=order_data['side'],
            order_type=order_data['type'],
            amount=order_data['amount'],
            price=order_data.get('price')
        )
        
        return jsonify({
            'status': 'success',
            'order_result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fmz/cancel-order', methods=['POST'])
def cancel_order():
    """取消订单"""
    if fmz_client is None:
        return jsonify({'error': 'FMZ客户端未初始化'}), 500
    
    try:
        data = request.json or {}
        exchange = data.get('exchange')
        order_id = data.get('order_id')
        
        if not exchange or not order_id:
            return jsonify({'error': '缺少必要参数'}), 400
        
        result = fmz_client.cancel_order(exchange, order_id)
        
        return jsonify({
            'status': 'success',
            'cancel_result': result,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/fmz/orders', methods=['GET'])
def get_orders():
    """获取订单列表"""
    if fmz_client is None:
        return jsonify({'error': 'FMZ客户端未初始化'}), 500
    
    exchange = request.args.get('exchange', 'binance')
    symbol = request.args.get('symbol')
    status = request.args.get('status')
    limit = int(request.args.get('limit', 100))
    
    try:
        orders = fmz_client.get_orders(exchange, symbol, status, limit)
        
        return jsonify({
            'exchange': exchange,
            'symbol': symbol,
            'orders': orders,
            'count': len(orders),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== 监控线程 ==========

class FMZMonitor(threading.Thread):
    """FMZ监控线程"""
    
    def __init__(self, interval=60):
        super().__init__()
        self.interval = interval
        self.running = False
        self.daemon = True
        
    def run(self):
        """监控线程主循环"""
        self.running = True
        logger.info(f"FMZ监控线程启动，检查间隔: {self.interval}秒")
        
        while self.running:
            try:
                if fmz_client and trading_enabled:
                    self.check_status()
            except Exception as e:
                logger.error(f"监控检查失败: {e}")
            
            time.sleep(self.interval)
    
    def check_status(self):
        """检查状态"""
        try:
            # 检查账户余额
            balance = fmz_client.get_balance('binance')
            logger.info(f"账户余额检查: {balance}")
            
            # 检查运行中的策略
            strategies = fmz_client.get_running_strategies()
            logger.info(f"运行中的策略: {len(strategies)}个")
            
            # 检查未完成订单
            orders = fmz_client.get_orders('binance', status='open')
            if orders:
                logger.info(f"未完成订单: {len(orders)}个")
                
        except Exception as e:
            logger.error(f"状态检查失败: {e}")
    
    def stop(self):
        """停止监控"""
        self.running = False


# ========== 启动函数 ==========

def start_fmz_api(host='0.0.0.0', port=5001, debug=False):
    """启动FMZ API服务"""
    # 初始化FMZ客户端
    if not init_fmz_client():
        logger.warning("FMZ客户端初始化失败，部分功能可能不可用")
    
    # 启动监控线程
    monitor = FMZMonitor(interval=60)
    monitor.start()
    
    logger.info(f"FMZ API服务启动: http://{host}:{port}")
    logger.info("可用端点:")
    logger.info("  GET  /api/fmz/status              - FMZ状态")
    logger.info("  GET  /api/fmz/balance             - 账户余额")
    logger.info("  GET  /api/fmz/positions           - 持仓信息")
    logger.info("  GET  /api/fmz/strategies          - 策略列表")
    logger.info("  POST /api/fmz/execute-signal      - 执行AI信号")
    logger.info("  POST /api/fmz/trading-control     - 交易控制")
    logger.info("  GET  /api/fmz/signal-history      - 信号历史")
    
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    start_fmz_api(debug=True)