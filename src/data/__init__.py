"""
数据层统一入口

提供统一的金融数据获取接口，自动识别市场并路由到对应 Provider。

用法：
    from src.data import get_market_data, get_provider

    # 一次拿全部数据
    bundle = get_market_data("600519")

    # 或分步获取
    provider = get_provider("AAPL")
    financials = provider.get_financials("AAPL")
"""

from typing import List, Optional

from .base import MarketDataProvider
from .models import (
    FinancialStatements,
    PriceData,
    ValuationData,
    NewsItem,
    AnalystRating,
    MarketDataBundle,
)
from .router import get_provider, get_provider_by_market, detect_market


def get_market_data(symbol: str) -> MarketDataBundle:
    """
    一次获取某只股票的全部市场数据

    Args:
        symbol: 股票代码（自动识别市场）

    Returns:
        MarketDataBundle
    """
    provider = get_provider(symbol)
    if provider is None:
        return MarketDataBundle(symbol=symbol, market="未知")

    market = provider.market
    bundle = MarketDataBundle(symbol=symbol, market=market)

    try:
        bundle.financials = provider.get_financials(symbol)
    except Exception as e:
        bundle.financials = FinancialStatements(symbol=symbol)

    try:
        bundle.price = provider.get_price(symbol)
    except Exception:
        bundle.price = PriceData(symbol=symbol, price=0, change=0, change_percent=0, volume=0)

    try:
        bundle.valuation = provider.get_valuation(symbol)
    except Exception:
        bundle.valuation = ValuationData(symbol=symbol)

    try:
        bundle.news = provider.get_news(symbol)
    except Exception:
        bundle.news = []

    try:
        bundle.analyst_ratings = provider.get_analyst_ratings(symbol)
    except Exception:
        bundle.analyst_ratings = []

    return bundle


__all__ = [
    "MarketDataProvider",
    "MarketDataBundle",
    "FinancialStatements",
    "PriceData",
    "ValuationData",
    "NewsItem",
    "AnalystRating",
    "get_provider",
    "get_provider_by_market",
    "detect_market",
    "get_market_data",
]
