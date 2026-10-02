import logging
import re
from typing import Dict

from src.state import FinanceState
from src.tools.pdf_parser import parse_pdf, extract_financial_metrics
from src.tools.calculator import calculate_ratio
from src.data import get_provider

logger = logging.getLogger(__name__)


def _safe_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_metrics_to_numbers(metrics: Dict) -> Dict:
    """把指标字符串转成数字（去掉单位）"""
    result = {}
    for key, value in metrics.items():
        if not isinstance(value, str):
            result[key] = value
            continue
        match = re.search(r"([0-9,.]+)", value)
        if match:
            num_str = match.group(1).replace(",", "")
            try:
                result[key] = float(num_str)
            except ValueError:
                result[key] = 0.0
        else:
            result[key] = 0.0
    return result


def financial_analyst_node(state: FinanceState) -> dict:
    """
    财报分析 Agent（LangGraph 节点）

    混合模式：
    - 生产路径：从 Provider 获取结构化财报数据，直接提取指标
    - 文本路径：同时获取财报文本，供报告撰写和评估使用

    Args:
        state: 当前状态

    Returns:
        要更新的字段
    """
    topic = state["topic"]
    symbol = state.get("symbol") or topic
    logger.info(f"[financial] 开始分析财报：{topic}（代码：{symbol}）")

    try:
        provider = get_provider(symbol)

        # 解析公司简称（供报告标题使用）
        company_name = topic
        if provider is not None:
            try:
                company_name = provider.get_company_name(symbol) or topic
            except Exception:
                company_name = topic

        if provider is not None:
            # ===== 生产路径：结构化数据 =====
            financials = provider.get_financials(symbol)
            latest = financials.latest
            bs_latest = financials.balance_sheet[0] if financials.balance_sheet else None

            if latest is not None:
                # 从利润表提取指标
                raw_metrics = {}
                if latest.revenue is not None:
                    raw_metrics["revenue"] = str(latest.revenue)
                if latest.net_income is not None:
                    raw_metrics["profit"] = str(latest.net_income)
                if latest.gross_profit is not None:
                    raw_metrics["gross_profit"] = str(latest.gross_profit)
                if latest.operating_income is not None:
                    raw_metrics["operating_income"] = str(latest.operating_income)

                # 从资产负债表提取指标
                if bs_latest is not None:
                    if bs_latest.total_assets is not None:
                        raw_metrics["total_assets"] = str(bs_latest.total_assets)
                    if bs_latest.total_liabilities is not None:
                        raw_metrics["debt"] = str(bs_latest.total_liabilities)
                    if bs_latest.total_equity is not None:
                        raw_metrics["equity"] = str(bs_latest.total_equity)

                # 从现金流量表提取
                cf_latest = financials.cashflow[0] if financials.cashflow else None
                if cf_latest is not None and cf_latest.operating_cashflow is not None:
                    raw_metrics["operating_cashflow"] = str(cf_latest.operating_cashflow)

                # 财报文本（供报告和评估使用）
                financial_text = provider.get_financial_text(symbol)
                source = f"{provider.market}:{latest.period}"
            else:
                # Provider 无数据，降级用文本提取
                raw_metrics, financial_text, source = _load_via_text(symbol)
        else:
            # 无法识别市场，降级用文本提取
            raw_metrics, financial_text, source = _load_via_text(symbol)

        # 转成数字
        metrics = _parse_metrics_to_numbers(raw_metrics)

        # 计算比率
        ratios = {}
        net_margin = calculate_ratio(metrics, "net_margin")
        if net_margin is not None:
            ratios["net_margin"] = round(net_margin, 4)

        roe = calculate_ratio(metrics, "roe")
        if roe is not None:
            ratios["roe"] = round(roe, 4)

        debt_ratio = calculate_ratio(metrics, "debt_ratio")
        if debt_ratio is not None:
            ratios["debt_ratio"] = round(debt_ratio, 4)

        # 组装结果
        financial_data = {
            "source": source,
            "raw_metrics": raw_metrics,
            "metrics": metrics,
            "ratios": ratios,
            "financial_text": financial_text,  # 供评估路径使用
        }

        logger.info(f"[financial] 分析完成：{len(metrics)} 个指标，{len(ratios)} 个比率，来源 {source}")

        return {
            "company_name": company_name,
            "financial_data": financial_data,
            "current_step": state.get("current_step", 0) + 1,
            "status": "running",
            "messages": [
                {"role": "system", "content": f"财报分析完成：{len(metrics)} 个指标，来源 {source}"}
            ]
        }

    except Exception as e:
        logger.error(f"[financial] 分析失败：{e}")
        return {
            "company_name": company_name,
            "status": "failed",
            "error": f"财报分析失败：{e}",
            "messages": [{"role": "system", "content": f"财报分析失败：{e}"}]
        }


def _load_via_text(topic: str) -> tuple:
    """
    降级路径：从 PDF 或 Mock 文本提取指标

    Returns:
        (raw_metrics, financial_text, source)
    """
    import os
    # 尝试找真实 PDF
    pdf_dir = "./data"
    if os.path.exists(pdf_dir):
        for filename in os.listdir(pdf_dir):
            if topic.upper() in filename.upper() and filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(pdf_dir, filename)
                ok, text = parse_pdf(pdf_path)
                if ok:
                    logger.info(f"[financial] 解析真实 PDF：{pdf_path}")
                    metrics = extract_financial_metrics(text)
                    return metrics, text, f"PDF:{filename}"

    # 最终降级：用 Provider 的文本生成（如果有 Provider）或空文本
    provider = get_provider(topic)
    if provider is not None:
        text = provider.get_financial_text(topic)
        metrics = extract_financial_metrics(text)
        return metrics, text, f"{provider.market}:text"

    return {}, "暂无财报数据", "none"


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    from src.state import create_initial_state

    state = create_initial_state("t1", "u1", "user", "AAPL")
    result = financial_analyst_node(state)
    print("状态:", result["status"])
    if "financial_data" in result:
        fd = result["financial_data"]
        print("来源:", fd["source"])
        print("指标:", fd["metrics"])
        print("比率:", fd["ratios"])
