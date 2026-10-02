"""
评估层统一入口

用法：
    python -m src.evaluation.evaluate --tickers 600519,AAPL,00700.HK
    python -m src.evaluation.evaluate --tickers 600519 --output report.md
"""

import logging
import json
import argparse
from datetime import datetime
from typing import List

from .base import StockEvaluation, EvaluationResult
from .financial_accuracy import evaluate_financial_accuracy
from .risk_consistency import evaluate_risk_consistency
from .report_completeness import evaluate_report_completeness
from .analyst_consensus import evaluate_analyst_consensus
from .debate_quality import evaluate_debate_quality
from src.data import get_provider

logger = logging.getLogger(__name__)


# 默认评估数据集（8 只蓝筹股）
DEFAULT_TICKERS = [
    "600519",   # 贵州茅台
    "600036",   # 招商银行
    "300750",   # 宁德时代
    "AAPL",     # 苹果
    "MSFT",     # 微软
    "GOOGL",    # 谷歌
    "00700.HK",  # 腾讯
    "3690.HK",  # 美团
]


def evaluate_stock(symbol: str) -> StockEvaluation:
    """
    对单只股票运行全部 5 个评估维度

    注意：财务准确率、风险一致性、分析师共识可以独立运行；
    报告完整性和辩论质量需要先运行完整流水线获取报告和辩论记录。
    这里先实现可独立运行的 3 个维度，报告完整性和辩论质量在流水线运行后补充。
    """
    provider = get_provider(symbol)
    market = provider.market if provider else "未知"
    stock_eval = StockEvaluation(symbol=symbol, market=market)

    logger.info(f"[eval] 开始评估 {symbol}（{market}）")

    # 1. 财务指标准确率
    try:
        r = evaluate_financial_accuracy(symbol)
        stock_eval.results.append(r)
        logger.info(f"[eval] {symbol} 财务准确率: {r.score}")
    except Exception as e:
        logger.error(f"[eval] {symbol} 财务准确率评估失败: {e}")
        stock_eval.results.append(EvaluationResult(
            name="财务指标准确率", score=0, passed=False, message=str(e)
        ))

    # 2. 风险评级一致性
    try:
        r = evaluate_risk_consistency(symbol, runs=3)
        stock_eval.results.append(r)
        logger.info(f"[eval] {symbol} 风险一致性: {r.score}")
    except Exception as e:
        logger.error(f"[eval] {symbol} 风险一致性评估失败: {e}")
        stock_eval.results.append(EvaluationResult(
            name="风险评级一致性", score=0, passed=False, message=str(e)
        ))

    # 3. 分析师共识对比（需要先有 Agent 立场，这里用中性占位）
    try:
        r = evaluate_analyst_consensus(symbol, agent_stance="中性")
        stock_eval.results.append(r)
        logger.info(f"[eval] {symbol} 分析师共识: {r.score}")
    except Exception as e:
        logger.error(f"[eval] {symbol} 分析师共识评估失败: {e}")
        stock_eval.results.append(EvaluationResult(
            name="分析师共识对比", score=0, passed=False, message=str(e)
        ))

    # 注：报告完整性、辩论质量需要运行完整流水线后传入结果
    # 这里先占位，等流水线集成后补充
    stock_eval.results.append(EvaluationResult(
        name="报告完整性", score=0.5, passed=True, message="需运行完整流水线后评估"
    ))
    stock_eval.results.append(EvaluationResult(
        name="辩论质量", score=0.5, passed=True, message="需运行完整流水线后评估"
    ))

    return stock_eval


def evaluate_batch(tickers: List[str]) -> List[StockEvaluation]:
    """批量评估多只股票"""
    results = []
    for symbol in tickers:
        try:
            se = evaluate_stock(symbol)
            results.append(se)
        except Exception as e:
            logger.error(f"[eval] {symbol} 评估失败: {e}")
    return results


def generate_markdown_report(evaluations: List[StockEvaluation]) -> str:
    """生成 Markdown 格式的评估报告"""
    lines = []
    lines.append(f"# Agent 评估报告")
    lines.append(f"")
    lines.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"评估标的数：{len(evaluations)}")
    lines.append(f"")

    # 汇总表
    lines.append("## 汇总")
    lines.append("")
    lines.append("| 标的 | 市场 | 综合得分 | 财务准确率 | 风险一致性 | 分析师共识 | 状态 |")
    lines.append("|------|------|---------|-----------|-----------|-----------|------|")
    for se in evaluations:
        fin = next((r for r in se.results if r.name == "财务指标准确率"), None)
        risk = next((r for r in se.results if r.name == "风险评级一致性"), None)
        cons = next((r for r in se.results if r.name == "分析师共识对比"), None)
        status = "✅" if se.all_passed else "❌"
        fin_s = f"{fin.score:.2f}" if fin else "-"
        risk_s = f"{risk.score:.2f}" if risk else "-"
        cons_s = f"{cons.score:.2f}" if cons else "-"
        lines.append(
            f"| {se.symbol} | {se.market} | {se.overall_score:.2f} | "
            f"{fin_s} | {risk_s} | {cons_s} | {status} |"
        )

    # 各标的详情
    lines.append("")
    lines.append("## 详情")
    for se in evaluations:
        lines.append("")
        lines.append(f"### {se.symbol}（{se.market}）")
        lines.append(f"")
        lines.append(f"**综合得分：{se.overall_score:.2f}** {'✅ 通过' if se.all_passed else '❌ 未通过'}")
        lines.append("")
        for r in se.results:
            icon = "✅" if r.passed else "❌"
            lines.append(f"- **{r.name}**：{r.score:.2f} {icon} — {r.message}")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="金融 Agent 评估工具")
    parser.add_argument(
        "--tickers",
        type=str,
        default=",".join(DEFAULT_TICKERS),
        help="股票代码列表，逗号分隔",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="",
        help="输出 Markdown 报告路径（不指定则打印到终端）",
    )
    args = parser.parse_args()

    tickers = [t.strip() for t in args.tickers.split(",") if t.strip()]
    logging.basicConfig(level=logging.INFO)

    evaluations = evaluate_batch(tickers)
    report = generate_markdown_report(evaluations)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"评估报告已保存到：{args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
