import json
import time
import logging
from typing import Dict, Tuple, List

from src.state import FinanceState
from src.config import settings
import src.optimization.model_router as router_module

logger = logging.getLogger(__name__)


REPORT_PROMPT = """你是一个专业的金融分析师，需要撰写一份投资研究报告。

【标的信息】
{company_name}（{symbol}，{company_type}）

注意：上述股票代码与公司名称的对应关系已确认，请勿在报告中质疑两者的关联性。

【财务数据】
{financial}

【同比增速】
{yoy}

【估值指标】
{valuation}

【新闻情绪】
{news}

【研报观点】
{reports}

【多空辩论裁决】
{debate}

【风险评估】
风险等级：{risk_level}
风险因素：
{risk_factors}

请撰写一份结构化的投资研究报告，包含以下部分：

# {company_name}（{symbol}）投资研究报告

## 一、公司概况
（一段话介绍）

## 二、财务分析
（引用具体数据，必须包含同比增速分析）

## 三、估值分析
（基于 PE/PB/市值等指标，分析当前估值水平）

## 四、市场情绪
（基于新闻和研报）

## 五、多空观点
### 多头观点
### 空头观点

## 六、风险提示
（必须引用上面的风险因素）

## 七、综合结论
（基于辩论裁决给出）

要求：
1. 每个结论必须引用数据来源
2. 不得给出明确的买卖建议
3. 必须包含风险提示
4. 使用 Markdown 格式
5. 不要质疑股票代码与公司名称的对应关系

只输出报告内容。"""


def _call_llm(prompt: str, max_retries: int = 2) -> Tuple[str, int, float]:
    """调用 LLM（走统一 router，报告撰写用 expensive 模型，失败降级 cheap）"""
    return router_module.call_llm(prompt, tier="expensive", temperature=0.5, max_retries=max_retries)


def _build_references(state: FinanceState) -> List[Dict]:
    """
    收集引用来源

    Args:
        state: 当前状态

    Returns:
        引用列表，每项 {source, url, snippet}
    """
    refs = []

    # 财务
    fd = state.get("financial_data", {})
    if fd.get("source"):
        refs.append({
            "source": f"财报（{fd['source']}）",
            "url": "",
            "snippet": f"营收 {fd.get('raw_metrics', {}).get('revenue', 'N/A')}，净利 {fd.get('raw_metrics', {}).get('profit', 'N/A')}"
        })

    # 新闻
    for n in state.get("news_data", [])[:3]:
        refs.append({
            "source": n.get("source", "新闻"),
            "url": "",
            "snippet": n.get("title", "")[:100]
        })

    # 研报
    for r in state.get("report_data", [])[:3]:
        refs.append({
            "source": r.get("broker", "研报"),
            "url": "",
            "snippet": r.get("title", "")[:100]
        })

    return refs


def report_writer_node(state: FinanceState) -> dict:
    """
    报告撰写 Agent（LangGraph 节点）

    流程：
    1. 收集所有上下文（财务、新闻、研报、辩论、风控）
    2. 调 LLM 生成报告
    3. 收集引用来源
    4. 写入 state.draft_report + state.report_references

    Args:
        state: 当前状态

    Returns:
        要更新的字段
    """
    topic = state["topic"]
    logger.info(f"[writer] 开始撰写报告：{topic}")

    try:
        # 1. 准备上下文
        fd = state.get("financial_data", {})
        financial = json.dumps(fd.get("raw_metrics", {}), ensure_ascii=False)
        if fd.get("ratios"):
            financial += f"\n比率：{json.dumps(fd['ratios'], ensure_ascii=False)}"

        # 同比增速
        yoy = json.dumps(fd.get("yoy", {}), ensure_ascii=False) if fd.get("yoy") else "无"

        # 估值指标
        val = fd.get("valuation", {})
        if val:
            val_parts = []
            if "pe_ttm" in val:
                val_parts.append(f"PE(TTM): {val['pe_ttm']}")
            elif "pe" in val:
                val_parts.append(f"PE(静): {val['pe']}")
            if "pb" in val:
                val_parts.append(f"PB: {val['pb']}")
            if "ps_ttm" in val:
                val_parts.append(f"PS(TTM): {val['ps_ttm']}")
            elif "ps" in val:
                val_parts.append(f"PS(静): {val['ps']}")
            if "market_cap" in val:
                mc = val["market_cap"]
                # A 股 AKShare 返回亿元；美股/港股 yfinance 返回原始货币单位
                if mc >= 1e12:
                    val_parts.append(f"总市值: {round(mc/1e12, 2)}万亿")
                elif mc >= 1e8:
                    val_parts.append(f"总市值: {round(mc/1e8, 2)}亿元")
                else:
                    val_parts.append(f"总市值: {round(mc, 2)}亿元")
            valuation = "，".join(val_parts)
        else:
            valuation = "暂无估值数据"

        news = "\n".join(f"- [{n.get('sentiment', '')}] {n.get('title', '')}"
                         for n in state.get("news_data", [])[:5]) or "无"

        reports = "\n".join(f"- [{r.get('rating', '')}] {r.get('title', '')}"
                            for r in state.get("report_data", [])[:5]) or "无"

        # 辩论裁决
        debate_records = state.get("debate_records", [])
        judge_record = next((r for r in debate_records if r.get("side") == "judge"), None)
        debate = judge_record["content"] if judge_record else "无"

        # 风控
        ra = state.get("risk_assessment", {})
        risk_level = ra.get("risk_level", "未知")
        risk_factors = "\n".join(f"- {r}" for r in ra.get("risk_factors", [])) or "无"

        # 2. 生成报告
        company_name = state.get("company_name") or topic
        symbol = state.get("symbol") or topic
        prompt = REPORT_PROMPT.format(
            topic=topic,
            symbol=symbol,
            company_name=company_name,
            company_type=state.get("company_type", "未知"),
            financial=financial,
            yoy=yoy,
            valuation=valuation,
            news=news,
            reports=reports,
            debate=debate,
            risk_level=risk_level,
            risk_factors=risk_factors,
        )
        content, tokens, cost = _call_llm(prompt)
        logger.info(f"[writer] 报告生成完成（{tokens} tokens）")

        # 3. 收集引用
        references = _build_references(state)

        return {
            "draft_report": content,
            "report_references": references,
            "current_step": state.get("current_step", 0) + 1,
            "status": "running",
            "total_tokens": state.get("total_tokens", 0) + tokens,
            "total_cost": state.get("total_cost", 0.0) + cost,
            "messages": [
                {"role": "system", "content": f"报告初稿完成：{len(content)} 字，{len(references)} 个引用"}
            ]
        }

    except Exception as e:
        logger.error(f"[writer] 撰写失败：{e}")
        return {
            "status": "failed",
            "error": f"报告撰写失败：{e}",
            "messages": [{"role": "system", "content": f"报告撰写失败：{e}"}]
        }
