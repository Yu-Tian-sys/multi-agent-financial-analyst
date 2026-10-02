"""
MarketDataProvider 抽象基类

定义统一的数据获取接口，所有市场 Provider 都实现这个接口。
Agent 层只面向接口编程，不感知具体市场和数据源。
"""

from abc import ABC, abstractmethod
from typing import List

from .models import (
    FinancialStatements,
    PriceData,
    ValuationData,
    NewsItem,
    AnalystRating,
)


class MarketDataProvider(ABC):
    """市场数据 Provider 抽象基类"""

    @property
    @abstractmethod
    def market(self) -> str:
        """市场标识：A股 / 港股 / 美股"""
        ...

    @abstractmethod
    def get_company_name(self, symbol: str) -> str:
        """
        获取公司简称

        Args:
            symbol: 标准化后的股票代码

        Returns:
            公司简称（如 "比亚迪"、"Apple Inc."）；失败返回原始 symbol
        """
        ...

    @abstractmethod
    def get_financials(self, symbol: str) -> FinancialStatements:
        """
        获取三大财务报表

        Args:
            symbol: 标准化后的股票代码

        Returns:
            FinancialStatements
        """
        ...

    @abstractmethod
    def get_price(self, symbol: str, days: int = 30) -> PriceData:
        """
        获取股价数据

        Args:
            symbol: 股票代码
            days: 历史天数

        Returns:
            PriceData
        """
        ...

    @abstractmethod
    def get_valuation(self, symbol: str) -> ValuationData:
        """
        获取估值指标（PE/PB/PS/市值）

        Args:
            symbol: 股票代码

        Returns:
            ValuationData
        """
        ...

    @abstractmethod
    def get_news(self, symbol: str, limit: int = 10) -> List[NewsItem]:
        """
        获取财经新闻

        Args:
            symbol: 股票代码
            limit: 返回条数

        Returns:
            NewsItem 列表
        """
        ...

    @abstractmethod
    def get_analyst_ratings(self, symbol: str) -> List[AnalystRating]:
        """
        获取分析师评级

        Args:
            symbol: 股票代码

        Returns:
            AnalystRating 列表
        """
        ...

    def get_financial_text(self, symbol: str) -> str:
        """
        获取财报文本（用于评估路径：让 LLM 从非结构化文本提取指标）

        默认实现：从结构化 FinancialStatements 生成文本。
        子类可覆盖以提供真实公告原文。
        """
        fs = self.get_financials(symbol)
        if not fs or not fs.income_statement:
            return "暂无财报数据"
        stmt = fs.income_statement[0]
        lines = [f"{symbol} {stmt.period} 财务报告", ""]
        if stmt.revenue is not None:
            lines.append(f"营业收入：{stmt.revenue}")
        if stmt.net_income is not None:
            lines.append(f"净利润：{stmt.net_income}")
        if stmt.gross_profit is not None:
            lines.append(f"毛利润：{stmt.gross_profit}")
        if stmt.total_assets is not None:
            lines.append(f"总资产：{stmt.total_assets}")
        if stmt.total_liabilities is not None:
            lines.append(f"总负债：{stmt.total_liabilities}")
        if stmt.total_equity is not None:
            lines.append(f"净资产：{stmt.total_equity}")
        if stmt.operating_cashflow is not None:
            lines.append(f"经营现金流：{stmt.operating_cashflow}")
        return "\n".join(lines)
