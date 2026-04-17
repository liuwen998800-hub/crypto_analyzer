"""
Binance数据获取模块
获取BTC、ETH、SOL的实时价格和历史数据
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BinanceDataFetcher:
    """Binance交易所数据获取器"""
    
    def __init__(self, api_key: str = "", api_secret: str = ""):
        """
        初始化Binance连接
        
        Args:
            api_key: Binance API密钥（可选，免费层有限制）
            api_secret: Binance API密钥（可选）
        """
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        
        # 支持的币种映射
        self.symbol_map = {
            'BTC': 'BTC/USDT',
            'ETH': 'ETH/USDT', 
            'SOL': 'SOL/USDT'
        }
        
        logger.info("Binance数据获取器初始化完成")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        获取当前价格
        
        Args:
            symbol: 币种符号 (BTC, ETH, SOL)
            
        Returns:
            当前价格，获取失败返回None
        """
        try:
            ccxt_symbol = self.symbol_map.get(symbol.upper())
            if not ccxt_symbol:
                logger.error(f"不支持的币种: {symbol}")
                return None
            
            ticker = self.exchange.fetch_ticker(ccxt_symbol)
            return float(ticker['last'])
            
        except Exception as e:
            logger.error(f"获取{symbol}价格失败: {e}")
            return None
    
    def get_ohlcv_data(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> Optional[pd.DataFrame]:
        """
        获取OHLCV数据
        
        Args:
            symbol: 币种符号
            timeframe: 时间框架 ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: 数据条数
            
        Returns:
            DataFrame包含: timestamp, open, high, low, close, volume
        """
        try:
            ccxt_symbol = self.symbol_map.get(symbol.upper())
            if not ccxt_symbol:
                logger.error(f"不支持的币种: {symbol}")
                return None
            
            # 获取K线数据
            ohlcv = self.exchange.fetch_ohlcv(ccxt_symbol, timeframe, limit=limit)
            
            # 转换为DataFrame
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"获取{symbol} {timeframe}数据成功，共{len(df)}条记录")
            return df
            
        except Exception as e:
            logger.error(f"获取{symbol} OHLCV数据失败: {e}")
            return None
    
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        批量获取多种币种价格信息
        
        Args:
            symbols: 币种符号列表
            
        Returns:
            字典格式的价格信息
        """
        results = {}
        
        for symbol in symbols:
            price = self.get_current_price(symbol)
            if price is not None:
                # 获取24小时变化
                change_info = self.get_24h_change(symbol)
                
                results[symbol] = {
                    'price': price,
                    'timestamp': datetime.now().isoformat(),
                    '24h_change': change_info.get('change_percent', 0),
                    '24h_high': change_info.get('high', price),
                    '24h_low': change_info.get('low', price),
                    '24h_volume': change_info.get('volume', 0)
                }
        
        return results
    
    def get_24h_change(self, symbol: str) -> Dict:
        """
        获取24小时价格变化
        
        Args:
            symbol: 币种符号
            
        Returns:
            24小时变化信息
        """
        try:
            ccxt_symbol = self.symbol_map.get(symbol.upper())
            if not ccxt_symbol:
                return {}
            
            ticker = self.exchange.fetch_ticker(ccxt_symbol)
            
            return {
                'open': float(ticker['open']),
                'high': float(ticker['high']),
                'low': float(ticker['low']),
                'close': float(ticker['close']),
                'change': float(ticker['change']),
                'change_percent': float(ticker['percentage']),
                'volume': float(ticker['quoteVolume'])
            }
            
        except Exception as e:
            logger.error(f"获取{symbol} 24h变化失败: {e}")
            return {}
    
    def get_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """
        获取订单簿数据
        
        Args:
            symbol: 币种符号
            limit: 深度限制
            
        Returns:
            订单簿数据
        """
        try:
            ccxt_symbol = self.symbol_map.get(symbol.upper())
            if not ccxt_symbol:
                return {}
            
            order_book = self.exchange.fetch_order_book(ccxt_symbol, limit)
            
            return {
                'bids': order_book['bids'][:limit],  # 买盘
                'asks': order_book['asks'][:limit],  # 卖盘
                'bid_volume': sum(bid[1] for bid in order_book['bids'][:limit]),
                'ask_volume': sum(ask[1] for ask in order_book['asks'][:limit]),
                'spread': order_book['asks'][0][0] - order_book['bids'][0][0] if order_book['asks'] and order_book['bids'] else 0
            }
            
        except Exception as e:
            logger.error(f"获取{symbol}订单簿失败: {e}")
            return {}
    
    def get_historical_data(self, symbol: str, days: int = 30, timeframe: str = '1h') -> Optional[pd.DataFrame]:
        """
        获取历史数据
        
        Args:
            symbol: 币种符号
            days: 天数
            timeframe: 时间框架
            
        Returns:
            历史数据DataFrame
        """
        try:
            # 计算需要的数据条数
            if timeframe == '1h':
                limit = days * 24
            elif timeframe == '4h':
                limit = days * 6
            elif timeframe == '1d':
                limit = days
            else:
                limit = days * 24 * 60  # 分钟级
            
            limit = min(limit, 1000)  # Binance API限制
            
            return self.get_ohlcv_data(symbol, timeframe, limit)
            
        except Exception as e:
            logger.error(f"获取{symbol}历史数据失败: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            连接是否成功
        """
        try:
            # 尝试获取BTC价格
            price = self.get_current_price('BTC')
            return price is not None and price > 0
            
        except Exception as e:
            logger.error(f"API连接测试失败: {e}")
            return False


# 使用示例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建数据获取器（无需API密钥）
    fetcher = BinanceDataFetcher()
    
    # 测试连接
    if fetcher.test_connection():
        print("✅ Binance API连接成功")
        
        # 获取BTC当前价格
        btc_price = fetcher.get_current_price('BTC')
        print(f"BTC当前价格: ${btc_price:,.2f}")
        
        # 获取多种币种价格
        prices = fetcher.get_multiple_prices(['BTC', 'ETH', 'SOL'])
        for symbol, data in prices.items():
            print(f"{symbol}: ${data['price']:,.2f} (24h: {data['24h_change']:+.2f}%)")
        
        # 获取BTC历史数据
        btc_history = fetcher.get_historical_data('BTC', days=7)
        if btc_history is not None:
            print(f"\nBTC历史数据形状: {btc_history.shape}")
            print(f"最新数据:\n{btc_history.tail()}")
    else:
        print("❌ Binance API连接失败")