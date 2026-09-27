from typing import TypedDict, Annotated
import operator
import time


def _take_max(a: int, b: int) -> int:
    """取较大值，用于并行节点同时更新 current_step 时合并"""
    return max(a, b)


def _keep_status(a: str, b: str) -> str:
    """状态合并：failed/rejected 优先；否则取最新值（支持串行节点的 completed 覆盖 running）"""
    severe = {"failed", "rejected"}
    if a in severe:
        return a
    if b in severe:
        return b
    return b  # 非严重状态取最新写入值


class FinanceState(TypedDict):
    # 【基础字段】
    task_id: str          # 任务唯一 ID（UUID）
    user_id: str          # 用户 ID
    user_role: str        # 用户角色：guest / user / admin
    topic: str            # 股票代码或行业名称
    company_type: str     # 公司类型：科技 / 银行 / 消费 / 医药 / 其他

    # 【任务规划】
    subtasks: list        # 子任务列表，每项 {id, task, status}
    current_step: Annotated[int, _take_max]  # 当前步骤（并行节点取 max）
    total_steps: int      # 总步骤数

    # 【数据收集】
    financial_data: dict  # 财报数据（营收、利润、负债等）
    news_data: list       # 新闻列表，每项 {title, source, date, content, sentiment}
    report_data: list     # 研报列表，每项 {title, broker, date, summary}
    market_data: dict     # 市场数据（股价、PE、PB、成交量）

    # 【验证】
    validation_result: dict  # 验证结果
    # consistency_score: float  一致性评分 0-1
    # conflicts: list           矛盾列表
    # confidence: float         置信度 0-1

    # 【辩论】
    debate_records: list  # 辩论记录，每项 {round, side, content}
    debate_rounds: int    # 辩论轮次

    # 【风控】
    risk_assessment: dict # 风险评估
    # risk_level: str       风险等级：低 / 中 / 高
    # risk_factors: list    风险因素列表
    # risk_warning: str     风险提示文本

    # 【报告】
    draft_report: str         # 初稿
    final_report: str         # 终稿
    report_references: list   # 引用来源，每项 {source, url, snippet}

    # 【合规】
    compliance_result: dict   # 合规检查
    # passed: bool
    # issues: list

    # 【消息与状态】
    messages: Annotated[list, operator.add]  # 消息历史，自动追加
    status: Annotated[str, _keep_status]  # pending / running / completed / failed / rejected（并行取最严重）
    error: str                # 错误信息，无错误为空字符串

    # 【成本与时间】
    start_time: float         # 开始时间戳
    total_tokens: int         # 总 token 数
    total_cost: float         # 总成本（元）


def create_initial_state(task_id: str, user_id: str, user_role: str, topic: str) -> FinanceState:
    """创建初始状态"""
    return FinanceState(
        task_id=task_id,
        user_id=user_id,
        user_role=user_role,
        topic=topic,
        company_type="",
        subtasks=[],
        current_step=0,
        total_steps=0,
        financial_data={},
        news_data=[],
        report_data=[],
        market_data={},
        validation_result={},
        debate_records=[],
        debate_rounds=0,
        risk_assessment={},
        draft_report="",
        final_report="",
        report_references=[],
        compliance_result={},
        messages=[],
        status="pending",
        error="",
        start_time=time.time(),
        total_tokens=0,
        total_cost=0.0,
    )
