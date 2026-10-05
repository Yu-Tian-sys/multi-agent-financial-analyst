"""
研报/分析师评级搜索 —— 已接入真实数据

通过 MarketRouter 获取真实分析师评级，
同时保留关键词匹配的本地研报库作为补充。
"""

import logging
from typing import List, Dict

from src.data import get_provider
from src.data.router import resolve_symbol

logger = logging.getLogger(__name__)


def search_reports(query: str, limit: int = 5) -> List[Dict]:
    """
    检索分析师评级 + 研报

    仅返回真实分析师评级，无数据时返回空列表（不用通用 mock 避免误导）。

    Args:
        query: 股票代码或关键词
        limit: 返回条数

    Returns:
        [{"title", "broker", "date", "summary", "rating", "target_price"}]
    """
    if not query or not query.strip():
        return []

    results = []

    # 获取真实分析师评级
    # 先解析为标准代码（支持中文别名如"苹果"→AAPL）
    symbol = resolve_symbol(query)
    provider = get_provider(symbol)
    if provider is not None:
        try:
            ratings = provider.get_analyst_ratings(symbol)
            for r in ratings[:limit]:
                title = f"{r.broker}：{r.rating}评级" if r.rating else f"{r.broker}研报"
                summary_parts = []
                if r.rating:
                    summary_parts.append(f"评级：{r.rating}")
                if r.target_price is not None:
                    summary_parts.append(f"目标价：{r.target_price}")
                results.append({
                    "title": title,
                    "broker": r.broker,
                    "date": r.date,
                    "summary": "；".join(summary_parts) if summary_parts else "分析师观点",
                    "rating": r.rating,
                    "target_price": r.target_price,
                })
        except Exception as e:
            logger.warning(f"[reports] 分析师评级获取失败 {query}: {e}")

    return results[:limit]
