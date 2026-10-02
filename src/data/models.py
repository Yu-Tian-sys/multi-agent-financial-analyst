"""
标准化金融数据模型

所有 Provider 返回的数据都转换成这些统一结构，
Agent 层不需要感知底层是 AKShare 还是 yfinance。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class FinancialStatement:
    """单期财务报表（标准化后的结构）"""
    period: str                    # 报告期，如 "2024-12-31"
    currency: str                  # 币种，CNY / USD / HKD
    # 利润表关键字段
    revenue: Optional[float] = None        # 营业收入
    net_income: Optional[float] = None     # 净利润
    gross_profit: Optional[float] = None   # 毛利润
    operating_income: Optional[float] = None  # 营业利润
    # 资产负债表关键字段
    total_assets: Optional[float] = None   # 总资产
    total_liabilities: Optional[float] = None  # 总负债
    total_equity: Optional[float] = None   # 净资产（股东权益）
    # 现金流量表关键字段
    operating_cashflow: Optional[float] = None   # 经营现金流
    investing_cashflow: Optional[float] = None   # 投资现金流
    financing_cashflow: Optional[float] = None   # 筹资现金流
    # 原始字段（保留 Provider 返回的全部数据，供评估/调试用）
    raw: Dict = field(default_factory=dict)


@dataclass
class FinancialStatements:
    """三大财务报表集合"""
    symbol: str
    income_statement: List[FinancialStatement] = field(default_factory=list)
    balance_sheet: List[FinancialStatement] = field(default_factory=list)
    cashflow: List[FinancialStatement] = field(default_factory=list)

    @property
    def latest(self) -> Optional[FinancialStatement]:
        """取最新一期利润表"""
        return self.income_statement[0] if self.income_statement else None


@dataclass
class PriceData:
    """股价数据"""
    symbol: str
    price: float                   # 当前价格
    change: float                  # 涨跌额
    change_percent: float          # 涨跌幅 %
    volume: float                  # 成交量
    history: List[float] = field(default_factory=list)  # 历史收盘价


@dataclass
class ValuationData:
    """估值数据"""
    symbol: str
    pe: Optional[float] = None     # 市盈率（静态）
    pe_ttm: Optional[float] = None  # 市盈率 TTM
    pb: Optional[float] = None     # 市净率
    ps: Optional[float] = None     # 市销率（静态）
    ps_ttm: Optional[float] = None  # 市销率 TTM
    market_cap: Optional[float] = None  # 市值


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    source: str = ""
    date: str = ""
    content: str = ""
    sentiment: str = "neutral"     # positive / negative / neutral
    url: str = ""


@dataclass
class AnalystRating:
    """分析师评级"""
    broker: str = ""               # 券商
    rating: str = ""               # 买入 / 增持 / 中性 / 减持 / 卖出
    target_price: Optional[float] = None
    date: str = ""
    summary: str = ""


@dataclass
class MarketDataBundle:
    """一次拉取的全部市场数据（供 Agent 使用）"""
    symbol: str
    market: str                    # A股 / 港股 / 美股
    financials: Optional[FinancialStatements] = None
    price: Optional[PriceData] = None
    valuation: Optional[ValuationData] = None
    news: List[NewsItem] = field(default_factory=list)
    analyst_ratings: List[AnalystRating] = field(default_factory=list)
