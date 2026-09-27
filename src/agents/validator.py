import logging
from typing import Dict, List, Tuple

from src.state import FinanceState

logger = logging.getLogger(__name__)


# ========================================
# 信号判断
# ========================================

def _financial_signal(financial_data: dict) -> str:
    """
    从财报数据判断信号

    Args:
        financial_data: 财报数据，含 metrics 和 raw_metrics

    Returns:
        positive / negative / neutral / unknown
    """
    raw = financial_data.get("raw_metrics", {})
    # 看利润的同比增长描述
    profit_str = raw.get("profit", "")
    if "增长" in profit_str or "+" in profit_str:
        return "positive"
    if "下滑" in profit_str or "下降" in profit_str or "-" in profit_str:
        return "negative"
    # 看净利率
    ratios = financial_data.get("ratios", {})
    net_margin = ratios.get("net_margin")
    if net_margin is not None:
        if net_margin > 0.15:
            return "positive"
        elif net_margin < 0.05:
            return "negative"
    return "neutral"


def _news_signal(news_data: List[dict]) -> str:
    """
    从新闻情感分布判断信号

    Args:
        news_data: 新闻列表

    Returns:
        positive / negative / neutral / unknown
    """
    if not news_data:
        return "unknown"
    pos = sum(1 for n in news_data if n.get("sentiment") == "positive")
    neg = sum(1 for n in news_data if n.get("sentiment") == "negative")
    total = len(news_data)

    if pos / total >= 0.6:
        return "positive"
    elif neg / total >= 0.6:
        return "negative"
    elif pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"


def _report_signal(report_data: List[dict]) -> str:
    """
    从研报评级判断信号

    Args:
        report_data: 研报列表

    Returns:
        positive / negative / neutral / unknown
    """
    if not report_data:
        return "unknown"
    pos_ratings = {"买入", "增持", "强烈推荐", "推荐", "谨慎推荐"}
    neg_ratings = {"减持", "卖出"}

    pos = sum(1 for r in report_data if r.get("rating") in pos_ratings)
    neg = sum(1 for r in report_data if r.get("rating") in neg_ratings)
    total = len(report_data)

    if pos / total >= 0.6:
        return "positive"
    elif neg / total >= 0.6:
        return "negative"
    elif pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"


# ========================================
# 交叉验证
# ========================================

def _cross_validate(signals: Dict[str, str]) -> Tuple[float, List[dict], float]:
    """
    交叉验证三个信号

    Args:
        signals: {"financial": ..., "news": ..., "report": ...}

    Returns:
        (一致性评分 0-1, 矛盾列表, 置信度 0-1)
    """
    conflicts = []

    # 过滤掉 unknown
    valid = {k: v for k, v in signals.items() if v != "unknown"}

    if len(valid) < 2:
        # 有效信号太少，置信度低
        return 0.5, [], 0.3

    # 计算一致性：两两比较
    keys = list(valid.keys())
    total_pairs = 0
    agree_pairs = 0

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            total_pairs += 1
            k1, k2 = keys[i], keys[j]
            v1, v2 = valid[k1], valid[k2]
            if v1 == v2:
                agree_pairs += 1
            else:
                # 记录矛盾（除非一方是 neutral）
                if v1 != "neutral" and v2 != "neutral":
                    conflicts.append({
                        "source_a": k1,
                        "value_a": v1,
                        "source_b": k2,
                        "value_b": v2,
                    })

    consistency = agree_pairs / total_pairs if total_pairs > 0 else 0.5
    # 置信度 = 一致性 * 有效信号覆盖率
    coverage = len(valid) / 3
    confidence = consistency * coverage

    return round(consistency, 4), conflicts, round(confidence, 4)


# ========================================
# LangGraph 节点
# ========================================

def validator_node(state: FinanceState) -> dict:
    """
    数据验证 Agent（LangGraph 节点）

    流程：
    1. 从财务、新闻、研报提取信号
    2. 交叉验证，找出矛盾
    3. 计算一致性评分和置信度
    4. 写入 state.validation_result

    Args:
        state: 当前状态

    Returns:
        要更新的字段
    """
    logger.info("[validator] 开始交叉验证")

    try:
        financial_data = state.get("financial_data", {})
        news_data = state.get("news_data", [])
        report_data = state.get("report_data", [])

        # 1. 提取三个信号
        signals = {
            "financial": _financial_signal(financial_data),
            "news": _news_signal(news_data),
            "report": _report_signal(report_data),
        }
        logger.info(f"[validator] 信号：{signals}")

        # 2. 交叉验证
        consistency, conflicts, confidence = _cross_validate(signals)

        validation_result = {
            "signals": signals,
            "consistency_score": consistency,
            "conflicts": conflicts,
            "confidence": confidence,
        }

        logger.info(f"[validator] 一致性 {consistency}，置信度 {confidence}，矛盾 {len(conflicts)} 个")

        return {
            "validation_result": validation_result,
            "current_step": state.get("current_step", 0) + 1,
            "status": "running",
            "messages": [
                {"role": "system", "content": f"数据验证完成：一致性 {consistency}，置信度 {confidence}"}
            ]
        }

    except Exception as e:
        logger.error(f"[validator] 验证失败：{e}")
        return {
            "status": "failed",
            "error": f"数据验证失败：{e}",
            "messages": [{"role": "system", "content": f"数据验证失败：{e}"}]
        }


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    from src.state import create_initial_state

    state = create_initial_state("t1", "u1", "user", "AAPL")
    # 手动填一些数据模拟
    state["financial_data"] = {
        "raw_metrics": {"revenue": "3832亿", "profit": "970亿，同比增长5%"},
        "metrics": {"revenue": 3832.0, "profit": 970.0},
        "ratios": {"net_margin": 0.2531},
    }
    state["news_data"] = [
        {"title": "销量超预期", "sentiment": "positive"},
        {"title": "财报超预期", "sentiment": "positive"},
        {"title": "面临调查", "sentiment": "negative"},
    ]
    state["report_data"] = [
        {"title": "维持买入", "rating": "买入"},
    ]

    result = validator_node(state)
    print("状态:", result["status"])
    vr = result["validation_result"]
    print("信号:", vr["signals"])
    print("一致性:", vr["consistency_score"])
    print("置信度:", vr["confidence"])
    print("矛盾数:", len(vr["conflicts"]))
