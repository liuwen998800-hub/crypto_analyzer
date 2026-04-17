#!/usr/bin/env python3
"""
FMZ发明者量化平台客户端
用于对接FMZ扩展API，执行AI分析信号的交易
"""

import requests
import json
import time
import hashlib
import hmac
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FMZClient:
    """FMZ平台客户端"""
    
    def __init__(self, api_key: str, secret_key: str, base_url: str = "https://api.fmz.com"):
        """
        初始化FMZ客户端
        
        Args:
            api_key: FMZ API Key
            secret_key: FMZ Secret Key
            base_url: FMZ API基础URL
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'CryptoAnalyzer/1.0'
        })
        
    def _generate_signature(self, params: Dict) -> str:
        """生成API签名"""
        # 按参数名排序
        sorted_params = sorted(params.items())
        # 构建待签名字符串
        sign_string = ''
        for key, value in sorted_params:
            if value is not None:
                sign_string += f"{key}={value}&"
        sign_string = sign_string.rstrip('&')
        
        # 使用HMAC-SHA256生成签名
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """发送API请求"""
        url = f"{self.base_url}{endpoint}"
        
        # 添加公共参数
        if params is None:
            params = {}
        
        params.update({
            'api_key': self.api_key,
            'timestamp': int(time.time() * 1000)
        })
        
        # 生成签名
        params['sign'] = self._generate_signature(params)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, params=params, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, params=params, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') != 0:
                logger.error(f"FMZ API错误: {result.get('msg', '未知错误')}")
                raise Exception(f"FMZ API错误: {result.get('msg', '未知错误')}")
            
            return result.get('data', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FMZ API请求失败: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"FMZ API响应解析失败: {e}")
            raise
    
    # ========== 账户相关API ==========
    
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        return self._request('GET', '/v1/account/info')
    
    def get_balance(self, exchange: str = 'binance') -> Dict:
        """
        获取交易所余额
        
        Args:
            exchange: 交易所名称，如binance, okex等
        """
        params = {'exchange': exchange}
        return self._request('GET', '/v1/account/balance', params=params)
    
    def get_positions(self, exchange: str = 'binance') -> List[Dict]:
        """
        获取持仓信息
        
        Args:
            exchange: 交易所名称
        """
        params = {'exchange': exchange}
        return self._request('GET', '/v1/account/positions', params=params)
    
    # ========== 交易相关API ==========
    
    def place_order(self, exchange: str, symbol: str, side: str, 
                   order_type: str, amount: float, price: float = None) -> Dict:
        """
        下单
        
        Args:
            exchange: 交易所名称
            symbol: 交易对，如BTC_USDT
            side: 买卖方向，buy/sell
            order_type: 订单类型，limit/market
            amount: 数量
            price: 价格（限价单需要）
        """
        data = {
            'exchange': exchange,
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'amount': amount
        }
        
        if price is not None:
            data['price'] = price
        
        return self._request('POST', '/v1/trade/order', data=data)
    
    def cancel_order(self, exchange: str, order_id: str) -> Dict:
        """
        取消订单
        
        Args:
            exchange: 交易所名称
            order_id: 订单ID
        """
        params = {
            'exchange': exchange,
            'order_id': order_id
        }
        return self._request('DELETE', '/v1/trade/order', params=params)
    
    def get_orders(self, exchange: str, symbol: str = None, 
                  status: str = None, limit: int = 100) -> List[Dict]:
        """
        获取订单列表
        
        Args:
            exchange: 交易所名称
            symbol: 交易对
            status: 订单状态
            limit: 返回数量限制
        """
        params = {
            'exchange': exchange,
            'limit': limit
        }
        
        if symbol:
            params['symbol'] = symbol
        if status:
            params['status'] = status
            
        return self._request('GET', '/v1/trade/orders', params=params)
    
    # ========== 策略相关API ==========
    
    def get_strategies(self) -> List[Dict]:
        """获取策略列表"""
        return self._request('GET', '/v1/strategy/list')
    
    def create_strategy(self, name: str, code: str, language: str = 'javascript') -> Dict:
        """
        创建策略
        
        Args:
            name: 策略名称
            code: 策略代码
            language: 编程语言，javascript/python
        """
        data = {
            'name': name,
            'code': code,
            'language': language
        }
        return self._request('POST', '/v1/strategy/create', data=data)
    
    def run_strategy(self, strategy_id: int, exchange: str, symbol: str, 
                    settings: Dict = None) -> Dict:
        """
        运行策略
        
        Args:
            strategy_id: 策略ID
            exchange: 交易所名称
            symbol: 交易对
            settings: 策略配置
        """
        if settings is None:
            settings = {}
        
        data = {
            'strategy_id': strategy_id,
            'exchange': exchange,
            'symbol': symbol,
            'settings': json.dumps(settings)
        }
        return self._request('POST', '/v1/strategy/run', data=data)
    
    def stop_strategy(self, robot_id: str) -> Dict:
        """
        停止策略
        
        Args:
            robot_id: 机器人ID
        """
        params = {'robot_id': robot_id}
        return self._request('POST', '/v1/strategy/stop', params=params)
    
    def get_running_strategies(self) -> List[Dict]:
        """获取运行中的策略"""
        return self._request('GET', '/v1/strategy/running')
    
    # ========== 市场数据API ==========
    
    def get_ticker(self, exchange: str, symbol: str) -> Dict:
        """
        获取行情数据
        
        Args:
            exchange: 交易所名称
            symbol: 交易对
        """
        params = {
            'exchange': exchange,
            'symbol': symbol
        }
        return self._request('GET', '/v1/market/ticker', params=params)
    
    def get_klines(self, exchange: str, symbol: str, interval: str = '1h', 
                  limit: int = 100) -> List[List]:
        """
        获取K线数据
        
        Args:
            exchange: 交易所名称
            symbol: 交易对
            interval: 时间间隔，如1m, 5m, 1h, 1d
            limit: 返回数量
        """
        params = {
            'exchange': exchange,
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        return self._request('GET', '/v1/market/klines', params=params)
    
    def get_depth(self, exchange: str, symbol: str, limit: int = 20) -> Dict:
        """
        获取深度数据
        
        Args:
            exchange: 交易所名称
            symbol: 交易对
            limit: 深度数量
        """
        params = {
            'exchange': exchange,
            'symbol': symbol,
            'limit': limit
        }
        return self._request('GET', '/v1/market/depth', params=params)
    
    # ========== AI信号执行 ==========
    
    def execute_ai_signal(self, signal: Dict) -> Dict:
        """
        执行AI分析信号
        
        Args:
            signal: AI分析信号，包含以下字段：
                - symbol: 交易对，如BTC_USDT
                - direction: 方向，buy/sell
                - confidence: 置信度
                - amount: 数量（可选）
                - price: 价格（可选，市价单不需要）
                - exchange: 交易所（默认binance）
                - order_type: 订单类型（默认market）
        """
        # 默认值
        exchange = signal.get('exchange', 'binance')
        order_type = signal.get('order_type', 'market')
        symbol = signal.get('symbol', 'BTC_USDT')
        direction = signal.get('direction', 'buy')
        confidence = signal.get('confidence', 0)
        
        # 根据置信度决定是否执行
        if confidence < 60:
            logger.warning(f"信号置信度过低({confidence}%)，跳过执行")
            return {'status': 'skipped', 'reason': 'confidence_too_low'}
        
        # 计算交易数量（可根据账户余额动态计算）
        amount = signal.get('amount')
        if amount is None:
            # 默认交易数量
            amount = 0.001 if 'BTC' in symbol else 1.0
        
        price = signal.get('price')
        
        try:
            # 执行交易
            order_result = self.place_order(
                exchange=exchange,
                symbol=symbol,
                side=direction,
                order_type=order_type,
                amount=amount,
                price=price
            )
            
            logger.info(f"AI信号执行成功: {direction} {amount} {symbol} at {price or 'market'}")
            
            return {
                'status': 'success',
                'order_id': order_result.get('order_id'),
                'symbol': symbol,
                'direction': direction,
                'amount': amount,
                'price': price,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"AI信号执行失败: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'symbol': symbol,
                'direction': direction,
                'timestamp': datetime.now().isoformat()
            }
    
    def create_ai_strategy(self, strategy_name: str = "AI量化策略") -> Dict:
        """
        创建AI量化策略模板
        
        Args:
            strategy_name: 策略名称
        """
        # AI策略模板代码（JavaScript）
        strategy_code = """
function main() {
    // AI量化策略 - 自动执行AI分析信号
    Log("AI量化策略启动");
    
    // 配置参数
    var exchange = "binance";
    var symbol = "BTC_USDT";
    var checkInterval = 300; // 检查间隔（秒）
    var minConfidence = 60;  // 最小置信度
    
    while (true) {
        try {
            // 1. 获取AI分析信号（通过HTTP API）
            var aiSignal = getAISignal();
            
            if (aiSignal && aiSignal.confidence >= minConfidence) {
                Log("收到AI信号:", aiSignal);
                
                // 2. 执行交易
                if (aiSignal.direction === "buy") {
                    // 买入逻辑
                    var account = exchange.GetAccount();
                    var usdtBalance = account.Balance.filter(function(b) {
                        return b.Currency === "USDT";
                    })[0];
                    
                    if (usdtBalance && usdtBalance.Available > 10) {
                        // 使用50%的USDT余额买入
                        var buyAmount = usdtBalance.Available * 0.5;
                        exchange.Buy(-1, buyAmount);
                        Log("执行买入:", buyAmount, "USDT");
                    }
                    
                } else if (aiSignal.direction === "sell") {
                    // 卖出逻辑
                    var account = exchange.GetAccount();
                    var btcBalance = account.Balance.filter(function(b) {
                        return b.Currency === "BTC";
                    })[0];
                    
                    if (btcBalance && btcBalance.Available > 0.001) {
                        // 卖出50%的BTC持仓
                        var sellAmount = btcBalance.Available * 0.5;
                        exchange.Sell(-1, sellAmount);
                        Log("执行卖出:", sellAmount, "BTC");
                    }
                }
            }
            
            // 3. 记录收益
            var profit = _N(exchange.GetAccount().Balance, 2);
            LogProfit(profit);
            
        } catch (error) {
            Log("策略执行错误:", error);
        }
        
        // 等待下次检查
        Sleep(checkInterval * 1000);
    }
}

// 获取AI分析信号的辅助函数
function getAISignal() {
    var url = "http://你的服务器地址:5000/api/ai-signal";
    var headers = {
        "Content-Type": "application/json"
    };
    
    try {
        var response = HttpQuery(url);
        var data = JSON.parse(response);
        return data;
    } catch (error) {
        Log("获取AI信号失败:", error);
        return null;
    }
}
"""
        
        return self.create_strategy(
            name=strategy_name,
            code=strategy_code,
            language='javascript'
        )


# ========== 配置管理 ==========

class FMZConfig:
    """FMZ配置管理"""
    
    @staticmethod
    def load_config(config_path: str = None) -> Dict:
        """加载FMZ配置"""
        import yaml
        import os
        
        if config_path is None:
            # 默认配置文件路径
            config_path = os.path.join(
                os.path.dirname(__file__),
                '../../config/fmz_config.yaml'
            )
        
        if not os.path.exists(config_path):
            # 创建默认配置模板
            default_config = {
                'fmz': {
                    'api_key': 'your_fmz_api_key_here',
                    'secret_key': 'your_fmz_secret_key_here',
                    'base_url': 'https://api.fmz.com',
                    'default_exchange': 'binance',
                    'trading': {
                        'min_confidence': 60,
                        'default_amount': 0.001,
                        'max_position_ratio': 0.5
                    }
                }
            }
            
            # 创建目录
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)
            
            logger.warning(f"配置文件不存在，已创建模板: {config_path}")
            logger.warning("请编辑配置文件，填写你的FMZ API Key和Secret Key")
            
            return default_config
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config
    
    @staticmethod
    def create_client_from_config(config_path: str = None) -> FMZClient:
        """从配置文件创建FMZ客户端"""
        config = FMZConfig.load_config(config_path)
        fmz_config = config.get('fmz', {})
        
        api_key = fmz_config.get('api_key')
        secret_key = fmz_config.get('secret_key')
        base_url = fmz_config.get('base_url', 'https://api.fmz.com')
        
        if not api_key or not secret_key:
            raise ValueError("请在配置文件中填写FMZ API Key和Secret Key")
        
        return FMZClient(api_key, secret_key, base_url)


# ========== 使用示例 ==========

if __name__ == "__main__":
    # 使用示例
    print("FMZ客户端测试")
    
    try:
        # 从