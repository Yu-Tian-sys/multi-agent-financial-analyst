import logging
import time
from typing import Literal
from functools import partial

from langgraph.graph import StateGraph, END, START
from langgraph.constants import Send

from src.state import FinanceState
from src.db import Database
from src.agents.precheck import precheck_node
from src.agents.planner import planner_node
from src.agents.financial_analyst import financial_analyst_node
from src.agents.news_analyst import news_analyst_node
from src.agents.report_analyst import report_analyst_node
from src.agents.validator import validator_node
from src.agents.debate import debate_node
from src.agents.risk import risk_node
from src.agents.report_writer import report_writer_node
from src.agents.compliance import compliance_node
from src.memory.integration import recall_node, save_node
from src.observability.tracer import Tracer

logger = logging.getLogger(__name__)

# 全局 Tracer 实例（在 build_graph 中初始化）
_tracer = None


# ========================================
# 路由函数
# ========================================

def route_after_precheck(state: FinanceState) -> Literal["planner", "end"]:
    """
    precheck 后路由：通过则进入规划，不通过直接结束

    Args:
        state: 当前状态

    Returns:
        "planner" 或 "end"
    """
    if state.get("status") == "rejected":
        logger.warning(f"[graph] 预检拒绝：{state.get('error')}")
        return "end"
    return "planner"


def route_to_parallel(state: FinanceState) -> list:
    """
    planner 后并行派发到三个数据收集 Agent

    用 Send 实现 fan-out。

    Args:
        state: 当前状态

    Returns:
        Send 列表
    """
    logger.info("[graph] 并行派发数据收集")
    return [
        Send("financial", state),
        Send("news", state),
        Send("report", state),
    ]


def finalize_node(state: FinanceState) -> dict:
    """
    收尾节点：根据合规结果决定最终状态

    Args:
        state: 当前状态

    Returns:
        要更新的字段
    """
    cr = state.get("compliance_result", {})
    passed = cr.get("passed", False)

    if passed:
        logger.info("[graph] 流水线完成（合规通过）")
        return {
            "status": "completed",
            "error": "",
            "messages": [{"role": "system", "content": "流水线完成"}]
        }
    else:
        issues = cr.get("issues", [])
        logger.warning(f"[graph] 流水线完成（合规不通过）：{issues}")
        return {
            "status": "failed",
            "error": f"合规审查不通过：{'; '.join(issues)}",
            "messages": [{"role": "system", "content": f"合规不通过：{issues}"}]
        }


# ========================================
# 建图
# ========================================

def build_graph() -> StateGraph:
    """
    构建 LangGraph 流水线

    Returns:
        编译后的图（可调用 invoke）

    流程：
    START → precheck → memory_recall → (条件) → planner → 并行(3个) → validator
          → debate → risk → writer → compliance → memory_save → finalize → END
    """
    graph = StateGraph(FinanceState)

    # 创建全局 Database + Tracer 实例
    global _tracer
    _db = Database()
    _tracer = Tracer(db=_db)

    def _recall_wrapper(state):
        return recall_node(state, _db)

    def _save_wrapper(state):
        return save_node(state, _db)

    def _wrap(agent_name, node_func):
        """包装节点函数，记录追踪事件"""
        def wrapped(state):
            trace_id = state.get("task_id", "unknown")
            start = time.time()
            _tracer.log_event(trace_id, agent_name, "start",
                              content=state.get("topic", ""),
                              task_id=trace_id)
            result = node_func(state)
            elapsed = time.time() - start
            _tracer.log_event(trace_id, agent_name, "end",
                              content=f"status={result.get('status', '')}",
                              duration=elapsed,
                              task_id=trace_id)
            return result
        return wrapped

    # 1. 添加所有节点（全部用 _wrap 包裹以记录追踪）
    graph.add_node("precheck", _wrap("precheck", precheck_node))
    graph.add_node("memory_recall", _wrap("memory_recall", _recall_wrapper))
    graph.add_node("planner", _wrap("planner", planner_node))
    graph.add_node("financial", _wrap("financial", financial_analyst_node))
    graph.add_node("news", _wrap("news", news_analyst_node))
    graph.add_node("report", _wrap("report", report_analyst_node))
    graph.add_node("validator", _wrap("validator", validator_node))
    graph.add_node("debate", _wrap("debate", debate_node))
    graph.add_node("risk", _wrap("risk", risk_node))
    graph.add_node("writer", _wrap("writer", report_writer_node))
    graph.add_node("compliance", _wrap("compliance", compliance_node))
    graph.add_node("memory_save", _wrap("memory_save", _save_wrapper))
    graph.add_node("finalize", _wrap("finalize", finalize_node))

    # 2. 入口
    graph.set_entry_point("precheck")

    # 3. precheck → memory_recall → (条件路由)
    graph.add_edge("precheck", "memory_recall")
    graph.add_conditional_edges(
        "memory_recall",
        route_after_precheck,
        {
            "planner": "planner",
            "end": END,
        }
    )

    # 4. planner 后并行派发（fan-out）
    graph.add_conditional_edges(
        "planner",
        route_to_parallel,
        ["financial", "news", "report"]
    )

    # 5. 三个并行节点汇聚到 validator（fan-in）
    graph.add_edge("financial", "validator")
    graph.add_edge("news", "validator")
    graph.add_edge("report", "validator")

    # 6. 后续串行
    graph.add_edge("validator", "debate")
    graph.add_edge("debate", "risk")
    graph.add_edge("risk", "writer")
    graph.add_edge("writer", "compliance")
    graph.add_edge("compliance", "memory_save")
    graph.add_edge("memory_save", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


# 全局编译好的图
app = build_graph()


# ========================================
# 便捷函数
# ========================================

def run_pipeline(task_id: str, user_id: str, user_role: str, topic: str) -> dict:
    """
    运行完整流水线

    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        user_role: 用户角色
        topic: 股票代码或行业

    Returns:
        最终状态
    """
    from src.state import create_initial_state
    if _tracer is not None:
        _tracer.start_trace(task_id, task_id=task_id, topic=topic)
    initial = create_initial_state(task_id, user_id, user_role, topic)
    logger.info(f"[graph] 启动流水线：{task_id} / {topic}")
    result = app.invoke(initial)
    logger.info(f"[graph] 流水线结束：{result.get('status')}")
    return result


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    import json

    result = run_pipeline("t1", "u1", "user", "AAPL")
    print("=" * 60)
    print("最终状态:", result.get("status"))
    print("公司类型:", result.get("company_type"))
    print("子任务数:", len(result.get("subtasks", [])))
    print("新闻数:", len(result.get("news_data", [])))
    print("研报数:", len(result.get("report_data", [])))
    print("辩论轮次:", result.get("debate_rounds"))
    print("风险等级:", result.get("risk_assessment", {}).get("risk_level"))
    print("合规通过:", result.get("compliance_result", {}).get("passed"))
    print("报告长度:", len(result.get("final_report", "")) or len(result.get("draft_report", "")))
    print("总 tokens:", result.get("total_tokens"))
    print("总成本:", result.get("total_cost"))
    print("错误:", result.get("error"))
    print("=" * 60)
