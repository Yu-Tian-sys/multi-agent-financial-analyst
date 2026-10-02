"""
财务指标提取准确率评估

评估方式：
1. 从 Provider 获取财报文本（非结构化）
2. 让 LLM 从文本中提取关键指标
3. 与结构化 ground truth 对比
4. 计算各指标的误差率和整体准确率
"""

import logging
import json
import re
from typing import Dict

from .base import EvaluationResult
from src.data import get_provider

logger = logging.getLogger(__name__)


# 需要评估的指标列表
METRICS_TO_CHECK = [
    ("revenue", "营业收入"),
    ("profit", "净利润"),
    ("total_assets", "总资产"),
    ("debt", "总负债"),
    ("equity", "净资产"),
]

EXTRACT_PROMPT = """你是一个财务数据提取助手。请从以下财报文本中提取关键财务指标。

【财报文本】
{text}

请提取以下指标（只输出数字，不要单位）：
1. 营业收入
2. 净利润
3. 总资产
4. 总负债
5. 净资产

输出 JSON 格式：
{{
    "营业收入": 数字,
    "净利润": 数字,
    "总资产": 数字,
    "总负债": 数字,
    "净资产": 数字
}}

如果某个指标在文本中找不到，填 null。只输出 JSON，不要其他内容。"""


def evaluate_financial_accuracy(symbol: str, tolerance: float = 0.05) -> EvaluationResult:
    """
    评估财务指标提取准确率

    Args:
        symbol: 股票代码
        tolerance: 允许的相对误差（默认 5%）

    Returns:
        EvaluationResult
    """
    provider = get_provider(symbol)
    if provider is None:
        return EvaluationResult(
            name="财务指标准确率",
            score=0.0,
            passed=False,
            message=f"无法识别市场：{symbol}",
        )

    # 1. 获取 ground truth（结构化数据）
    financials = provider.get_financials(symbol)
    bs = financials.balance_sheet[0] if financials.balance_sheet else None
    inc = financials.latest

    if inc is None:
        return EvaluationResult(
            name="财务指标准确率",
            score=0.0,
            passed=False,
            message="无法获取财报数据",
        )

    ground_truth = {
        "营业收入": inc.revenue,
        "净利润": inc.net_income,
        "总资产": bs.total_assets if bs else None,
        "总负债": bs.total_liabilities if bs else None,
        "净资产": bs.total_equity if bs else None,
    }

    # 2. 获取财报文本
    text = provider.get_financial_text(symbol)

    # 3. 让 LLM 提取指标
    import src.optimization.model_router as router_module
    try:
        prompt = EXTRACT_PROMPT.format(text=text[:3000])  # 限制长度
        content, tokens, cost = router_module.call_llm(prompt, tier="cheap", temperature=0.0)
        # 解析 JSON
        extracted = _parse_json(content)
    except Exception as e:
        logger.error(f"[eval] LLM 提取失败：{e}")
        return EvaluationResult(
            name="财务指标准确率",
            score=0.0,
            passed=False,
            message=f"LLM 提取失败：{e}",
        )

    # 4. 对比计算准确率
    metric_scores = {}
    correct_count = 0
    total_count = 0

    for key, label in METRICS_TO_CHECK:
        gt = ground_truth.get(label)
        pred = extracted.get(label)
        total_count += 1

        if gt is None or pred is None:
            metric_scores[label] = {"ground_truth": gt, "predicted": pred, "match": False, "reason": "数据缺失"}
            continue

        # 相对误差
        if gt == 0:
            match = abs(pred) < tolerance
        else:
            rel_error = abs(pred - gt) / abs(gt)
            match = rel_error <= tolerance

        metric_scores[label] = {
            "ground_truth": gt,
            "predicted": pred,
            "relative_error": round(abs(pred - gt) / abs(gt), 4) if gt else None,
            "match": match,
        }
        if match:
            correct_count += 1

    score = correct_count / total_count if total_count > 0 else 0.0

    return EvaluationResult(
        name="财务指标准确率",
        score=round(score, 4),
        passed=score >= 0.6,
        threshold=0.6,
        details={
            "metrics": metric_scores,
            "correct": correct_count,
            "total": total_count,
        },
        message=f"{correct_count}/{total_count} 个指标误差在 {tolerance*100:.0f}% 以内",
    )


def _parse_json(text: str) -> Dict:
    """从 LLM 输出中解析 JSON"""
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 尝试提取 JSON 部分
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}
