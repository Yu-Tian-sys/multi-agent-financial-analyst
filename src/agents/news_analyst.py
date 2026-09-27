import logging
from typing import List, Dict

from src.state import FinanceState
from src.tools.news_search import search_news, analyze_sentiment

logger = logging.getLogger(__name__)


def _summarize_sentiment(news_list: List[Dict]) -> Dict:
    """
    统计新闻情感分布

    Args:
        news_list: 新闻列表

    Returns:
        {"positive": n, "negative": n, "neutral": n, "total": n}
    """
    counts = {"positive": 0, "negative": 0, "neutral": 0}

    for news in news_list:
        # 优先用已有 sentiment，没有就现算
        sentiment = news.get("sentiment")
        if not sentiment:
            text = news.get("title", "") + " " + news.get("content", "")
            sentiment = analyze_sentiment(text)

        if sentiment in counts:
            counts[sentiment] += 1

    counts["total"] = len(news_list)
    return counts


def news_analyst_node(state: FinanceState) -> dict:
    """
    新闻分析 Agent（LangGraph 节点）

    流程：
    1. 用 topic 搜索新闻
    2. 对每条新闻做情感分析
    3. 统计情感分布
    4. 写入 state.news_data

    Args:
        state: 当前状态

    Returns:
        要更新的字段
    """
    topic = state["topic"]
    logger.info(f"[news] 开始分析新闻：{topic}")

    try:
        # 1. 搜索新闻
        news_list = search_news(topic, limit=10)
        logger.info(f"[news] 搜到 {len(news_list)} 条新闻")

        # 2. 对每条新闻补全情感
        enriched = []
        for news in news_list:
            text = news.get("title", "") + " " + news.get("content", "")
            sentiment = news.get("sentiment") or analyze_sentiment(text)
            enriched.append({
                "title": news.get("title", ""),
                "source": news.get("source", ""),
                "date": news.get("date", ""),
                "content": news.get("content", ""),
                "sentiment": sentiment,
            })

        # 3. 统计情感分布
        sentiment_summary = _summarize_sentiment(enriched)
        logger.info(f"[news] 情感分布：{sentiment_summary}")

        return {
            "news_data": enriched,
            "current_step": state.get("current_step", 0) + 1,
            "status": "running",
            "messages": [
                {"role": "system", "content": f"新闻分析完成：{len(enriched)} 条，情感分布 {sentiment_summary}"}
            ]
        }

    except Exception as e:
        logger.error(f"[news] 分析失败：{e}")
        return {
            "status": "failed",
            "error": f"新闻分析失败：{e}",
            "messages": [{"role": "system", "content": f"新闻分析失败：{e}"}]
        }


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    from src.state import create_initial_state

    state = create_initial_state("t1", "u1", "user", "AAPL")
    result = news_analyst_node(state)
    print("状态:", result["status"])
    print("新闻数:", len(result["news_data"]))
    print("第一条:", result["news_data"][0]["title"] if result["news_data"] else "无")
    print("情感分布:", _summarize_sentiment(result["news_data"]))
