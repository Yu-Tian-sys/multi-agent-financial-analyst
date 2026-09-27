import re
import logging
from typing import List, Dict

from src.state import FinanceState
from src.tools.report_search import search_reports

logger = logging.getLogger(__name__)


def _extract_rating(text: str) -> str:
    """
    从研报文本中提取评级

    Args:
        text: 研报标题 + 摘要

    Returns:
        评级：买入 / 增持 / 中性 / 减持 / 卖出 / 未知
    """
    ratings = ["买入", "增持", "中性", "减持", "卖出",
               "强烈推荐", "推荐", "谨慎推荐"]
    for r in ratings:
        if r in text:
            return r
    return "未知"


def _extract_target_price(text: str) -> str:
    """
    从研报文本中提取目标价

    Args:
        text: 研报文本

    Returns:
        目标价字符串，找不到返回空
    """
    # 匹配 "目标价 250 美元" 或 "目标价：250美元"
    match = re.search(r"目标价[：:\s]*([0-9,.]+)\s*(美元|元|港币|港元)?", text)
    if match:
        price = match.group(1)
        unit = match.group(2) or ""
        return f"{price}{unit}"
    return ""


def _extract_key_points(text: str) -> List[str]:
    """
    从研报摘要中提取关键观点（按句号切分）

    Args:
        text: 研报摘要

    Returns:
        关键观点列表（最多 3 条）
    """
    if not text:
        return []
    # 按中英文句号切分
    sentences = re.split(r"[。.！!？?]", text)
    # 去掉空句子和太短的
    points = [s.strip() for s in sentences if len(s.strip()) > 10]
    return points[:3]


def report_analyst_node(state: FinanceState) -> dict:
    """
    研报分析 Agent（LangGraph 节点）

    流程：
    1. 检索研报
    2. 对每篇研报提取评级、目标价、关键观点
    3. 统计评级分布
    4. 写入 state.report_data

    Args:
        state: 当前状态

    Returns:
        要更新的字段
    """
    topic = state["topic"]
    logger.info(f"[report] 开始分析研报：{topic}")

    try:
        # 1. 检索研报
        reports = search_reports(topic, limit=5)
        logger.info(f"[report] 检索到 {len(reports)} 篇研报")

        # 2. 提取关键信息
        enriched = []
        rating_counts = {}
        for r in reports:
            text = r.get("title", "") + " " + r.get("summary", "")
            rating = _extract_rating(text)
            target_price = _extract_target_price(text)
            key_points = _extract_key_points(r.get("summary", ""))

            enriched.append({
                "title": r.get("title", ""),
                "broker": r.get("broker", ""),
                "date": r.get("date", ""),
                "summary": r.get("summary", ""),
                "rating": rating,
                "target_price": target_price,
                "key_points": key_points,
            })

            rating_counts[rating] = rating_counts.get(rating, 0) + 1

        # 3. 统计
        summary = {
            "total": len(enriched),
            "rating_distribution": rating_counts,
        }
        logger.info(f"[report] 评级分布：{rating_counts}")

        return {
            "report_data": enriched,
            "current_step": state.get("current_step", 0) + 1,
            "status": "running",
            "messages": [
                {"role": "system", "content": f"研报分析完成：{len(enriched)} 篇，评级分布 {rating_counts}"}
            ]
        }

    except Exception as e:
        logger.error(f"[report] 分析失败：{e}")
        return {
            "status": "failed",
            "error": f"研报分析失败：{e}",
            "messages": [{"role": "system", "content": f"研报分析失败：{e}"}]
        }


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    from src.state import create_initial_state

    state = create_initial_state("t1", "u1", "user", "苹果")
    result = report_analyst_node(state)
    print("状态:", result["status"])
    print("研报数:", len(result["report_data"]))
    if result["report_data"]:
        first = result["report_data"][0]
        print("第一篇标题:", first["title"])
        print("评级:", first["rating"])
        print("目标价:", first["target_price"])
        print("关键观点:", first["key_points"])
