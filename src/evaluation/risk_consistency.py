"""
风险评级一致性评估

评估方式：
对同一只股票运行多次风险评估，检查风险等级是否稳定。
LLM 有随机性，一致性差是真实问题。

得分 = 多数派风险等级出现的频次 / 总运行次数
"""

import logging
from collections import Counter
from typing import Dict, List

from .base import EvaluationResult
from src.data import get_provider
from src.agents.risk import risk_node
from src.state import create_initial_state

logger = logging.getLogger(__name__)


def evaluate_risk_consistency(symbol: str, runs: int = 3) -> EvaluationResult:
    """
    评估风险评级一致性

    Args:
        symbol: 股票代码
        runs: 运行次数

    Returns:
        EvaluationResult
    """
    provider = get_provider(symbol)
    if provider is None:
        return EvaluationResult(
            name="风险评级一致性",
            score=0.0,
            passed=False,
            message=f"无法识别市场：{symbol}",
        )

    # 准备数据（用真实数据填充 state）
    financials = provider.get_financials(symbol)
    price = provider.get_price(symbol)
    valuation = provider.get_valuation(symbol)
    news = provider.get_news(symbol, limit=5)

    inc = financials.latest
    bs = financials.balance_sheet[0] if financials.balance_sheet else None

    financial_data = {
        "raw_metrics": {},
        "metrics": {},
        "ratios": {},
    }
    if inc:
        financial_data["metrics"] = {
            "revenue": inc.revenue or 0,
            "profit": inc.net_income or 0,
            "total_assets": (bs.total_assets if bs else 0) or 0,
            "debt": (bs.total_liabilities if bs else 0) or 0,
            "equity": (bs.total_equity if bs else 0) or 0,
        }
    if news:
        news_data = [{"title": n.title, "sentiment": n.sentiment} for n in news]
    else:
        news_data = []

    risk_levels: List[str] = []
    for i in range(runs):
        try:
            state = create_initial_state(f"eval_risk_{i}", "eval", "user", symbol)
            state["financial_data"] = financial_data
            state["news_data"] = news_data
            state["market_data"] = {
                "price": price.price,
                "pe": valuation.pe_ttm or valuation.pe,
                "pb": valuation.pb,
            }
            result = risk_node(state)
            risk = result.get("risk_assessment", {})
            level = risk.get("risk_level", "未知")
            risk_levels.append(level)
        except Exception as e:
            logger.warning(f"[eval] 第 {i+1} 次风险评估失败：{e}")
            risk_levels.append("error")

    if not risk_levels:
        return EvaluationResult(
            name="风险评级一致性",
            score=0.0,
            passed=False,
            message="所有运行都失败",
        )

    # 统计多数派
    counter = Counter(risk_levels)
    majority_level, majority_count = counter.most_common(1)[0]
    score = majority_count / len(risk_levels)

    return EvaluationResult(
        name="风险评级一致性",
        score=round(score, 4),
        passed=score >= 0.6,
        threshold=0.6,
        details={
            "risk_levels": risk_levels,
            "distribution": dict(counter),
            "majority": majority_level,
        },
        message=f"{runs} 次运行中 {majority_count} 次为「{majority_level}」",
    )
