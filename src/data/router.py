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


def resolve_symbol(topic: str) -> str:
    """
    将用户输入解析为标准股票代码。

    - 如果已经是可识别的股票代码（A股/港股/美股），原样返回
    - 如果是中文公司名，尝试匹配 A 股代码（如 中芯国际 → 688981）
    - 无法解析时原样返回

    Args:
        topic: 用户输入（股票代码或公司名）

    Returns:
        解析后的股票代码
    """
    topic = topic.strip()
    # 已经是标准代码，直接返回
    if detect_market(topic) != "未知":
        return topic

    # 尝试 A 股公司名 → 代码
    name_map = _load_a_code_name_map()
    if topic in name_map:
        code = name_map[topic]
        logger.info(f"[router] 公司名解析：{topic} → {code}")
        return code

    # 模糊匹配（包含关系）
    for name, code in name_map.items():
        if topic in name or name in topic:
            logger.info(f"[router] 公司名模糊匹配：{topic} → {name}({code})")
            return code

    logger.warning(f"[router] 无法解析为股票代码：{topic}")
    return topic
