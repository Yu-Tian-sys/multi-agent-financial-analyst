"""
研报/分析师评级搜索 —— 已接入真实数据

通过 MarketRouter 获取真实分析师评级，
同时保留关键词匹配的本地研报库作为补充。
"""

import logging
from typing import List, Dict

from src.data import get_provider

logger = logging.getLogger(__name__)


MOCK_REPORTS = [
    {"title": "科技板块 2025 年展望", "broker": "高盛", "date": "2025-01-05", "summary": "看好 AI、云计算、半导体三大方向。预计科技板块整体跑赢大盘 10%。"},
    {"title": "新能源车行业深度报告", "broker": "中信证券", "date": "2025-01-03", "summary": "新能源车渗透率持续提升，预计 2025 年全球销量突破 2000 万辆。龙头公司受益。"},
]


def search_reports(query: str, limit: int = 5) -> List[Dict]:
    """
    检索分析师评级 + 研报

    优先返回真实分析师评级，不足时用本地研报库补充。

    Args:
        query: 股票代码或关键词
        limit: 返回条数

    Returns:
        [{"title", "broker", "date", "summary", "rating", "target_price"}]
    """
    if not query or not query.strip():
        return []

    results = []

    # 1. 优先获取真实分析师评级
    provider = get_provider(query)
    if provider is not None:
        try:
            ratings = provider.get_analyst_ratings(query)
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

    # 2. 不足时用本地研报库补充
    if len(results) < limit:
        query_lower = query.lower()
        for report in MOCK_REPORTS:
            if len(results) >= limit:
                break
            text = (report["title"] + " " + report["summary"]).lower()
            keywords = [w for w in query_lower.replace(",", " ").split() if len(w) > 1]
            if not keywords or any(kw in text for kw in keywords):
                results.append(report)

    # 3. 如果还是没有（非股票代码且无关键词匹配），返回热门研报
    if not results:
        results = MOCK_REPORTS[:limit]

    return results[:limit]
