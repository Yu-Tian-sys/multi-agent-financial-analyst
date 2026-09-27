import json
import logging
import threading
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class Tracer:
    """Agent 流水线追踪器：记录每个 Agent 的事件，支持查询和汇总"""

    def __init__(self, db=None):
        """
        初始化

        Args:
            db: 可选的 Database 实例，用于持久化
        """
        self.db = db
        self.events: Dict[str, List[Dict]] = {}
        self._lock = threading.Lock()  # 串行化 DB 写入

        if db is not None:
            self._init_table()

    def _init_table(self) -> None:
        """创建 traces 表（如果不存在）"""
        self.db.conn.execute("""
            CREATE TABLE IF NOT EXISTS traces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                task_id TEXT,
                agent TEXT NOT NULL,
                action TEXT NOT NULL,
                content TEXT,
                metadata TEXT,
                duration REAL,
                tokens INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                created_at TEXT
            )
        """)
        self.db.conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_trace ON traces(trace_id)")
        self.db.conn.execute("CREATE INDEX IF NOT EXISTS idx_traces_task ON traces(task_id)")
        self.db.conn.commit()

    def start_trace(self, trace_id: str, task_id: str = "", topic: str = "") -> None:
        """
        开始一个追踪

        Args:
            trace_id: 追踪 ID
            task_id: 任务 ID
            topic: 分析标的
        """
        self.events[trace_id] = []
        self.log_event(
            trace_id=trace_id,
            agent="system",
            action="start",
            content=f"开始追踪：{topic}",
            metadata={"topic": topic},
            task_id=task_id,
        )
        logger.info(f"[tracer] 开始追踪：{trace_id} / {topic}")

    def log_event(
        self,
        trace_id: str,
        agent: str,
        action: str,
        content: str = "",
        metadata: Optional[Dict] = None,
        duration: Optional[float] = None,
        tokens: int = 0,
        cost: float = 0.0,
        task_id: str = "",
    ) -> None:
        """
        记录一条事件

        Args:
            trace_id: 追踪 ID
            agent: Agent 名（precheck/planner/...）
            action: 动作类型（start/end/think/tool_call/llm_call/error）
            content: 内容摘要（截断到 200 字）
            metadata: 额外信息
            duration: 耗时（秒）
            tokens: token 数
            cost: 成本（元）
            task_id: 任务 ID
        """
        event = {
            "trace_id": trace_id,
            "task_id": task_id,
            "agent": agent,
            "action": action,
            "content": (content or "")[:200],
            "metadata": metadata or {},
            "duration": duration,
            "tokens": tokens,
            "cost": cost,
            "timestamp": datetime.now().isoformat(),
        }

        # 写内存
        if trace_id not in self.events:
            self.events[trace_id] = []
        self.events[trace_id].append(event)

        # 写数据库（加锁，防止多线程并发写冲突）
        if self.db is not None:
            with self._lock:
                try:
                    self.db.conn.execute(
                        """INSERT INTO traces
                           (trace_id, task_id, agent, action, content, metadata,
                            duration, tokens, cost, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            trace_id, task_id, agent, action, event["content"],
                            json.dumps(event["metadata"], ensure_ascii=False),
                            duration, tokens, cost, event["timestamp"],
                        )
                    )
                    self.db.conn.commit()
                except Exception as e:
                    logger.warning(f"[tracer] 持久化失败：{e}")

    def get_trace(self, trace_id: str) -> List[Dict]:
        """
        从内存读该 trace 的所有事件

        Args:
            trace_id: 追踪 ID

        Returns:
            事件列表
        """
        return self.events.get(trace_id, [])

    def get_trace_from_db(self, trace_id: str) -> List[Dict]:
        """
        从数据库读该 trace 的所有事件

        Args:
            trace_id: 追踪 ID

        Returns:
            事件列表（按时间顺序）
        """
        if self.db is None:
            return []
        cursor = self.db.conn.execute(
            """SELECT agent, action, content, metadata, duration, tokens, cost, created_at
               FROM traces WHERE trace_id = ? ORDER BY id ASC""",
            (trace_id,)
        )
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            # 反序列化 metadata
            try:
                d["metadata"] = json.loads(d.get("metadata") or "{}")
            except json.JSONDecodeError:
                d["metadata"] = {}
            result.append(d)
        return result

    def summary(self, trace_id: str) -> Dict:
        """
        汇总统计

        Args:
            trace_id: 追踪 ID

        Returns:
            {trace_id, total_events, agents, total_tokens, total_cost, total_duration}
        """
        events = self.get_trace(trace_id)
        if not events:
            return {
                "trace_id": trace_id,
                "total_events": 0,
                "agents": [],
                "total_tokens": 0,
                "total_cost": 0.0,
                "total_duration": 0.0,
            }

        agents = sorted(set(e["agent"] for e in events))
        total_tokens = sum(e.get("tokens", 0) or 0 for e in events)
        total_cost = sum(e.get("cost", 0.0) or 0.0 for e in events)
        total_duration = sum(e.get("duration", 0.0) or 0.0 for e in events)

        return {
            "trace_id": trace_id,
            "total_events": len(events),
            "agents": agents,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 6),
            "total_duration": round(total_duration, 3),
        }

    def clear(self) -> None:
        """清空内存（不影响数据库）"""
        self.events.clear()
        logger.info("[tracer] 内存已清空")


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    tracer = Tracer()

    # 模拟一个追踪
    tracer.start_trace("trace-001", task_id="t1", topic="AAPL")
    tracer.log_event("trace-001", "planner", "start", "开始规划")
    tracer.log_event("trace-001", "planner", "llm_call", "识别公司类型", duration=1.5, tokens=100, cost=0.0001)
    tracer.log_event("trace-001", "planner", "end", "生成 4 个子任务", duration=2.0)
    tracer.log_event("trace-001", "financial", "start", "开始财报分析")
    tracer.log_event("trace-001", "financial", "end", "提取 5 个指标", duration=0.5)
    tracer.log_event("trace-001", "system", "end", "流水线完成", duration=10.0)

    # 查询
    events = tracer.get_trace("trace-001")
    print(f"事件数：{len(events)}")
    for e in events:
        print(f"  [{e['agent']}/{e['action']}] {e['content'][:40]}")

    # 汇总
    print()
    print("汇总：", tracer.summary("trace-001"))
