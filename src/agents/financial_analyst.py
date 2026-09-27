import logging
import os
from typing import Dict

from src.state import FinanceState
from src.tools.pdf_parser import parse_pdf, extract_financial_metrics
from src.tools.calculator import calculate_ratio

logger = logging.getLogger(__name__)


# ========================================
# Mock 财报文本（当没有真实 PDF 时使用）
# ========================================
MOCK_FINANCIAL_TEXT = {
    "AAPL": """
苹果公司 2024 年年度报告

营业收入：3832亿美元，同比增长 2%
净利润：970亿美元，同比增长 5%
负债总额：2900亿美元
净资产：620亿美元
总资产：3520亿美元
毛利率：46%
ROE：15.6%
研发投入：300亿美元
    """,
    "TSLA": """
特斯拉 2024 年年度报告

营业收入：967亿美元，同比增长 19%
净利润：150亿美元，同比增长 12%
负债总额：430亿美元
净资产：620亿美元
总资产：1050亿美元
毛利率：18%
ROE：24.2%
研发投入：45亿美元
    """,
    "default": """
公司年度报告

营业收入：100亿美元，同比增长 8%
净利润：15亿美元，同比增长 10%
负债总额：40亿美元
净资产：60亿美元
总资产：100亿美元
毛利率：30%
ROE：25%
研发投入：5亿美元
    """,
}


def _load_financial_text(topic: str) -> tuple:
    """
    加载财报文本

    优先从 data/ 目录找真实 PDF；找不到就用 mock 文本。

    Args:
        topic: 公司代码或名称

    Returns:
        (财报文本, 来源说明)
    """
    # 1. 尝试找真实 PDF
    pdf_dir = "./data"
    if os.path.exists(pdf_dir):
        for filename in os.listdir(pdf_dir):
            if topic.upper() in filename.upper() and filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(pdf_dir, filename)
                ok, text = parse_pdf(pdf_path)
                if ok:
                    logger.info(f"[financial] 解析真实 PDF：{pdf_path}")
                    return text, f"PDF:{filename}"
                else:
                    logger.warning(f"[financial] PDF 解析失败：{text}")

    # 2. 降级用 mock
    key = topic.upper() if topic.upper() in MOCK_FINANCIAL_TEXT else "default"
    logger.info(f"[financial] 使用 mock 财报文本：{key}")
    return MOCK_FINANCIAL_TEXT[key], f"mock:{key}"


def _parse_metrics_to_numbers(metrics: Dict) -> Dict:
    """
    把指标字符串转成数字（去掉单位）

    Args:
        metrics: 原始指标，如 {"revenue": "3832亿", "profit": "970亿"}

    Returns:
        数字指标，如 {"revenue": 3832.0, "profit": 970.0}
    """
    import re
    result = {}
    for key, value in metrics.items():
        if not isinstance(value, str):
            result[key] = value
            continue
        # 提取数字
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

    流程：
    1. 加载财报文本（真实 PDF 或 mock）
    2. 提取财务指标
    3. 计算财务比率（净利率、ROE、资产负债率）
    4. 写入 state.financial_data

    Args:
        state: 当前状态

    Returns:
        要更新的字段
    """
    topic = state["topic"]
    logger.info(f"[financial] 开始分析财报：{topic}")

    try:
        # 1. 加载文本
        text, source = _load_financial_text(topic)

        # 2. 提取指标
        raw_metrics = extract_financial_metrics(text)
        logger.info(f"[financial] 提取指标：{raw_metrics}")

        # 3. 转成数字
        metrics = _parse_metrics_to_numbers(raw_metrics)

        # 4. 计算比率
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

        # 5. 组装结果
        financial_data = {
            "source": source,
            "raw_metrics": raw_metrics,
            "metrics": metrics,
            "ratios": ratios,
        }

        logger.info(f"[financial] 分析完成：{len(metrics)} 个指标，{len(ratios)} 个比率")

        return {
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
            "status": "failed",
            "error": f"财报分析失败：{e}",
            "messages": [{"role": "system", "content": f"财报分析失败：{e}"}]
        }


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    from src.state import create_initial_state

    state = create_initial_state("t1", "u1", "user", "AAPL")
    result = financial_analyst_node(state)
    print("状态:", result["status"])
    print("来源:", result["financial_data"]["source"])
    print("指标:", result["financial_data"]["metrics"])
    print("比率:", result["financial_data"]["ratios"])
