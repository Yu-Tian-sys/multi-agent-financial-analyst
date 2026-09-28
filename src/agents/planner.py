import json
import logging
import time
from typing import Dict, List

from src.state import FinanceState
from src.config import settings
import src.optimization.model_router as router_module

logger = logging.getLogger(__name__)


# ========================================
# 公司类型 → 子任务模板
# ========================================
TASK_TEMPLATES = {
    "科技": [
        "分析研发投入和专利情况",
        "分析用户增长和留存率",
        "分析毛利率和盈利能力",
        "分析新产品和市场前景",
    ],
    "银行": [
        "分析不良贷款率和拨备覆盖率",
        "分析净息差和利息收入",
        "分析资本充足率",
        "分析监管政策影响",
    ],
    "消费": [
        "分析品牌力和市场份额",
        "分析渠道布局和销售网络",
        "分析复购率和客户忠诚度",
        "分析成本结构和毛利率",
    ],
    "医药": [
        "分析研发管线和新药进展",
        "分析专利到期风险",
        "分析医保政策和集采影响",
        "分析销售费用和研发费用",
    ],
    "其他": [
        "分析财务健康状况",
        "分析行业地位和竞争格局",
        "分析近期重大事件",
        "分析风险和机会",
    ],
}

# 公司类型识别 prompt
CLASSIFY_PROMPT = """判断以下公司属于哪个类型。只输出一个词：科技 / 银行 / 消费 / 医药 / 其他。

公司或行业：{topic}

只输出类型，不要解释。"""

# 子任务规划 prompt
PLAN_PROMPT = """你是一个金融研究任务规划器。

任务：研究「{topic}」（类型：{company_type}）

请生成 3-5 个子任务，覆盖：财务数据、市场表现、行业趋势、风险因素。

只输出 JSON 数组，每项格式：{{"id": 1, "task": "任务描述", "status": "pending"}}

示例：
[
    {{"id": 1, "task": "分析研发投入和专利情况", "status": "pending"}},
    {{"id": 2, "task": "分析用户增长和留存率", "status": "pending"}}
]

只输出 JSON，不要其他内容。"""


# ========================================
# 公司类型识别
# ========================================

def classify_company(topic: str) -> tuple:
    """
    识别公司类型

    Args:
        topic: 公司名或行业名

    Returns:
        (公司类型, tokens, cost)
    """
    prompt = CLASSIFY_PROMPT.format(topic=topic)
    content, tokens, cost = router_module.call_llm(prompt, tier="cheap", temperature=0.3, max_retries=2)
    content = content.strip()

    # 校验返回值
    for valid in ["科技", "银行", "消费", "医药"]:
        if valid in content:
            return valid, tokens, cost

    return "其他", tokens, cost


# ========================================
# 子任务规划
# ========================================

def generate_subtasks(topic: str, company_type: str) -> tuple:
    """
    生成子任务列表

    Args:
        topic: 公司名或行业名
        company_type: 公司类型

    Returns:
        (子任务列表, tokens, cost)
    """
    prompt = PLAN_PROMPT.format(topic=topic, company_type=company_type)

    for attempt in range(3):
        content, tokens, cost = router_module.call_llm(prompt, tier="cheap", temperature=0.3, max_retries=0)

        # 清理 markdown 代码块
        text = content.replace("```json", "").replace("```", "").strip()

        try:
            subtasks = json.loads(text)
            # 校验格式
            if isinstance(subtasks, list) and all("task" in s for s in subtasks):
                # 补全 id 和 status
                for i, s in enumerate(subtasks):
                    s["id"] = i + 1
                    s.setdefault("status", "pending")
                return subtasks, tokens, cost
        except json.JSONDecodeError:
            logger.warning(f"[planner] JSON 解析失败（第 {attempt+1} 次）：{text[:100]}")

    # 降级：用模板
    logger.warning(f"[planner] JSON 解析失败 3 次，降级用模板")
    template = TASK_TEMPLATES.get(company_type, TASK_TEMPLATES["其他"])
    subtasks = [
        {"id": i + 1, "task": t, "status": "pending"}
        for i, t in enumerate(template)
    ]
    return subtasks, 0, 0.0


# ========================================
# LangGraph 节点
# ========================================

def planner_node(state: FinanceState) -> dict:
    """
    任务规划 Agent（LangGraph 节点）

    流程：
    1. 识别公司类型
    2. 根据类型生成子任务列表
    3. 更新 state

    Args:
        state: 当前状态

    Returns:
        要更新的字段
    """
    topic = state["topic"]
    logger.info(f"[planner] 开始规划：{topic}")

    total_tokens = 0
    total_cost = 0.0

    try:
        # 1. 识别公司类型
        company_type, t1, c1 = classify_company(topic)
        total_tokens += t1
        total_cost += c1
        logger.info(f"[planner] 公司类型：{company_type}")

        # 2. 生成子任务
        subtasks, t2, c2 = generate_subtasks(topic, company_type)
        total_tokens += t2
        total_cost += c2
        logger.info(f"[planner] 生成 {len(subtasks)} 个子任务")

        return {
            "company_type": company_type,
            "subtasks": subtasks,
            "current_step": 1,
            "total_steps": len(subtasks),
            "status": "running",
            "total_tokens": state.get("total_tokens", 0) + total_tokens,
            "total_cost": state.get("total_cost", 0.0) + total_cost,
            "messages": [
                {"role": "system", "content": f"规划完成：{company_type} 类型，{len(subtasks)} 个子任务"}
            ]
        }

    except Exception as e:
        logger.error(f"[planner] 规划失败：{e}")
        return {
            "status": "failed",
            "error": f"任务规划失败：{e}",
            "messages": [{"role": "system", "content": f"规划失败：{e}"}]
        }


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    from src.state import create_initial_state

    state = create_initial_state("t1", "u1", "user", "AAPL")
    result = planner_node(state)
    print("状态:", result["status"])
    print("公司类型:", result.get("company_type"))
    print("子任务数:", len(result.get("subtasks", [])))
    print("tokens:", result.get("total_tokens"))
    print("cost:", result.get("total_cost"))
