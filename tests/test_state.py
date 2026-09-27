import pytest
from src.state import FinanceState, create_initial_state


def test_create_initial_state():
    """测试创建初始状态"""
    state = create_initial_state(
        task_id="test-001",
        user_id="user-001",
        user_role="user",
        topic="AAPL"
    )
    assert state["task_id"] == "test-001"
    assert state["user_id"] == "user-001"
    assert state["user_role"] == "user"
    assert state["topic"] == "AAPL"
    assert state["status"] == "pending"
    assert state["messages"] == []
    assert state["total_tokens"] == 0
    assert state["total_cost"] == 0.0
    assert state["current_step"] == 0


def test_messages_append():
    """测试 messages 字段的 Annotated 追加是否生效"""
    from langgraph.graph import StateGraph, END

    def node_a(state: FinanceState):
        return {"messages": [{"role": "user", "content": "hello"}]}

    def node_b(state: FinanceState):
        return {"messages": [{"role": "assistant", "content": "hi"}]}

    graph = StateGraph(FinanceState)
    graph.add_node("a", node_a)
    graph.add_node("b", node_b)
    graph.set_entry_point("a")
    graph.add_edge("a", "b")
    graph.add_edge("b", END)
    app = graph.compile()

    state = create_initial_state("t", "u", "user", "topic")
    result = app.invoke(state)

    assert len(result["messages"]) == 2
    assert result["messages"][0]["content"] == "hello"
    assert result["messages"][1]["content"] == "hi"


def test_all_fields_exist():
    """测试所有字段都存在"""
    state = create_initial_state("t", "u", "user", "topic")
    required_fields = [
        "task_id", "user_id", "user_role", "topic", "company_type",
        "subtasks", "current_step", "total_steps",
        "financial_data", "news_data", "report_data", "market_data",
        "validation_result", "debate_records", "debate_rounds",
        "risk_assessment", "draft_report", "final_report", "report_references",
        "compliance_result", "messages", "status", "error",
        "start_time", "total_tokens", "total_cost",
    ]
    for field in required_fields:
        assert field in state, f"缺少字段：{field}"
