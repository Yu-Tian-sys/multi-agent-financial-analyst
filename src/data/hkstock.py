"""
港股数据 Provider（基于 yfinance）

港股代码格式：0700.HK、3690.HK 等。
yfinance 通过 .HK 后缀区分港股。
"""

from .usstock import USStockProvider

# 港股英文/简称 → 中文名映射（yfinance 返回英文名，需转中文）
HK_NAME_MAP: dict[str, str] = {
    "TENCENT": "腾讯控股",
    "TENCENT HOLDINGS": "腾讯控股",
    "MEITUAN": "美团",
    "MEITUAN-W": "美团",
    "KUAISHOU-W": "快手",
    "XIAOMI-W": "小米集团",
    "XIAOMI CORP": "小米集团",
    "ALIBABA HEALTH": "阿里健康",
    "JD HEALTH": "京东健康",
    "NETEASE": "网易",
    "BAIDU": "百度",
    "BILIBILI": "哔哩哔哩",
    "PDD HOLDINGS": "拼多多",
    "NIO": "蔚来",
    "XPENG": "小鹏汽车",
    "LI AUTO": "理想汽车",
    "BYD COMPANY": "比亚迪股份",
    "CHINA MOBILE": "中国移动",
    "PING AN": "中国平安",
    "CCB": "建设银行",
    "ICBC": "工商银行",
    "BANK OF CHINA": "中国银行",
    "AGRICULTURAL BANK": "农业银行",
    "CM BANK": "招商银行",
    "LONGFOR": "龙湖集团",
    "COUNTRY GARDEN": "碧桂园",
    "HAIDILAO": "海底捞",
    "SHENZHOU INTL": "申洲国际",
    "TRIP.COM": "携程",
}


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

    def get_company_name(self, symbol: str) -> str:
        """获取公司中文名（yfinance 返回英文名，需映射）"""
        name = super().get_company_name(symbol)
        # 映射到中文名
        upper = name.upper()
        for en, cn in HK_NAME_MAP.items():
            if en in upper:
                return cn
        return name

    def get_financials(self, symbol: str):
        return super().get_financials(self._normalize_symbol(symbol))

    def get_price(self, symbol: str, days: int = 30):
        return super().get_price(self._normalize_symbol(symbol), days)

    def get_valuation(self, symbol: str):
        return super().get_valuation(self._normalize_symbol(symbol))

    def get_news(self, symbol: str, limit: int = 10):
        """港股新闻：优先用 yfinance，拿不到则尝试 AKShare 港股新闻"""
        items = super().get_news(self._normalize_symbol(symbol), limit)
        if items:
            return items
        # 降级：尝试 AKShare 港股新闻
        try:
            import akshare as ak
            code = self._normalize_symbol(symbol).replace(".HK", "")
            df = ak.stock_hk_news_em(symbol=code)
            if df is not None and not df.empty:
                from .models import NewsItem
                result = []
                for _, row in df.head(limit).iterrows():
                    result.append(NewsItem(
                        title=str(row.get("新闻标题", "")),
                        source=str(row.get("文章来源", "")),
                        date=str(row.get("发布时间", "")),
                        content=str(row.get("新闻内容", "")),
                        url=str(row.get("新闻链接", "")),
                    ))
                if result:
                    return result
        except Exception:
            pass
        return items

    def get_analyst_ratings(self, symbol: str):
        return super().get_analyst_ratings(self._normalize_symbol(symbol))
