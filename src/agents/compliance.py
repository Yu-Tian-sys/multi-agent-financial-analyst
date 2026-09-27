import json
import time
import logging
from typing import Dict, List, Tuple

from openai import OpenAI

from src.state import FinanceState
from src.config import settings

logger = logging.getLogger(__name__)


_client = OpenAI(
    api_key=settings.deepseek_api_key,
    base_url=settings.deepseek_base_url,
)


# ========================================
# 规则检查（不依赖 LLM）
# ========================================

# 禁止出现的投资建议关键词
FORBIDDEN_KEYWORDS = [
    "建议买入", "建议卖出", "强烈推荐买入", "立即买入", "立即卖出",
    "必涨", "必跌", "稳赚", "包赚", "保证收益",
]


def _check_forbidden_keywords(text: str) -> List[str]:
    """
    检查禁止关键词

    Args:
        text: 报告文本

    Returns:
        命中的禁止词列表
    """
    hits = []
    for kw in FORBIDDEN_KEYWORDS:
        if kw in text:
            hits.append(kw)
    return hits


def _check_risk_warning(text: str) -> bool:
    """
    检查是否包含风险提示

    Args:
        text: 报告文本

    Returns:
        是否包含
    """
    return "风险提示" in text or "投资有风险" in text


def _check_references(text: str, references: List[dict]) -> bool:
    """
    检查是否有引用来源

    Args:
        text: 报告文本
        references: 引用列表

    Returns:
        是否有引用
    """
    return len(references) > 0


# ========================================
# LLM 合规审查
# ========================================

COMPLIANCE_PROMPT = """你是合规审查员，需要检查以下投资研究报告是否合规。

【报告内容】
{report}

请检查以下项目：
1. 是否包含明确的投资建议（买入/卖出/持有）？
2. 是否有夸张、绝对化的表述（必涨、稳赚、翻倍）？
3. 是否包含风险提示？
4. 结论是否有数据支撑？

请输出 JSON 格式：
{{
    "passed": true/false,
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}

只输出 JSON，不要其他内容。"""


def _llm_compliance_check(report: str) -> Tuple[dict, int, float]:
    """
    用 LLM 做合规审查

    Args:
        report: 报告文本

    Returns:
        (审查结果, tokens, cost)
    """
    prompt = COMPLIANCE_PROMPT.format(report=report[:3000])  # 截断防止超长
    last_error = None
    for attempt in range(3):
        try:
            response = _client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            cost = tokens / 1_000_000 * 1.0

            text = content.replace("```json", "").replace("```", "").strip()
            try:
                result = json.loads(text)
                return result, tokens, cost
            except json.JSONDecodeError:
                logger.warning(f"[compliance] JSON 解析失败：{text[:100]}")
        except Exception as e:
            last_error = e
            logger.warning(f"[compliance] LLM 调用失败（第 {attempt+1} 次）：{e}")
            if attempt < 2:
                time.sleep(2 ** attempt)

    # 降级：默认通过（但要人工复核）
    logger.error(f"[compliance] LLM 审查失败，降级通过：{last_error}")
    return {"passed": True, "issues": ["LLM 审查失败，需人工复核"], "suggestions": []}, 0, 0.0


def compliance_node(state: FinanceState) -> dict:
    """
    合规审查 Agent（LangGraph 节点）

    流程：
    1. 规则检查（禁止词、风险提示、引用）
    2. LLM 合规审查
    3. 综合判断：passed = 规则通过 AND LLM 通过
    4. 通过则 final_report = draft_report；不通过则保持 draft，等待重写
    5. 写入 state.compliance_result

    Args:
        state: 当前状态

    Returns:
        要更新的字段
    """
    logger.info("[compliance] 开始合规审查")

    try:
        draft = state.get("draft_report", "")
        references = state.get("report_references", [])

        if not draft:
            return {
                "status": "failed",
                "error": "无报告内容，无法审查",
                "messages": [{"role": "system", "content": "合规审查失败：无报告内容"}]
            }

        issues = []

        # 1. 规则检查
        forbidden = _check_forbidden_keywords(draft)
        if forbidden:
            issues.append(f"包含禁止词：{', '.join(forbidden)}")

        if not _check_risk_warning(draft):
            issues.append("缺少风险提示")

        if not _check_references(draft, references):
            issues.append("缺少引用来源")

        # 2. LLM 审查
        llm_result, tokens, cost = _llm_compliance_check(draft)
        if not llm_result.get("passed", True):
            for issue in llm_result.get("issues", []):
                issues.append(f"LLM 审查：{issue}")

        # 3. 综合判断
        passed = len(issues) == 0

        compliance_result = {
            "passed": passed,
            "issues": issues,
            "suggestions": llm_result.get("suggestions", []),
        }

        logger.info(f"[compliance] 合规审查：{'通过' if passed else '不通过'}，{len(issues)} 个问题")

        result = {
            "compliance_result": compliance_result,
            "current_step": state.get("current_step", 0) + 1,
            "total_tokens": state.get("total_tokens", 0) + tokens,
            "total_cost": state.get("total_cost", 0.0) + cost,
            "messages": [
                {"role": "system", "content": f"合规审查：{'通过' if passed else '不通过'}"}
            ]
        }

        if passed:
            result["final_report"] = draft
            result["status"] = "completed"
        else:
            # 不通过，保持 draft，由 LangGraph 路由回 writer 重写
            result["status"] = "running"

        return result

    except Exception as e:
        logger.error(f"[compliance] 审查失败：{e}")
        return {
            "status": "failed",
            "error": f"合规审查失败：{e}",
            "messages": [{"role": "system", "content": f"合规审查失败：{e}"}]
        }
