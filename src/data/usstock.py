"""
美股数据 Provider（基于 yfinance）

文档：https://pypi.org/project/yfinance/
免费，Yahoo Finance 非官方 API。
"""

import logging
from typing import List, Optional

from .base import MarketDataProvider
from .models import (
    FinancialStatement,
    FinancialStatements,
    PriceData,
    ValuationData,
    NewsItem,
    AnalystRating,
)

logger = logging.getLogger(__name__)


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        import pandas as pd
        if pd.isna(val):
            return None
        return float(val)
    except (ValueError, TypeError, ImportError):
        return None


class USStockProvider(MarketDataProvider):
    """美股数据 Provider"""

    @property
    def market(self) -> str:
        return "美股"

    def _get_ticker(self, symbol: str):
        import yfinance as yf
        return yf.Ticker(symbol)

    # ---------- 公司简称 ----------
    def get_company_name(self, symbol: str) -> str:
        try:
            ticker = self._get_ticker(symbol)
            info = ticker.info
            name = info.get("shortName") or info.get("longName")
            if name:
                return str(name).strip()
        except Exception as e:
            logger.warning(f"[usstock] 公司名称获取失败 {symbol}: {e}")
        return symbol

    # ---------- 财务报表 ----------
    def get_financials(self, symbol: str) -> FinancialStatements:
        try:
            ticker = self._get_ticker(symbol)
        except ImportError:
            logger.error("yfinance 未安装，请运行 pip install yfinance")
            return FinancialStatements(symbol=symbol)

        fs = FinancialStatements(symbol=symbol)

        # 利润表
        try:
            df = ticker.income_stmt
            fs.income_statement = self._parse_yf_statement(df, "income")
        except Exception as e:
            logger.warning(f"[usstock] 利润表获取失败 {symbol}: {e}")

        # 资产负债表
        try:
            df = ticker.balance_sheet
            fs.balance_sheet = self._parse_yf_statement(df, "balance")
        except Exception as e:
            logger.warning(f"[usstock] 资产负债表获取失败 {symbol}: {e}")

        # 现金流量表
        try:
            df = ticker.cashflow
            fs.cashflow = self._parse_yf_statement(df, "cashflow")
        except Exception as e:
            logger.warning(f"[usstock] 现金流量表获取失败 {symbol}: {e}")

        return fs

    def _parse_yf_statement(self, df, stmt_type: str) -> List[FinancialStatement]:
        """
        yfinance 返回的 DataFrame：行是科目，列是报告期（Timestamp）
        """
        statements = []
        if df is None or df.empty:
            return statements

        periods = list(df.columns)[:4]  # 最近 4 期

        for period in periods:
            period_str = str(period)[:10]  # 取日期部分
            stmt = FinancialStatement(period=period_str, currency="USD")

            col_data = df[period]

            def _get(key):
                for k in col_data.index:
                    if key.lower() in str(k).lower():
                        return _safe_float(col_data[k])
                return None

            if stmt_type == "income":
                stmt.revenue = _get("Total Revenue")
                stmt.net_income = _get("Net Income")
                stmt.gross_profit = _get("Gross Profit")
                stmt.operating_income = _get("Operating Income")
            elif stmt_type == "balance":
                stmt.total_assets = _get("Total Assets")
                stmt.total_liabilities = _get("Total Liabilities Net Minority Interest") or _get("Total Liabilities")
                stmt.total_equity = _get("Stockholders Equity") or _get("Total Equity")
            elif stmt_type == "cashflow":
                stmt.operating_cashflow = _get("Operating Cash Flow")
                stmt.investing_cashflow = _get("Investing Cash Flow")
                stmt.financing_cashflow = _get("Financing Cash Flow")

            # raw 数据
            stmt.raw = {str(k): _safe_float(v) for k, v in col_data.items()}
            statements.append(stmt)

        return statements

    # ---------- 股价 ----------
    def get_price(self, symbol: str, days: int = 30) -> PriceData:
        try:
            ticker = self._get_ticker(symbol)
            df = ticker.history(period=f"{days}d")
            if df is None or df.empty:
                return PriceData(symbol=symbol, price=0, change=0, change_percent=0, volume=0)

            close = df["Close"].tolist()
            latest = close[-1]
            prev = close[-2] if len(close) >= 2 else latest
            change = latest - prev
            change_pct = (change / prev * 100) if prev else 0
            volume = float(df["Volume"].iloc[-1])

            return PriceData(
                symbol=symbol,
                price=round(latest, 2),
                change=round(change, 2),
                change_percent=round(change_pct, 2),
                volume=volume,
                history=[round(float(x), 2) for x in close],
            )
        except ImportError:
            logger.error("yfinance 未安装")
            return PriceData(symbol=symbol, price=0, change=0, change_percent=0, volume=0)
        except Exception as e:
            logger.warning(f"[usstock] 股价获取失败 {symbol}: {e}")
            return PriceData(symbol=symbol, price=0, change=0, change_percent=0, volume=0)

    # ---------- 估值 ----------
    def get_valuation(self, symbol: str) -> ValuationData:
        try:
            ticker = self._get_ticker(symbol)
            info = ticker.info
            return ValuationData(
                symbol=symbol,
                pe=_safe_float(info.get("trailingPE")),
                pb=_safe_float(info.get("priceToBook")),
                ps=_safe_float(info.get("priceToSalesTrailing12Months")),
                market_cap=_safe_float(info.get("marketCap")),
            )
        except ImportError:
            return ValuationData(symbol=symbol)
        except Exception as e:
            logger.warning(f"[usstock] 估值获取失败 {symbol}: {e}")
            return ValuationData(symbol=symbol)

    # ---------- 新闻 ----------
    def get_news(self, symbol: str, limit: int = 10) -> List[NewsItem]:
        try:
            ticker = self._get_ticker(symbol)
            news = ticker.news or []
            items = []
            for n in news[:limit]:
                items.append(NewsItem(
                    title=n.get("title", ""),
                    source=n.get("publisher", ""),
                    content=n.get("summary", ""),
                    url=n.get("link", ""),
                ))
            return items
        except ImportError:
            return []
        except Exception as e:
            logger.warning(f"[usstock] 新闻获取失败 {symbol}: {e}")
            return []

    # ---------- 分析师评级 ----------
    def get_analyst_ratings(self, symbol: str) -> List[AnalystRating]:
        try:
            ticker = self._get_ticker(symbol)
            df = ticker.recommendations
            if df is None or df.empty:
                return []
            ratings = []
            for _, row in df.tail(20).iterrows():
                ratings.append(AnalystRating(
                    broker=str(row.get("Firm", "")),
                    rating=str(row.get("To Grade", "")),
                    date=str(row.get("Date", "")),
                ))
            return ratings
        except ImportError:
            return []
        except Exception as e:
            logger.warning(f"[usstock] 分析师评级获取失败 {symbol}: {e}")
            return []
