import os
import pytest
import tempfile
from src.db import Database
from src.observability.tracer import Tracer
from src.observability.metrics import Metrics
from src.observability.dashboard import (
    trace_to_mermaid, trace_report, overview_report
)


@pytest.fixture
def db():
    """临时数据库"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    yield database
    database.close()
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def tracer_with_data(db):
    """带测试数据的 tracer"""
    t = Tracer(db=db)
    t.start_trace("tr1", task_id="t1", topic="AAPL")
    t.log_event("tr1", "planner", "start", "开始规划", task_id="t1")
    t.log_event("tr1", "planner", "llm_call", "识别", duration=1.5, tokens=100, cost=0.0001, task_id="t1")
    t.log_event("tr1", "planner", "end", "完成", duration=2.0, task_id="t1")
    t.log_event("tr1", "financial", "end", "财报完成", duration=0.5, task_id="t1")
    t.log_event("tr1", "debate", "error", "超时", task_id="t1")
    return t


# ========================================
# tracer 测试
# ========================================

def test_tracer_start_and_log(db):
    """测试开始追踪和记录事件"""
    t = Tracer(db=db)
    t.start_trace("tr1", task_id="t1", topic="AAPL")
    assert len(t.get_trace("tr1")) == 1
    t.log_event("tr1", "planner", "start", "test")
    assert len(t.get_trace("tr1")) == 2


def test_tracer_persistence(db):
    """测试持久化到数据库"""
    t = Tracer(db=db)
    t.start_trace("tr1", task_id="t1", topic="AAPL")
    t.log_event("tr1", "planner", "llm_call", "test", tokens=100)
    from_db = t.get_trace_from_db("tr1")
    assert len(from_db) == 2
    assert from_db[0]["agent"] == "system"


def test_tracer_summary(tracer_with_data):
    """测试汇总"""
    s = tracer_with_data.summary("tr1")
    assert s["total_events"] == 6
    assert s["total_tokens"] == 100
    assert "planner" in s["agents"]


def test_tracer_content_truncation(db):
    """测试内容截断到 200 字"""
    t = Tracer(db=db)
    t.start_trace("tr1")
    long_content = "a" * 500
    t.log_event("tr1", "planner", "start", long_content)
    events = t.get_trace("tr1")
    assert len(events[-1]["content"]) <= 200


def test_tracer_clear(tracer_with_data):
    """测试清空内存"""
    tracer_with_data.clear()
    assert len(tracer_with_data.get_trace("tr1")) == 0


# ========================================
# metrics 测试
# ========================================

def test_metrics_overview(db, tracer_with_data):
    """测试总览指标"""
    m = Metrics(db)
    o = m.overview(days=1)
    assert o["total_traces"] == 1
    assert o["total_events"] == 6
    assert o["total_tokens"] == 100
    assert o["error_count"] == 1


def test_metrics_by_agent(db, tracer_with_data):
    """测试按 Agent 统计"""
    m = Metrics(db)
    agents = m.by_agent(days=1)
    agent_names = [a["agent"] for a in agents]
    assert "planner" in agent_names
    planner = next(a for a in agents if a["agent"] == "planner")
    assert planner["llm_calls"] == 1
    assert planner["total_tokens"] == 100


def test_metrics_latency(db, tracer_with_data):
    """测试延迟统计"""
    m = Metrics(db)
    lat = m.latency(days=1)
    assert lat["count"] == 3  # 3 条有 duration 的事件
    assert lat["max"] >= 2.0


def test_metrics_errors(db, tracer_with_data):
    """测试错误列表"""
    m = Metrics(db)
    errs = m.errors(days=1)
    assert len(errs) == 1
    assert errs[0]["agent"] == "debate"


# ========================================
# dashboard 测试
# ========================================

def test_trace_to_mermaid(tracer_with_data):
    """测试 Mermaid 生成"""
    mer = trace_to_mermaid(tracer_with_data, "tr1")
    assert "sequenceDiagram" in mer
    assert "participant system" in mer
    assert "planner" in mer


def test_trace_to_mermaid_empty(db):
    """测试空追踪"""
    t = Tracer(db=db)
    mer = trace_to_mermaid(t, "not_exist")
    assert "sequenceDiagram" in mer


def test_trace_report(tracer_with_data):
    """测试文本报告"""
    report = trace_report(tracer_with_data, "tr1")
    assert "# Trace 报告" in report
    assert "总 tokens" in report


def test_overview_report(db, tracer_with_data):
    """测试总览报告"""
    m = Metrics(db)
    report = overview_report(m)
    assert "可观测性总览" in report
    assert "延迟分布" in report
