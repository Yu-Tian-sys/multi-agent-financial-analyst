"""
港股数据 Provider（基于 yfinance）

港股代码格式：0700.HK、3690.HK 等。
yfinance 通过 .HK 后缀区分港股。
"""

from .usstock import USStockProvider


class HKStockProvider(USStockProvider):
    """港股数据 Provider，复用 yfinance 逻辑"""

    @property
    def market(self) -> str:
        return "港股"

    def _normalize_symbol(self, symbol: str) -> str:
        """确保港股代码带 .HK 后缀（yfinance 用 4 位数字）"""
        s = symbol.upper()
        if s.endswith(".HK"):
            s = s[:-3]
        # yfinance 港股用 4 位数字：00700 -> 700 -> 0700.HK，3690 -> 3690.HK
        if s.isdigit():
            s = str(int(s)).zfill(4)  # 先去前导零再补 4 位
        return s + ".HK"

    def _get_ticker(self, symbol: str):
        import yfinance as yf
        return yf.Ticker(self._normalize_symbol(symbol))

    def get_financials(self, symbol: str):
        return super().get_financials(self._normalize_symbol(symbol))

    def get_price(self, symbol: str, days: int = 30):
        return super().get_price(self._normalize_symbol(symbol), days)

    def get_valuation(self, symbol: str):
        return super().get_valuation(self._normalize_symbol(symbol))

    def get_news(self, symbol: str, limit: int = 10):
        return super().get_news(self._normalize_symbol(symbol), limit)

    def get_analyst_ratings(self, symbol: str):
        return super().get_analyst_ratings(self._normalize_symbol(symbol))
