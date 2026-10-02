"""
辩论质量评估（LLM-as-judge）

用独立的 LLM 实例对多空辩论记录打分。
评分维度：
1. 数据支撑（论据是否有具体数字/事实）
2. 反驳质量（是否针对对方观点回应）
3. 无重复（论据是否有新意）
"""

import logging
import json
import re
from typing import List, Dict

from .base import EvaluationResult

logger = logging.getLogger(__name__)


JUDGE_PROMPT = """你是一个金融辩论评审专家。请评估以下多空辩论记录的质量。

【辩论记录】
{debate}

请从以下三个维度打分（每项 0-10 分）：

1. 数据支撑：论据是否有具体数字、事实、来源支撑？
2. 反驳质量：双方是否针对对方的观点进行有效反驳，而非自说自话？
3. 论据多样性：多空双方的论据是否有新意，没有大量重复？

输出 JSON 格式：
{{
    "数据支撑": 分数,
    "反驳质量": 分数,
    "论据多样性": 分数,
    "总评": "一句话总结"
}}

只输出 JSON，不要其他内容。"""


def evaluate_debate_quality(debate_records: List[Dict]) -> EvaluationResult:
    """
    评估辩论质量（LLM-as-judge）

    Args:
        debate_records: 辩论记录列表，每项 {round, side, content}

    Returns:
        EvaluationResult
    """
    if not debate_records:
        return EvaluationResult(
            name="辩论质量",
            score=0.0,
            passed=False,
            message="无辩论记录",
        )

    # 格式化辩论记录
    debate_text = ""
    for r in debate_records:
        side = "多头" if r.get("side") == "bull" else ("空头" if r.get("side") == "bear" else "主持人")
        debate_text += f"[{side}] {r.get('content', '')}\n\n"

    # 调用 LLM 评审
    import src.optimization.model_router as router_module
    try:
        prompt = JUDGE_PROMPT.format(debate=debate_text[:4000])
        content, tokens, cost = router_module.call_llm(prompt, tier="cheap", temperature=0.0)
        scores = _parse_judge_scores(content)
    except Exception as e:
        logger.error(f"[eval] 辩论质量评审失败：{e}")
        return EvaluationResult(
            name="辩论质量",
            score=0.0,
            passed=False,
            message=f"LLM 评审失败：{e}",
        )

    if not scores:
        return EvaluationResult(
            name="辩论质量",
            score=0.0,
            passed=False,
            message="无法解析评审结果",
        )

    # 计算综合得分（0-1 归一化）
    data_score = scores.get("数据支撑", 0) / 10
    rebuttal_score = scores.get("反驳质量", 0) / 10
    diversity_score = scores.get("论据多样性", 0) / 10

    overall = (data_score + rebuttal_score + diversity_score) / 3

    return EvaluationResult(
        name="辩论质量",
        score=round(overall, 4),
        passed=overall >= 0.6,
        threshold=0.6,
        details={
            "数据支撑": scores.get("数据支撑"),
            "反驳质量": scores.get("反驳质量"),
            "论据多样性": scores.get("论据多样性"),
            "总评": scores.get("总评", ""),
        },
        message=f"数据 {scores.get('数据支撑')}/10，反驳 {scores.get('反驳质量')}/10，多样性 {scores.get('论据多样性')}/10",
    )


def _parse_judge_scores(text: str) -> Dict:
    """解析 LLM 评审结果"""
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}
