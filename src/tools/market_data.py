import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_cache: Dict[str, tuple] = {}
CACHE_TTL = 300  # 5 分钟


def _get_cache(key: str):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
        else:
            del _cache[key]
    return None


def _set_cache(key: str, data):
    _cache[key] = (time.time(), data)


# 模拟市场数据
MOCK_PRICES = {
    "AAPL": {"price": 250.5, "change": 2.3, "volume": 55000000, "history": [245, 247, 248, 246, 250, 251, 250.5]},
    "TSLA": {"price": 220.8, "change": -1.5, "volume": 88000000, "history": [225, 223, 221, 222, 220, 219, 220.8]},
    "GOOGL": {"price": 185.2, "change": 1.1, "volume": 22000000, "history": [182, 183, 184, 183, 185, 184, 185.2]},
    "default": {"price": 100.0, "change": 0.0, "volume": 1000000, "history": [100, 100, 100, 100, 100, 100, 100]},
}

MOCK_VALUATION = {
    "AAPL": {"pe": 32.5, "pb": 45.2, "ps": 8.1},
    "TSLA": {"pe": 65.3, "pb": 12.8, "ps": 9.5},
    "GOOGL": {"pe": 24.1, "pb": 6.8, "ps": 6.2},
    "default": {"pe": 20.0, "pb": 2.0, "ps": 2.0},
}


def get_stock_price(symbol: str, days: int = 30) -> Dict:
    """
    获取股价数据（模拟，带缓存）

    Args:
        symbol: 股票代码，如 "AAPL"
        days: 历史天数

    Returns:
        {"symbol": ..., "price": ..., "change": ..., "volume": ..., "history": [...]}
    """
    cache_key = f"price:{symbol}:{days}"
    cached = _get_cache(cache_key)
    if cached is not None:
        logger.info(f"股价缓存命中：{symbol}")
        return cached

    symbol_upper = symbol.upper()
    data = MOCK_PRICES.get(symbol_upper, MOCK_PRICES["default"])
    result = {
        "symbol": symbol_upper,
        "price": data["price"],
        "change": data["change"],
        "volume": data["volume"],
        "history": data["history"][-days:],
    }

    _set_cache(cache_key, result)
    return result


def get_valuation(symbol: str) -> Dict:
    """
    获取估值指标（模拟）

    Args:
        symbol: 股票代码

    Returns:
        {"pe": ..., "pb": ..., "ps": ...}
    """
    cache_key = f"valuation:{symbol}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    symbol_upper = symbol.upper()
    result = MOCK_VALUATION.get(symbol_upper, MOCK_VALUATION["default"])
    result = {"symbol": symbol_upper, **result}

    _set_cache(cache_key, result)
    return result
