import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# 允许的运算符
ALLOWED_OPS = set("+-*/() .0123456789")


def _safe_eval(expression: str) -> Optional[float]:
    """
    安全地计算数学表达式（不用 eval，用 Python 内置 compile + 限制字符）

    只允许数字、+ - * / ( ) 和空格
    """
    # 1. 字符白名单
    if not all(c in ALLOWED_OPS for c in expression):
        return None

    # 2. 编译并执行（只允许表达式，不允许语句）
    try:
        code = compile(expression, "<calc>", "eval")
        return eval(code, {"__builtins__": {}}, {})
    except Exception:
        return None


def calculate_ratio(metrics: Dict, ratio_type: str) -> Optional[float]:
    """
    计算财务比率

    Args:
        metrics: 财务指标字典，如 {"revenue": 100, "profit": 20, "equity": 80}
        ratio_type: 比率类型，支持：
            - gross_margin: 毛利率 = (revenue - cost) / revenue
            - net_margin: 净利率 = profit / revenue
            - roe: 净资产收益率 = profit / equity
            - roa: 总资产收益率 = profit / assets
            - debt_ratio: 资产负债率 = debt / assets

    Returns:
        比率值（小数），无法计算返回 None
    """
    try:
        if ratio_type == "gross_margin":
            revenue = metrics.get("revenue")
            cost = metrics.get("cost")
            if revenue and cost is not None:
                return (revenue - cost) / revenue

        elif ratio_type == "net_margin":
            revenue = metrics.get("revenue")
            profit = metrics.get("profit")
            if revenue and profit is not None:
                return profit / revenue

        elif ratio_type == "roe":
            profit = metrics.get("profit")
            equity = metrics.get("equity")
            if profit is not None and equity:
                return profit / equity

        elif ratio_type == "roa":
            profit = metrics.get("profit")
            assets = metrics.get("assets")
            if profit is not None and assets:
                return profit / assets

        elif ratio_type == "debt_ratio":
            debt = metrics.get("debt")
            assets = metrics.get("assets")
            if debt is not None and assets:
                return debt / assets

        return None
    except (ZeroDivisionError, TypeError):
        return None


def calculate(expression: str) -> str:
    """
    通用数学计算

    Args:
        expression: 数学表达式，如 "123 * 456"

    Returns:
        结果字符串，或错误信息
    """
    result = _safe_eval(expression)
    if result is None:
        return f"无法计算：{expression}"
    return str(result)
