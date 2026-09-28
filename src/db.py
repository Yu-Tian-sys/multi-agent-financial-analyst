import sqlite3
import json
import os
from datetime import datetime
from typing import Optional


class Database:
    """SQLite 数据库封装，负责任务状态持久化"""

    # 需要 JSON 序列化/反序列化的字段（list/dict 类型）
    JSON_FIELDS = [
        "subtasks", "financial_data", "news_data", "report_data", "market_data",
        "validation_result", "debate_records", "risk_assessment", "report_references",
        "compliance_result", "messages",
    ]

    def __init__(self, db_path: str = "./data/agent.db"):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径
        """
        # 确保目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        self.db_path = db_path
        # check_same_thread=False 允许跨线程使用（FastAPI 多线程需要）
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        # 让查询结果可以按列名访问
        self.conn.row_factory = sqlite3.Row
        # 开启 WAL 模式，允许并发读 + 单写，减少多线程锁等待
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self._init_tables()

    def _init_tables(self):
        """创建所有表（如果不存在）"""
        cursor = self.conn.cursor()

        # 1. 任务表：存任务状态
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_role TEXT NOT NULL,
                topic TEXT NOT NULL,
                company_type TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                current_step INTEGER DEFAULT 0,
                total_steps INTEGER DEFAULT 0,
                subtasks TEXT DEFAULT '[]',
                financial_data TEXT DEFAULT '{}',
                news_data TEXT DEFAULT '[]',
                report_data TEXT DEFAULT '[]',
                market_data TEXT DEFAULT '{}',
                validation_result TEXT DEFAULT '{}',
                debate_records TEXT DEFAULT '[]',
                debate_rounds INTEGER DEFAULT 0,
                risk_assessment TEXT DEFAULT '{}',
                draft_report TEXT DEFAULT '',
                final_report TEXT DEFAULT '',
                report_references TEXT DEFAULT '[]',
                compliance_result TEXT DEFAULT '{}',
                messages TEXT DEFAULT '[]',
                error TEXT DEFAULT '',
                start_time REAL DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # 2. 消息表：存对话历史（独立于 tasks，方便查询）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                created_at TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            )
        """)

        # 3. 工具调用表：含幂等性（同一 tool_call_id 只执行一次）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_calls (
                task_id TEXT NOT NULL,
                tool_call_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                arguments TEXT DEFAULT '{}',
                result TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                PRIMARY KEY (task_id, tool_call_id)
            )
        """)

        # 4. 审计日志表：记录所有危险操作
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT,
                action TEXT NOT NULL,
                detail TEXT,
                status TEXT DEFAULT 'success',
                created_at TEXT
            )
        """)

        # 5. 情景记忆表：存用户长期事实
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                user_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT,
                PRIMARY KEY (user_id, key)
            )
        """)

        # 6. 成本记录表：每次 LLM 调用记录 token 和成本
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                model TEXT,
                tokens INTEGER DEFAULT 0,
                cost REAL DEFAULT 0.0,
                created_at TEXT
            )
        """)

        # 建索引，加速查询
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_task ON messages(task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cost_task ON cost_log(task_id)")

        self.conn.commit()

    def close(self):
        """关闭连接"""
        self.conn.close()

    # ========================================
    # 任务相关方法
    # ========================================

    def create_task(self, task_id: str, user_id: str, user_role: str, topic: str) -> None:
        """创建新任务，status='pending'，其他字段用默认值"""
        now = datetime.now().isoformat()
        self.conn.execute(
            """INSERT INTO tasks (task_id, user_id, user_role, topic, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'pending', ?, ?)""",
            (task_id, user_id, user_role, topic, now, now),
        )
        self.conn.commit()

    def get_task(self, task_id: str) -> Optional[dict]:
        """读取任务，JSON 字段自动反序列化为 Python 对象；不存在返回 None"""
        cursor = self.conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return None
        task = dict(row)
        # 反序列化 JSON 字段
        for field in self.JSON_FIELDS:
            if field in task and task[field]:
                try:
                    task[field] = json.loads(task[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return task

    def list_tasks(self, limit: int = 50, offset: int = 0) -> list:
        """按创建时间倒序返回任务列表（只返回列表需要的字段）。

        Args:
            limit: 返回条数上限
            offset: 跳过条数（用于分页）

        Returns:
            任务摘要列表，每条含 task_id / topic / status / created_at / updated_at / total_cost
        """
        cursor = self.conn.execute(
            "SELECT task_id, topic, status, created_at, updated_at, total_cost "
            "FROM tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [dict(row) for row in cursor.fetchall()]

    def update_task(self, task_id: str, **kwargs) -> None:
        """更新任务任意字段，list/dict 自动 json.dumps，自动更新 updated_at"""
        if not kwargs:
            return
        # 自动序列化 list/dict
        for key, value in kwargs.items():
            if isinstance(value, (list, dict)):
                kwargs[key] = json.dumps(value, ensure_ascii=False)
        kwargs["updated_at"] = datetime.now().isoformat()
        sets = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [task_id]
        self.conn.execute(f"UPDATE tasks SET {sets} WHERE task_id = ?", values)
        self.conn.commit()

    def mark_completed(self, task_id: str) -> None:
        """标记任务完成"""
        self.update_task(task_id, status="completed")

    def mark_failed(self, task_id: str, error: str) -> None:
        """标记任务失败，记录错误信息"""
        self.update_task(task_id, status="failed", error=str(error))

    # ========================================
    # 消息相关方法
    # ========================================

    def save_message(self, task_id: str, role: str, content: str) -> None:
        """保存消息：写入 messages 表 + 追加到 tasks.messages（同一事务）"""
        now = datetime.now().isoformat()
        # 1. 插入 messages 表
        self.conn.execute(
            "INSERT INTO messages (task_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (task_id, role, content, now),
        )
        # 2. 追加到 tasks.messages
        cursor = self.conn.execute("SELECT messages FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        if row:
            messages = json.loads(row[0]) if row[0] else []
            messages.append({"role": role, "content": content})
            self.conn.execute(
                "UPDATE tasks SET messages = ?, updated_at = ? WHERE task_id = ?",
                (json.dumps(messages, ensure_ascii=False), now, task_id),
            )
        self.conn.commit()

    def get_messages(self, task_id: str, limit: int = 100) -> list:
        """读最近 limit 条消息，按 id 升序返回"""
        cursor = self.conn.execute(
            "SELECT role, content, created_at FROM messages WHERE task_id = ? ORDER BY id ASC LIMIT ?",
            (task_id, limit),
        )
        return [dict(r) for r in cursor.fetchall()]

    # ========================================
    # 工具调用相关方法
    # ========================================

    def is_tool_executed(self, task_id: str, tool_call_id: str) -> bool:
        """检查工具是否已成功执行（幂等性）"""
        cursor = self.conn.execute(
            "SELECT status FROM tool_calls WHERE task_id = ? AND tool_call_id = ?",
            (task_id, tool_call_id),
        )
        row = cursor.fetchone()
        return row is not None and row[0] == "success"

    def save_tool_result(self, task_id: str, tool_call_id: str, tool_name: str,
                         arguments: dict, result, status: str = "success") -> None:
        """插入或替换工具调用结果，arguments 自动 json.dumps"""
        now = datetime.now().isoformat()
        self.conn.execute(
            """INSERT OR REPLACE INTO tool_calls
               (task_id, tool_call_id, tool_name, arguments, result, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (task_id, tool_call_id, tool_name,
             json.dumps(arguments, ensure_ascii=False),
             str(result), status, now),
        )
        self.conn.commit()

    def get_tool_result(self, task_id: str, tool_call_id: str):
        """读工具结果，不存在返回 None"""
        cursor = self.conn.execute(
            "SELECT result FROM tool_calls WHERE task_id = ? AND tool_call_id = ?",
            (task_id, tool_call_id),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    # ========================================
    # 审计相关方法
    # ========================================

    def log_audit(self, user_id: str, role: str, action: str,
                  detail: str, status: str = "success") -> None:
        """记录审计日志"""
        self.conn.execute(
            "INSERT INTO audit_log (user_id, role, action, detail, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, role, action, str(detail), status, datetime.now().isoformat()),
        )
        self.conn.commit()

    def get_audit_log(self, user_id: str, limit: int = 50) -> list:
        """读某用户最近 limit 条审计记录，按时间倒序"""
        cursor = self.conn.execute(
            "SELECT action, detail, status, created_at FROM audit_log WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        return [dict(r) for r in cursor.fetchall()]

    # ========================================
    # 记忆相关方法
    # ========================================

    def save_memory(self, user_id: str, key: str, value: str) -> None:
        """保存或更新一条记忆（user_id + key 联合主键）"""
        self.conn.execute(
            "INSERT OR REPLACE INTO memories (user_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, key, value, datetime.now().isoformat()),
        )
        self.conn.commit()

    def get_memories(self, user_id: str) -> list:
        """读某用户所有记忆"""
        cursor = self.conn.execute(
            "SELECT key, value, updated_at FROM memories WHERE user_id = ?",
            (user_id,),
        )
        return [dict(r) for r in cursor.fetchall()]

    def delete_memory(self, user_id: str, key: str) -> None:
        """删除一条记忆"""
        self.conn.execute(
            "DELETE FROM memories WHERE user_id = ? AND key = ?",
            (user_id, key),
        )
        self.conn.commit()

    # ========================================
    # 成本相关方法
    # ========================================

    def log_cost(self, task_id: str, model: str, tokens: int, cost: float) -> None:
        """记录一次 LLM 调用的 token 和成本"""
        self.conn.execute(
            "INSERT INTO cost_log (task_id, model, tokens, cost, created_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, model, tokens, cost, datetime.now().isoformat()),
        )
        self.conn.commit()


