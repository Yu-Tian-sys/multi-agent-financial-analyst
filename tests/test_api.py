import pytest
from fastapi.testclient import TestClient
import src.main as main_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    """测试客户端：用临时数据库 + mock 流水线"""
    # 用临时数据库
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(main_module.settings, "db_path", db_path)

    # mock run_pipeline，避免真实调用
    def mock_run_pipeline(task_id, user_id, user_role, topic):
        return {
            "status": "completed",
            "final_report": "# 测试报告\n## 风险提示\n投资有风险。",
            "draft_report": "# 测试报告",
            "risk_assessment": {"risk_level": "低"},
            "compliance_result": {"passed": True},
            "total_tokens": 1000,
            "total_cost": 0.001,
            "error": "",
        }

    monkeypatch.setattr(main_module, "run_pipeline", mock_run_pipeline)

    # 触发 lifespan
    with TestClient(main_module.app) as c:
        yield c


def test_health(client):
    """测试健康检查"""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_analyze_empty_topic(client):
    """测试空 topic 被拒绝"""
    resp = client.post("/analyze", json={"topic": ""})
    assert resp.status_code == 400


def test_analyze_and_query(client):
    """测试提交任务 + 查询状态"""
    # 提交
    resp = client.post("/analyze", json={
        "topic": "AAPL",
        "user_id": "u1",
        "user_role": "user",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    task_id = data["task_id"]

    # 查询
    resp = client.get(f"/task/{task_id}")
    assert resp.status_code == 200
    task = resp.json()
    assert task["topic"] == "AAPL"
    assert task["user_id"] == "u1"


def test_task_not_found(client):
    """测试查询不存在的任务"""
    resp = client.get("/task/not-exist-task")
    assert resp.status_code == 404


def test_metrics(client):
    """测试统计接口"""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tasks" in data
    assert "completed" in data
    assert "failed" in data


def test_cost(client):
    """测试成本接口"""
    resp = client.get("/cost")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tokens" in data
    assert "total_cost" in data
    assert "tasks" in data
    assert "avg_cost_per_task" in data
    assert "llm_calls" in data  # 兼容旧字段
