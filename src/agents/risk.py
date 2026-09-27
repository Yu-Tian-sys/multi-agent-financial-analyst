import logging
from typing import Dict, List

from src.state import FinanceState

logger = logging.getLogger(__name__)


# ========================================
# 风险因素识别规则
# ========================================

def _check_financial_risk(financial_data: dict) -> List[str]:
    """
    从财报数据识别风险

    Args:
        financial_data: 财报数据

    Returns:
        风险因素列表
    """
    risks = []
    ratios = financial_data.get("ratios", {})
    raw = financial_data.get("raw_metrics", {})

    # 资产负债率过高
    debt_ratio = ratios.get("debt_ratio")
    if debt_ratio is not None and debt_ratio > 0.7:
        risks.append(f"资产负债率过高（{debt_ratio:.1%}），偿债压力大")

    # 净利率过低
    net_margin = ratios.get("net_margin")
    if net_margin is not None and net_margin < 0.05:
        risks.append(f"净利率偏低（{net_margin:.1%}），盈利能力弱")

    # 利润下滑
    profit_str = raw.get("profit", "")
    if "下滑" in profit_str or "下降" in profit_str:
        risks.append(f"净利润下滑（{profit_str}）")

    return risks


def _check_news_risk(news_data: List[dict]) -> List[str]:
    """
    从新闻识别风险

    Args:
        news_data: 新闻列表

    Returns:
        风险因素列表
    """
    risks = []
    negative_count = sum(1 for n in news_data if n.get("sentiment") == "negative")
    total = len(news_data)

    if total > 0 and negative_count / total >= 0.5:
        risks.append(f"负面新闻占比高（{negative_count}/{total}）")

    # 关键词识别
    risk_keywords = ["调查", "召回", "诉讼", "罚款", "违规", "退市", "亏损"]
    for news in news_data:
        title = news.get("title", "")
        for kw in risk_keywords:
            if kw in title:
                risks.append(f"负面事件：{title[:30]}")
                break

    return risks[:5]


def _check_debate_risk(debate_records: List[dict]) -> List[str]:
    """
    从辩论记录识别风险

    Args:
        debate_records: 辩论记录

    Returns:
        风险因素列表
    """
    risks = []
    # 找主持人的裁决
    judge_record = next(
        (r for r in debate_records if r.get("side") == "judge"),
        None
    )
    if judge_record:
        import json
        try:
            verdict = json.loads(judge_record["content"])
            stance = verdict.get("stance", "")
            confidence = verdict.get("confidence", 0.5)
            # 看空或置信度低
            if stance == "看空":
                risks.append(f"辩论裁决看空（置信度 {confidence}）")
            elif confidence < 0.5:
                risks.append(f"辩论置信度低（{confidence}），存在不确定性")
            # 空头核心观点也算风险
            for bp in verdict.get("bear_points", [])[:2]:
                risks.append(f"空头观点：{bp[:50]}")
        except (json.JSONDecodeError, KeyError):
            pass

    return risks


def _determine_risk_level(all_risks: List[str]) -> str:
    """
    根据风险数量决定等级

    Args:
        all_risks: 所有风险因素

    Returns:
        低 / 中 / 高
    """
    count = len(all_risks)
    if count == 0:
        return "低"
    elif count <= 2:
        return "中"
    else:
        return "高"


def _build_warning(risk_level: str, risks: List[str]) -> str:
    """
    生成风险提示文本（合规要求）

    Args:
        risk_level: 风险等级
        risks: 风险因素列表

    Returns:
        风险提示文本
    """
    base = "【风险提示】本报告仅供参考，不构成任何投资建议。投资有风险，入市需谨慎。"
    if risk_level == "高":
        return base + " 本标的识别出多项风险因素，请投资者高度谨慎。"
    elif risk_level == "中":
        return base + " 本标的识别出部分风险因素，请投资者注意。"
    return base


# ========================================
# LangGraph 节点
# ========================================

def risk_node(state: FinanceState) -> dict:
    """
    风控 Agent（LangGraph 节点）

    流程：
    1. 从财务、新闻、辩论三方面识别风险
    2. 综合定级（低/中/高）
    3. 生成风险提示文本
    4. 写入 state.risk_assessment

    Args:
        state: 当前状态

    Returns:
        要更新的字段
    """
    logger.info("[risk] 开始风险评估")

    try:
        financial_data = state.get("financial_data", {})
        news_data = state.get("news_data", [])
        debate_records = state.get("debate_records", [])

        # 1. 识别各类风险
        fin_risks = _check_financial_risk(financial_data)
        news_risks = _check_news_risk(news_data)
        debate_risks = _check_debate_risk(debate_records)

        all_risks = fin_risks + news_risks + debate_risks

        # 2. 定级
        risk_level = _determine_risk_level(all_risks)

        # 3. 生成提示
        risk_warning = _build_warning(risk_level, all_risks)

        risk_assessment = {
            "risk_level": risk_level,
            "risk_factors": all_risks,
            "risk_warning": risk_warning,
            "financial_risks": fin_risks,
            "news_risks": news_risks,
            "debate_risks": debate_risks,
        }

        logger.info(f"[risk] 风险等级：{risk_level}，风险因素 {len(all_risks)} 个")

        return {
            "risk_assessment": risk_assessment,
            "current_step": state.get("current_step", 0) + 1,
            "status": "running",
            "messages": [
                {"role": "system", "content": f"风控完成：风险等级 {risk_level}，{len(all_risks)} 个风险因素"}
            ]
        }

    except Exception as e:
        logger.error(f"[risk] 风控失败：{e}")
        return {
            "status": "failed",
            "error": f"风控失败：{e}",
            "messages": [{"role": "system", "content": f"风控失败：{e}"}]
        }


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    from src.state import create_initial_state

    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["financial_data"] = {
        "raw_metrics": {"profit": "970亿，同比下滑5%"},
        "ratios": {"net_margin": 0.03, "debt_ratio": 0.85},
    }
    state["news_data"] = [
        {"title": "面临反垄断调查", "sentiment": "negative"},
        {"title": "召回部分产品", "sentiment": "negative"},
    ]
    state["debate_records"] = [
        {"round": 4, "side": "judge", "content": '{"stance": "看空", "confidence": 0.7, "bear_points": ["竞争加剧", "增长放缓"]}'},
    ]

    result = risk_node(state)
    print("状态:", result["status"])
    ra = result["risk_assessment"]
    print("风险等级:", ra["risk_level"])
    print("风险数量:", len(ra["risk_factors"]))
    print("风险提示:", ra["risk_warning"][:50])
