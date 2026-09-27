import pytest
import os
import tempfile
from src.db import Database


@pytest.fixture
def db():
    """每个测试用独立的临时数据库"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    yield database
    database.close()
    if os.path.exists(path):
        os.remove(path)


def test_create_and_get_task(db):
    """测试创建和读取任务"""
    db.create_task("t1", "u1", "user", "AAPL")
    task = db.get_task("t1")
    assert task is not None
    assert task["task_id"] == "t1"
    assert task["user_id"] == "u1"
    assert task["topic"] == "AAPL"
    assert task["status"] == "pending"
    assert task["current_step"] == 0


def test_get_nonexistent_task(db):
    """测试读取不存在的任务返回 None"""
    assert db.get_task("not_exist") is None


def test_update_task(db):
    """测试更新任务"""
    db.create_task("t1", "u1", "user", "AAPL")
    db.update_task("t1", status="running", current_step=3)
    task = db.get_task("t1")
    assert task["status"] == "running"
    assert task["current_step"] == 3


def test_update_task_with_json(db):
    """测试更新任务时 list/dict 自动序列化"""
    db.create_task("t1", "u1", "user", "AAPL")
    db.update_task("t1", subtasks=[{"id": 1, "task": "研究"}], market_data={"price": 250})
    task = db.get_task("t1")
    assert task["subtasks"] == [{"id": 1, "task": "研究"}]
    assert task["market_data"] == {"price": 250}


def test_mark_completed_and_failed(db):
    """测试标记完成和失败"""
    db.create_task("t1", "u1", "user", "AAPL")
    db.mark_completed("t1")
    assert db.get_task("t1")["status"] == "completed"

    db.create_task("t2", "u1", "user", "AAPL")
    db.mark_failed("t2", "测试错误")
    task = db.get_task("t2")
    assert task["status"] == "failed"
    assert task["error"] == "测试错误"


def test_save_and_get_messages(db):
    """测试保存和读取消息"""
    db.create_task("t1", "u1", "user", "AAPL")
    db.save_message("t1", "user", "你好")
    db.save_message("t1", "assistant", "你好，我是助手")
    msgs = db.get_messages("t1")
    assert len(msgs) == 2
    assert msgs[0]["content"] == "你好"
    assert msgs[1]["content"] == "你好，我是助手"
    # 同时应该追加到 tasks.messages
    task = db.get_task("t1")
    assert len(task["messages"]) == 2


def test_tool_idempotency(db):
    """测试工具调用幂等性"""
    db.create_task("t1", "u1", "user", "AAPL")
    assert not db.is_tool_executed("t1", "call_001")
    db.save_tool_result("t1", "call_001", "get_stock_price", {"symbol": "AAPL"}, "$250.5")
    assert db.is_tool_executed("t1", "call_001")
    assert db.get_tool_result("t1", "call_001") == "$250.5"


def test_tool_result_nonexistent(db):
    """测试读取不存在的工具结果"""
    assert db.get_tool_result("t1", "not_exist") is None


def test_audit_log(db):
    """测试审计日志"""
    db.log_audit("u1", "user", "query_stock", "AAPL", "success")
    db.log_audit("u1", "user", "query_stock", "GOOGL", "success")
    logs = db.get_audit_log("u1")
    assert len(logs) == 2
    # 倒序，最新的在前
    assert logs[0]["detail"] == "GOOGL"


def test_memories(db):
    """测试记忆的增删查"""
    db.save_memory("u1", "用户偏好", "关注科技股")
    db.save_memory("u1", "风险承受", "中等")
    mems = db.get_memories("u1")
    assert len(mems) == 2

    db.delete_memory("u1", "风险承受")
    mems = db.get_memories("u1")
    assert len(mems) == 1
    assert mems[0]["key"] == "用户偏好"


def test_memory_overwrite(db):
    """测试记忆覆盖（同 key 更新）"""
    db.save_memory("u1", "用户偏好", "科技股")
    db.save_memory("u1", "用户偏好", "消费股")
    mems = db.get_memories("u1")
    assert len(mems) == 1
    assert mems[0]["value"] == "消费股"


def test_log_cost(db):
    """测试成本记录"""
    db.create_task("t1", "u1", "user", "AAPL")
    db.log_cost("t1", "deepseek-chat", 1500, 0.0015)
    cursor = db.conn.execute("SELECT * FROM cost_log WHERE task_id = ?", ("t1",))
    row = cursor.fetchone()
    assert row is not None
    assert row["tokens"] == 1500
    assert abs(row["cost"] - 0.0015) < 1e-9
