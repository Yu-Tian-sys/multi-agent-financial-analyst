"""
报告结构完整性评估

检查最终报告是否包含所有必需章节、引用是否齐全。
"""

import logging
import re
from typing import List

from .base import EvaluationResult

logger = logging.getLogger(__name__)


# 必需章节（关键词匹配）
REQUIRED_SECTIONS = [
    ("公司概况", ["公司概况", "公司简介", "基本情况"]),
    ("财务分析", ["财务分析", "财务数据", "经营情况"]),
    ("多空观点", ["多空", "多头", "空头", "看多", "看空"]),
    ("风险提示", ["风险", "风险提示", "风险因素"]),
    ("结论", ["结论", "总结", "投资建议", "综合判断"]),
]

# 引用检查
CITATION_PATTERNS = [
    r"来源[：:]",
    r"引用[：:]",
    r"参考[：:]",
    r"\[来源\]",
    r"data-source",
]


def evaluate_report_completeness(report: str) -> EvaluationResult:
    """
    评估报告结构完整性

    Args:
        report: 最终报告文本

    Returns:
        EvaluationResult
    """
    if not report or len(report.strip()) < 100:
        return EvaluationResult(
            name="报告完整性",
            score=0.0,
            passed=False,
            message="报告为空或过短",
        )

    # 1. 检查必需章节
    section_results = {}
    section_score = 0
    for section_name, keywords in REQUIRED_SECTIONS:
        found = any(kw in report for kw in keywords)
        section_results[section_name] = found
        if found:
            section_score += 1

    # 2. 检查引用
    has_citation = any(re.search(p, report) for p in CITATION_PATTERNS)

    # 3. 检查是否有数据支撑（数字）
    numbers = re.findall(r"\d+\.?\d*%", report) + re.findall(r"\d+\.?\d*(?:亿|万|倍)", report)
    has_data = len(numbers) >= 3

    # 计算得分（章节占 70%，引用占 15%，数据支撑占 15%）
    section_ratio = section_score / len(REQUIRED_SECTIONS)
    score = section_ratio * 0.7 + (0.15 if has_citation else 0) + (0.15 if has_data else 0)

    return EvaluationResult(
        name="报告完整性",
        score=round(score, 4),
        passed=score >= 0.6,
        threshold=0.6,
        details={
            "sections": section_results,
            "sections_found": section_score,
            "sections_total": len(REQUIRED_SECTIONS),
            "has_citation": has_citation,
            "has_data_support": has_data,
            "number_count": len(numbers),
        },
        message=f"{section_score}/{len(REQUIRED_SECTIONS)} 章节齐全，引用={'有' if has_citation else '无'}，数据支撑={'有' if has_data else '无'}",
    )
