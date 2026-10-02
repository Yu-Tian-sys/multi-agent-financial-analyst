"""
评估层

量化金融 Agent 的分析质量，五个维度：
1. 财务指标准确率
2. 风险评级一致性
3. 报告完整性
4. 分析师共识对比
5. 辩论质量（LLM-as-judge）
"""

from .base import EvaluationResult, StockEvaluation
from .financial_accuracy import evaluate_financial_accuracy
from .risk_consistency import evaluate_risk_consistency
from .report_completeness import evaluate_report_completeness
from .analyst_consensus import evaluate_analyst_consensus
from .debate_quality import evaluate_debate_quality
from .evaluate import evaluate_stock, evaluate_batch, generate_markdown_report, DEFAULT_TICKERS

__all__ = [
    "EvaluationResult",
    "StockEvaluation",
    "evaluate_financial_accuracy",
    "evaluate_risk_consistency",
    "evaluate_report_completeness",
    "evaluate_analyst_consensus",
    "evaluate_debate_quality",
    "evaluate_stock",
    "evaluate_batch",
    "generate_markdown_report",
    "DEFAULT_TICKERS",
]
