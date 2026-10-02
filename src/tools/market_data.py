"""
市场数据工具 —— 已接入真实数据（AKShare / yfinance）

通过 MarketRouter 自动识别市场，返回统一格式。
保留原有函数签名，对 registry 和 Agent 层透明。
"""

import logging
from typing import Dict

from src.data import get_provider

logger = logging.getLogger(__name__)


def get_stock_price(symbol: str, days: int = 30) -> Dict:
    """
    获取股价数据（真实数据，带缓存）

    Args:
        symbol: 股票代码，如 "AAPL"、"600519"、"00700.HK"
        days: 历史天数

    Returns:
        {"symbol", "price", "change", "volume", "history"}
        获取失败时返回默认值
    """
    provider = get_provider(symbol)
    if provider is None:
        logger.warning(f"[market_data] 无法识别市场：{symbol}，返回默认值")
        return {"symbol": symbol, "price": 100.0, "change": 0, "volume": 0, "history": []}

    try:
        price = provider.get_price(symbol, days)
        return {
            "symbol": price.symbol,
            "price": price.price,
            "change": price.change,
            "change_percent": price.change_percent,
            "volume": price.volume,
            "history": price.history,
        }
    except Exception as e:
        logger.error(f"[market_data] 股价获取失败 {symbol}: {e}")
        return {"symbol": symbol, "price": 0, "change": 0, "volume": 0, "history": []}


def get_valuation(symbol: str) -> Dict:
    """
    获取估值指标（PE/PB/PS/市值）

    Args:
        symbol: 股票代码

    Returns:
        {"symbol", "pe", "pb", "ps", "market_cap"}
    """
    provider = get_provider(symbol)
    if provider is None:
        return {"symbol": symbol, "pe": None, "pb": None, "ps": None, "market_cap": None}

    try:
        val = provider.get_valuation(symbol)
        return {
            "symbol": val.symbol,
            "pe": val.pe,
            "pb": val.pb,
            "ps": val.ps,
            "market_cap": val.market_cap,
        }
    except Exception as e:
        logger.error(f"[market_data] 估值获取失败 {symbol}: {e}")
        return {"symbol": symbol, "pe": None, "pb": None, "ps": None, "market_cap": None}
