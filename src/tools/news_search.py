"""
新闻搜索工具 —— 已接入真实数据

通过 MarketRouter 获取真实财经新闻，并用关键词法做情感分析。
"""

import time
import logging
from typing import List, Dict

from src.data import get_provider
from src.data.router import resolve_symbol

logger = logging.getLogger(__name__)

_cache: Dict[str, tuple] = {}
CACHE_TTL = 3600  # 1 小时


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


def search_news(query: str, limit: int = 10) -> List[Dict]:
    """
    搜索指定股票的真实新闻

    Args:
        query: 股票代码，如 "AAPL"、"600519"
        limit: 返回条数

    Returns:
        [{"title", "source", "date", "content", "sentiment", "url"}]
    """
    cache_key = f"news:{query}:{limit}"
    cached = _get_cache(cache_key)
    if cached is not None:
        logger.info(f"[news] 缓存命中：{query}")
        return cached

    # 先解析为标准代码（支持中文别名如"苹果"→AAPL）
    symbol = resolve_symbol(query)
    provider = get_provider(symbol)
    result = []

    if provider is not None:
        try:
            news_items = provider.get_news(symbol, limit)
            for item in news_items:
                sentiment = analyze_sentiment(item.title + " " + item.content)
                result.append({
                    "title": item.title,
                    "source": item.source,
                    "date": item.date,
                    "content": item.content,
                    "sentiment": sentiment,
                    "url": item.url,
                })
        except Exception as e:
            logger.error(f"[news] 新闻获取失败 {query}: {e}")

    # 真实数据为空时返回空列表（不再用通用 mock，避免误导）
    if result:
        _set_cache(cache_key, result)
    return result


def analyze_sentiment(text: str) -> str:
    """简单情感分析（关键词匹配）"""
    positive_words = ["增长", "超预期", "看好", "提升", "利好", "突破", "上涨", "盈利", "创新高", "增持", "买入"]
    negative_words = ["下跌", "亏损", "召回", "调查", "风险", "下滑", "暴跌", "减持", "卖出", "处罚", "违约"]
    pos = sum(1 for w in positive_words if w in text)
    neg = sum(1 for w in negative_words if w in text)
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    else:
        return "neutral"
