"""
A 股数据 Provider（基于 AKShare）

文档：https://akshare.akfamily.xyz/
完全免费，无积分限制。
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
    """安全转 float，失败返回 None"""
    if val is None:
        return None
    try:
        f = float(val)
        return f if f == f else None  # NaN check
    except (ValueError, TypeError):
        return None


class AStockProvider(MarketDataProvider):
    """A 股数据 Provider"""

    @property
    def market(self) -> str:
        return "A股"

    def _normalize_symbol(self, symbol: str) -> str:
        """AKShare 大部分接口需要不带交易所前缀的纯数字代码"""
        s = symbol.upper()
        for prefix in ("SH", "SZ", "BJ"):
            if s.startswith(prefix):
                s = s[len(prefix):]
        return s

    def _symbol_with_prefix(self, symbol: str) -> str:
        """
        stock_zh_a_daily 等接口需要带交易所前缀：sh600519 / sz000001

        规则：
        - 60/68/90 开头 → 沪市 sh
        - 00/30/20 开头 → 深市 sz
        - 8/4 开头 → 北交所 bj
        """
        code = self._normalize_symbol(symbol)
        if not code.isdigit():
            return code
        first_two = code[:2]
        first_one = code[:1]
        if first_two in ("60", "68", "90"):
            return f"sh{code}"
        elif first_two in ("00", "30", "20"):
            return f"sz{code}"
        elif first_one in ("8", "4"):
            return f"bj{code}"
        return f"sh{code}"  # 默认沪市

    # ---------- 公司简称 ----------
    def get_company_name(self, symbol: str) -> str:
        try:
            import akshare as ak
        except ImportError:
            return symbol

        code = self._normalize_symbol(symbol)
        try:
            # stock_info_a_code_name 返回全 A 股代码-名称对照表（稳定，不依赖东方财富实时接口）
            df = ak.stock_info_a_code_name()
            if df is not None and not df.empty:
                row = df[df["code"] == code]
                if not row.empty:
                    name = str(row.iloc[0]["name"]).strip()
                    if name:
                        return name
        except Exception as e:
            logger.warning(f"[astock] 公司名称获取失败 {code}: {e}")
        return symbol

    # ---------- 财务报表 ----------
    def get_financials(self, symbol: str) -> FinancialStatements:
        try:
            import akshare as ak
        except ImportError:
            logger.error("akshare 未安装，请运行 pip install akshare")
            return FinancialStatements(symbol=symbol)

        code = self._normalize_symbol(symbol)
        fs = FinancialStatements(symbol=symbol)

        try:
            # 利润表
            df_inc = ak.stock_financial_report_sina(stock=code, symbol="利润表")
            fs.income_statement = self._parse_statement(df_inc, "income")
        except Exception as e:
            logger.warning(f"[astock] 利润表获取失败 {code}: {e}")

        try:
            df_bs = ak.stock_financial_report_sina(stock=code, symbol="资产负债表")
            fs.balance_sheet = self._parse_statement(df_bs, "balance")
        except Exception as e:
            logger.warning(f"[astock] 资产负债表获取失败 {code}: {e}")

        try:
            df_cf = ak.stock_financial_report_sina(stock=code, symbol="现金流量表")
            fs.cashflow = self._parse_statement(df_cf, "cashflow")
        except Exception as e:
            logger.warning(f"[astock] 现金流量表获取失败 {code}: {e}")

        return fs

    def _parse_statement(self, df, stmt_type: str) -> List[FinancialStatement]:
        """
        把 AKShare 返回的 DataFrame 转成标准化 FinancialStatement 列表

        AKShare 财报格式：行=报告期，列=科目
        第一列是「报告日」，其余列是财务指标。
        """
        statements = []
        if df is None or df.empty:
            return statements

        for _, row in df.head(4).iterrows():
            period = str(row.get("报告日", ""))
            stmt = FinancialStatement(period=period, currency="CNY")
            row_map = {str(k): v for k, v in row.items()}

            def _get(*keys):
                for k in keys:
                    if k in row_map:
                        return _safe_float(row_map[k])
                return None

            if stmt_type == "income":
                stmt.revenue = _get("营业收入", "营业总收入")
                stmt.net_income = _get("净利润", "归属于母公司所有者的净利润")
                stmt.gross_profit = _get("毛利润")  # 可能没有
                stmt.operating_income = _get("营业利润")
            elif stmt_type == "balance":
                stmt.total_assets = _get("资产总计", "总资产")
                stmt.total_liabilities = _get("负债合计", "总负债")
                stmt.total_equity = _get("所有者权益(或股东权益)合计", "股东权益合计", "所有者权益合计")
            elif stmt_type == "cashflow":
                stmt.operating_cashflow = _get("经营活动产生的现金流量净额", "经营活动现金流量净额")
                stmt.investing_cashflow = _get("投资活动产生的现金流量净额", "投资活动现金流量净额")
                stmt.financing_cashflow = _get("筹资活动产生的现金流量净额", "筹资活动现金流量净额")

            stmt.raw = row_map
            statements.append(stmt)

        return statements

    # ---------- 股价 ----------
    def get_price(self, symbol: str, days: int = 30) -> PriceData:
        try:
            import akshare as ak
        except ImportError:
            logger.error("akshare 未安装")
            return PriceData(symbol=symbol, price=0, change=0, change_percent=0, volume=0)

        code = self._symbol_with_prefix(symbol)
        try:
            df = ak.stock_zh_a_daily(symbol=code, adjust="qfq")
            if df is None or df.empty:
                return PriceData(symbol=symbol, price=0, change=0, change_percent=0, volume=0)

            df = df.tail(days)
            close = df["close"].tolist()
            latest = close[-1]
            prev = close[-2] if len(close) >= 2 else latest
            change = latest - prev
            change_pct = (change / prev * 100) if prev else 0
            volume = float(df["volume"].iloc[-1])

            return PriceData(
                symbol=symbol,
                price=round(latest, 2),
                change=round(change, 2),
                change_percent=round(change_pct, 2),
                volume=volume,
                history=[round(float(x), 2) for x in close],
            )
        except Exception as e:
            logger.warning(f"[astock] 股价获取失败 {code}: {e}")
            return PriceData(symbol=symbol, price=0, change=0, change_percent=0, volume=0)

    # ---------- 估值 ----------
    def get_valuation(self, symbol: str) -> ValuationData:
        try:
            import akshare as ak
        except ImportError:
            return ValuationData(symbol=symbol)

        code = self._normalize_symbol(symbol)
        val = ValuationData(symbol=symbol)

        # 用百度股市通获取 PE_TTM / PB / 市值
        indicators = {
            "pe_ttm": "市盈率(TTM)",
            "pb": "市净率",
            "market_cap": "总市值",
        }
        for field, indicator in indicators.items():
            try:
                df = ak.stock_zh_valuation_baidu(symbol=code, indicator=indicator, period="近一月")
                if df is not None and not df.empty:
                    setattr(val, field, _safe_float(df.iloc[-1]["value"]))
            except Exception as e:
                logger.warning(f"[astock] 估值 {indicator} 获取失败 {code}: {e}")

        # 尝试获取静态 PE
        try:
            df = ak.stock_zh_valuation_baidu(symbol=code, indicator="市盈率(静)", period="近一月")
            if df is not None and not df.empty:
                val.pe = _safe_float(df.iloc[-1]["value"])
        except Exception:
            pass

        return val

    # ---------- 新闻 ----------
    def get_news(self, symbol: str, limit: int = 10) -> List[NewsItem]:
        try:
            import akshare as ak
        except ImportError:
            return []

        code = self._normalize_symbol(symbol)
        try:
            df = ak.stock_news_em(symbol=code)
            if df is None or df.empty:
                return []

            # 获取公司名，用于过滤不相关新闻（新股接口常混入同期其他新股）
            company_name = self.get_company_name(symbol)
            # 过滤关键词：公司名 + 股票代码（去掉前导0的变体也试一下）
            keywords = [company_name, code, code.lstrip("0")]
            keywords = [k for k in keywords if k and k != symbol]

            items = []
            for _, row in df.iterrows():
                title = str(row.get("新闻标题", ""))
                content = str(row.get("新闻内容", ""))
                text = title + " " + content
                # 过滤：标题或内容必须包含公司名或代码
                if keywords and not any(k in text for k in keywords):
                    continue
                items.append(NewsItem(
                    title=title,
                    source=str(row.get("文章来源", "")),
                    date=str(row.get("发布时间", "")),
                    content=content,
                    url=str(row.get("新闻链接", "")),
                ))
                if len(items) >= limit:
                    break
            return items
        except Exception as e:
            logger.warning(f"[astock] 新闻获取失败 {code}: {e}")
            return []

    # ---------- 分析师评级 ----------
    def get_analyst_ratings(self, symbol: str) -> List[AnalystRating]:
        try:
            import akshare as ak
        except ImportError:
            return []

        code = self._normalize_symbol(symbol)
        try:
            df = ak.stock_research_report_em(symbol=code)
            if df is None or df.empty:
                return []
            ratings = []
            for _, row in df.head(20).iterrows():
                # 目标价 = EPS预测 * PE预测（用2026年预测）
                eps = _safe_float(row.get("2026-盈利预测-收益"))
                pe_forecast = _safe_float(row.get("2026-盈利预测-市盈率"))
                target_price = None
                if eps is not None and pe_forecast is not None:
                    target_price = round(eps * pe_forecast, 2)

                ratings.append(AnalystRating(
                    broker=str(row.get("机构", "")),
                    rating=str(row.get("东财评级", "")),
                    target_price=target_price,
                    date=str(row.get("日期", "")),
                    summary=str(row.get("报告名称", "")),
                ))
            return ratings
        except Exception as e:
            logger.warning(f"[astock] 分析师评级获取失败 {code}: {e}")
            return []
