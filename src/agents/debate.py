import json
import time
import logging
from typing import Dict, Tuple

from src.state import FinanceState
from src.config import settings
import src.optimization.model_router as router_module

logger = logging.getLogger(__name__)


# 最大辩论轮次
MAX_DEBATE_ROUNDS = 2


# ========================================
# Prompt 模板
# ========================================

BULL_PROMPT = """你是一个乐观的多头研究员，正在为「{topic}」的投资价值进行辩护。

以下是收集到的资料：

【财务数据】
{financial}

【新闻情绪】
{news}

【研报观点】
{reports}

【历史辩论】
{history}

请从多头的角度，给出你的看多论据（3-5 条），要具体、有数据支撑。
如果对方（空头）已经发言，请针对性反驳。

只输出你的论据文本，不要其他格式。"""

BEAR_PROMPT = """你是一个谨慎的空头研究员，正在对「{topic}」的投资风险进行剖析。

以下是收集到的资料：

【财务数据】
{financial}

【新闻情绪】
{news}

【研报观点】
{reports}

【历史辩论】
{history}

请从空头的角度，给出你的看空论据（3-5 条），要具体、有数据支撑。
如果对方（多头）已经发言，请针对性反驳。

只输出你的论据文本，不要其他格式。"""

JUDGE_PROMPT = """你是一个中立的辩论主持人，需要综合多空双方的观点，给出最终判断。

【辩论记录】
{debate}

请输出 JSON 格式的裁决，包含：
{{
    "stance": "看多 / 看空 / 中性",
    "confidence": 0.0-1.0 之间的置信度,
    "bull_points": ["多头核心论据1", "多头核心论据2"],
    "bear_points": ["空头核心论据1", "空头核心论据2"],
    "conclusion": "综合判断的结论（100字以内）"
}}

只输出 JSON，不要其他内容。"""


# ========================================
# 资料格式化
# ========================================

def _format_context(state: FinanceState) -> Dict[str, str]:
    """
    把 state 里的资料格式化成文本

    Args:
        state: 当前状态

    Returns:
        {"financial": ..., "news": ..., "reports": ...}
    """
    # 财务
    fd = state.get("financial_data", {})
    financial = json.dumps(fd.get("raw_metrics", {}), ensure_ascii=False) if fd else "无"
    ratios = fd.get("ratios", {})
    if ratios:
        financial += f"\n比率：{json.dumps(ratios, ensure_ascii=False)}"

    # 新闻
    news_list = state.get("news_data", [])
    if news_list:
        news = "\n".join(f"- [{n.get('sentiment', '')}] {n.get('title', '')}"
                         for n in news_list[:5])
    else:
        news = "无"

    # 研报
    reports_list = state.get("report_data", [])
    if reports_list:
        reports = "\n".join(f"- [{r.get('rating', '')}] {r.get('title', '')}"
                            for r in reports_list[:5])
    else:
        reports = "无"

    return {"financial": financial, "news": news, "reports": reports}


def _format_history(records: list) -> str:
    """
    格式化辩论历史

    Args:
        records: 辩论记录列表

    Returns:
        格式化的历史文本
    """
    if not records:
        return "（暂无）"
    lines = []
    for r in records:
        side = "多头" if r.get("side") == "bull" else "空头"
        lines.append(f"[{side}第{r.get('round', 0)}轮] {r.get('content', '')}")
    return "\n".join(lines)


# ========================================
# 辩论主体
# ========================================

def debate_node(state: FinanceState) -> dict:
    """
    多空辩论 Agent（LangGraph 节点）

    流程：
    1. 准备资料
    2. 多空双方轮流发言，最多 3 轮
    3. 主持人综合裁决
    4. 写入 state.debate_records + state.debate_rounds

    Args:
        state: 当前状态

    Returns:
        要更新的字段
    """
    topic = state["topic"]
    logger.info(f"[debate] 开始多空辩论：{topic}")

    total_tokens = 0
    total_cost = 0.0

    try:
        # 1. 准备资料
        context = _format_context(state)
        records = []

        # 2. 轮流发言
        for round_num in range(1, MAX_DEBATE_ROUNDS + 1):
            # 多头发言
            history = _format_history(records)
            bull_prompt = BULL_PROMPT.format(
                topic=topic,
                financial=context["financial"],
                news=context["news"],
                reports=context["reports"],
                history=history,
            )
            bull_content, t1, c1 = router_module.call_llm(bull_prompt, tier="cheap", temperature=0.7)
            total_tokens += t1
            total_cost += c1
            records.append({
                "round": round_num,
                "side": "bull",
                "content": bull_content,
            })
            logger.info(f"[debate] 第 {round_num} 轮多头发言完成（{t1} tokens）")

            # 空头发言
            history = _format_history(records)
            bear_prompt = BEAR_PROMPT.format(
                topic=topic,
                financial=context["financial"],
                news=context["news"],
                reports=context["reports"],
                history=history,
            )
            bear_content, t2, c2 = router_module.call_llm(bear_prompt, tier="cheap", temperature=0.7)
            total_tokens += t2
            total_cost += c2
            records.append({
                "round": round_num,
                "side": "bear",
                "content": bear_content,
            })
            logger.info(f"[debate] 第 {round_num} 轮空头发言完成（{t2} tokens）")

        # 3. 主持人裁决
        judge_prompt = JUDGE_PROMPT.format(debate=_format_history(records))
        judge_content, t3, c3 = router_module.call_llm(judge_prompt, tier="cheap", temperature=0.7)
        total_tokens += t3
        total_cost += c3

        # 解析裁决 JSON
        text = judge_content.replace("```json", "").replace("```", "").strip()
        try:
            verdict = json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"[debate] 裁决 JSON 解析失败：{text[:100]}")
            verdict = {
                "stance": "中性",
                "confidence": 0.5,
                "bull_points": [],
                "bear_points": [],
                "conclusion": judge_content[:200],
            }

        # 把裁决也存进 records
        records.append({
            "round": MAX_DEBATE_ROUNDS + 1,
            "side": "judge",
            "content": json.dumps(verdict, ensure_ascii=False),
        })

        logger.info(f"[debate] 裁决：{verdict.get('stance')}，置信度 {verdict.get('confidence')}")

        return {
            "debate_records": records,
            "debate_rounds": MAX_DEBATE_ROUNDS,
            "current_step": state.get("current_step", 0) + 1,
            "status": "running",
            "total_tokens": state.get("total_tokens", 0) + total_tokens,
            "total_cost": state.get("total_cost", 0.0) + total_cost,
            "messages": [
                {"role": "system", "content": f"多空辩论完成：{MAX_DEBATE_ROUNDS} 轮，裁决 {verdict.get('stance')}"}
            ]
        }

    except Exception as e:
        logger.error(f"[debate] 辩论失败：{e}")
        return {
            "status": "failed",
            "error": f"多空辩论失败：{e}",
            "messages": [{"role": "system", "content": f"多空辩论失败：{e}"}]
        }


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    from src.state import create_initial_state

    state = create_initial_state("t1", "u1", "user", "AAPL")
    state["financial_data"] = {
        "raw_metrics": {"revenue": "3832亿", "profit": "970亿，同比增长5%"},
        "ratios": {"net_margin": 0.2531, "roe": 0.15},
    }
    state["news_data"] = [
        {"title": "销量超预期", "sentiment": "positive"},
        {"title": "面临调查", "sentiment": "negative"},
    ]
    state["report_data"] = [
        {"title": "维持买入", "rating": "买入", "target_price": "250美元"},
    ]

    result = debate_node(state)
    print("状态:", result["status"])
    print("辩论轮次:", result.get("debate_rounds"))
    print("记录数:", len(result.get("debate_records", [])))
    print("tokens:", result.get("total_tokens"))
