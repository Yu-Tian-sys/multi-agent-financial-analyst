import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


MOCK_REPORTS = [
    {"title": "苹果：创新驱动增长，维持买入评级", "broker": "中金公司", "date": "2025-01-10", "summary": "苹果公司在 AI 和可穿戴设备领域持续创新，预计 2025 年营收增长 8%。维持买入评级，目标价 250 美元。"},
    {"title": "特斯拉：产能释放，但竞争加剧", "broker": "摩根士丹利", "date": "2025-01-09", "summary": "特斯拉上海工厂产能持续释放，但面临中国本土品牌竞争加剧。维持中性评级，目标价 220 美元。"},
    {"title": "科技板块 2025 年展望", "broker": "高盛", "date": "2025-01-05", "summary": "看好 AI、云计算、半导体三大方向。预计科技板块整体跑赢大盘 10%。"},
    {"title": "新能源车行业深度报告", "broker": "中信证券", "date": "2025-01-03", "summary": "新能源车渗透率持续提升，预计 2025 年全球销量突破 2000 万辆。龙头公司受益。"},
]


def search_reports(query: str, limit: int = 5) -> List[Dict]:
    """检索研报（模拟关键词匹配，后续替换成 ChromaDB 语义检索）"""
    if not query:
        return []
    query_lower = query.lower()
    results = []
    for report in MOCK_REPORTS:
        text = (report["title"] + " " + report["summary"]).lower()
        keywords = [w for w in query_lower.replace(",", " ").split() if len(w) > 1]
        if any(kw in text for kw in keywords):
            results.append(report)
    if not results:
        logger.info(f"研报检索无匹配，降级返回热门研报：{query}")
        results = MOCK_REPORTS[:limit]
    return results[:limit]
