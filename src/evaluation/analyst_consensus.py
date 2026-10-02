"""
分析师共识对比评估

将 Agent 的投资立场（看多/看空/中性）与市场分析师共识对比。
同时检查目标价偏差。
"""

import logging
from typing import List, Optional, Dict
from collections import Counter

from .base import EvaluationResult
from src.data import get_provider

logger = logging.getLogger(__name__)

# 评级映射到数值
RATING_SCORE = {
    "买入": 1.0,
    "增持": 0.75,
    "强烈推荐": 1.0,
    "推荐": 0.75,
    "中性": 0.5,
    "持有": 0.5,
    "减持": 0.25,
    "卖出": 0.0,
    "回避": 0.0,
}

STANCE_SCORE = {
    "看多": 1.0,
    "看空": 0.0,
    "中性": 0.5,
}


def evaluate_analyst_consensus(
    symbol: str,
    agent_stance: str,
    agent_target_price: Optional[float] = None,
) -> EvaluationResult:
    """
    评估 Agent 立场与分析师共识的一致性

    Args:
        symbol: 股票代码
        agent_stance: Agent 的立场（看多/看空/中性）
        agent_target_price: Agent 给出的目标价（可选）

    Returns:
        EvaluationResult
    """
    provider = get_provider(symbol)
    if provider is None:
        return EvaluationResult(
            name="分析师共识对比",
            score=0.0,
            passed=False,
            message=f"无法识别市场：{symbol}",
        )

    ratings = provider.get_analyst_ratings(symbol)
    if not ratings:
        return EvaluationResult(
            name="分析师共识对比",
            score=0.5,
            passed=True,
            message="无分析师评级数据，跳过对比",
        )

    # 1. 计算分析师共识（平均评级分数）
    scores = []
    target_prices = []
    for r in ratings:
        if r.rating in RATING_SCORE:
            scores.append(RATING_SCORE[r.rating])
        if r.target_price is not None:
            target_prices.append(r.target_price)

    if not scores:
        return EvaluationResult(
            name="分析师共识对比",
            score=0.5,
            passed=True,
            message="分析师评级无法解析",
        )

    consensus_score = sum(scores) / len(scores)
    consensus_stance = _score_to_stance(consensus_score)

    # 2. Agent 立场得分
    agent_score = STANCE_SCORE.get(agent_stance, 0.5)

    # 3. 计算一致性（偏差越小越好）
    stance_deviation = abs(agent_score - consensus_score)
    stance_score = 1.0 - stance_deviation  # 偏差 0 → 1.0，偏差 1 → 0.0

    # 4. 目标价偏差（如果有）
    target_score = 1.0
    target_deviation = None
    if agent_target_price is not None and target_prices:
        avg_target = sum(target_prices) / len(target_prices)
        if avg_target > 0:
            target_deviation = abs(agent_target_price - avg_target) / avg_target
            target_score = max(0, 1.0 - target_deviation * 2)  # 偏差 50% 以内给分

    # 综合得分（立场 70%，目标价 30%）
    score = stance_score * 0.7 + target_score * 0.3

    # 评级分布
    rating_dist = Counter(r.rating for r in ratings if r.rating)

    return EvaluationResult(
        name="分析师共识对比",
        score=round(score, 4),
        passed=score >= 0.5,
        threshold=0.5,
        details={
            "agent_stance": agent_stance,
            "consensus_stance": consensus_stance,
            "consensus_score": round(consensus_score, 4),
            "rating_distribution": dict(rating_dist),
            "analyst_count": len(ratings),
            "avg_target_price": round(sum(target_prices) / len(target_prices), 2) if target_prices else None,
            "agent_target_price": agent_target_price,
            "target_deviation": round(target_deviation, 4) if target_deviation else None,
        },
        message=f"Agent「{agent_stance}」 vs 共识「{consensus_stance}」，分析师 {len(ratings)} 家",
    )


def _score_to_stance(score: float) -> str:
    if score >= 0.75:
        return "看多"
    elif score <= 0.25:
        return "看空"
    else:
        return "中性"
