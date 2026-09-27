import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def _escape_mermaid(text: str) -> str:
    """转义 Mermaid 特殊字符"""
    return (text or "").replace('"', "'").replace("\n", " ")[:50]


def trace_to_mermaid(tracer, trace_id: str) -> str:
    """
    把 trace 转成 Mermaid 时序图

    Args:
        tracer: Tracer 实例
        trace_id: 追踪 ID

    Returns:
        Mermaid 代码字符串
    """
    events = tracer.get_trace(trace_id)
    if not events:
        return "sequenceDiagram\n    Note over system: 无事件"

    # 收集所有 agent
    agents = sorted(set(e["agent"] for e in events if e["agent"] != "system"))

    lines = ["sequenceDiagram"]
    lines.append("    participant system")
    for a in agents:
        lines.append(f"    participant {a}")

    # 遍历事件画箭头
    for e in events:
        agent = e["agent"]
        action = e["action"]
        content = _escape_mermaid(e.get("content", ""))
        duration = e.get("duration")
        tokens = e.get("tokens", 0)

        if agent == "system":
            # system 自己的事件用 Note
            if action == "start":
                lines.append(f"    Note over system: 开始 {content}")
            elif action == "end":
                lines.append(f"    Note over system: 完成 {content}")
            continue

        if action == "start":
            lines.append(f"    system->>{agent}: start")
        elif action == "end":
            lines.append(f"    {agent}-->>system: end ({duration}s)")
        elif action == "llm_call":
            info = f"LLM {tokens}tok"
            if duration:
                info += f" / {duration}s"
            lines.append(f"    Note over {agent}: {info}")
        elif action == "tool_call":
            lines.append(f"    Note over {agent}: 工具 {content}")
        elif action == "error":
            lines.append(f"    Note over {agent}: ERROR {content}")

    return "\n".join(lines)


def trace_report(tracer, trace_id: str) -> str:
    """
    单次 trace 的文本报告

    Args:
        tracer: Tracer 实例
        trace_id: 追踪 ID

    Returns:
        Markdown 格式报告
    """
    events = tracer.get_trace(trace_id)
    if not events:
        return f"# Trace {trace_id}\n\n无事件。"

    s = tracer.summary(trace_id)

    lines = [
        f"# Trace 报告：{trace_id}",
        "",
        f"- 事件数：{s['total_events']}",
        f"- 涉及 Agent：{', '.join(s['agents'])}",
        f"- 总 tokens：{s['total_tokens']}",
        f"- 总成本：{s['total_cost']} 元",
        f"- 总耗时：{s['total_duration']} 秒",
        "",
        "## 事件时间线",
        "",
        "| # | Agent | Action | 内容 | 耗时 | Tokens |",
        "|---|-------|--------|------|------|--------|",
    ]

    for i, e in enumerate(events, 1):
        content = (e.get("content", "") or "")[:50]
        duration = e.get("duration") or "-"
        tokens = e.get("tokens") or "-"
        lines.append(
            f"| {i} | {e['agent']} | {e['action']} | {content} | {duration} | {tokens} |"
        )

    return "\n".join(lines)


def overview_report(metrics) -> str:
    """
    全局概览报告

    Args:
        metrics: Metrics 实例

    Returns:
        Markdown 格式报告
    """
    o = metrics.overview(days=1)
    by_agent = metrics.by_agent(days=1)
    lat = metrics.latency(days=1)
    errs = metrics.errors(days=1, limit=5)

    lines = [
        "# 可观测性总览（最近 24 小时）",
        "",
        "## 总览",
        "",
        f"- 追踪数：{o['total_traces']}",
        f"- 事件数：{o['total_events']}",
        f"- 总 tokens：{o['total_tokens']}",
        f"- 总成本：{o['total_cost']} 元",
        f"- 平均每次追踪耗时：{o['avg_duration_per_trace']} 秒",
        f"- 错误数：{o['error_count']}（错误率 {o['error_rate']:.2%}）",
        "",
        "## Top 5 Agent（按事件数）",
        "",
        "| Agent | 事件数 | LLM 调用 | Tokens | 成本 | 平均耗时 | 最大耗时 |",
        "|-------|--------|----------|--------|------|----------|----------|",
    ]

    for a in by_agent[:5]:
        lines.append(
            f"| {a['agent']} | {a['events']} | {a['llm_calls']} | "
            f"{a['total_tokens']} | {a['total_cost']} | "
            f"{a['avg_duration']} | {a['max_duration']} |"
        )

    lines.extend([
        "",
        "## 延迟分布",
        "",
        f"- P50：{lat['p50']} 秒",
        f"- P90：{lat['p90']} 秒",
        f"- P95：{lat['p95']} 秒",
        f"- P99：{lat['p99']} 秒",
        f"- Max：{lat['max']} 秒",
        f"- 样本数：{lat['count']}",
        "",
        "## 最近错误",
        "",
    ])

    if errs:
        for e in errs:
            lines.append(f"- [{e['created_at']}] {e['agent']}: {e['content']}")
    else:
        lines.append("（无错误）")

    return "\n".join(lines)


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    import tempfile, os
    from src.db import Database
    from src.observability.tracer import Tracer
    from src.observability.metrics import Metrics

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)

    t = Tracer(db=db)
    t.start_trace("tr1", task_id="t1", topic="AAPL")
    t.log_event("tr1", "planner", "start", "开始规划", task_id="t1")
    t.log_event("tr1", "planner", "llm_call", "识别公司类型", duration=1.5, tokens=100, cost=0.0001, task_id="t1")
    t.log_event("tr1", "planner", "end", "生成4个子任务", duration=2.0, task_id="t1")
    t.log_event("tr1", "financial", "start", "开始财报分析", task_id="t1")
    t.log_event("tr1", "financial", "end", "提取5个指标", duration=0.5, task_id="t1")
    t.log_event("tr1", "debate", "error", "超时", task_id="t1")
    t.log_event("tr1", "system", "end", "流水线完成", duration=10.0, task_id="t1")

    print("=" * 60)
    print("Mermaid 图：")
    print("=" * 60)
    print(trace_to_mermaid(t, "tr1"))

    print()
    print("=" * 60)
    print("Trace 报告：")
    print("=" * 60)
    print(trace_report(t, "tr1"))

    print()
    print("=" * 60)
    print("总览报告：")
    print("=" * 60)
    m = Metrics(db)
    print(overview_report(m))

    db.close()
    os.remove(path)
