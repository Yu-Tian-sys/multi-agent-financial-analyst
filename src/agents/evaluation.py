"""
评估节点：流水线完成后自动运行五维度评估

在 compliance 之后、memory_save 之前执行。
评估结果存入 state.evaluation_result，供前端展示和后续分析。
"""

import logging
from typing import Dict, List

from src.state import FinanceState
from src.config import settings
from src.evaluation import (
    evaluate_financial_accuracy,
    evaluate_risk_consistency,
    evaluate_report_completeness,
    evaluate_analyst_consensus,
    evaluate_debate_quality,
)

logger = logging.getLogger(__name__)


# 投资立场关键词（用于从报告中提取 agent_stance）
STANCE_KEYWORDS = [
    ("买入", ["买入", "强烈推荐", "看多", "增持"]),
    ("增持", ["增持", "推荐", "谨慎乐观"]),
    ("中性", ["中性", "持有", "观望", "区间操作"]),
    ("减持", ["减持", "谨慎", "看空"]),
    ("卖出", ["卖出", "强烈卖出", "回避"]),
]


def _extract_stance(report: str) -> str:
    """从最终报告中提取 Agent 投资立场"""
    if not report:
        return "中性"
    for stance, keywords in STANCE_KEYWORDS:
        if any(kw in report for kw in keywords):
            return stance
    return "中性"


def evaluation_node(state: FinanceState) -> dict:
    """
    五维度评估节点

    在报告生成并通过合规审查后运行，评估 Agent 输出质量。
    评估失败不影响流水线主流程（try/except 兜底）。

    Args:
        state: 当前状态（含 final_report、debate_records、financial_data 等）

    Returns:
        要更新的字段（evaluation_result）
    """
    # 全局开关：可通过 .env ENABLE_EVALUATION=false 关闭
    if not settings.enable_evaluation:
        logger.info("[eval] 评估已关闭（enable_evaluation=False）")
        return {"evaluation_result": {}}

    # 合规未通过则跳过评估
    compliance = state.get("compliance_result", {})
    if not compliance.get("passed", False):
        logger.info("[eval] 合规未通过，跳过评估")
        return {"evaluation_result": {}}

    symbol = state.get("symbol") or state.get("topic", "")
    if not symbol:
        return {"evaluation_result": {}}

    logger.info(f"[eval] 开始五维度评估：{symbol}")

    results: List[Dict] = []
    total_tokens = state.get("total_tokens", 0)
    total_cost = state.get("total_cost", 0.0)

    # 1. 财务指标准确率（需 LLM 提取报告中的数字）
    try:
        r = evaluate_financial_accuracy(symbol)
        results.append(_result_to_dict(r))
        logger.info(f"[eval] 财务准确率: {r.score}")
    except Exception as e:
        logger.error(f"[eval] 财务准确率评估失败: {e}")
        results.append({"name": "财务指标准确率", "score": 0.0, "passed": False, "message": str(e)})

    # 2. 风险评级一致性（多次运行 risk_node 检查稳定性）
    try:
        r = evaluate_risk_consistency(symbol, runs=3)
        results.append(_result_to_dict(r))
        logger.info(f"[eval] 风险一致性: {r.score}")
    except Exception as e:
        logger.error(f"[eval] 风险一致性评估失败: {e}")
        results.append({"name": "风险评级一致性", "score": 0.0, "passed": False, "message": str(e)})

    # 3. 报告完整性（检查章节、引用、数据支撑）
    try:
        report = state.get("final_report", "") or state.get("draft_report", "")
        r = evaluate_report_completeness(report)
        results.append(_result_to_dict(r))
        logger.info(f"[eval] 报告完整性: {r.score}")
    except Exception as e:
        logger.error(f"[eval] 报告完整性评估失败: {e}")
        results.append({"name": "报告完整性", "score": 0.0, "passed": False, "message": str(e)})

    # 4. 分析师共识对比（Agent 立场 vs 市场分析师一致评级）
    try:
        report = state.get("final_report", "") or state.get("draft_report", "")
        stance = _extract_stance(report)
        r = evaluate_analyst_consensus(symbol, agent_stance=stance)
        results.append(_result_to_dict(r))
        logger.info(f"[eval] 分析师共识: {r.score} (立场={stance})")
    except Exception as e:
        logger.error(f"[eval] 分析师共识评估失败: {e}")
        results.append({"name": "分析师共识对比", "score": 0.0, "passed": False, "message": str(e)})

    # 5. 辩论质量（LLM-as-judge 评审多空辩论）
    try:
        debate_records = state.get("debate_records", [])
        r = evaluate_debate_quality(debate_records)
        results.append(_result_to_dict(r))
        logger.info(f"[eval] 辩论质量: {r.score}")
    except Exception as e:
        logger.error(f"[eval] 辩论质量评估失败: {e}")
        results.append({"name": "辩论质量", "score": 0.0, "passed": False, "message": str(e)})

    # 计算综合得分
    scores = [r["score"] for r in results]
    overall_score = sum(scores) / len(scores) if scores else 0.0
    all_passed = all(r["passed"] for r in results)

    evaluation_result = {
        "symbol": symbol,
        "overall_score": round(overall_score, 4),
        "all_passed": all_passed,
        "dimensions": results,
    }

    logger.info(f"[eval] 评估完成：{symbol} 综合得分 {overall_score:.2f}，{'通过' if all_passed else '未通过'}")

    return {
        "evaluation_result": evaluation_result,
        "messages": [
            {"role": "system", "content": f"五维度评估完成：综合得分 {overall_score:.2f}，{'全部通过' if all_passed else '部分未通过'}"}
        ],
    }


def _result_to_dict(r) -> Dict:
    """把 EvaluationResult 转成可序列化 dict"""
    return {
        "name": r.name,
        "score": r.score,
        "passed": r.passed,
        "message": r.message,
        "details": r.details or {},
    }
