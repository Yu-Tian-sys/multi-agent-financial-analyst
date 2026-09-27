import time
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

_cache: Dict[str, tuple] = {}
CACHE_TTL = 3600


def _get_cache(key: str):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
        else:
            del _cache[key]
    return None


def _set_cache(key: str, data):
    _cache[key] = (time.time(), data)


MOCK_NEWS = {
    "AAPL": [
        {"title": "苹果发布新款 iPhone，销量超预期", "source": "Reuters", "date": "2025-01-10", "content": "苹果公司今日发布新款 iPhone...", "sentiment": "positive"},
        {"title": "苹果面临欧盟反垄断调查", "source": "Bloomberg", "date": "2025-01-08", "content": "欧盟委员会对苹果展开反垄断调查...", "sentiment": "negative"},
        {"title": "苹果季度财报超预期", "source": "CNBC", "date": "2025-01-05", "content": "苹果公布季度财报，营收同比增长...", "sentiment": "positive"},
    ],
    "TSLA": [
        {"title": "特斯拉上海工厂产能提升", "source": "Reuters", "date": "2025-01-12", "content": "特斯拉上海工厂产能持续提升...", "sentiment": "positive"},
        {"title": "特斯拉召回部分 Model 3", "source": "Bloomberg", "date": "2025-01-09", "content": "特斯拉宣布召回部分 Model 3...", "sentiment": "negative"},
    ],
    "default": [
        {"title": "市场整体表现平稳", "source": "Reuters", "date": "2025-01-11", "content": "今日市场整体表现平稳...", "sentiment": "neutral"},
        {"title": "分析师看好科技板块", "source": "CNBC", "date": "2025-01-10", "content": "多位分析师看好科技板块后市...", "sentiment": "positive"},
    ],
}


def search_news(query: str, limit: int = 10) -> List[Dict]:
    """搜索新闻（模拟，带缓存 + 重试 + 降级）"""
    cache_key = f"news:{query}:{limit}"
    cached = _get_cache(cache_key)
    if cached is not None:
        logger.info(f"新闻缓存命中：{query}")
        return cached
    result = []
    for attempt in range(3):
        try:
            time.sleep(0.1)
            key = query.upper() if query.upper() in MOCK_NEWS else "default"
            result = MOCK_NEWS[key][:limit]
            break
        except Exception as e:
            logger.warning(f"新闻搜索失败（第 {attempt+1} 次）：{e}")
            if attempt == 2:
                result = cached or []
    if result:
        _set_cache(cache_key, result)
    return result


def analyze_sentiment(text: str) -> str:
    """简单情感分析（关键词匹配）"""
    positive_words = ["增长", "超预期", "看好", "提升", "利好", "突破"]
    negative_words = ["下跌", "亏损", "召回", "调查", "风险", "下滑"]
    pos = sum(1 for w in positive_words if w in text)
    neg = sum(1 for w in negative_words if w in text)
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    else:
        return "neutral"
