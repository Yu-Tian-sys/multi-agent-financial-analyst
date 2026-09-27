import os
import pytest
from src.tools.pdf_parser import extract_financial_metrics, parse_pdf
from src.tools.news_search import search_news, analyze_sentiment
from src.tools.report_search import search_reports
from src.tools.market_data import get_stock_price, get_valuation
from src.tools.calculator import calculate, calculate_ratio
from src.tools.chart import generate_chart


# ========================================
# pdf_parser 测试
# ========================================

def test_extract_financial_metrics():
    """测试财务指标提取"""
    text = "营业收入：100亿，净利润：20亿，ROE：15%"
    metrics = extract_financial_metrics(text)
    assert metrics.get("revenue") == "100亿"
    assert metrics.get("profit") == "20亿"
    assert metrics.get("roe") == "15"


def test_extract_financial_metrics_empty():
    """测试无指标文本"""
    metrics = extract_financial_metrics("今天天气不错")
    assert metrics == {} or len(metrics) == 0


def test_parse_pdf_nonexistent():
    """测试解析不存在的 PDF"""
    ok, msg = parse_pdf("not_exist.pdf")
    assert ok is False
    assert "不存在" in msg


def test_parse_pdf_wrong_ext():
    """测试非 PDF 文件"""
    ok, msg = parse_pdf("test.txt")
    assert ok is False


# ========================================
# news_search 测试
# ========================================

def test_search_news():
    """测试搜索新闻"""
    news = search_news("AAPL")
    assert len(news) > 0
    assert "title" in news[0]


def test_search_news_cache():
    """测试新闻缓存"""
    news1 = search_news("AAPL")
    news2 = search_news("AAPL")
    assert len(news1) == len(news2)


def test_analyze_sentiment_positive():
    """测试正面情感"""
    assert analyze_sentiment("销量超预期，大幅增长") == "positive"


def test_analyze_sentiment_negative():
    """测试负面情感"""
    assert analyze_sentiment("业绩下滑，面临调查") == "negative"


def test_analyze_sentiment_neutral():
    """测试中性情感"""
    assert analyze_sentiment("今天发布了一个公告") == "neutral"


# ========================================
# report_search 测试
# ========================================

def test_search_reports():
    """测试检索研报"""
    reports = search_reports("苹果")
    assert len(reports) > 0


def test_search_reports_empty():
    """测试空查询"""
    assert search_reports("") == []


# ========================================
# market_data 测试
# ========================================

def test_get_stock_price():
    """测试获取股价"""
    price = get_stock_price("AAPL")
    assert price["symbol"] == "AAPL"
    assert price["price"] > 0
    assert "history" in price


def test_get_stock_price_unknown():
    """测试未知股票返回默认值"""
    price = get_stock_price("UNKNOWN_STOCK")
    assert price["price"] == 100.0


def test_get_valuation():
    """测试获取估值"""
    val = get_valuation("AAPL")
    assert val["pe"] > 0
    assert val["pb"] > 0


# ========================================
# calculator 测试
# ========================================

def test_calculate_normal():
    """测试正常计算"""
    assert calculate("123 * 456") == "56088"
    assert calculate("10 + 20") == "30"


def test_calculate_invalid():
    """测试非法表达式"""
    result = calculate("__import__('os').system('ls')")
    assert "无法计算" in result


def test_calculate_ratio_net_margin():
    """测试净利率"""
    result = calculate_ratio({"revenue": 100, "profit": 20}, "net_margin")
    assert result == 0.2


def test_calculate_ratio_roe():
    """测试 ROE"""
    result = calculate_ratio({"profit": 20, "equity": 80}, "roe")
    assert result == 0.25


def test_calculate_ratio_missing_data():
    """测试缺数据返回 None"""
    assert calculate_ratio({}, "net_margin") is None


def test_calculate_ratio_zero_division():
    """测试除零返回 None"""
    assert calculate_ratio({"revenue": 0, "profit": 20}, "net_margin") is None


# ========================================
# chart 测试
# ========================================

def test_generate_chart(tmp_path, monkeypatch):
    """测试生成图表"""
    # 把 OUTPUT_DIR 改到临时目录
    import src.tools.chart as chart_module
    monkeypatch.setattr(chart_module, "OUTPUT_DIR", str(tmp_path))

    path = generate_chart([1, 3, 2, 5, 4], chart_type="line", title="test")
    assert path != ""
    assert os.path.exists(path)


def test_generate_chart_bar(tmp_path, monkeypatch):
    """测试柱状图"""
    import src.tools.chart as chart_module
    monkeypatch.setattr(chart_module, "OUTPUT_DIR", str(tmp_path))

    path = generate_chart([10, 20, 30], chart_type="bar", title="test_bar")
    assert path != ""
    assert os.path.exists(path)
