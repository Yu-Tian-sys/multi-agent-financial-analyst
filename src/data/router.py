"""
MarketRouter —— 市场识别与自动路由

根据股票代码自动判断市场（A 股 / 港股 / 美股），
返回对应的 MarketDataProvider 实例。
"""

import re
import logging
from typing import Optional

from .base import MarketDataProvider
from .astock import AStockProvider
from .usstock import USStockProvider
from .hkstock import HKStockProvider

logger = logging.getLogger(__name__)

# 单例 Provider 实例（避免重复创建）
_a_provider: Optional[AStockProvider] = None
_us_provider: Optional[USStockProvider] = None
_hk_provider: Optional[HKStockProvider] = None


def _get_a_provider() -> AStockProvider:
    global _a_provider
    if _a_provider is None:
        _a_provider = AStockProvider()
    return _a_provider


def _get_us_provider() -> USStockProvider:
    global _us_provider
    if _us_provider is None:
        _us_provider = USStockProvider()
    return _us_provider


def _get_hk_provider() -> HKStockProvider:
    global _hk_provider
    if _hk_provider is None:
        _hk_provider = HKStockProvider()
    return _hk_provider


def detect_market(symbol: str) -> str:
    """
    根据股票代码识别市场

    规则：
    - 纯字母 → 美股（AAPL, TSLA, MSFT）
    - 以 .HK 结尾 → 港股
    - 5 位数字 → 港股（00700, 03690）
    - 6 位数字 → A 股
        - 60/68 开头 → 沪市
        - 00/30 开头 → 深市
        - 8/4 开头 → 北交所
    - SH/SZ/BJ 前缀 → A 股

    Args:
        symbol: 股票代码

    Returns:
        "A股" / "港股" / "美股" / "未知"
    """
    s = symbol.strip().upper()

    # 港股后缀
    if s.endswith(".HK"):
        return "港股"

    # A 股前缀
    if s.startswith(("SH", "SZ", "BJ")):
        return "A股"

    # 纯字母 → 美股
    if re.match(r"^[A-Z]+$", s):
        return "美股"

    # 纯数字
    if s.isdigit():
        if len(s) == 5:
            return "港股"
        if len(s) == 6:
            return "A股"

    # 带点的字母+数字组合（如 BRK.B）→ 美股
    if re.match(r"^[A-Z]+\.[A-Z]$", s):
        return "美股"

    logger.warning(f"[router] 无法识别市场：{symbol}")
    return "未知"


def get_provider(symbol: str) -> Optional[MarketDataProvider]:
    """
    根据股票代码返回对应的 Provider

    Args:
        symbol: 股票代码

    Returns:
        MarketDataProvider 实例，无法识别返回 None
    """
    market = detect_market(symbol)
    if market == "A股":
        return _get_a_provider()
    elif market == "港股":
        return _get_hk_provider()
    elif market == "美股":
        return _get_us_provider()
    return None


def get_provider_by_market(market: str) -> Optional[MarketDataProvider]:
    """按市场名获取 Provider"""
    if market == "A股":
        return _get_a_provider()
    elif market == "港股":
        return _get_hk_provider()
    elif market == "美股":
        return _get_us_provider()
    return None


# A 股代码→名称 缓存（避免每次都请求 AKShare）
_a_code_name_cache: Optional[dict] = None


# 美股 / 港股常见中文别名 → 标准代码（硬编码，因为没有免费的中文名称 API）
# 覆盖最常被搜索的中概股和港股蓝筹
COMMON_ALIAS_MAP: dict[str, str] = {
    # ===== A股常见简称 =====
    "茅台": "600519",
    "贵州茅台": "600519",
    "五粮液": "000858",
    "招行": "600036",
    "招商银行": "600036",
    "工行": "601398",
    "工商银行": "601398",
    "建行": "601939",
    "建设银行": "601939",
    "中行": "601988",
    "中国银行": "601988",
    "农行": "601288",
    "农业银行": "601288",
    "平安": "601318",
    "中国平安": "601318",
    "宁德": "300750",
    "宁德时代": "300750",
    "比亚迪": "002594",
    "中芯国际": "688981",
    "隆基": "601012",
    "隆基绿能": "601012",
    "美的": "000333",
    "美的集团": "000333",
    "格力": "000651",
    "格力电器": "000651",
    "海康": "002415",
    "海康威视": "002415",
    "恒瑞": "600276",
    "恒瑞医药": "600276",
    "伊利": "600887",
    "伊利股份": "600887",
    "万科": "000002",
    "万科A": "000002",
    "中国中免": "601888",
    "中免": "601888",
    "药明康德": "603259",
    "紫金矿业": "601899",
    "长江电力": "600900",
    "长电": "600900",
    # ===== 美股中概股 =====
    "苹果": "AAPL",
    "苹果公司": "AAPL",
    "微软": "MSFT",
    "谷歌": "GOOGL",
    "亚马逊": "AMZN",
    "特斯拉": "TSLA",
    "英伟达": "NVDA",
    "Meta": "META",
    "脸书": "META",
    "奈飞": "NFLX",
    "网飞": "NFLX",
    "阿里巴巴": "BABA",
    "阿里": "BABA",
    "京东": "JD",
    "拼多多": "PDD",
    "百度": "BIDU",
    "网易": "NTES",
    "携程": "TCOM",
    "哔哩哔哩": "BILI",
    "B站": "BILI",
    "微博": "WB",
    "爱奇艺": "IQ",
    "知乎": "ZH",
    "滴滴": "DIDI",
    "理想汽车": "LI",
    "理想": "LI",
    "小鹏汽车": "XPEV",
    "小鹏": "XPEV",
    "蔚来": "NIO",
    # 港股
    "腾讯": "00700.HK",
    "腾讯控股": "00700.HK",
    "阿里巴巴港股": "09988.HK",
    "美团": "03690.HK",
    "美团点评": "03690.HK",
    "京东港股": "09618.HK",
    "网易港股": "09999.HK",
    "百度港股": "09888.HK",
    "哔哩哔哩港股": "09626.HK",
    "快手": "01024.HK",
    "小米": "01810.HK",
    "小米集团": "01810.HK",
    "中国移动": "00941.HK",
    "中国平安港股": "02318.HK",
    "建设银行港股": "00939.HK",
    "工商银行港股": "01398.HK",
    "比亚迪股份": "01211.HK",
    "比亚迪港股": "01211.HK",
    "理想汽车港股": "02015.HK",
    "小鹏汽车港股": "09868.HK",
    "蔚来港股": "09866.HK",
    "携程港股": "09961.HK",
    "申洲国际": "02313.HK",
    "海底捞": "06862.HK",
}


def _load_a_code_name_map() -> dict:
    """加载 A 股代码-名称对照表（缓存）"""
    global _a_code_name_cache
    if _a_code_name_cache is not None:
        return _a_code_name_cache
    try:
        import akshare as ak
        df = ak.stock_info_a_code_name()
        # code 列可能是 'code' 或 'symbol'，name 列可能是 'name'
        code_col = "code" if "code" in df.columns else df.columns[0]
        name_col = "name" if "name" in df.columns else df.columns[1]
        _a_code_name_cache = dict(zip(df[name_col].str.strip(), df[code_col].str.strip()))
        logger.info(f"[router] 加载 A 股代码表：{len(_a_code_name_cache)} 条")
    except Exception as e:
        logger.warning(f"[router] 加载 A 股代码表失败：{e}")
        _a_code_name_cache = {}
    return _a_code_name_cache


def _fuzzy_match_a_stock(topic: str, name_map: dict) -> Optional[str]:
    """
    A 股模糊匹配：返回最佳匹配的代码。

    匹配优先级：
    1. 精确匹配（name == topic）
    2. 前缀匹配（name.startswith(topic) 或 topic.startswith(name)）
    3. 包含匹配（topic in name 或 name in topic）
    同优先级内取名称最短的（更精确）。
    """
    # 1. 精确
    if topic in name_map:
        return name_map[topic]

    # 收集候选：(name, code, priority)
    candidates: list[tuple[str, str, int]] = []
    for name, code in name_map.items():
        if not name or not topic:
            continue
        if name == topic:
            return code  # 精确直接返回
        if name.startswith(topic) or topic.startswith(name):
            candidates.append((name, code, 2))
        elif topic in name or name in topic:
            candidates.append((name, code, 3))

    if not candidates:
        return None

    # 按优先级排序，同优先级按名称长度升序（短的更精确）
    candidates.sort(key=lambda x: (x[2], len(x[0])))
    best_name, best_code, _ = candidates[0]
    logger.info(f"[router] A股模糊匹配：{topic} → {best_name}({best_code})")
    return best_code


def resolve_symbol(topic: str) -> str:
    """
    将用户输入解析为标准股票代码（简化版，仅返回代码）。

    解析优先级：
    1. 标准股票代码（AAPL / 600519 / 00700.HK）→ 原样返回
    2. 常见别名表（茅台 → 600519、腾讯 → 00700.HK）
    3. A 股公司名精确/模糊匹配

    Args:
        topic: 用户输入（股票代码、公司名或简称）

    Returns:
        解析后的股票代码；无法解析时原样返回
    """
    return resolve_symbol_detailed(topic)["symbol"]


def resolve_symbol_detailed(topic: str) -> dict:
    """
    详细版股票代码解析，返回匹配类型，用于判断是否需要用户确认。

    Args:
        topic: 用户输入

    Returns:
        {
            "symbol": str,           # 解析后的股票代码
            "match_type": str,       # "exact" / "alias" / "fuzzy" / "unknown"
            "matched_name": str,     # 匹配到的公司名（模糊匹配时用于反问）
        }
        match_type 说明：
        - exact:   标准代码，可直接启动分析
        - alias:   别名表命中（热门股简称），可信度高，可直接启动
        - fuzzy:   A股模糊匹配，需反问用户确认
        - unknown: 无法解析
    """
    topic = topic.strip()
    if not topic:
        return {"symbol": topic, "match_type": "unknown", "matched_name": ""}

    # 1. 标准代码 → exact
    if detect_market(topic) != "未知":
        return {"symbol": topic, "match_type": "exact", "matched_name": topic}

    # 2. 别名表 → alias（热门股简称，可信度高）
    if topic in COMMON_ALIAS_MAP:
        code = COMMON_ALIAS_MAP[topic]
        logger.info(f"[router] 别名匹配：{topic} → {code}")
        return {"symbol": code, "match_type": "alias", "matched_name": topic}

    # 3. A股模糊匹配 → fuzzy（需确认）
    name_map = _load_a_code_name_map()
    matched = _fuzzy_match_a_stock(topic, name_map)
    if matched:
        # 反查公司名
        matched_name = ""
        for name, code in name_map.items():
            if code == matched:
                matched_name = name
                break
        return {"symbol": matched, "match_type": "fuzzy", "matched_name": matched_name}

    logger.warning(f"[router] 无法解析为股票代码：{topic}")
    return {"symbol": topic, "match_type": "unknown", "matched_name": ""}
