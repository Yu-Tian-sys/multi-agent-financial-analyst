"""
评估层 —— 量化金融 Agent 的分析质量

五个评估维度：
1. 财务指标提取准确率（FinancialAccuracy）
2. 风险评级一致性（RiskConsistency）
3. 报告结构完整性（ReportCompleteness）
4. 分析师共识对比（AnalystConsensus）
5. 辩论质量（DebateQuality，LLM-as-judge）
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EvaluationResult:
    """单个评估维度的结果"""
    name: str                       # 评估维度名称
    score: float                    # 得分 0-1
    passed: bool                    # 是否通过（score >= threshold）
    threshold: float = 0.6          # 通过阈值
    details: Dict = field(default_factory=dict)  # 详细数据
    message: str = ""               # 说明文字


@dataclass
class StockEvaluation:
    """单只股票的完整评估结果"""
    symbol: str
    market: str
    results: List[EvaluationResult] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        """综合得分（各维度加权平均）"""
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)
