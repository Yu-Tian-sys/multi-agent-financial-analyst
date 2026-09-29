import logging
from typing import Dict, List

from src.db import Database

logger = logging.getLogger(__name__)


class Metrics:
    """可观测性指标：从 traces 表聚合统计"""

    def __init__(self, db: Database):
        """
        初始化

        Args:
            db: Database 实例
        """
        self.db = db

    def overview(self, days: int = 1) -> Dict:
        """
        总览统计

        Args:
            days: 统计最近多少天

        Returns:
            {total_traces, total_events, total_tokens, total_cost,
             avg_duration_per_trace, error_count, error_rate}
        """
        # traces 表聚合：追踪数/事件数/耗时/错误（traces 表不记录 token/cost，
        # 因为 _wrap 记录事件时不持有 LLM 调用的 token 数）
        cursor = self.db.conn.execute(
            f"""
            SELECT
                COUNT(DISTINCT trace_id) as total_traces,
                COUNT(*) as total_events,
                COALESCE(SUM(duration), 0.0) as total_duration,
                SUM(CASE WHEN action = 'error' THEN 1 ELSE 0 END) as error_count
            FROM traces
            WHERE created_at > datetime('now', '-{days} day')
            """
        )
        row = cursor.fetchone()
        total_traces = row["total_traces"] or 0
        total_events = row["total_events"] or 0
        error_count = row["error_count"] or 0
        total_duration = row["total_duration"] or 0.0

        # tokens/cost 从 tasks 表聚合（与 /cost 接口一致；traces 表无此数据）
        cursor2 = self.db.conn.execute(
            f"""
            SELECT
                COALESCE(SUM(total_tokens), 0) as total_tokens,
                COALESCE(SUM(total_cost), 0.0) as total_cost
            FROM tasks
            WHERE created_at > datetime('now', '-{days} day')
            """
        )
        row2 = cursor2.fetchone()

        return {
            "total_traces": total_traces,
            "total_events": total_events,
            "total_tokens": row2["total_tokens"] or 0,
            "total_cost": round(row2["total_cost"] or 0.0, 6),
            "avg_duration_per_trace": round(total_duration / total_traces, 3) if total_traces > 0 else 0.0,
            "error_count": error_count,
            "error_rate": round(error_count / total_events, 4) if total_events > 0 else 0.0,
        }

    def by_agent(self, days: int = 1) -> List[Dict]:
        """
        按 Agent 分组统计

        Args:
            days: 统计最近多少天

        Returns:
            [{agent, events, llm_calls, total_tokens, total_cost,
              avg_duration, max_duration}, ...]
        """
        cursor = self.db.conn.execute(
            f"""
            SELECT
                agent,
                COUNT(*) as events,
                SUM(CASE WHEN action = 'llm_call' THEN 1 ELSE 0 END) as llm_calls,
                COALESCE(SUM(tokens), 0) as total_tokens,
                COALESCE(SUM(cost), 0.0) as total_cost,
                COALESCE(AVG(duration), 0.0) as avg_duration,
                COALESCE(MAX(duration), 0.0) as max_duration
            FROM traces
            WHERE created_at > datetime('now', '-{days} day')
            GROUP BY agent
            ORDER BY events DESC
            """
        )
        rows = cursor.fetchall()
        return [
            {
                "agent": r["agent"],
                "events": r["events"],
                "llm_calls": r["llm_calls"] or 0,
                "total_tokens": r["total_tokens"] or 0,
                "total_cost": round(r["total_cost"] or 0.0, 6),
                "avg_duration": round(r["avg_duration"] or 0.0, 3),
                "max_duration": round(r["max_duration"] or 0.0, 3),
            }
            for r in rows
        ]

    def latency(self, days: int = 1) -> Dict:
        """
        延迟统计（P50/P90/P95/P99/max）

        Args:
            days: 统计最近多少天

        Returns:
            {p50, p90, p95, p99, max, count}
        """
        cursor = self.db.conn.execute(
            f"""
            SELECT duration FROM traces
            WHERE created_at > datetime('now', '-{days} day')
              AND duration IS NOT NULL
              AND duration > 0
            ORDER BY duration ASC
            """
        )
        durations = [r["duration"] for r in cursor.fetchall()]

        if not durations:
            return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0, "count": 0}

        def percentile(data, p):
            """计算百分位"""
            if not data:
                return 0.0
            k = (len(data) - 1) * p
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            if f == c:
                return data[f]
            return data[f] + (data[c] - data[f]) * (k - f)

        return {
            "p50": round(percentile(durations, 0.5), 3),
            "p90": round(percentile(durations, 0.9), 3),
            "p95": round(percentile(durations, 0.95), 3),
            "p99": round(percentile(durations, 0.99), 3),
            "max": round(max(durations), 3),
            "count": len(durations),
        }

    def errors(self, days: int = 1, limit: int = 20) -> List[Dict]:
        """
        最近 N 条错误事件

        Args:
            days: 统计最近多少天
            limit: 返回条数上限

        Returns:
            [{agent, content, created_at}, ...]
        """
        cursor = self.db.conn.execute(
            f"""
            SELECT agent, content, created_at FROM traces
            WHERE created_at > datetime('now', '-{days} day')
              AND action = 'error'
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(r) for r in cursor.fetchall()]


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    import tempfile, os
    from src.db import Database
    from src.observability.tracer import Tracer

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)

    # 造点数据
    tracer = Tracer(db=db)
    tracer.start_trace("tr1", task_id="t1", topic="AAPL")
    tracer.log_event("tr1", "planner", "llm_call", "识别", duration=1.5, tokens=100, cost=0.0001, task_id="t1")
    tracer.log_event("tr1", "financial", "end", "完成", duration=0.5, task_id="t1")
    tracer.log_event("tr1", "debate", "error", "超时", task_id="t1")

    tracer.start_trace("tr2", task_id="t2", topic="TSLA")
    tracer.log_event("tr2", "planner", "llm_call", "识别", duration=2.0, tokens=150, cost=0.00015, task_id="t2")
    tracer.log_event("tr2", "news", "end", "完成", duration=1.0, task_id="t2")

    # 指标
    m = Metrics(db)
    print("总览:", m.overview())
    print()
    print("按 Agent:")
    for a in m.by_agent():
        print(f"  {a}")
    print()
    print("延迟:", m.latency())
    print()
    print("错误:", m.errors())

    db.close()
    os.remove(path)
