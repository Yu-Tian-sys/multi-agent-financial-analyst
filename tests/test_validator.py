import pytest
from src.state import create_initial_state
from src.agents.validator import (
    _financial_signal, _news_signal, _report_signal,
    _cross_validate, validator_node,
)


# ========================================
# 信号判断测试
# ========================================

def test_financial_signal_positive():
    """测试财报正面信号"""
    data = {"raw_metrics": {"profit": "970亿，同比增长5%"}, "ratios": {"net_margin": 0.25}}
    assert _financial_signal(data) == "positive"


def test_financial_signal_negative():
    """测试财报负面信号"""
    data = {"raw_metrics": {"profit": "亏损，同比下降10%"}, "ratios": {"net_margin": 0.02}}
    assert _financial_signal(data) == "negative"


def test_financial_signal_neutral():
    """测试财报中性信号"""
    data = {"raw_metrics": {}, "ratios": {"net_margin": 0.10}}
    assert _financial_signal(data) == "neutral"


def test_news_signal_positive():
    """测试新闻正面信号"""
    news = [{"sentiment": "positive"}] * 3 + [{"sentiment": "negative"}]
    assert _news_signal(news) == "positive"


def test_news_signal_negative():
    """测试新闻负面信号"""
    news = [{"sentiment": "negative"}] * 4
    assert _news_signal(news) == "negative"


def test_news_signal_empty():
    """测试空新闻返回 unknown"""
    assert _news_signal([]) == "unknown"


def test_report_signal_positive():
    """测试研报正面信号"""
    reports = [{"rating": "买入"}, {"rating": "增持"}, {"rating": "买入"}]
    assert _report_signal(reports) == "positive"


def test_report_signal_negative():
    """测试研报负面信号"""
    reports = [{"rating": "减持"}, {"rating": "卖出"}, {"rating": "减持"}]
    assert _report_signal(reports) == "negative"


def test_report_signal_empty():
    """测试空研报返回 unknown"""
    assert _report_signal([]) == "unknown"


# ========================================
# 交叉验证测试
# ========================================

def test_cross_validate_all_agree():
    """测试三个信号全部一致"""
    signals = {"financial": "positive", "news": "positive", "report": "positive"}
    consistency, conflicts, confidence = _cross_validate(signals)
    assert consistency == 1.0
    assert len(conflicts) == 0
    assert confidence == 1.0


def test_cross_validate_conflict():
    """测试信号矛盾"""
    signals = {"financial": "positive", "news": "negative", "report": "positive"}
    consistency, conflicts, confidence = _cross_validate(signals)
    assert consistency < 1.0
    assert len(conflicts) >= 1


def test_cross_validate_insufficient_signals():
    """测试有效信号不足"""
    signals = {"financial": "positive", "news": "unknown", "report": "unknown"}
    consistency, conflicts, confidence = _cross_validate(signals)
    assert consistency == 0.5
    assert confidence == 0.3


# ========================================
# validator_node 测试
# ========================================

def test_validator_node_consistent():
    """测试 validator_node 一致场景"""
    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["financial_data"] = {
        "raw_metrics": {"profit": "970亿，同比增长5%"},
        "metrics": {"revenue": 3832.0, "profit": 970.0},
        "ratios": {"net_margin": 0.2531},
    }
    state["news_data"] = [
        {"title": "超预期", "sentiment": "positive"},
        {"title": "增长", "sentiment": "positive"},
        {"title": "调查", "sentiment": "negative"},
    ]
    state["report_data"] = [{"title": "维持买入", "rating": "买入"}]

    result = validator_node(state)
    assert result["status"] == "running"
    vr = result["validation_result"]
    assert vr["signals"]["financial"] == "positive"
    assert vr["signals"]["news"] == "positive"
    assert vr["signals"]["report"] == "positive"
    assert vr["consistency_score"] == 1.0
    assert len(vr["conflicts"]) == 0


def test_validator_node_conflict():
    """测试 validator_node 矛盾场景"""
    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["financial_data"] = {
        "raw_metrics": {"profit": "970亿，同比增长5%"},
        "ratios": {"net_margin": 0.2531},
    }
    state["news_data"] = [
        {"title": "下滑", "sentiment": "negative"},
        {"title": "调查", "sentiment": "negative"},
        {"title": "召回", "sentiment": "negative"},
    ]
    state["report_data"] = [{"title": "维持买入", "rating": "买入"}]

    result = validator_node(state)
    assert result["status"] == "running"
    vr = result["validation_result"]
    assert vr["signals"]["financial"] == "positive"
    assert vr["signals"]["news"] == "negative"
    assert vr["consistency_score"] < 1.0
    assert len(vr["conflicts"]) >= 1


def test_validator_node_empty_data():
    """测试空数据场景"""
    state = create_initial_state("t1", "u1", "user", "AAPL")
    result = validator_node(state)
    assert result["status"] == "running"
    vr = result["validation_result"]
    # 三个信号都是 unknown，有效信号不足
    assert vr["consistency_score"] == 0.5
