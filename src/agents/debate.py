import json
import time
import logging
from typing import Dict, Tuple

from src.state import FinanceState
from src.config import settings
import src.optimization.model_router as router_module

logger = logging.getLogger(__name__)


# 最大辩论轮数（2 轮 = 双方各 1 次发言 + 1 次反驳，辩论充分性足够且降本）
MAX_DEBATE_ROUNDS = 2
# 重复检测阈值：本轮与上一轮观点 Jaccard 相似度超过此值则认为空转，提前终止
REPEAT_THRESHOLD = 0.6


def _jaccard_similarity(a: str, b: str) -> float:
    """计算两段文本的 Jaccard 相似度（按字符 bigram）"""
    if not a or not b:
        return 0.0
    def bigrams(s):
        return set(s[i:i+2] for i in range(len(s)-1))
    sa, sb = bigrams(a), bigrams(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _is_repeat(records: list, side: str, new_content: str, threshold: float = REPEAT_THRESHOLD) -> bool:
    """检测本轮观点是否与上一轮同方观点高度重复"""
    prev = [r for r in records if r.get("side") == side]
    if not prev:
        return False
    last = prev[-1].get("content", "")
    sim = _jaccard_similarity(last, new_content)
    return sim >= threshold


# ========================================
# Prompt 模板
# ========================================

SUMMARIZE_PROMPT = """你是一个金融数据整理员。请把以下资料压缩成不超过 200 字的研究摘要。

【分析标的】
{target}

【财务数据】
{financial}

【新闻情绪】
{news}

【研报观点】
{reports}

要求：
1. 保留所有具体数字（营收、利润、净利率、目标价）
2. 保留所有评级（买入/中性/卖出）
3. 保留所有新闻标题的核心事件
4. 用紧凑格式，不要解释
5. 只输出摘要，不要其他内容"""

BULL_PROMPT = """你是一个乐观的多头研究员，正在为「{target}」的投资价值进行辩护。

以下是收集到的资料：

【研究摘要】
{summary}

【历史辩论】
{history}

请从多头的角度，给出你的看多论据（3-5 条），要具体、有数据支撑。
如果对方（空头）已经发言，请针对性反驳。

注意：股票代码与公司名称的对应关系已确认，无需质疑。

只输出你的论据文本，不要其他格式。"""

BEAR_PROMPT = """你是一个谨慎的空头研究员，正在对「{target}」的投资风险进行剖析。

以下是收集到的资料：

【研究摘要】
{summary}

【历史辩论】
{history}

请从空头的角度，给出你的看空论据（3-5 条），要具体、有数据支撑。
如果对方（多头）已经发言，请针对性反驳。

注意：股票代码与公司名称的对应关系已确认，无需质疑。

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

def summarize_context(context: Dict[str, str], target: str) -> Tuple[str, int, float]:
    """
    把财务/新闻/研报压缩成 200 字摘要

    Args:
        context: _format_context 返回的 {"financial": ..., "news": ..., "reports": ...}
        target: 标的名称（如 "宇树科技（688836）"）

    Returns:
        (摘要文本, tokens, cost)
        失败时降级：直接返回原始拼接
    """
    prompt = SUMMARIZE_PROMPT.format(
        target=target,
        financial=context["financial"],
        news=context["news"],
        reports=context["reports"],
    )
    try:
        summary, tokens, cost = router_module.call_llm(
            prompt, tier="cheap", temperature=0.3
        )
        return summary, tokens, cost
    except Exception as e:
        logger.warning(f"[debate] 总结失败，降级用原始上下文：{e}")
        fallback = f"{context['financial']}\n{context['news']}\n{context['reports']}"
        return fallback, 0, 0.0


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
    symbol = state.get("symbol", topic)
    company_name = state.get("company_name") or topic
    target = f"{company_name}（{symbol}）"
    logger.info(f"[debate] 开始多空辩论：{target}")

    total_tokens = 0
    total_cost = 0.0

    try:
        # 1. 准备资料
        context = _format_context(state)
        # 先总结上下文（降本）
        summary, sum_tokens, sum_cost = summarize_context(context, target)
        total_tokens += sum_tokens
        total_cost += sum_cost
        logger.info(f"[debate] 上下文已总结（{sum_tokens} tokens）")
        records = []

        # 2. 轮流发言（最多 MAX_DEBATE_ROUNDS 轮，检测到空转则提前终止）
        stop_early = False
        for round_num in range(1, MAX_DEBATE_ROUNDS + 1):
            if stop_early:
                break
            # 多头发言
            history = _format_history(records)
            bull_prompt = BULL_PROMPT.format(
                target=target,
                summary=summary,
                history=history,
            )
            bull_content, t1, c1 = router_module.call_llm(bull_prompt, tier="expensive", temperature=0.7)
            total_tokens += t1
            total_cost += c1
            # 重复检测：与上一轮多头观点高度相似则空转，提前进裁决
            if _is_repeat(records, "bull", bull_content):
                logger.info(f"[debate] 第 {round_num} 轮多头观点重复，提前终止辩论")
                stop_early = True
                continue
            records.append({
                "round": round_num,
                "side": "bull",
                "content": bull_content,
            })
            logger.info(f"[debate] 第 {round_num} 轮多头发言完成（{t1} tokens）")

            # 空头发言
            history = _format_history(records)
            bear_prompt = BEAR_PROMPT.format(
                target=target,
                summary=summary,
                history=history,
            )
            bear_content, t2, c2 = router_module.call_llm(bear_prompt, tier="expensive", temperature=0.7)
            total_tokens += t2
            total_cost += c2
            if _is_repeat(records, "bear", bear_content):
                logger.info(f"[debate] 第 {round_num} 轮空头观点重复，提前终止辩论")
                stop_early = True
                continue
            records.append({
                "round": round_num,
                "side": "bear",
                "content": bear_content,
            })
            logger.info(f"[debate] 第 {round_num} 轮空头发言完成（{t2} tokens）")

        actual_rounds = max((r.get("round", 0) for r in records if r.get("side") != "judge"), default=0)

        # 3. 主持人裁决
        judge_prompt = JUDGE_PROMPT.format(debate=_format_history(records))
        judge_content, t3, c3 = router_module.call_llm(judge_prompt, tier="expensive", temperature=0.7)
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
            "debate_rounds": actual_rounds,
            "current_step": state.get("current_step", 0) + 1,
            "status": "running",
            "total_tokens": state.get("total_tokens", 0) + total_tokens,
            "total_cost": state.get("total_cost", 0.0) + total_cost,
            "messages": [
                {"role": "system", "content": f"多空辩论完成：{actual_rounds} 轮，裁决 {verdict.get('stance')}"}
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
